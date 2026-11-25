from datetime import date, datetime
import re
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth import get_current_user
from app_settings import settings
from database import (
    DEFAULT_DOMAIN_CONFIRMATION_COUNT, DEFAULT_DOMAIN_DNS_INTERVAL, DEFAULT_DOMAIN_EXPIRY_DAYS,
    DEFAULT_DOMAIN_RDAP_INTERVAL, DomainAlert, DomainAlertDelivery, MonitoredDomain, SystemConfig, User, get_db,
)
from aliyun_sms import fit, normalize_phone_numbers, send_configured_sms, sms_configured
from domain_monitor import expire_check, expiry_reminder_days, sms_enabled, stop_sms_delivery
from domain_probes import discover_ns, normalize_name, normalize_value, safe
from notification import NotificationService
from notification_template import NotificationTemplate

router = APIRouter(prefix="/api/domains", tags=["域名监控"])


def require_admin(user: User = Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(403, "仅管理员可管理域名监控")


class NameInput(BaseModel):
    name: str = Field(max_length=253)


class RecordInput(BaseModel):
    name: str = Field(max_length=253)
    kind: Literal["A", "AAAA", "CNAME"]
    values: list[str] = Field(min_length=1, max_length=10)


class DomainInput(NameInput):
    expected_ns: list[str] = Field(min_length=1, max_length=8)
    records: list[RecordInput] = Field(default_factory=list, max_length=8)
    enabled: bool = True
    notify: bool = True
    notify_sms: bool = False
    reminder_minutes: int = Field(default=30, ge=0, le=1440)
    manual_expiry: date | None = None


class DomainSettings(BaseModel):
    dns_interval: int = Field(default=DEFAULT_DOMAIN_DNS_INTERVAL, ge=1, le=1440)
    rdap_interval: int = Field(default=DEFAULT_DOMAIN_RDAP_INTERVAL, ge=1, le=1440)
    confirmation_count: int = Field(default=DEFAULT_DOMAIN_CONFIRMATION_COUNT, ge=1, le=10)
    expiry_days: list[Annotated[int, Field(ge=1, le=365)]] = Field(
        default_factory=lambda: list(DEFAULT_DOMAIN_EXPIRY_DAYS), max_length=12,
    )


class DomainNotificationSettings(BaseModel):
    webhook_url: str = ""
    webhook_secret: str = ""
    sms_access_key_id: str = ""
    sms_access_key_secret_set: bool = False   # the secret itself is never returned
    sms_sign_name: str = ""
    sms_template_code: str = ""
    sms_phone_numbers: str = ""               # one number per line


class DomainNotificationUpdate(BaseModel):
    # Omitted fields keep their saved value, so older clients that only send DingTalk settings are safe.
    webhook_url: str = Field(default="", max_length=1000)
    webhook_secret: str = Field(default="", max_length=255)
    sms_access_key_id: str = Field(default="", max_length=128)
    # Write-only. Empty keeps the saved secret; clearing the AccessKey ID clears the secret too.
    sms_access_key_secret: str = Field(default="", max_length=255)
    sms_sign_name: str = Field(default="", max_length=64)
    sms_template_code: str = Field(default="", max_length=64)
    sms_phone_numbers: str = Field(default="", max_length=20000)


class DomainNotificationTest(BaseModel):
    alert_type: Literal["domain_warning", "domain_critical", "domain_recovery", "domain_expiry"] = "domain_warning"


class DomainStateUpdate(BaseModel):
    enabled: bool | None = None
    notify: bool | None = None
    notify_sms: bool | None = None


class DomainBulkStateUpdate(DomainStateUpdate):
    ids: list[int] = Field(min_length=1, max_length=500)


def get_system_config(db):
    return db.query(SystemConfig).first()


def settings_payload(config):
    if config is None:
        return DomainSettings()
    return DomainSettings(
        dns_interval=config.domain_dns_interval,
        rdap_interval=config.domain_rdap_interval,
        confirmation_count=config.domain_confirmation_count,
        expiry_days=list(expiry_reminder_days(config)),
    )


@router.get("/settings", dependencies=[Depends(require_admin)])
def get_settings(db: Session = Depends(get_db)) -> DomainSettings:
    return settings_payload(get_system_config(db))


@router.put("/settings", dependencies=[Depends(require_admin)])
def update_settings(body: DomainSettings, db: Session = Depends(get_db)) -> DomainSettings:
    config = get_system_config(db) or SystemConfig()
    config.domain_dns_interval = body.dns_interval
    config.domain_rdap_interval = body.rdap_interval
    config.domain_confirmation_count = body.confirmation_count
    config.domain_expiry_days = ",".join(map(str, sorted(set(body.expiry_days), reverse=True)))
    db.add(config)
    db.commit()
    return settings_payload(config)


def notification_payload(config) -> DomainNotificationSettings:
    if config is None:
        return DomainNotificationSettings()
    return DomainNotificationSettings(
        webhook_url=config.domain_webhook_url or "",
        webhook_secret=config.domain_webhook_secret or "",
        sms_access_key_id=config.sms_access_key_id or "",
        sms_access_key_secret_set=bool(config.sms_access_key_secret),
        sms_sign_name=config.sms_sign_name or "",
        sms_template_code=config.sms_template_code or "",
        sms_phone_numbers="\n".join(filter(None, (config.sms_phone_numbers or "").split(","))),
    )


@router.get("/notification", dependencies=[Depends(require_admin)])
def get_notification(db: Session = Depends(get_db)) -> DomainNotificationSettings:
    return notification_payload(get_system_config(db))


@router.get("/notification/status", dependencies=[Depends(require_admin)])
def get_notification_status(db: Session = Depends(get_db)):
    config = get_system_config(db)
    return {
        "dingtalk_configured": bool(config and config.domain_webhook_url),
        "sms_configured": sms_configured(config),
    }


@router.put("/notification", dependencies=[Depends(require_admin)])
def update_notification(body: DomainNotificationUpdate, db: Session = Depends(get_db)) -> DomainNotificationSettings:
    config = get_system_config(db) or SystemConfig()
    sent = body.model_fields_set

    def pick(field, saved):
        return (getattr(body, field) if field in sent else saved or "").strip()

    url = pick("webhook_url", config.domain_webhook_url)
    secret = pick("webhook_secret", config.domain_webhook_secret)
    if url and not re.fullmatch(r"https://oapi\.dingtalk\.com/robot/send\?access_token=[a-zA-Z0-9_-]+", url):
        raise HTTPException(422, "请输入钉钉自定义机器人的完整 Webhook 地址")

    key_id = pick("sms_access_key_id", config.sms_access_key_id)
    key_secret = (body.sms_access_key_secret.strip() if "sms_access_key_secret" in sent else "") or (config.sms_access_key_secret or "")
    if not key_id:
        key_secret = ""
    sign_name = pick("sms_sign_name", config.sms_sign_name)
    template_code = pick("sms_template_code", config.sms_template_code)
    try:
        phones = normalize_phone_numbers(body.sms_phone_numbers if "sms_phone_numbers" in sent else config.sms_phone_numbers)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    sms_fields = (key_id, key_secret, sign_name, template_code, phones)
    if any(sms_fields) and not all(sms_fields):
        raise HTTPException(422, "阿里云短信需要同时填写 AccessKey ID、AccessKey Secret、签名名称、模板 Code 和接收手机号；全部清空即可关闭短信")
    if key_id and not re.fullmatch(r"[A-Za-z0-9]{8,128}", key_id):
        raise HTTPException(422, "AccessKey ID 格式不正确")
    if template_code and not re.fullmatch(r"SMS_[0-9A-Za-z_]{1,60}", template_code):
        raise HTTPException(422, "模板 Code 应形如 SMS_123456789")
    if sign_name and re.search(r"[【】\[\]]", sign_name):
        raise HTTPException(422, "签名名称只填文字，不需要带【】")

    was_configured = sms_configured(config)
    config.domain_webhook_url = url or None
    config.domain_webhook_secret = (secret or None) if url else None
    config.sms_access_key_id = key_id or None
    config.sms_access_key_secret = key_secret or None
    config.sms_sign_name = sign_name or None
    config.sms_template_code = template_code or None
    config.sms_phone_numbers = ",".join(phones) or None
    if was_configured and not sms_configured(config):
        db.execute(update(DomainAlertDelivery).where(
            DomainAlertDelivery.channel == "sms",
            DomainAlertDelivery.status.in_(("pending", "failed")),
            DomainAlertDelivery.next_attempt_at.is_not(None),
        ).values(status="no_channel", next_attempt_at=None, last_error="未配置阿里云短信"))
    db.add(config)
    db.commit()
    return notification_payload(config)


def refuse_test_when_notifications_disabled(what: str) -> None:
    # Automatic alerts always obey DISABLE_NOTIFICATIONS; a manual test may send only when explicitly allowed.
    if settings.disable_notifications and not settings.allow_test_notifications:
        raise HTTPException(
            503,
            f"当前环境已关闭外部通知（DISABLE_NOTIFICATIONS=true），未发送{what}。"
            "如需在此环境手动测试，请设置 ALLOW_TEST_NOTIFICATIONS=true 后重启后端",
        )


@router.post("/notification/test", dependencies=[Depends(require_admin)])
def test_notification(body: DomainNotificationTest | None = None, db: Session = Depends(get_db)):
    refuse_test_when_notifications_disabled("钉钉测试通知")
    config = get_system_config(db)
    if not config or not config.domain_webhook_url:
        raise HTTPException(400, "请先保存域名专用钉钉机器人的 Webhook 地址")

    alert_type = body.alert_type if body else "domain_warning"
    examples = {
        "domain_warning": "- 公共 DNS 查询异常：本次未取得足够的可验证样本",
        "domain_critical": "- 注册局 NS：登记的服务器与预期配置不一致\n- 权威 DNS：连续检测到解析记录异常",
        "domain_recovery": "- 恢复说明：注册局 NS、权威 DNS 和公共 DNS 均已连续检查正常",
        "domain_expiry": "- 到期信息：示例域名将在 30 天后到期，请及时确认续费",
    }
    labels = {
        "domain_warning": "警告提醒",
        "domain_critical": "严重异常",
        "domain_recovery": "恢复正常",
        "domain_expiry": "到期提醒",
    }
    sample = NotificationTemplate.get_domain_alert(
        "example.com", alert_type, examples[alert_type], is_test=True,
    )
    notifier = NotificationService()
    notifier.configure(webhook_url=config.domain_webhook_url, webhook_secret=config.domain_webhook_secret)
    if not notifier.send_webhook(sample["content"], alert_type=alert_type, title=sample["title"], manual_test=True):
        raise HTTPException(502, "域名测试通知发送失败，请核对域名机器人的 Webhook 和安全设置")
    return {"message": f"域名{labels[alert_type]}模板测试通知已发送", "alert_type": alert_type}


@router.post("/notification/sms/test", dependencies=[Depends(require_admin)])
def test_sms_notification(db: Session = Depends(get_db)):
    refuse_test_when_notifications_disabled("测试短信")
    config = get_system_config(db)
    if not sms_configured(config):
        raise HTTPException(400, "请先完整保存阿里云短信配置")
    outcome = send_configured_sms(config, {
        "name": fit("example.com"),   # the same link-safe form real alerts use
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "测试",
        "msg": "这是一条测试短信，不代表真实故障",
    })
    if not outcome.ok:
        raise HTTPException(502, f"测试短信发送失败：{outcome.error}")
    count = len(config.sms_phone_numbers.split(","))
    return {"message": f"阿里云已受理测试短信（{count} 个号码），请以手机实际收到为准", "biz_id": outcome.biz_id}


def domain_name(value):
    try:
        name = normalize_name(value)
        if "." not in name:
            raise ValueError("请输入可公开注册的完整域名")
        return name
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def normalized(body):
    fields = body.model_dump()
    name = fields["name"] = domain_name(body.name)
    try:
        fields["expected_ns"] = sorted({normalize_name(value) for value in body.expected_ns})
        seen = set()
        for record in fields["records"]:
            raw = record["name"].strip()
            wildcard = raw.startswith("*.")
            owner = normalize_name(raw[2:] if wildcard else raw)
            if owner != name and not owner.endswith("." + name):
                raise ValueError("记录名称必须属于监控域名")
            if wildcard and len(owner) > 226:
                raise ValueError("泛解析名称过长")
            record["name"] = "*." + owner if wildcard else owner
            key = record["name"], record["kind"]
            if key in seen:
                raise ValueError("同名同类型记录只能配置一次")
            seen.add(key)
            record["values"] = sorted({normalize_value(record["kind"], v) for v in record["values"]})
            if record["kind"] == "CNAME" and len(record["values"]) != 1:
                raise ValueError("CNAME 只能配置一个目标")
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return fields


def get_domain(db, domain_id):
    row = db.get(MonitoredDomain, domain_id)
    if not row:
        raise HTTPException(404, "监控域名不存在")
    return row


def commit_domain(db):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "此域名已添加") from exc


@router.get("", dependencies=[Depends(require_admin)])
def list_domains(db: Session = Depends(get_db)):
    return db.scalars(select(MonitoredDomain).order_by(MonitoredDomain.name)).all()


def sync_sms_deliveries(db: Session, domain: MonitoredDomain):
    """Turning SMS (or the whole domain) off cancels its queued SMS; the DingTalk switch does not."""
    if sms_enabled(domain):
        return
    alert_ids = select(DomainAlert.id).where(DomainAlert.domain_id == domain.id)
    db.execute(update(DomainAlertDelivery).where(
        DomainAlertDelivery.channel == "sms",
        DomainAlertDelivery.domain_alert_id.in_(alert_ids),
        DomainAlertDelivery.status.in_(("pending", "failed")),
        DomainAlertDelivery.next_attempt_at.is_not(None),
    ).values(status="disabled", next_attempt_at=None, last_error=None))


@router.patch("/{domain_id}/state", dependencies=[Depends(require_admin)])
def update_domain_state(domain_id: int, body: DomainStateUpdate, db: Session = Depends(get_db)):
    row = get_domain(db, domain_id)
    fields = body.model_dump(exclude_unset=True, exclude_none=True)
    if not fields:
        return row
    for key, value in fields.items():
        setattr(row, key, value)
    if not row.enabled or not row.notify:
        stop_delivery(db, row.id)
    sync_sms_deliveries(db, row)
    commit_domain(db)
    return row


@router.patch("/bulk-state", dependencies=[Depends(require_admin)])
def update_domains_state(body: DomainBulkStateUpdate, db: Session = Depends(get_db)):
    ids = list(dict.fromkeys(body.ids))
    rows = db.scalars(select(MonitoredDomain).where(MonitoredDomain.id.in_(ids))).all()
    if len(rows) != len(ids):
        raise HTTPException(404, "部分域名不存在，请刷新列表后重试")
    fields = body.model_dump(exclude={"ids"}, exclude_unset=True, exclude_none=True)
    if not fields:
        raise HTTPException(422, "请选择要批量修改的设置")
    for row in rows:
        for key, value in fields.items():
            setattr(row, key, value)
        if not row.enabled or not row.notify:
            stop_delivery(db, row.id)
        sync_sms_deliveries(db, row)
    commit_domain(db)
    return {"updated": len(rows), "items": rows}


@router.post("/discover", dependencies=[Depends(require_admin)])
def discover(body: NameInput):
    values = safe(discover_ns, domain_name(body.name))
    if not isinstance(values, list):
        raise HTTPException(422, "未取得一致的公开 NS，请核对后手动填写")
    return {"expected_ns": values}


@router.post("", status_code=201, dependencies=[Depends(require_admin)])
def add_domain(body: DomainInput, db: Session = Depends(get_db)):
    row = MonitoredDomain(**normalized(body))
    if row.manual_expiry:
        row.checks = {"expiry": expire_check(
            {}, datetime.now(), row.manual_expiry, expiry_reminder_days(get_system_config(db)),
        )}
    db.add(row)
    commit_domain(db)
    return row


def stop_delivery(db, domain_id, status="disabled", *, alert_type=None):
    query = update(DomainAlert).where(
        DomainAlert.domain_id == domain_id, DomainAlert.next_attempt_at.is_not(None),
    )
    if alert_type:
        query = query.where(DomainAlert.alert_type == alert_type)
    db.execute(query.values(delivery_status=status, next_attempt_at=None))


@router.put("/{domain_id}", dependencies=[Depends(require_admin)])
def edit_domain(domain_id: int, body: DomainInput, db: Session = Depends(get_db)):
    row = get_domain(db, domain_id)
    fields = normalized(body)
    for optional_field in ("manual_expiry", "notify_sms"):
        if optional_field not in body.model_fields_set:
            fields[optional_field] = getattr(row, optional_field)
    expiry_changed = row.manual_expiry != fields["manual_expiry"]
    checks_changed = (row.name, row.expected_ns, row.records, row.enabled) != tuple(
        fields[k] for k in ("name", "expected_ns", "records", "enabled")
    )
    if checks_changed:
        if row.name != fields["name"]:
            row.expiry = None
        row.checks = {}
        row.incident_level = 0
        row.last_incident_at = row.last_checked_at = row.rdap_checked_at = None
        stop_delivery(db, row.id, "superseded")
        stop_sms_delivery(db, row.id, "superseded")
    if expiry_changed or (checks_changed and fields["manual_expiry"]):
        checks = dict(row.checks)
        checks["expiry"] = expire_check(
            checks.get("registration", {}), datetime.now(), fields["manual_expiry"],
            expiry_reminder_days(get_system_config(db)),
        )
        row.checks = checks
        stop_delivery(db, row.id, "superseded", alert_type="domain_expiry")
        stop_sms_delivery(db, row.id, "superseded", alert_types=("domain_expiry",))
        if not fields["manual_expiry"]:
            row.rdap_checked_at = None
    if not fields["enabled"] or not fields["notify"]:
        stop_delivery(db, row.id)
    for key, value in fields.items():
        setattr(row, key, value)
    sync_sms_deliveries(db, row)
    commit_domain(db)
    return row


@router.delete("/{domain_id}", dependencies=[Depends(require_admin)])
def remove_domain(domain_id: int, db: Session = Depends(get_db)):
    row = get_domain(db, domain_id)
    stop_delivery(db, row.id)
    stop_sms_delivery(db, row.id)
    db.delete(row)
    db.commit()
    return {"deleted": True}
