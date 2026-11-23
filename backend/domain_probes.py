from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import lru_cache
from ipaddress import ip_address
import re
from secrets import token_hex
from urllib.parse import urlsplit

import dns.flags
import dns.message
import dns.query
import dns.rcode
import dns.rdatatype
import dns.resolver
import requests

RESOLVERS = {
    "阿里公共 DNS": "https://dns.alidns.com/resolve",
    "腾讯公共 DNS": "https://doh.pub/dns-query",
}
LABEL = re.compile(r"[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?")
HOLD = {"serverhold", "clienthold", "inactive", "pendingdelete", "redemptionperiod"}


def normalize_name(raw: str) -> str:
    name = raw.strip().rstrip(".").encode("idna").decode().lower()
    if len(name) > 253 or not all(LABEL.fullmatch(part) for part in name.split(".")):
        raise ValueError("请输入有效的域名")
    return name


def normalize_value(kind, value):
    if kind in ("CNAME", "NS"):
        return normalize_name(value)
    address = ip_address(value.strip())
    if address.version != (4 if kind == "A" else 6):
        raise ValueError(f"{kind} 记录的 IP 版本不匹配")
    return str(address)


def result(state, detail, *, level=1):
    return {"state": state, "detail": detail, "level": level}


def safe(call, *args):
    try:
        return call(*args)
    except (dns.exception.DNSException, requests.RequestException, OSError, KeyError, ValueError, TypeError) as exc:
        response = exc.response if isinstance(exc, requests.HTTPError) else None
        if response is not None:
            detail = f"查询接口返回 HTTP {response.status_code}"
        elif isinstance(exc, requests.ConnectTimeout):
            detail = "连接查询接口超时"
        elif isinstance(exc, requests.ReadTimeout):
            detail = "等待查询接口响应超时"
        elif isinstance(exc, dns.exception.Timeout):
            detail = "DNS 查询超时"
        else:
            detail = type(exc).__name__
        return result("unknown", detail)


def direct(server, name, kind):
    addresses = dns.resolver.resolve(server, "A", lifetime=3, search=False)
    for record in addresses:
        if ip_address(record.address).is_global:
            query = dns.message.make_query(name, kind, flags=0)
            reply, tcp = dns.query.udp_with_fallback(query, record.address, timeout=3)
            if reply.flags & dns.flags.RA and not tcp:
                reply = dns.query.tcp(query, record.address, timeout=3)
            if not reply.flags & dns.flags.RA:
                return reply
    raise ValueError("没有可验证的公网权威响应")


def get_values(reply, name, kind, *, referral=False):
    sections = reply.answer + reply.authority if referral else reply.answer
    return {
        normalize_value(kind, item.to_text()) for rrset in sections
        if rrset.name.to_text().rstrip(".").lower() == name
        and rrset.rdtype == dns.rdatatype.from_text(kind)
        for item in rrset
    }


def has_soa(reply, zone):
    return bool(reply.flags & dns.flags.AA) and any(
        rrset.rdtype == dns.rdatatype.SOA and rrset.name.to_text().rstrip(".").lower() == zone
        for rrset in reply.authority
    )


def parent_servers(name):
    parent = dns.resolver.zone_for_name(name.split(".", 1)[1], lifetime=5)
    servers = sorted(normalize_name(item.to_text()) for item in dns.resolver.resolve(parent, "NS", lifetime=4))
    # Prefer distinct hosts but bound the number of direct checks per domain.
    return parent.to_text().rstrip(".").lower(), servers[:2]


def parent_sample(server, name, zone):
    reply = direct(server, name, "NS")
    values = get_values(reply, name, "NS", referral=True)
    if reply.rcode() == dns.rcode.NOERROR and values:
        return sorted(values)
    if reply.rcode() in (dns.rcode.NXDOMAIN, dns.rcode.NOERROR) and has_soa(reply, zone):
        return []
    raise ValueError("父区响应无法确认委派")


def query_parent(name):
    zone, servers = parent_servers(name)
    with ThreadPoolExecutor(max_workers=2) as pool:
        return list(zip(servers, pool.map(lambda host: safe(parent_sample, host, name, zone), servers)))


def discover_ns(name):
    samples = query_parent(name)
    sets = [values for _, values in samples if isinstance(values, list)]
    if not sets or not sets[0] or any(values != sets[0] for values in sets):
        raise ValueError("未取得一致的公开 NS，请手动填写预期值")
    return sets[0]


def delegation(name, expected):
    samples = query_parent(name)
    details = []
    normal = changed = 0
    for server, values in samples:
        if isinstance(values, dict):
            details.append(f"{server} {values['detail']}")
            continue
        matches = set(values) == set(expected)
        normal += matches
        changed += not matches
        details.append(f"{server} → {', '.join(values) if values else '未公布委派'}")
    summary = "；".join([*details, "预期 " + ", ".join(expected)])
    if changed:
        # Two authorities in agreement confirm a change immediately. A single
        # contradictory answer must be seen again before it pages the team.
        return result("bad", summary, level=2) | {"immediate": changed >= 2}
    if not normal:
        return result("unknown", f"未取得父区有效响应；{summary}")
    # A timeout is not a conflicting answer from another parent server.
    return result("ok", f"NS 与预期一致（{normal}/{len(samples)} 台返回有效结果）；{summary}")


def record_authority(server, zone, name, kind, expected):
    reply = direct(server, name, kind)
    code = reply.rcode()
    if not reply.flags & dns.flags.AA:
        return result("unknown", "未收到权威回答")
    values = get_values(reply, name, kind)
    if code == dns.rcode.NOERROR and values == expected:
        return result("ok", ", ".join(sorted(values)))
    if values or has_soa(reply, zone) or (code == dns.rcode.NOERROR and reply.answer):
        return result("bad", ", ".join(sorted(values)) or "记录不存在")
    return result("unknown", dns.rcode.to_text(code))


def record_recursive(url, name, kind, expected):
    def query(record_type):
        response = requests.get(
            url, params={"name": name, "type": record_type},
            headers={"Accept": "application/dns-json"}, timeout=4,
        )
        response.raise_for_status()
        return response.json()

    data = query("A" if kind == "CNAME" else kind)
    code = data["Status"]
    if code in (dns.rcode.NXDOMAIN, dns.rcode.REFUSED, dns.rcode.SERVFAIL):
        return result("bad", dns.rcode.to_text(code))
    if code != dns.rcode.NOERROR:
        return result("unknown", f"DNS {code}")
    records = data.get("Answer", [])
    values = {
        normalize_value(kind, item["data"]) for item in records
        if item["type"] == dns.rdatatype.from_text(kind) and normalize_name(item["name"]) == name
    }
    if values != expected:
        return result("bad", ", ".join(sorted(values)) or "记录不存在")
    if kind == "CNAME":
        mapping = {
            normalize_name(item["name"]): normalize_name(item["data"])
            for item in records if item["type"] == dns.rdatatype.CNAME
        }
        if not any(item["type"] == dns.rdatatype.A for item in records):
            ipv6 = query("AAAA")
            if ipv6["Status"] == dns.rcode.NOERROR:
                records += ipv6.get("Answer", [])
        ips = {
            normalize_name(item["name"]) for item in records
            if item["type"] in (dns.rdatatype.A, dns.rdatatype.AAAA)
        }
        visited = set()
        current = name
        while current in mapping and current not in visited:
            visited.add(current)
            current = mapping[current]
        if current not in ips:
            return result("bad", "CNAME 目标没有返回 IP 地址")
    return result("ok", ", ".join(sorted(values)))


def summarize(samples, label):
    detail = "；".join(f"{name} {value['detail']}" for name, value in samples)
    failures = sum(value["state"] == "bad" for _, value in samples)
    incomplete = any(value["state"] == "unknown" for _, value in samples)
    state = "bad" if failures else "unknown" if incomplete else "ok"
    level = 2 if failures and failures == len(samples) else 1
    return result(state, f"{label} · {detail}", level=level) | {"incomplete": incomplete}


def dns_checks(name, expected_ns, records):
    observations = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        delegation_job = pool.submit(safe, delegation, name, expected_ns)
        record_jobs = []
        for idx, record in enumerate(records):
            owner = record["name"]
            label = f"{owner} {record['kind']}"
            if owner.startswith("*."):
                owner = f"ping-check-{token_hex(6)}.{owner[2:]}"
            kind, expected = record["kind"], set(record["values"])
            authority = [
                (server, pool.submit(safe, record_authority, server, name, owner, kind, expected))
                for server in expected_ns[:3]
            ]
            recursive = [
                (source, pool.submit(safe, record_recursive, url, owner, kind, expected))
                for source, url in RESOLVERS.items()
            ]
            record_jobs += [(f"authority:{idx}", label, authority), (f"recursive:{idx}", label, recursive)]
        observations["delegation"] = delegation_job.result()
        for key, label, jobs in record_jobs:
            observations[key] = summarize([(source, future.result()) for source, future in jobs], label)
    return observations


@lru_cache(maxsize=1)
def rdap_services(day):
    response = requests.get("https://data.iana.org/rdap/dns.json", timeout=(5, 8))
    response.raise_for_status()
    return {
        suffix.lower(): tuple(url for url in endpoints if urlsplit(url).scheme == "https")
        for suffixes, endpoints in response.json()["services"] for suffix in suffixes
    }


def lookup_rdap(name):
    services = rdap_services(datetime.now().date())
    parts = name.split(".")
    urls = next((services[".".join(parts[i:])] for i in range(1, len(parts)) if services.get(".".join(parts[i:]))), ())
    if not urls:
        return result("unsupported", "IANA 未公布此后缀的 RDAP 服务")
    response = requests.get(urls[0].rstrip("/") + "/domain/" + name,
                            headers={"Accept": "application/rdap+json"}, timeout=(8, 9))
    if response.status_code == 404:
        if response.json().get("errorCode") == 404:
            return result("bad", "注册局未找到该域名", level=2) | {"immediate": True}
    response.raise_for_status()
    payload = response.json()
    if payload.get("objectClassName") != "domain" or normalize_name(payload.get("ldhName", "")) != name:
        raise ValueError("RDAP 域名对象不匹配")
    statuses = payload.get("status", [])
    holds = [status for status in statuses if re.sub("[^a-z]", "", status.lower()) in HOLD]
    dates = []
    for event in payload.get("events", []):
        if event.get("eventAction") == "expiration":
            date = datetime.fromisoformat(event["eventDate"].replace("Z", "+00:00"))
            if date.tzinfo:
                dates.append(date.astimezone().replace(tzinfo=None))
    detail = ", ".join(holds or statuses) or "注册记录存在"
    registration = result("bad" if holds else "ok", detail, level=2 if holds else 1)
    return registration | {"immediate": bool(holds), "expiry": min(dates).isoformat() if dates else None}
