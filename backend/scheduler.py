from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from cache import cache_manager
from database import Alert, Host, PingRecord, SessionLocal, SystemConfig, get_database_backend
from ip_location_service import ip_location_service
from notification_template import NotificationTemplate
from ping_service import PingService

logger = logging.getLogger(__name__)

LOCATION_FIELDS = ("country", "province", "city", "isp", "latitude", "longitude")
DISPLAY_LOCATION_FIELDS = ("country", "province", "city")


def host_has_display_location(host: Host) -> bool:
    return any(getattr(host, field, None) for field in DISPLAY_LOCATION_FIELDS)


def host_has_any_location(host: Host) -> bool:
    return host_has_display_location(host) or host.latitude is not None or host.longitude is not None


def host_needs_location_completion(host: Host) -> bool:
    return not host_has_display_location(host) or host.latitude is None or host.longitude is None


def apply_location_result(host: Host, location: dict, *, overwrite_existing: bool) -> None:
    if location.get("status") == "success":
        for field in LOCATION_FIELDS:
            new_value = location.get(field)
            current_value = getattr(host, field, None)
            should_write = overwrite_existing or current_value in (None, "")
            if should_write and new_value is not None:
                setattr(host, field, new_value)

        host.location_status = "success" if host_has_any_location(host) else "failed"
        return

    if host_has_any_location(host):
        host.location_status = "success"
    else:
        host.location_status = location.get("status", "failed")


class MonitorScheduler:
    def __init__(self) -> None:
        self.scheduler = BackgroundScheduler(
            timezone=ZoneInfo("Asia/Shanghai"),
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 120,
            },
        )
        self.ping_service = PingService()
        self.alert_queue = []
        self.alert_lock = threading.Lock()
        self.current_interval = 5
        self.aggregate_interval = 1
        self.cleanup_time = "03:00"
        self.daily_report_enabled = False
        self.daily_report_time = "09:00"
        self.weekly_report_enabled = False
        self.weekly_report_time = "09:00"
        self.monthly_report_enabled = False
        self.monthly_report_time = "09:00"
        self.auto_refresh_location = False

    def start(self) -> None:
        self.reload_config(initial=True)

        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("监控调度器已启动")

        thread = threading.Thread(target=self.monitor_all_hosts, daemon=True)
        thread.start()

    def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("监控调度器已停止")

    def reload_config(self, initial: bool = False) -> None:
        db = SessionLocal()
        try:
            config = db.query(SystemConfig).first()
            if config:
                self.current_interval = config.check_interval
                self.aggregate_interval = config.aggregate_interval
                self.cleanup_time = config.cleanup_time or "03:00"
                self.auto_refresh_location = bool(config.auto_refresh_location)
                self.daily_report_enabled = bool(
                    config.daily_report_enabled and self._is_dingtalk_webhook(config.report_webhook_url)
                )
                self.daily_report_time = config.daily_report_time or "09:00"
                self.weekly_report_enabled = bool(
                    config.weekly_report_enabled and self._is_dingtalk_webhook(config.report_webhook_url)
                )
                self.weekly_report_time = config.weekly_report_time or "09:00"
                self.monthly_report_enabled = bool(
                    config.monthly_report_enabled and self._is_dingtalk_webhook(config.report_webhook_url)
                )
                self.monthly_report_time = config.monthly_report_time or "09:00"
            else:
                self.current_interval = 5
                self.aggregate_interval = 1
                self.cleanup_time = "03:00"
                self.auto_refresh_location = False
                self.daily_report_enabled = False
                self.daily_report_time = "09:00"
                self.weekly_report_enabled = False
                self.weekly_report_time = "09:00"
                self.monthly_report_enabled = False
                self.monthly_report_time = "09:00"
        finally:
            db.close()

        cleanup_hour, cleanup_minute = self.cleanup_time.split(":")
        daily_report_hour, daily_report_minute = self.daily_report_time.split(":")
        weekly_report_hour, weekly_report_minute = self.weekly_report_time.split(":")
        monthly_report_hour, monthly_report_minute = self.monthly_report_time.split(":")

        self._upsert_job(
            job_id="monitor_hosts",
            func=self.monitor_all_hosts,
            trigger="interval",
            replace_existing=True,
            minutes=self.current_interval,
        )
        self._upsert_job(
            job_id="hourly_aggregation",
            func=self._run_hourly_aggregation,
            trigger="cron",
            replace_existing=True,
            hour=f"*/{self.aggregate_interval}",
            minute=5,
        )
        self._upsert_job(
            job_id="daily_tasks",
            func=self._run_daily_tasks,
            trigger="cron",
            replace_existing=True,
            hour=int(cleanup_hour),
            minute=int(cleanup_minute),
        )
        self._sync_report_job(
            enabled=self.daily_report_enabled,
            job_id="daily_report",
            func=self._run_daily_report,
            trigger="cron",
            replace_existing=True,
            hour=int(daily_report_hour),
            minute=int(daily_report_minute),
        )
        self._sync_report_job(
            enabled=self.weekly_report_enabled,
            job_id="weekly_report",
            func=self._run_weekly_report,
            trigger="cron",
            replace_existing=True,
            day_of_week="mon",
            hour=int(weekly_report_hour),
            minute=int(weekly_report_minute),
        )
        self._sync_report_job(
            enabled=self.monthly_report_enabled,
            job_id="monthly_report",
            func=self._run_monthly_report,
            trigger="cron",
            replace_existing=True,
            day=1,
            hour=int(monthly_report_hour),
            minute=int(monthly_report_minute),
        )

        if not initial:
            logger.info(
                (
                    "调度配置已刷新: check_interval=%s, aggregate_interval=%s, cleanup_time=%s, "
                    "auto_refresh_location=%s, daily_report=%s@%s, weekly_report=%s@%s, monthly_report=%s@%s"
                ),
                self.current_interval,
                self.aggregate_interval,
                self.cleanup_time,
                self.auto_refresh_location,
                self.daily_report_enabled,
                self.daily_report_time,
                self.weekly_report_enabled,
                self.weekly_report_time,
                self.monthly_report_enabled,
                self.monthly_report_time,
            )

    def _upsert_job(self, *, job_id: str, func, trigger: str, replace_existing: bool, **kwargs) -> None:
        self._remove_job_if_exists(job_id)

        self.scheduler.add_job(
            func,
            trigger,
            id=job_id,
            replace_existing=replace_existing,
            **kwargs,
        )

    def _sync_report_job(self, *, enabled: bool, job_id: str, func, trigger: str, replace_existing: bool, **kwargs) -> None:
        if not enabled:
            self._remove_job_if_exists(job_id)
            return
        self._upsert_job(
            job_id=job_id,
            func=func,
            trigger=trigger,
            replace_existing=replace_existing,
            **kwargs,
        )

    def _remove_job_if_exists(self, job_id: str) -> None:
        existing = self.scheduler.get_job(job_id)
        if existing:
            self.scheduler.remove_job(job_id)

    @staticmethod
    def _is_dingtalk_webhook(webhook_url: str | None) -> bool:
        return bool(webhook_url and "oapi.dingtalk.com" in webhook_url)

    def update_interval(self, minutes: int) -> None:
        self.current_interval = minutes
        self._upsert_job(
            job_id="monitor_hosts",
            func=self.monitor_all_hosts,
            trigger="interval",
            replace_existing=True,
            minutes=minutes,
        )
        logger.info("监控间隔已更新为 %s 分钟", minutes)

    def monitor_all_hosts(self) -> None:
        start_time = datetime.now()
        with self.alert_lock:
            self.alert_queue = []

        db = SessionLocal()
        try:
            config = db.query(SystemConfig).first()
            packet_count = config.packet_count if config else 10
            packet_timeout = config.packet_timeout if config else 2
            notification_mode = config.notification_mode if config else "status_change"
            auto_refresh_location = bool(config.auto_refresh_location) if config else False
            hosts = db.query(Host).filter(Host.enabled.is_(True)).all()
        finally:
            db.close()

        if not hosts:
            logger.info("没有启用中的主机，跳过本轮监控")
            return

        backend = get_database_backend()
        max_workers = 4 if backend == "sqlite" else min(max(len(hosts), 4), 32)

        logger.info(
            "开始执行监控任务，主机数=%s, packet_count=%s, packet_timeout=%s, workers=%s",
            len(hosts),
            packet_count,
            packet_timeout,
            max_workers,
        )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    self._monitor_host_in_thread,
                    host.id,
                    packet_count,
                    packet_timeout,
                    notification_mode,
                    auto_refresh_location,
                )
                for host in hosts
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    logger.error("监控线程执行失败: %s", exc)

        duration = (datetime.now() - start_time).total_seconds()
        logger.info("监控任务完成，耗时 %.2f 秒", duration)

        cache_manager.invalidate_namespace("dashboard")
        cache_manager.invalidate_namespace("databoard")

        if self.alert_queue:
            logger.warning("本轮监控产生 %s 条告警", len(self.alert_queue))
            for alert_info in self.alert_queue:
                logger.warning(
                    "[%s] %s (%s) - 丢包率 %s, 阈值 %s, 延迟 %s",
                    alert_info["type"],
                    alert_info["host"],
                    alert_info["address"],
                    alert_info["packet_loss"],
                    alert_info["threshold"],
                    alert_info["rtt"],
                )

    def _monitor_host_in_thread(
        self,
        host_id: int,
        packet_count: int,
        packet_timeout: int,
        notification_mode: str,
        auto_refresh_location: bool,
    ) -> None:
        db = SessionLocal()
        try:
            host = db.query(Host).filter(Host.id == host_id).first()
            if host:
                self.monitor_single_host(
                    db,
                    host,
                    packet_count=packet_count,
                    packet_timeout=packet_timeout,
                    notification_mode=notification_mode,
                    auto_refresh_location=auto_refresh_location,
                )
        finally:
            db.close()

    def monitor_single_host(
        self,
        db: Session,
        host: Host,
        *,
        packet_count: int,
        packet_timeout: int,
        notification_mode: str,
        auto_refresh_location: bool,
    ) -> None:
        try:
            # DNS解析域名为IP
            import socket
            try:
                resolved_ip = socket.gethostbyname(host.address)
                if host.resolved_ip != resolved_ip:
                    host.resolved_ip = resolved_ip
                    db.commit()
            except socket.gaierror:
                # 解析失败，保持原有IP或设为None
                if host.resolved_ip is None:
                    host.resolved_ip = host.address
                    db.commit()

            result = self.ping_service.ping_host(
                host.address,
                count=packet_count,
                timeout=packet_timeout,
            )

            record = PingRecord(
                host_id=host.id,
                packet_sent=result["packet_sent"],
                packet_received=result["packet_received"],
                packet_loss=result["packet_loss"],
                min_rtt=result["min_rtt"],
                max_rtt=result["max_rtt"],
                avg_rtt=result["avg_rtt"],
                created_at=datetime.now(),
            )
            db.add(record)
            db.commit()

            current_status = "normal"
            if result["status"] == "unreachable" or result["packet_loss"] >= host.alert_threshold:
                current_status = "abnormal"

            last_status = host.last_status
            should_alert = False

            if notification_mode == "status_change":
                if last_status is None and current_status == "abnormal":
                    should_alert = True
                elif last_status is not None and last_status != current_status:
                    should_alert = True
            elif notification_mode == "every_time" and current_status == "abnormal":
                should_alert = True

            host.last_status = current_status
            db.commit()

            if should_alert:
                self._handle_host_alert(db, host, result, current_status, last_status)
            if host.resolved_ip and (auto_refresh_location or host_needs_location_completion(host)):
                try:
                    location = asyncio.run(
                        ip_location_service.get_location(
                            host.resolved_ip,
                            force_refresh=bool(auto_refresh_location),
                        )
                    )
                    apply_location_result(
                        host,
                        location,
                        overwrite_existing=bool(auto_refresh_location),
                    )
                    db.commit()
                except Exception as geo_exc:
                    db.rollback()
                    logger.warning("涓绘満 %s 鍦扮悊浣嶇疆鍚屾澶辫触: %s", host.name, geo_exc)
        except Exception as exc:
            logger.error("监控主机 %s 失败: %s", host.name, exc)

    def _handle_host_alert(self, db: Session, host: Host, result: dict, current_status: str, last_status: str | None) -> None:
        if current_status == "abnormal":
            if result["packet_loss"] >= host.alert_threshold:
                alert_type = "packet_loss"
                msg_data = NotificationTemplate.get_abnormal_alert(
                    host_name=host.name,
                    host_address=host.address,
                    packet_loss=result["packet_loss"],
                    alert_threshold=host.alert_threshold,
                    avg_rtt=result["avg_rtt"],
                    use_markdown=True,
                )
                rtt_text = f"{result['avg_rtt']:.2f}ms" if result["avg_rtt"] is not None else "无数据"
            else:
                alert_type = "unreachable"
                msg_data = NotificationTemplate.get_unreachable_alert(
                    host_name=host.name,
                    host_address=host.address,
                    use_markdown=True,
                )
                rtt_text = "无响应"

            with self.alert_lock:
                self.alert_queue.append(
                    {
                        "type": alert_type,
                        "host": host.name,
                        "address": host.address,
                        "packet_loss": f"{result['packet_loss']:.1f}%",
                        "threshold": f"{host.alert_threshold:.0f}%",
                        "rtt": rtt_text,
                    }
                )

            alert = Alert(
                host_id=host.id,
                host_name=host.name,
                alert_type=alert_type,
                message=msg_data["content"],
                is_sent=False,
                created_at=datetime.now(),
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)
            self._send_alert_notification(alert.id, msg_data["content"], alert_type, msg_data["title"])
            return

        if current_status == "normal" and last_status == "abnormal":
            msg_data = NotificationTemplate.get_recovery_alert(
                host_name=host.name,
                host_address=host.address,
                packet_loss=result["packet_loss"],
                avg_rtt=result["avg_rtt"],
                use_markdown=True,
            )
            alert = Alert(
                host_id=host.id,
                host_name=host.name,
                alert_type="recovery",
                message=msg_data["content"],
                is_sent=False,
                created_at=datetime.now(),
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)
            self._send_alert_notification(alert.id, msg_data["content"], "recovery", msg_data["title"])

    def _send_alert_notification(self, alert_id: int, message: str, alert_type: str, title: str | None = None) -> None:
        thread = threading.Thread(
            target=self._do_send_notification,
            args=(alert_id, message, alert_type, title),
            daemon=True,
        )
        thread.start()

    def _do_send_notification(self, alert_id: int, message: str, alert_type: str, title: str | None = None) -> None:
        db = SessionLocal()
        try:
            from notification import notifier

            config = db.query(SystemConfig).first()
            if not config:
                return

            notifier.configure(
                serverchan_key=config.serverchan_key,
                webhook_url=config.webhook_url,
                webhook_secret=config.webhook_secret,
            )

            success = False
            if config.serverchan_key:
                success = notifier.send_serverchan(title or "告警通知", message)
            elif config.webhook_url:
                success = notifier.send_webhook(message, alert_type=alert_type, title=title)

            if success:
                alert = db.query(Alert).filter(Alert.id == alert_id).first()
                if alert:
                    alert.is_sent = True
                    db.commit()
        except Exception as exc:
            logger.error("发送告警通知失败: %s", exc)
        finally:
            db.close()

    def _run_hourly_aggregation(self) -> None:
        from data_maintenance import DataMaintenance

        logger.info("开始执行小时聚合任务")
        DataMaintenance.aggregate_hourly_stats()

    def _run_daily_tasks(self) -> None:
        from data_maintenance import DataMaintenance

        logger.info("开始执行每日维护任务")
        DataMaintenance.aggregate_daily_stats()
        DataMaintenance.cleanup_old_records()

    def _run_daily_report(self) -> None:
        from report_service import ReportService

        logger.info("开始发送日报")
        ReportService.send_report_with_new_session("daily", trigger_source="scheduler")

    def _run_weekly_report(self) -> None:
        from report_service import ReportService

        logger.info("开始发送周报")
        ReportService.send_report_with_new_session("weekly", trigger_source="scheduler")

    def _run_monthly_report(self) -> None:
        from report_service import ReportService

        logger.info("开始发送月报")
        ReportService.send_report_with_new_session("monthly", trigger_source="scheduler")


scheduler = MonitorScheduler()
