from __future__ import annotations

import logging
from calendar import monthrange
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app_settings import settings
from data_maintenance import DataMaintenance
from database import Alert, Host, PingRecord, PingStatistics, SessionLocal, SystemConfig
from host_status import ONLINE_PACKET_LOSS_THRESHOLD, is_host_reachable
from notification import NotificationService

logger = logging.getLogger(__name__)


REPORT_LABELS = {
    "daily": "日报",
    "weekly": "周报",
    "monthly": "月报",
}

REPORT_COMPARE_LABELS = {
    "daily": "前一日",
    "weekly": "前一周",
    "monthly": "前一月",
}

REPORT_NOTES = {
    "daily": "日报统计上一自然日，并对比前一自然日。",
    "weekly": "周报统计上一自然周（周一至周日），并对比再前一自然周。",
    "monthly": "月报统计上一自然月，并对比再前一自然月。",
}

TOP_HOST_LIMIT = 5
DEFAULT_ALERT_THRESHOLD = 20.0


@dataclass
class PeriodMetrics:
    start: datetime
    end: datetime
    host_count: int = 0
    total_checks: int = 0
    total_online_count: int = 0
    avg_online_rate: float = 0.0
    avg_packet_loss: float = 0.0
    avg_rtt: float = 0.0
    total_alerts: int = 0
    problem_host_count: int = 0
    alert_counts: dict[str, int] = field(default_factory=dict)
    top_hosts: list[dict] = field(default_factory=list)


class ReportService:
    @classmethod
    def send_report(cls, report_type: str, *, db: Session, trigger_source: str) -> dict:
        report_type = cls._normalize_report_type(report_type)
        config = cls._get_or_create_config(db)
        label = REPORT_LABELS[report_type]

        if settings.disable_notifications:
            raise RuntimeError("Notifications are disabled by DISABLE_NOTIFICATIONS")

        if not cls._is_dingtalk_webhook(config.report_webhook_url):
            raise ValueError("请先在报表配置中填写报表专用钉钉机器人 Webhook 地址")

        current_start, current_end, previous_start, previous_end = cls._get_period_bounds(report_type)
        current_metrics = cls._collect_period_metrics(db, current_start, current_end)
        previous_metrics = cls._collect_period_metrics(db, previous_start, previous_end)

        title = cls._build_report_title(report_type, current_start, current_end)
        content = cls._build_report_markdown(
            report_type=report_type,
            current=current_metrics,
            previous=previous_metrics,
            generated_at=datetime.now(),
        )

        report_notifier = NotificationService()
        report_notifier.configure(
            webhook_url=config.report_webhook_url,
            webhook_secret=config.report_webhook_secret,
        )
        success = report_notifier.send_webhook(content, alert_type="info", title=title)
        if not success:
            raise RuntimeError(f"{label}发送失败，请检查报表专用钉钉 Webhook 配置")

        DataMaintenance.log_system_event(
            db,
            log_type="report",
            module="report_service",
            message=f"{label}发送成功",
            details={
                "report_type": report_type,
                "trigger_source": trigger_source,
                "current_period": {
                    "start": current_start.isoformat(),
                    "end": current_end.isoformat(),
                },
                "previous_period": {
                    "start": previous_start.isoformat(),
                    "end": previous_end.isoformat(),
                },
                "summary": {
                    "host_count": current_metrics.host_count,
                    "total_checks": current_metrics.total_checks,
                    "avg_online_rate": current_metrics.avg_online_rate,
                    "avg_packet_loss": current_metrics.avg_packet_loss,
                    "avg_rtt": current_metrics.avg_rtt,
                    "total_alerts": current_metrics.total_alerts,
                },
            },
        )
        logger.info("%s已发送: %s", label, title)

        return {
            "report_type": report_type,
            "title": title,
            "period": cls._format_period_range(current_start, current_end),
            "compare_period": cls._format_period_range(previous_start, previous_end),
            "message": f"{label}发送成功",
        }

    @classmethod
    def send_report_with_new_session(cls, report_type: str, *, trigger_source: str) -> dict | None:
        db = SessionLocal()
        try:
            return cls.send_report(report_type, db=db, trigger_source=trigger_source)
        except Exception as exc:
            report_label = REPORT_LABELS.get(report_type, report_type)
            logger.error("发送%s失败: %s", report_label, exc)
            DataMaintenance.log_system_event(
                db,
                log_type="error",
                module="report_service",
                message=f"{report_label}发送失败: {exc}",
                details={
                    "report_type": report_type,
                    "trigger_source": trigger_source,
                    "error": str(exc),
                },
            )
            return None
        finally:
            db.close()

    @staticmethod
    def _normalize_report_type(report_type: str) -> str:
        value = (report_type or "").strip().lower()
        if value not in REPORT_LABELS:
            raise ValueError("仅支持 daily、weekly、monthly 三种报表类型")
        return value

    @staticmethod
    def _get_or_create_config(db: Session) -> SystemConfig:
        config = db.query(SystemConfig).first()
        if config:
            return config

        config = SystemConfig()
        db.add(config)
        db.commit()
        db.refresh(config)
        return config

    @staticmethod
    def _is_dingtalk_webhook(webhook_url: str | None) -> bool:
        return bool(webhook_url and "oapi.dingtalk.com" in webhook_url)

    @classmethod
    def _get_period_bounds(cls, report_type: str) -> tuple[datetime, datetime, datetime, datetime]:
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if report_type == "daily":
            current_end = today
            current_start = current_end - timedelta(days=1)
            previous_end = current_start
            previous_start = previous_end - timedelta(days=1)
            return current_start, current_end, previous_start, previous_end

        if report_type == "weekly":
            current_week_start = today - timedelta(days=today.weekday())
            current_end = current_week_start
            current_start = current_end - timedelta(days=7)
            previous_end = current_start
            previous_start = previous_end - timedelta(days=7)
            return current_start, current_end, previous_start, previous_end

        current_month_start = today.replace(day=1)
        current_end = current_month_start
        current_start = cls._shift_months(current_month_start, -1)
        previous_end = current_start
        previous_start = cls._shift_months(current_start, -1)
        return current_start, current_end, previous_start, previous_end

    @staticmethod
    def _shift_months(value: datetime, months: int) -> datetime:
        month_index = value.month - 1 + months
        year = value.year + month_index // 12
        month = month_index % 12 + 1
        day = min(value.day, monthrange(year, month)[1])
        return value.replace(year=year, month=month, day=day)

    @classmethod
    def _collect_period_metrics(cls, db: Session, start: datetime, end: datetime) -> PeriodMetrics:
        host_meta = {
            host.id: {
                "name": host.name,
                "address": host.address,
                "alert_threshold": host.alert_threshold,
            }
            for host in db.query(Host).all()
        }
        host_stats: dict[int, dict] = {}

        raw_start = start
        last_daily_stat_time = (
            db.query(func.max(PingStatistics.stat_time))
            .filter(
                PingStatistics.stat_type == "daily",
                PingStatistics.stat_time >= start,
                PingStatistics.stat_time < end,
            )
            .scalar()
        )
        if last_daily_stat_time is not None:
            raw_start = min(end, last_daily_stat_time + timedelta(days=1))
            cls._merge_daily_rows(db, host_meta, host_stats, start, raw_start)

        if raw_start < end:
            cls._merge_raw_rows(db, host_meta, host_stats, raw_start, end)

        cls._override_host_availability_from_raw(db, host_meta, host_stats, start, end)

        host_alert_counts = {
            int(host_id): int(count)
            for host_id, count in (
                db.query(Alert.host_id, func.count(Alert.id))
                .filter(Alert.created_at >= start, Alert.created_at < end)
                .group_by(Alert.host_id)
                .all()
            )
        }
        alert_counts = defaultdict(int)
        for alert_type, count in (
            db.query(Alert.alert_type, func.count(Alert.id))
            .filter(Alert.created_at >= start, Alert.created_at < end)
            .group_by(Alert.alert_type)
            .all()
        ):
            alert_counts[alert_type] = int(count)

        host_summaries = []
        total_checks = 0
        total_online_count = 0
        weighted_packet_loss_sum = 0.0
        weighted_rtt_sum = 0.0
        weighted_rtt_count = 0
        problem_host_count = 0

        for host_id, entry in host_stats.items():
            if entry["check_count"] <= 0:
                continue

            alert_count = host_alert_counts.get(host_id, 0)
            online_rate = round((entry["online_count"] / entry["check_count"]) * 100, 2)
            avg_packet_loss = round(entry["weighted_packet_loss"] / entry["check_count"], 2)
            avg_rtt = (
                round(entry["weighted_rtt"] / entry["weighted_rtt_count"], 2)
                if entry["weighted_rtt_count"] > 0
                else 0.0
            )

            total_checks += entry["check_count"]
            total_online_count += entry["online_count"]
            weighted_packet_loss_sum += entry["weighted_packet_loss"]
            weighted_rtt_sum += entry["weighted_rtt"]
            weighted_rtt_count += entry["weighted_rtt_count"]

            is_problem = online_rate < 100 or avg_packet_loss > 0 or alert_count > 0
            if is_problem:
                problem_host_count += 1

            host_summaries.append(
                {
                    "id": host_id,
                    "name": entry["name"],
                    "address": entry["address"],
                    "check_count": entry["check_count"],
                    "online_rate": online_rate,
                    "avg_packet_loss": avg_packet_loss,
                    "avg_rtt": avg_rtt,
                    "alert_count": alert_count,
                }
            )

        problem_hosts = [
            item
            for item in host_summaries
            if item["online_rate"] < 100 or item["avg_packet_loss"] > 0 or item["alert_count"] > 0
        ]
        problem_hosts.sort(
            key=lambda item: (
                item["avg_packet_loss"],
                item["alert_count"],
                item["avg_rtt"],
                -item["online_rate"],
            ),
            reverse=True,
        )

        avg_online_rate = round((total_online_count / total_checks) * 100, 2) if total_checks > 0 else 0.0
        avg_packet_loss = round(weighted_packet_loss_sum / total_checks, 2) if total_checks > 0 else 0.0
        avg_rtt = round(weighted_rtt_sum / weighted_rtt_count, 2) if weighted_rtt_count > 0 else 0.0

        return PeriodMetrics(
            start=start,
            end=end,
            host_count=len(host_summaries),
            total_checks=total_checks,
            total_online_count=total_online_count,
            avg_online_rate=avg_online_rate,
            avg_packet_loss=avg_packet_loss,
            avg_rtt=avg_rtt,
            total_alerts=sum(alert_counts.values()),
            problem_host_count=problem_host_count,
            alert_counts=dict(alert_counts),
            top_hosts=problem_hosts[:TOP_HOST_LIMIT],
        )

    @classmethod
    def _merge_daily_rows(
        cls,
        db: Session,
        host_meta: dict[int, dict],
        host_stats: dict[int, dict],
        start: datetime,
        end: datetime,
    ) -> None:
        if start >= end:
            return

        rows = (
            db.query(
                PingStatistics.host_id,
                PingStatistics.check_count,
                PingStatistics.online_count,
                PingStatistics.avg_packet_loss,
                PingStatistics.avg_rtt,
            )
            .filter(
                PingStatistics.stat_type == "daily",
                PingStatistics.stat_time >= start,
                PingStatistics.stat_time < end,
            )
            .all()
        )

        for row in rows:
            entry = cls._ensure_host_entry(host_stats, host_meta, row.host_id)
            check_count = int(row.check_count or 0)
            entry["check_count"] += check_count
            entry["online_count"] += int(row.online_count or 0)
            entry["weighted_packet_loss"] += float(row.avg_packet_loss or 0) * check_count
            if row.avg_rtt is not None:
                entry["weighted_rtt"] += float(row.avg_rtt) * check_count
                entry["weighted_rtt_count"] += check_count

    @classmethod
    def _merge_raw_rows(
        cls,
        db: Session,
        host_meta: dict[int, dict],
        host_stats: dict[int, dict],
        start: datetime,
        end: datetime,
    ) -> None:
        rows = (
            db.query(
                PingRecord.host_id,
                PingRecord.packet_loss,
                PingRecord.avg_rtt,
            )
            .filter(PingRecord.created_at >= start, PingRecord.created_at < end)
            .all()
        )

        for row in rows:
            entry = cls._ensure_host_entry(host_stats, host_meta, row.host_id)
            entry["check_count"] += 1
            if is_host_reachable(row.packet_loss):
                entry["online_count"] += 1
            entry["weighted_packet_loss"] += float(row.packet_loss or 0)
            if row.avg_rtt is not None:
                entry["weighted_rtt"] += float(row.avg_rtt)
                entry["weighted_rtt_count"] += 1

    @staticmethod
    def _ensure_host_entry(host_stats: dict[int, dict], host_meta: dict[int, dict], host_id: int) -> dict:
        if host_id in host_stats:
            return host_stats[host_id]

        meta = host_meta.get(host_id, {})
        entry = {
            "name": meta.get("name") or f"主机-{host_id}",
            "address": meta.get("address") or "-",
            "alert_threshold": float(meta.get("alert_threshold") or DEFAULT_ALERT_THRESHOLD),
            "check_count": 0,
            "online_count": 0,
            "weighted_packet_loss": 0.0,
            "weighted_rtt": 0.0,
            "weighted_rtt_count": 0,
        }
        host_stats[host_id] = entry
        return entry

    @classmethod
    def _override_host_availability_from_raw(
        cls,
        db: Session,
        host_meta: dict[int, dict],
        host_stats: dict[int, dict],
        start: datetime,
        end: datetime,
    ) -> None:
        rows = (
            db.query(
                PingRecord.host_id,
                func.count(PingRecord.id).label("check_count"),
                func.sum(
                    case(
                        (PingRecord.packet_loss < ONLINE_PACKET_LOSS_THRESHOLD, 1),
                        else_=0,
                    )
                ).label("online_count"),
            )
            .filter(PingRecord.created_at >= start, PingRecord.created_at < end)
            .group_by(PingRecord.host_id)
            .all()
        )

        for row in rows:
            entry = cls._ensure_host_entry(host_stats, host_meta, row.host_id)
            entry["check_count"] = int(row.check_count or 0)
            entry["online_count"] = int(row.online_count or 0)

    @classmethod
    def _build_report_title(cls, report_type: str, start: datetime, end: datetime) -> str:
        label = REPORT_LABELS[report_type]
        if report_type == "daily":
            return f"Ping监控{label} {start.strftime('%Y-%m-%d')}"
        if report_type == "weekly":
            end_inclusive = end - timedelta(days=1)
            return f"Ping监控{label} {start.strftime('%m/%d')}-{end_inclusive.strftime('%m/%d')}"
        return f"Ping监控{label} {start.strftime('%Y-%m')}"

    @classmethod
    def _build_report_markdown(
        cls,
        *,
        report_type: str,
        current: PeriodMetrics,
        previous: PeriodMetrics,
        generated_at: datetime,
    ) -> str:
        compare_label = REPORT_COMPARE_LABELS[report_type]
        lines = [
            f"### 📊 Ping监控{REPORT_LABELS[report_type]}",
            "",
            f"> 统计周期：{cls._format_period_range(current.start, current.end)}",
            f"> 对比周期：{cls._format_period_range(previous.start, previous.end)}",
            "",
            "#### 核心指标",
            f"- 纳入统计主机：{current.host_count} 台",
            f"- 总检测次数：{cls._format_int(current.total_checks)} 次",
            (
                f"- 平均在线率：{current.avg_online_rate:.2f}%"
                f"（较{compare_label} {cls._format_delta(current.avg_online_rate, previous.avg_online_rate, unit='pp')}）"
            ),
            (
                f"- 平均丢包率：{current.avg_packet_loss:.2f}%"
                f"（较{compare_label} {cls._format_delta(current.avg_packet_loss, previous.avg_packet_loss, unit='pp')}）"
            ),
            (
                f"- 平均延迟：{current.avg_rtt:.2f}ms"
                f"（较{compare_label} {cls._format_delta(current.avg_rtt, previous.avg_rtt, unit='ms')}）"
            ),
            (
                f"- 告警通知：{cls._format_int(current.total_alerts)} 次"
                f"（较{compare_label} {cls._format_delta(current.total_alerts, previous.total_alerts, precision=0)} 次）"
            ),
            (
                f"- 异常主机：{current.problem_host_count} 台"
                f"（较{compare_label} {cls._format_delta(current.problem_host_count, previous.problem_host_count, precision=0)} 台）"
            ),
            "",
            "#### 告警分布",
            f"- 丢包告警：{cls._format_int(current.alert_counts.get('packet_loss', 0))} 次",
            f"- 不可达告警：{cls._format_int(current.alert_counts.get('unreachable', 0))} 次",
            f"- 恢复通知：{cls._format_int(current.alert_counts.get('recovery', 0))} 次",
            "",
            "#### 重点主机",
        ]

        if current.top_hosts:
            for index, host in enumerate(current.top_hosts, start=1):
                lines.append(
                    (
                        f"{index}. {host['name']} `{host['address']}`"
                        f"，在线率 {host['online_rate']:.2f}%"
                        f"，丢包 {host['avg_packet_loss']:.2f}%"
                        f"，延迟 {host['avg_rtt']:.2f}ms"
                        f"，告警 {host['alert_count']} 次"
                    )
                )
        else:
            lines.append("- 当前统计周期未发现明显异常主机。")

        lines.extend(
            [
                "",
                "#### 统计口径",
                f"- {REPORT_NOTES[report_type]}",
                f"- 生成时间：{generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _format_period_range(start: datetime, end: datetime) -> str:
        end_inclusive = end - timedelta(seconds=1)
        return f"{start.strftime('%Y-%m-%d')} 至 {end_inclusive.strftime('%Y-%m-%d')}"

    @staticmethod
    def _format_delta(current: float | int, previous: float | int, *, unit: str = "", precision: int = 2) -> str:
        delta = float(current) - float(previous)
        if abs(delta) < (0.5 if precision == 0 else 0.005):
            if precision == 0:
                return f"0{unit}"
            return f"0.{('0' * precision)}{unit}"

        if precision == 0:
            return f"{delta:+.0f}{unit}"
        return f"{delta:+.{precision}f}{unit}"

    @staticmethod
    def _format_int(value: int) -> str:
        return f"{int(value):,}"
