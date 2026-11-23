from datetime import date, datetime
import re
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth import get_current_user
from database import (
    DEFAULT_DOMAIN_CONFIRMATION_COUNT, DEFAULT_DOMAIN_DNS_INTERVAL, DEFAULT_DOMAIN_EXPIRY_DAYS,
    DEFAULT_DOMAIN_RDAP_INTERVAL, DomainAlert, MonitoredDomain, SystemConfig, User, get_db,
)
from domain_monitor import expire_check, expiry_reminder_days
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
    webhook_url: str = Field(default="", max_length=1000)
    webhook_secret: str = Field(default="", max_length=255)


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


@router.get("/notification", dependencies=[Depends(require_admin)])
def get_notification(db: Session = Depends(get_db)) -> DomainNotificationSettings:
    config = get_system_config(db)
    return DomainNotificationSettings(
        webhook_url=(config.domain_webhook_url or "") if config else "",
        webhook_secret=(config.domain_webhook_secret or "") if config else "",
    )


@router.put("/notification", dependencies=[Depends(require_admin)])
def update_notification(body: DomainNotificationSettings, db: Session = Depends(get_db)) -> DomainNotificationSettings:
    url, secret = body.webhook_url.strip(), body.webhook_secret.strip()
    if url and not re.fullmatch(r"https://oapi\.dingtalk\.com/robot/send\?access_token=[a-zA-Z0-9_-]+", url):
        raise HTTPException(422, "请输入钉钉自定义机器人的完整 Webhook 地址")
    config = get_system_config(db) or SystemConfig()
    config.domain_webhook_url = url or None
    config.domain_webhook_secret = (secret or None) if url else None
    db.add(config)
    db.commit()
    return DomainNotificationSettings(webhook_url=url, webhook_secret=config.domain_webhook_secret or "")


@router.post("/notification/test", dependencies=[Depends(require_admin)])
def test_notification(db: Session = Depends(get_db)):
    config = get_system_config(db)
    if not config or not config.domain_webhook_url:
        raise HTTPException(400, "请先保存域名专用钉钉机器人的 Webhook 地址")
    sample = NotificationTemplate.get_domain_alert(
        "example.com", "domain_warning", "- 通知渠道：域名监控机器人测试", is_test=True,
    )
    notifier = NotificationService()
    notifier.configure(webhook_url=config.domain_webhook_url, webhook_secret=config.domain_webhook_secret)
    if not notifier.send_webhook(sample["content"], title=sample["title"]):
        raise HTTPException(502, "测试通知发送失败，请核对域名机器人的 Webhook 和安全设置")
    return {"message": "域名测试通知已发送"}


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
    if "manual_expiry" not in body.model_fields_set:
        fields["manual_expiry"] = row.manual_expiry
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
    if expiry_changed or (checks_changed and fields["manual_expiry"]):
        checks = dict(row.checks)
        checks["expiry"] = expire_check(
            checks.get("registration", {}), datetime.now(), fields["manual_expiry"],
            expiry_reminder_days(get_system_config(db)),
        )
        row.checks = checks
        stop_delivery(db, row.id, "superseded", alert_type="domain_expiry")
        if not fields["manual_expiry"]:
            row.rdap_checked_at = None
    if not fields["enabled"] or not fields["notify"]:
        stop_delivery(db, row.id)
    for key, value in fields.items():
        setattr(row, key, value)
    commit_domain(db)
    return row


@router.delete("/{domain_id}", dependencies=[Depends(require_admin)])
def remove_domain(domain_id: int, db: Session = Depends(get_db)):
    row = get_domain(db, domain_id)
    stop_delivery(db, row.id)
    db.delete(row)
    db.commit()
    return {"deleted": True}
