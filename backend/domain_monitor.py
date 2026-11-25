from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import logging
from threading import Lock

from sqlalchemy import select, update

from app_settings import settings
from database import (
    DEFAULT_DOMAIN_CONFIRMATION_COUNT, DEFAULT_DOMAIN_DNS_INTERVAL, DEFAULT_DOMAIN_EXPIRY_DAYS,
    DEFAULT_DOMAIN_RDAP_INTERVAL, DomainAlert, DomainAlertDelivery, MonitoredDomain, SessionLocal, SystemConfig,
)
from aliyun_sms import SMS_ALERT_TYPES, build_template_param, send_configured_sms, sms_configured
from domain_probes import dns_checks, lookup_rdap, result, safe
from notification import NotificationService
from notification_template import NotificationTemplate

logger = logging.getLogger(__name__)
LOCK = Lock()
SMS_MAX_ATTEMPTS = 5
DOMAIN_INCIDENT_TYPES = ("domain_critical", "domain_warning")


def sms_enabled(domain):
    return bool(domain and domain.enabled and domain.notify_sms)


def stop_sms_delivery(db, domain_id, status="disabled", *, alert_types=None):
    alert_ids = select(DomainAlert.id).where(DomainAlert.domain_id == domain_id)
    if alert_types:
        alert_ids = alert_ids.where(DomainAlert.alert_type.in_(alert_types))
    db.execute(update(DomainAlertDelivery).where(
        DomainAlertDelivery.channel == "sms",
        DomainAlertDelivery.domain_alert_id.in_(alert_ids),
        DomainAlertDelivery.status.in_(("pending", "failed")),
        DomainAlertDelivery.next_attempt_at.is_not(None),
    ).values(status=status, next_attempt_at=None))


def expiry_reminder_days(config):
    if config is None:
        return DEFAULT_DOMAIN_EXPIRY_DAYS
    return tuple(int(day) for day in config.domain_expiry_days.split(",") if day)


def check_label(key):
    labels = {
        "delegation": "父区 NS 委派",
        "registration": "域名注册状态",
        "authority": "权威 DNS 解析",
        "recursive": "公共 DNS 解析",
    }
    if key.startswith("coverage:"):
        label = labels.get(key[9:].split(":")[0], "域名")
        return f"{label}探测异常"
    return labels.get(key.split(":")[0], "域名检查")


def queue_alert(db, domain, kind, message, now, *, config=None):
    event = DomainAlert(
        domain_id=domain.id, domain_name=domain.name, alert_type=kind, message=message,
        delivery_status="pending" if domain.notify else "disabled",
        next_attempt_at=now if domain.notify else None, created_at=now,
    )
    db.add(event)
    db.flush()
    # SMS is independent of the DingTalk switch and only carries faults (the template is a fault notice).
    if kind in SMS_ALERT_TYPES and sms_enabled(domain):
        config = config or db.query(SystemConfig).first()
        configured = sms_configured(config)
        db.add(DomainAlertDelivery(
            domain_alert_id=event.id,
            channel="sms",
            status="pending" if configured else "no_channel",
            next_attempt_at=now if configured else None,
            created_at=now,
        ))


def expire_check(registration, now, manual_expiry=None, reminder_days=DEFAULT_DOMAIN_EXPIRY_DAYS):
    rdap_expiry = registration.get("expiry")
    if manual_expiry:
        days_left = (manual_expiry - now.date()).days
        display = manual_expiry.isoformat()
        expiry_key = f"manual:{display}"
        source = "manual"
    elif rdap_expiry:
        expiry = datetime.fromisoformat(rdap_expiry)
        days_left = (expiry - now).total_seconds() / 86400
        display = expiry.strftime("%Y-%m-%d %H:%M")
        expiry_key = rdap_expiry
        source = "rdap"
    else:
        state = "unsupported" if registration.get("state") == "unsupported" else "unknown"
        return result(state, "未取得公开到期日，可在编辑域名时手动填写")

    # A date entered without a time is valid through the selected day.
    expires_today = manual_expiry is not None and days_left == 0
    suffix = "，手动填写" if manual_expiry else ""
    thresholds = sorted(set((0, *reminder_days)))
    for days in thresholds:
        if days_left <= days:
            if manual_expiry and days_left <= 0:
                detail = "域名已经到期" if days_left < 0 else "域名今天到期"
            else:
                detail = "域名已经到期" if days == 0 else f"域名将在 {days} 天内到期"
            return result("bad", f"{detail}（{display}{suffix}）") | {
                "threshold": f"{expiry_key}:{days}", "source": source,
            }
    return result("ok", f"{display}{suffix}") | {"source": source}


def update_check(previous, observation, confirmation_count=DEFAULT_DOMAIN_CONFIRMATION_COUNT):
    state = observation["state"]
    active = previous.get("active", 0)
    active_detail = previous.get("active_detail", "")
    count = previous.get("streak", 0) + 1 if previous.get("state") == state else 1
    if state == "bad" and (count >= confirmation_count or observation.get("immediate")):
        active, active_detail = observation["level"], observation["detail"]
    elif state == "ok" and count >= confirmation_count:
        active, active_detail = 0, ""
    return observation | {"active": active, "active_detail": active_detail, "streak": min(count, confirmation_count)}


def record_results(db, domain, observations, now, *, dns_due=True, rdap_due=False, config=None):
    confirmation_count = config.domain_confirmation_count if config else DEFAULT_DOMAIN_CONFIRMATION_COUNT
    previous = domain.checks or {}
    checks = dict(previous)
    previous_level = domain.incident_level
    last_incident = domain.last_incident_at
    # Retire the old timeout-only incident without calling it a recovery.
    if checks.pop("coverage:registration", {}).get("active"):
        previous_level = max((item.get("active", 0) for item in checks.values()), default=0)
        if not previous_level:
            last_incident = domain.last_incident_at = None
    if rdap_due:
        domain.rdap_checked_at = now
        registration = observations["registration"]
        if registration.get("expiry"):
            domain.expiry = datetime.fromisoformat(registration["expiry"])
    else:
        registration = previous.get("registration", {})
    if rdap_due or domain.manual_expiry:
        observations["expiry"] = expire_check(registration, now, domain.manual_expiry, expiry_reminder_days(config))
    for key, observation in observations.items():
        if key == "expiry":
            previous_threshold = previous.get(key, {}).get("notified_threshold")
            threshold = observation.get("threshold")
            if threshold and threshold != previous_threshold:
                queue_alert(db, domain, "domain_expiry", observation["detail"], now, config=config)
                previous_threshold = threshold
            if observation["state"] == "ok":
                previous_threshold = None
            checks[key] = observation | {"notified_threshold": previous_threshold}
            continue
        if key != "registration":
            incomplete = observation["state"] == "unknown" or observation.get("incomplete")
            coverage_state = "bad" if incomplete else "ok"
            coverage_detail = f"{observation['detail']}，部分或全部探测未取得可验证结果"
            checks[f"coverage:{key}"] = update_check(
                previous.get(f"coverage:{key}", {}), result(coverage_state, coverage_detail), confirmation_count,
            )
        checks[key] = update_check(previous.get(key, {}), observation, confirmation_count)

    confirmed = {key: item for key, item in checks.items() if item.get("active")}
    level = max((item["active"] for item in confirmed.values()), default=0)
    if level:
        lines = [
            f"- {check_label(key)}：{item['active_detail']}" for key, item in confirmed.items()
            if not (key.startswith("coverage:") and key[9:] in confirmed)
        ]
        if level == 2:
            lines.extend(
                f"- {check_label(key)}（待复核）：{item['detail']}" for key, item in observations.items()
                if key != "expiry" and key not in confirmed and item["state"] == "bad"
            )
        message = "\n".join(lines)
        reminder_due = (
            domain.reminder_minutes and last_incident and
            now - last_incident >= timedelta(minutes=domain.reminder_minutes)
        )
        kind = "domain_critical" if level == 2 else "domain_warning"
        if level > previous_level or reminder_due:
            queue_alert(db, domain, kind, message, now, config=config)
            domain.last_incident_at = now
        else:
            latest = db.scalars(select(DomainAlert).where(
                DomainAlert.domain_id == domain.id,
                DomainAlert.alert_type.in_(DOMAIN_INCIDENT_TYPES),
                DomainAlert.created_at == domain.last_incident_at,
            ).order_by(DomainAlert.id.desc())).first()
            if latest and not latest.is_sent:
                latest.message = message
    elif previous_level:
        active_alerts = select(DomainAlert.id).where(
            DomainAlert.domain_id == domain.id, DomainAlert.next_attempt_at.is_not(None),
            DomainAlert.alert_type.in_(DOMAIN_INCIDENT_TYPES),
        )
        active_alert_ids = db.scalars(active_alerts).all()
        # SMS is independent of DingTalk: an unsent fault SMS may be queued even when DingTalk is off.
        # Once the domain has recovered it must not go out late.
        stop_sms_delivery(db, domain.id, "superseded", alert_types=DOMAIN_INCIDENT_TYPES)
        db.execute(update(DomainAlert).where(
            DomainAlert.id.in_(active_alert_ids),
        ).values(delivery_status="superseded", next_attempt_at=None))
        queue_alert(db, domain, "domain_recovery", "已确认域名探测恢复正常", now, config=config)
        domain.last_incident_at = None

    domain.incident_level = level
    domain.checks = checks
    if dns_due:
        domain.last_checked_at = now


def collect(job):
    domain_id, name, ns, records, dns_due, rdap_due = job
    observations = dns_checks(name, ns, records) if dns_due else {}
    if rdap_due:
        observations["registration"] = safe(lookup_rdap, name)
    return observations


def deliver_pending():
    if settings.disable_notifications:
        return
    now = datetime.now()
    with SessionLocal() as db:
        config = db.query(SystemConfig).first()
        if not config or not config.domain_webhook_url:
            status_filter = DomainAlert.delivery_status.in_(("pending", "failed"))
            db.execute(DomainAlert.__table__.update().where(status_filter).values(
                delivery_status="no_channel", next_attempt_at=None,
            ))
            db.commit()
            deliver_sms_pending(db, config, now)
            return
        notifier = NotificationService()
        notifier.configure(webhook_url=config.domain_webhook_url, webhook_secret=config.domain_webhook_secret)
        rows = db.scalars(select(DomainAlert).where(
            DomainAlert.delivery_status.in_(("pending", "failed")), DomainAlert.next_attempt_at <= now,
        ).order_by(DomainAlert.next_attempt_at, DomainAlert.id).limit(10)).all()
        for event in rows:
            domain = db.get(MonitoredDomain, event.domain_id)
            if not domain or not domain.enabled or not domain.notify:
                event.delivery_status = "disabled"
                event.next_attempt_at = None
                db.commit()
                continue
            if event.alert_type in ("domain_warning", "domain_critical"):
                # Old queued notifications can still contain the retired coverage check.
                retired_prefix = f"- {check_label('coverage:registration')}："
                lines = event.message.splitlines()
                if any(line.startswith(retired_prefix) for line in lines):
                    lines = [line for line in lines if not line.startswith(retired_prefix)]
                    if not any(line.strip() for line in lines):
                        event.delivery_status = "superseded"
                        event.next_attempt_at = None
                        db.commit()
                        continue
                    event.message = "\n".join(lines)
            notification = NotificationTemplate.get_domain_alert(
                domain_name=event.domain_name,
                alert_type=event.alert_type,
                message=event.message,
                created_at=event.created_at,
            )
            event.attempts += 1
            event.is_sent = notifier.send_webhook(
                notification["content"], title=notification["title"],
            )
            event.delivery_status = "sent" if event.is_sent else "failed"
            event.next_attempt_at = None if event.is_sent else now + timedelta(minutes=min(30, 2 ** min(event.attempts - 1, 5)))
            db.commit()
        deliver_sms_pending(db, config, now)


def deliver_sms_pending(db, config, now):
    rows = db.scalars(select(DomainAlertDelivery).where(
        DomainAlertDelivery.channel == "sms",
        DomainAlertDelivery.status.in_(("pending", "failed")),
        DomainAlertDelivery.next_attempt_at <= now,
    ).order_by(DomainAlertDelivery.next_attempt_at, DomainAlertDelivery.id).limit(20)).all()
    for delivery in rows:
        event = db.get(DomainAlert, delivery.domain_alert_id)
        domain = db.get(MonitoredDomain, event.domain_id) if event else None
        if not event or not sms_enabled(domain):
            delivery.status = "disabled"
            delivery.next_attempt_at = None
            db.commit()
            continue
        if not sms_configured(config):
            delivery.status = "no_channel"
            delivery.next_attempt_at = None
            delivery.last_error = "未配置阿里云短信"
            db.commit()
            continue
        outcome = send_configured_sms(
            config, build_template_param(event.domain_name, event.alert_type, event.message, event.created_at),
        )
        delivery.attempts += 1
        delivery.status = "sent" if outcome.ok else "failed"
        delivery.sent_at = now if outcome.ok else None
        delivery.last_error = outcome.error
        # Only transport/throttling failures are retried; SendSms is not idempotent and config errors need a fix.
        if outcome.ok or not outcome.retryable or delivery.attempts >= SMS_MAX_ATTEMPTS:
            delivery.next_attempt_at = None
        else:
            delivery.next_attempt_at = now + timedelta(minutes=min(30, 2 ** min(delivery.attempts - 1, 5)))
        db.commit()


def run_domain_monitor():
    if not LOCK.acquire(blocking=False):
        return
    try:
        now = datetime.now()
        with SessionLocal() as db:
            config = db.query(SystemConfig).first()
            dns_interval = timedelta(minutes=config.domain_dns_interval if config else DEFAULT_DOMAIN_DNS_INTERVAL)
            rdap_interval = timedelta(minutes=config.domain_rdap_interval if config else DEFAULT_DOMAIN_RDAP_INTERVAL)
            enabled = db.scalars(select(MonitoredDomain).where(
                MonitoredDomain.enabled.is_(True),
            )).all()
            jobs = []
            for row in enabled:
                dns_due = not row.last_checked_at or now - row.last_checked_at >= dns_interval
                rdap_due = not row.rdap_checked_at or now - row.rdap_checked_at >= rdap_interval
                if dns_due or rdap_due:
                    jobs.append((row.id, row.name, row.expected_ns, row.records, dns_due, rdap_due))
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [(job, pool.submit(collect, job)) for job in jobs]
            for job, future in futures:
                try:
                    domain_id, name, ns, records, dns_due, rdap_due = job
                    observations = future.result()
                    with SessionLocal() as db:
                        row = db.get(MonitoredDomain, domain_id)
                        if row and row.enabled and (row.name, row.expected_ns, row.records) == (name, ns, records):
                            record_results(db, row, observations, now, dns_due=dns_due, rdap_due=rdap_due, config=config)
                            db.commit()
                except Exception:
                    logger.exception("域名检查失败，ID %s", job[0])
        deliver_pending()
    finally:
        LOCK.release()
