from __future__ import annotations

import ipaddress
import logging
import re
import time
from typing import Any

import httpx

from cache import cache_manager

logger = logging.getLogger(__name__)


class IPLocationService:
    """Resolve public IP geolocation with fallback providers and caching."""

    TIMEOUT = 5.0
    CACHE_NAMESPACE = "ip_location"
    SUCCESS_CACHE_TTL = 60 * 60 * 12
    FAILURE_CACHE_TTL = 60 * 5
    DEFAULT_COOLDOWN_SECONDS = 60
    REQUEST_HEADERS = {
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
        "User-Agent": "ping-monitor/2.0",
    }
    BAIDU_REQUEST_HEADERS = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
        "Referer": "https://qifu.baidu.com/?activeId=SEARCH_IP_ADDRESS",
        "Sec-CH-UA": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Windows"',
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/136.0.0.0 Safari/537.36"
        ),
    }

    API_SOURCES = [
        {
            "name": "baidu-qifu",
            "url": "https://qifu.baidu.com/api/v1/ip-portrait/brief-info?ip={ip}",
            "parser": "parse_baidu_qifu",
            "headers": BAIDU_REQUEST_HEADERS,
        },
        {
            "name": "ip2location.io",
            "url": "https://api.ip2location.io/?ip={ip}&format=json",
            "parser": "parse_ip2location",
        },
        {
            "name": "ip-api.com",
            "url": (
                "http://ip-api.com/json/{ip}"
                "?lang=zh-CN&fields=status,message,country,countryCode,regionName,city,isp,org,lat,lon"
            ),
            "parser": "parse_ipapi",
        },
        {
            "name": "ipwho.is",
            "url": "https://ipwho.is/{ip}?lang=zh-CN",
            "parser": "parse_ipwhois",
        },
    ]

    _unknown_texts = {
        "",
        "-",
        "--",
        "n/a",
        "na",
        "null",
        "none",
        "unknown",
        "undefined",
    }
    _country_code_to_zh = {
        "AU": "澳大利亚",
        "CA": "加拿大",
        "CN": "中国",
        "DE": "德国",
        "FR": "法国",
        "GB": "英国",
        "HK": "中国香港",
        "IN": "印度",
        "JP": "日本",
        "KR": "韩国",
        "MO": "中国澳门",
        "RU": "俄罗斯",
        "SG": "新加坡",
        "TW": "中国台湾",
        "US": "美国",
    }
    _country_aliases = {
        "china": "中国",
        "people's republic of china": "中国",
        "peoples republic of china": "中国",
        "united states": "美国",
        "united states of america": "美国",
        "japan": "日本",
        "korea, republic of": "韩国",
        "south korea": "韩国",
        "hong kong": "中国香港",
        "macao": "中国澳门",
        "macau": "中国澳门",
        "taiwan": "中国台湾",
        "singapore": "新加坡",
        "germany": "德国",
        "france": "法国",
        "canada": "加拿大",
        "australia": "澳大利亚",
        "india": "印度",
        "russia": "俄罗斯",
        "united kingdom": "英国",
        "great britain": "英国",
    }
    _china_province_aliases = {
        "北京": "北京市",
        "北京市": "北京市",
        "beijing": "北京市",
        "天津": "天津市",
        "天津市": "天津市",
        "tianjin": "天津市",
        "上海": "上海市",
        "上海市": "上海市",
        "shanghai": "上海市",
        "重庆": "重庆市",
        "重庆市": "重庆市",
        "chongqing": "重庆市",
        "河北": "河北省",
        "河北省": "河北省",
        "hebei": "河北省",
        "山西": "山西省",
        "山西省": "山西省",
        "shanxi": "山西省",
        "内蒙古": "内蒙古自治区",
        "内蒙古自治区": "内蒙古自治区",
        "inner mongolia": "内蒙古自治区",
        "辽宁": "辽宁省",
        "辽宁省": "辽宁省",
        "liaoning": "辽宁省",
        "吉林": "吉林省",
        "吉林省": "吉林省",
        "jilin": "吉林省",
        "黑龙江": "黑龙江省",
        "黑龙江省": "黑龙江省",
        "heilongjiang": "黑龙江省",
        "江苏": "江苏省",
        "江苏省": "江苏省",
        "jiangsu": "江苏省",
        "浙江": "浙江省",
        "浙江省": "浙江省",
        "zhejiang": "浙江省",
        "安徽": "安徽省",
        "安徽省": "安徽省",
        "anhui": "安徽省",
        "福建": "福建省",
        "福建省": "福建省",
        "fujian": "福建省",
        "江西": "江西省",
        "江西省": "江西省",
        "jiangxi": "江西省",
        "山东": "山东省",
        "山东省": "山东省",
        "shandong": "山东省",
        "河南": "河南省",
        "河南省": "河南省",
        "henan": "河南省",
        "湖北": "湖北省",
        "湖北省": "湖北省",
        "hubei": "湖北省",
        "湖南": "湖南省",
        "湖南省": "湖南省",
        "hunan": "湖南省",
        "广东": "广东省",
        "广东省": "广东省",
        "guangdong": "广东省",
        "广西": "广西壮族自治区",
        "广西壮族自治区": "广西壮族自治区",
        "guangxi": "广西壮族自治区",
        "海南": "海南省",
        "海南省": "海南省",
        "hainan": "海南省",
        "四川": "四川省",
        "四川省": "四川省",
        "sichuan": "四川省",
        "贵州": "贵州省",
        "贵州省": "贵州省",
        "guizhou": "贵州省",
        "云南": "云南省",
        "云南省": "云南省",
        "yunnan": "云南省",
        "西藏": "西藏自治区",
        "西藏自治区": "西藏自治区",
        "xizang": "西藏自治区",
        "tibet": "西藏自治区",
        "陕西": "陕西省",
        "陕西省": "陕西省",
        "shaanxi": "陕西省",
        "甘肃": "甘肃省",
        "甘肃省": "甘肃省",
        "gansu": "甘肃省",
        "青海": "青海省",
        "青海省": "青海省",
        "qinghai": "青海省",
        "宁夏": "宁夏回族自治区",
        "宁夏回族自治区": "宁夏回族自治区",
        "ningxia": "宁夏回族自治区",
        "新疆": "新疆维吾尔自治区",
        "新疆维吾尔自治区": "新疆维吾尔自治区",
        "xinjiang": "新疆维吾尔自治区",
        "香港": "中国香港",
        "中国香港": "中国香港",
        "hong kong": "中国香港",
        "澳门": "中国澳门",
        "中国澳门": "中国澳门",
        "macau": "中国澳门",
        "macao": "中国澳门",
        "台湾": "中国台湾",
        "中国台湾": "中国台湾",
        "taiwan": "中国台湾",
    }
    _isp_patterns = [
        (re.compile(r"china\s*telecom|中国电信|chinatelecom", re.IGNORECASE), "中国电信"),
        (re.compile(r"china\s*unicom|中国联通", re.IGNORECASE), "中国联通"),
        (re.compile(r"china\s*mobile|中国移动|cmcc", re.IGNORECASE), "中国移动"),
        (re.compile(r"aliyun|alibaba|阿里云|阿里巴巴", re.IGNORECASE), "阿里云"),
        (re.compile(r"tencent|腾讯云", re.IGNORECASE), "腾讯云"),
        (re.compile(r"huawei|华为云", re.IGNORECASE), "华为云"),
        (re.compile(r"amazon|aws", re.IGNORECASE), "AWS"),
        (re.compile(r"microsoft|azure", re.IGNORECASE), "Azure"),
        (re.compile(r"google", re.IGNORECASE), "Google"),
        (re.compile(r"oracle", re.IGNORECASE), "Oracle"),
        (re.compile(r"cloudflare", re.IGNORECASE), "Cloudflare"),
    ]
    _local_cache: dict[str, tuple[float, dict[str, Any]]] = {}
    _source_backoff_until: dict[str, float] = {}

    @classmethod
    def is_valid_ip(cls, ip: str) -> bool:
        try:
            ipaddress.ip_address((ip or "").strip())
            return True
        except ValueError:
            return False

    @classmethod
    def is_private_ip(cls, ip: str) -> bool:
        ip_obj = ipaddress.ip_address(ip)
        return any(
            (
                ip_obj.is_private,
                ip_obj.is_loopback,
                ip_obj.is_link_local,
                ip_obj.is_multicast,
                ip_obj.is_reserved,
                ip_obj.is_unspecified,
            )
        )

    @classmethod
    def _empty_result(cls, status: str, error: str | None = None) -> dict[str, Any]:
        return {
            "country": None,
            "province": None,
            "city": None,
            "isp": None,
            "latitude": None,
            "longitude": None,
            "status": status,
            "error": error,
            "source": None,
        }

    @classmethod
    def _local_ip_result(cls) -> dict[str, Any]:
        result = cls._empty_result(status="success")
        result.update(
            {
                "country": "本地",
                "province": "内网",
                "city": "非公网 IP",
                "isp": "内网",
            }
        )
        return result

    @classmethod
    def _cache_key(cls, ip: str) -> str:
        return cache_manager.build_key(cls.CACHE_NAMESPACE, ip)

    @classmethod
    def _get_cached_result(cls, ip: str) -> dict[str, Any] | None:
        now = time.monotonic()
        cached = cls._local_cache.get(ip)
        if cached:
            expires_at, value = cached
            if expires_at > now:
                return value.copy()
            cls._local_cache.pop(ip, None)

        cached_value = cache_manager.get_json(cls._cache_key(ip))
        if isinstance(cached_value, dict):
            ttl = cls.SUCCESS_CACHE_TTL if cached_value.get("status") == "success" else cls.FAILURE_CACHE_TTL
            cls._local_cache[ip] = (now + ttl, cached_value)
            return cached_value.copy()
        return None

    @classmethod
    def _set_cached_result(cls, ip: str, result: dict[str, Any]) -> None:
        ttl = cls.SUCCESS_CACHE_TTL if result.get("status") == "success" else cls.FAILURE_CACHE_TTL
        cls._local_cache[ip] = (time.monotonic() + ttl, result.copy())
        cache_manager.set_json(cls._cache_key(ip), result, ttl)

    @classmethod
    def _source_available(cls, source_name: str) -> bool:
        cooldown_until = cls._source_backoff_until.get(source_name, 0.0)
        now = time.monotonic()
        if cooldown_until > now:
            return False
        if cooldown_until:
            cls._source_backoff_until.pop(source_name, None)
        return True

    @classmethod
    def _set_source_backoff(cls, source_name: str, seconds: int) -> None:
        cls._source_backoff_until[source_name] = time.monotonic() + max(seconds, 1)

    @classmethod
    def _extract_backoff_seconds(cls, response: httpx.Response) -> int:
        for header_name in ("Retry-After", "X-Ttl"):
            header_value = response.headers.get(header_name)
            if not header_value:
                continue
            try:
                return max(int(float(header_value)), 1)
            except ValueError:
                continue
        return cls.DEFAULT_COOLDOWN_SECONDS

    @classmethod
    def _apply_success_headers(cls, source_name: str, response: httpx.Response) -> None:
        remaining = response.headers.get("X-Rl")
        ttl = response.headers.get("X-Ttl")
        if remaining == "0" and ttl:
            try:
                cls._set_source_backoff(source_name, int(float(ttl)))
            except ValueError:
                logger.warning("Unable to parse %s X-Ttl header: %s", source_name, ttl)

    @classmethod
    def _clean_text(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        text = re.sub(r"\s+", " ", text)
        if text.casefold() in cls._unknown_texts:
            return None
        return text

    @staticmethod
    def _has_cjk(text: str | None) -> bool:
        if not text:
            return False
        return any("\u4e00" <= char <= "\u9fff" for char in text)

    @staticmethod
    def _to_float(value: Any) -> float | None:
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _normalize_country(cls, country: Any, country_code: Any = None) -> str | None:
        clean_country = cls._clean_text(country)
        clean_code = cls._clean_text(country_code)

        if clean_code:
            mapped_name = cls._country_code_to_zh.get(clean_code.upper())
            if mapped_name and (not clean_country or clean_country.upper() == clean_code.upper()):
                return mapped_name

        if not clean_country:
            return None

        normalized = cls._country_aliases.get(clean_country.casefold())
        if normalized:
            return normalized

        if clean_code:
            mapped_name = cls._country_code_to_zh.get(clean_code.upper())
            if mapped_name and clean_country.casefold() in cls._country_aliases:
                return mapped_name

        return clean_country

    @classmethod
    def _normalize_region(cls, country: str | None, region: Any) -> str | None:
        clean_region = cls._clean_text(region)
        if not clean_region:
            return None

        if country and clean_region.startswith(country):
            clean_region = clean_region[len(country) :].strip(" -_/")

        if country == "中国":
            mapped_region = cls._china_province_aliases.get(clean_region.casefold())
            if mapped_region:
                return mapped_region

        return clean_region or None

    @classmethod
    def _normalize_city(cls, province: str | None, city: Any) -> str | None:
        clean_city = cls._clean_text(city)
        if not clean_city:
            return None

        if province and clean_city == province:
            return None

        return clean_city

    @classmethod
    def _normalize_isp(cls, country: str | None, isp: Any) -> str | None:
        clean_isp = cls._clean_text(isp)
        if not clean_isp:
            return None

        if country == "中国":
            if clean_isp in {"电信", "中国电信"}:
                return "中国电信"
            if clean_isp in {"联通", "中国联通"}:
                return "中国联通"
            if clean_isp in {"移动", "中国移动"}:
                return "中国移动"
            if clean_isp in {"广电", "中国广电"}:
                return "中国广电"

        for pattern, replacement in cls._isp_patterns:
            if pattern.search(clean_isp):
                return replacement

        return clean_isp

    @classmethod
    def _province_compare_key(cls, country: str | None, province: Any) -> str | None:
        normalized = cls._normalize_region(country, province)
        if not normalized:
            return None
        if country == "中国":
            return normalized
        return normalized.casefold()

    @classmethod
    def _city_compare_key(cls, city: Any) -> tuple[str, str] | None:
        clean_city = cls._clean_text(city)
        if not clean_city:
            return None

        if cls._has_cjk(clean_city):
            normalized_city = clean_city
            for suffix in ("特别行政区", "自治州", "地区", "盟", "州", "市"):
                if normalized_city.endswith(suffix):
                    normalized_city = normalized_city[: -len(suffix)]
                    break
            return ("cjk", normalized_city)

        return ("text", clean_city.casefold())

    @classmethod
    def _locations_compatible(cls, current: dict[str, Any], candidate: dict[str, Any]) -> bool:
        current_country = cls._normalize_country(current.get("country"))
        candidate_country = cls._normalize_country(candidate.get("country"))
        if current_country and candidate_country and current_country != candidate_country:
            return False

        compare_country = current_country or candidate_country
        current_province = cls._province_compare_key(compare_country, current.get("province"))
        candidate_province = cls._province_compare_key(compare_country, candidate.get("province"))
        if current_province and candidate_province and current_province != candidate_province:
            return False

        current_city = cls._city_compare_key(current.get("city"))
        candidate_city = cls._city_compare_key(candidate.get("city"))
        if current_city and candidate_city and current_city[0] == candidate_city[0] and current_city[1] != candidate_city[1]:
            return False

        return True

    @classmethod
    def _normalize_result(cls, raw: dict[str, Any] | None) -> dict[str, Any] | None:
        if not raw:
            return None

        country = cls._normalize_country(raw.get("country"), raw.get("country_code"))
        province = cls._normalize_region(country, raw.get("province"))
        city = cls._normalize_city(province, raw.get("city"))
        isp = cls._normalize_isp(country, raw.get("isp"))
        latitude = cls._to_float(raw.get("latitude"))
        longitude = cls._to_float(raw.get("longitude"))

        if not any(
            [
                country,
                province,
                city,
                isp,
                latitude is not None,
                longitude is not None,
            ]
        ):
            return None

        return {
            "country": country,
            "province": province,
            "city": city,
            "isp": isp,
            "latitude": latitude,
            "longitude": longitude,
        }

    @classmethod
    def _merge_result(cls, current: dict[str, Any] | None, candidate: dict[str, Any]) -> dict[str, Any]:
        merged = cls._empty_result(status="success") if current is None else current.copy()

        for field in ("country", "province", "city", "isp"):
            if merged.get(field) is None and candidate.get(field) is not None:
                merged[field] = candidate[field]

        if (
            (merged.get("latitude") is None or merged.get("longitude") is None)
            and candidate.get("latitude") is not None
            and candidate.get("longitude") is not None
            and cls._locations_compatible(merged, candidate)
        ):
            if merged.get("latitude") is None:
                merged["latitude"] = candidate["latitude"]
            if merged.get("longitude") is None:
                merged["longitude"] = candidate["longitude"]

        return merged

    @staticmethod
    def _is_complete(result: dict[str, Any]) -> bool:
        has_name = any(result.get(field) for field in ("country", "province", "city"))
        has_coordinates = result.get("latitude") is not None and result.get("longitude") is not None
        return has_name and has_coordinates

    @staticmethod
    def _extract_error_message(data: Any) -> str | None:
        if not isinstance(data, dict):
            return None

        message = data.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()

        error = data.get("error")
        if isinstance(error, str) and error.strip():
            return error.strip()

        if isinstance(error, dict):
            for key in ("message", "error_message", "detail"):
                value = error.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()

        return None

    @staticmethod
    def parse_ipwhois(data: dict[str, Any]) -> dict[str, Any] | None:
        if not data.get("success", True):
            return None

        connection = data.get("connection") or {}
        return {
            "country": data.get("country"),
            "country_code": data.get("country_code"),
            "province": data.get("region"),
            "city": data.get("city"),
            "isp": connection.get("isp") or connection.get("org"),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
        }

    @staticmethod
    def parse_baidu_qifu(data: dict[str, Any]) -> dict[str, Any] | None:
        if data.get("code") != 200:
            return None

        payload = data.get("data") or {}
        return {
            "country": payload.get("country"),
            "province": payload.get("province"),
            "city": payload.get("city"),
            "isp": payload.get("isp"),
            "latitude": None,
            "longitude": None,
        }

    @staticmethod
    def parse_ipapi(data: dict[str, Any]) -> dict[str, Any] | None:
        if data.get("status") != "success":
            return None

        return {
            "country": data.get("country"),
            "country_code": data.get("countryCode"),
            "province": data.get("regionName"),
            "city": data.get("city"),
            "isp": data.get("isp") or data.get("org"),
            "latitude": data.get("lat"),
            "longitude": data.get("lon"),
        }

    @staticmethod
    def parse_ip2location(data: dict[str, Any]) -> dict[str, Any] | None:
        if data.get("error"):
            return None

        return {
            "country": data.get("country_name"),
            "country_code": data.get("country_code"),
            "province": data.get("region_name"),
            "city": data.get("city_name"),
            "isp": data.get("isp") or data.get("as"),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
        }

    @classmethod
    async def _fetch_from_source(
        cls,
        client: httpx.AsyncClient,
        ip: str,
        source: dict[str, str],
    ) -> tuple[dict[str, Any] | None, str | None]:
        source_name = source["name"]

        if not cls._source_available(source_name):
            return None, f"{source_name} is temporarily rate-limited"

        url = source["url"].format(ip=ip)
        request_headers = cls.REQUEST_HEADERS.copy()
        request_headers.update(source.get("headers") or {})
        try:
            logger.info("Resolving IP %s via %s", ip, source_name)
            response = await client.get(url, headers=request_headers)
            if response.status_code == 429:
                cooldown_seconds = cls._extract_backoff_seconds(response)
                cls._set_source_backoff(source_name, cooldown_seconds)
                return None, f"{source_name} rate limit exceeded"

            response.raise_for_status()
            cls._apply_success_headers(source_name, response)

            payload = response.json()
            parser = getattr(cls, source["parser"])
            parsed = parser(payload)
            normalized = cls._normalize_result(parsed)
            if normalized:
                return normalized, None

            error_message = cls._extract_error_message(payload)
            return None, error_message or f"{source_name} returned no usable data"
        except httpx.TimeoutException:
            return None, f"{source_name} request timed out"
        except httpx.HTTPStatusError as exc:
            return None, f"{source_name} HTTP error: {exc.response.status_code}"
        except ValueError:
            return None, f"{source_name} returned invalid JSON"
        except Exception as exc:  # pragma: no cover - runtime safety
            return None, f"{source_name} parse error: {exc}"

    @classmethod
    async def get_location(cls, ip: str, force_refresh: bool = False) -> dict[str, Any]:
        ip = (ip or "").strip()

        if not cls.is_valid_ip(ip):
            return cls._empty_result(status="failed", error="IP 地址格式无效")

        if cls.is_private_ip(ip):
            return cls._local_ip_result()

        if not force_refresh:
            cached_result = cls._get_cached_result(ip)
            if cached_result is not None:
                return cached_result

        merged_result: dict[str, Any] | None = None
        last_error: str | None = None
        used_sources: list[str] = []

        async with httpx.AsyncClient(
            timeout=cls.TIMEOUT,
            headers=cls.REQUEST_HEADERS,
            follow_redirects=True,
        ) as client:
            for source in cls.API_SOURCES:
                candidate, error = await cls._fetch_from_source(client, ip, source)
                if error:
                    last_error = error
                    logger.warning("IP %s geolocation via %s failed: %s", ip, source["name"], error)
                    continue

                if not candidate:
                    continue

                merged_result = cls._merge_result(merged_result, candidate)
                used_sources.append(source["name"])
                logger.info("IP %s geolocation merged from %s: %s", ip, source["name"], merged_result)

                if cls._is_complete(merged_result):
                    break

        if merged_result:
            merged_result["status"] = "success"
            merged_result["error"] = None
            merged_result["source"] = " + ".join(used_sources) if used_sources else None
            cls._set_cached_result(ip, merged_result)
            return merged_result

        failed_result = cls._empty_result(status="failed", error=last_error or "所有地理位置服务都失败了")
        cls._set_cached_result(ip, failed_result)
        return failed_result

    @classmethod
    def format_location(cls, location: dict[str, Any]) -> str:
        if location.get("status") == "failed":
            return "未知"

        parts: list[str] = []
        for field in ("country", "province", "city"):
            value = location.get(field)
            if value and value not in parts:
                parts.append(str(value))
        return " ".join(parts) if parts else "未知"


ip_location_service = IPLocationService()
