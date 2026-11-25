"""Alibaba Cloud SMS for domain alerts: SendSms (dysmsapi 2017-05-25) with the V3 signature (ACS3-HMAC-SHA256).

API:       https://help.aliyun.com/zh/sms/developer-reference/api-dysmsapi-2017-05-25-sendsms
Signature: https://help.aliyun.com/zh/sdk/product-overview/v3-request-structure-and-signature

The template configured in 设置 → 域名通知 is a fault notice with four variables:
  服务器故障通知：服务器${name}于${time}时间有故障，状态${status}，告警信息：${msg}，请您及时联系技术人员处理。
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import logging
import re
from typing import NamedTuple
from urllib.parse import quote
import uuid

import requests

logger = logging.getLogger(__name__)

SMS_HOST = "dysmsapi.aliyuncs.com"
SMS_ACTION = "SendSms"
SMS_VERSION = "2017-05-25"
SIGNATURE_ALGORITHM = "ACS3-HMAC-SHA256"
EMPTY_BODY_SHA256 = hashlib.sha256(b"").hexdigest()
MAX_PHONE_NUMBERS = 1000          # SendSms accepts up to 1000 comma-separated numbers per call
VARIABLE_MAX_LENGTH = 35          # 通知短信: each variable 1–35 characters, longer values fail the send
# Only faults are sent: the template says "有故障". Recoveries stay on the DingTalk robot.
SMS_ALERT_TYPES = ("domain_critical", "domain_warning", "domain_expiry")
# Codes worth retrying later. Everything else (isv.*, signature/AccessKey errors) needs a config fix.
RETRYABLE_CODE_PREFIXES = ("Throttling", "ServiceUnavailable", "InternalError", "isp.SYSTEM_ERROR", "isv.BUSINESS_LIMIT_CONTROL")
PHONE_PATTERN = re.compile(r"\+?\d{5,20}")
LABEL_LINE = re.compile(r"^-\s*(.+?)(?:（待复核）)?[：:]")


class SmsResult(NamedTuple):
    ok: bool
    error: str | None = None
    retryable: bool = False
    biz_id: str | None = None


def percent_encode(value) -> str:
    # RFC 3986: only A–Z a–z 0–9 - _ . ~ stay as-is; space becomes %20 and * becomes %2A.
    return quote(str(value), safe="")


def canonical_query(params: dict) -> str:
    return "&".join(f"{percent_encode(key)}={percent_encode(params[key])}" for key in sorted(params))


def sign_request(*, access_key_id: str, access_key_secret: str, method: str, host: str, action: str, version: str,
                 query: dict, date: str, nonce: str, body_hash: str = EMPTY_BODY_SHA256) -> dict:
    """Return the request headers, including Authorization, for an RPC-style call with an empty body."""
    headers = {
        "host": host,
        "x-acs-action": action,
        "x-acs-content-sha256": body_hash,
        "x-acs-date": date,
        "x-acs-signature-nonce": nonce,
        "x-acs-version": version,
    }
    names = sorted(headers)
    signed_headers = ";".join(names)
    canonical_headers = "".join(f"{name}:{headers[name].strip()}\n" for name in names)
    canonical_request = "\n".join((method, "/", canonical_query(query), canonical_headers, signed_headers, body_hash))
    string_to_sign = f"{SIGNATURE_ALGORITHM}\n{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    signature = hmac.new(access_key_secret.encode("utf-8"), string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    headers["Authorization"] = (
        f"{SIGNATURE_ALGORITHM} Credential={access_key_id},SignedHeaders={signed_headers},Signature={signature}"
    )
    return headers


def normalize_phone_numbers(raw: str | None) -> list[str]:
    """Split on commas (either width), semicolons, spaces or new lines; keep order, drop duplicates."""
    numbers = list(dict.fromkeys(part for part in re.split(r"[\s,，;；、]+", raw or "") if part))
    for number in numbers:
        if not PHONE_PATTERN.fullmatch(number):
            raise ValueError(f"手机号格式不正确：{number}")
    if len(numbers) > MAX_PHONE_NUMBERS:
        raise ValueError(f"接收手机号最多 {MAX_PHONE_NUMBERS} 个")
    return numbers


def sms_configured(config) -> bool:
    return bool(config and all((
        config.sms_access_key_id, config.sms_access_key_secret, config.sms_sign_name,
        config.sms_template_code, config.sms_phone_numbers,
    )))


# Aliyun rejects any variable that looks like a link (isv.PARAM_NOT_SUPPORT_URL), and a bare domain such as
# "example.com" counts. The replacement must be a plain ASCII character: uncommon symbols such as "·" or "•"
# fail with isv.UNSUPPORTED_CONTENT instead. So "example.com" is sent as "example_com".
URLISH_DOT = re.compile(r"(?<=[0-9A-Za-z-])\.(?=[0-9A-Za-z])")
URLISH_DOT_REPLACEMENT = "_"


def fit(value, limit: int = VARIABLE_MAX_LENGTH) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip() or "无"
    text = URLISH_DOT.sub(URLISH_DOT_REPLACEMENT, re.sub(r"(?i)\b[a-z][a-z0-9+.-]*://", "", text))
    return text if len(text) <= limit else text[: limit - 3] + "..."


def alert_summary(alert_type: str, message: str) -> str:
    """Short, variable-safe ${msg}: check names only.

    Raw probe details carry NS host names and IP addresses, which SMS variables must not contain.
    The full detail stays in DingTalk and the admin alert list.
    """
    lines = [line.strip() for line in (message or "").splitlines() if line.strip()]
    if alert_type == "domain_expiry":
        return fit(lines[0].lstrip("- ") if lines else "域名即将到期")
    labels = []
    for line in lines:
        match = LABEL_LINE.match(line)
        if not match:
            continue
        label = match.group(1).strip()
        label = label if label.endswith("异常") else f"{label}异常"
        if label not in labels:
            labels.append(label)
    return fit("、".join(labels) or "域名检测异常")


def alert_status(alert_type: str, message: str) -> str:
    if alert_type == "domain_expiry":
        if "已经到期" in (message or ""):
            return "已到期"
        if "今天到期" in (message or ""):
            return "今天到期"
        return "即将到期"
    return {"domain_critical": "严重", "domain_warning": "警告"}.get(alert_type, "异常")


def build_template_param(domain_name: str, alert_type: str, message: str, created_at: datetime) -> dict:
    return {
        "name": fit(domain_name),
        "time": created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "status": alert_status(alert_type, message),
        "msg": alert_summary(alert_type, message),
    }


def send_sms(*, access_key_id: str, access_key_secret: str, sign_name: str, template_code: str,
             phone_numbers: str, template_param: dict, timeout=(5, 10)) -> SmsResult:
    query = {
        "PhoneNumbers": ",".join(normalize_phone_numbers(phone_numbers)),
        "SignName": sign_name,
        "TemplateCode": template_code,
        "TemplateParam": json.dumps(template_param, ensure_ascii=False, separators=(",", ":")),
    }
    headers = sign_request(
        access_key_id=access_key_id, access_key_secret=access_key_secret, method="POST", host=SMS_HOST,
        action=SMS_ACTION, version=SMS_VERSION, query=query,
        date=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), nonce=uuid.uuid4().hex,
    )
    headers["accept"] = "application/json"
    try:
        response = requests.post(
            f"https://{SMS_HOST}/?{canonical_query(query)}", headers=headers, timeout=timeout, allow_redirects=False,
        )
    except requests.ConnectTimeout:
        return SmsResult(False, "连接阿里云短信服务超时", True)
    except requests.ReadTimeout:
        # SendSms is not idempotent: the message may already be on its way, so do not resend automatically.
        return SmsResult(False, "阿里云短信接口响应超时，短信可能已发出，未自动重试", False)
    except requests.ConnectionError:
        return SmsResult(False, "无法连接阿里云短信服务", True)
    except requests.RequestException as exc:
        return SmsResult(False, type(exc).__name__, False)

    try:
        result = response.json()
    except ValueError:
        result = None
    if not isinstance(result, dict):
        return SmsResult(False, f"HTTP {response.status_code}", response.status_code >= 500)
    code = str(result.get("Code") or "")
    if code == "OK":
        return SmsResult(True, None, False, result.get("BizId"))
    detail = f"{code or f'HTTP {response.status_code}'}: {result.get('Message') or '发送失败'}"
    retryable = response.status_code >= 500 or code.startswith(RETRYABLE_CODE_PREFIXES)
    # Variables are what Aliyun usually objects to; phone numbers and keys are never logged.
    logger.warning("阿里云短信被拒: %s RequestId=%s 变量=%s", detail, result.get("RequestId"),
                   json.dumps(template_param, ensure_ascii=False))
    return SmsResult(False, detail[:500], retryable)


def send_configured_sms(config, template_param: dict) -> SmsResult:
    return send_sms(
        access_key_id=config.sms_access_key_id, access_key_secret=config.sms_access_key_secret,
        sign_name=config.sms_sign_name, template_code=config.sms_template_code,
        phone_numbers=config.sms_phone_numbers, template_param=template_param,
    )
