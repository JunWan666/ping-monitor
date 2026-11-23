"""Verify domain settings, channel isolation and the runtime behavior they control."""
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from auth import get_current_user
from database import Base, DomainAlert, MonitoredDomain, SystemConfig, get_db
import database_migrations
from domain_api import router
import domain_monitor
from domain_probes import result

HOST_URL = "https://oapi.dingtalk.com/robot/send?access_token=host-test-only"
DOMAIN_URL = "https://oapi.dingtalk.com/robot/send?access_token=domain-test-only"
REPORT_URL = "https://oapi.dingtalk.com/robot/send?access_token=report-test-only"


class DomainSettingsTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, expire_on_commit=False)
        with self.sessions() as db:
            db.add(SystemConfig(
                webhook_url=HOST_URL, webhook_secret="host-secret",
                report_webhook_url=REPORT_URL, report_webhook_secret="report-secret",
            ))
            db.add(MonitoredDomain(name="example.com", expected_ns=["ns.example.com"], records=[]))
            db.commit()
        app = FastAPI()
        app.include_router(router)

        def database():
            with self.sessions() as db:
                yield db

        app.dependency_overrides[get_db] = database
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(is_admin=True)
        self.app = app
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        self.engine.dispose()

    def test_settings_survive_reload_without_overwriting_any_notification_channel(self):
        self.assertEqual(self.client.get("/api/domains/settings").json()["dns_interval"], 1)
        self.client.put("/api/domains/notification", json={
            "webhook_url": DOMAIN_URL, "webhook_secret": "domain-secret",
        }).raise_for_status()
        self.client.put("/api/domains/settings", json={
            "dns_interval": 30, "rdap_interval": 2, "confirmation_count": 3,
            "expiry_days": [90, 14, 3, 14],
        }).raise_for_status()
        self.assertEqual(self.client.get("/api/domains/settings").json(), {
            "dns_interval": 30, "rdap_interval": 2, "confirmation_count": 3, "expiry_days": [90, 14, 3],
        })
        with self.sessions() as db:
            config = db.query(SystemConfig).one()
            self.assertEqual((config.webhook_url, config.webhook_secret), (HOST_URL, "host-secret"))
            self.assertEqual((config.report_webhook_url, config.report_webhook_secret), (REPORT_URL, "report-secret"))
            self.assertEqual((config.domain_webhook_url, config.domain_webhook_secret), (DOMAIN_URL, "domain-secret"))

    def test_non_admin_cannot_read_or_change_domain_settings_or_test_channel(self):
        self.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(is_admin=False)
        with patch("notification.requests.post") as send:
            for path in ("settings", "notification"):
                self.assertEqual(self.client.get(f"/api/domains/{path}").status_code, 403)
                self.assertEqual(self.client.put(f"/api/domains/{path}", json={}).status_code, 403)
            self.assertEqual(self.client.post("/api/domains/notification/test").status_code, 403)
            send.assert_not_called()

    def test_invalid_policy_and_webhook_are_rejected_before_saving(self):
        for payload in ({"dns_interval": 0}, {"rdap_interval": 1441}, {"confirmation_count": 11},
                        {"expiry_days": [366]}, {"expiry_days": [-1]}, {"expiry_days": [1.5]}):
            with self.subTest(payload=payload):
                self.assertEqual(self.client.put("/api/domains/settings", json=payload).status_code, 422)
        for url in ("http://oapi.dingtalk.com/robot/send?access_token=x", "https://example.com/",
                    "https://oapi.dingtalk.com.evil.test/robot/send?access_token=x",
                    "https://oapi.dingtalk.com/robot/send?access_token="):
            self.assertEqual(self.client.put("/api/domains/notification", json={"webhook_url": url}).status_code, 422)
        self.assertEqual(self.client.get("/api/domains/settings").json()["dns_interval"], 1)

    def test_test_message_uses_only_domain_robot_and_handles_failure(self):
        self.client.put("/api/domains/notification", json={
            "webhook_url": DOMAIN_URL, "webhook_secret": "domain-secret",
        }).raise_for_status()
        with patch("domain_api.NotificationService") as service:
            service.return_value.send_webhook.return_value = True
            self.assertEqual(self.client.post("/api/domains/notification/test").status_code, 200)
            service.return_value.configure.assert_called_once_with(
                webhook_url=DOMAIN_URL, webhook_secret="domain-secret",
            )
            self.assertIn("模板测试", service.return_value.send_webhook.call_args.kwargs["title"])
            service.return_value.send_webhook.return_value = False
            self.assertEqual(self.client.post("/api/domains/notification/test").status_code, 502)

    def test_missing_domain_channel_never_falls_back_to_host_robot_or_replays_old_events(self):
        with self.sessions() as db:
            domain = db.query(MonitoredDomain).one()
            domain_monitor.queue_alert(db, domain, "domain_warning", "测试", datetime.now())
            db.commit()
        with patch.object(domain_monitor, "SessionLocal", self.sessions), \
                patch.object(domain_monitor.settings, "disable_notifications", False), \
                patch("notification.requests.post") as send:
            domain_monitor.deliver_pending()
            send.assert_not_called()
            with self.sessions() as db:
                event = db.scalars(select(DomainAlert)).one()
                self.assertEqual(event.delivery_status, "no_channel")
                self.assertIsNone(event.next_attempt_at)
            self.assertEqual(self.client.post("/api/domains/notification/test").status_code, 400)
            self.client.put("/api/domains/notification", json={"webhook_url": DOMAIN_URL}).raise_for_status()
            domain_monitor.deliver_pending()
            send.assert_not_called()

    def test_dns_and_registry_schedules_work_independently(self):
        now = datetime.now()
        with self.sessions() as db:
            config = db.query(SystemConfig).one()
            config.domain_dns_interval, config.domain_rdap_interval = 30, 1
            domain = db.query(MonitoredDomain).one()
            domain.last_checked_at, domain.rdap_checked_at = now, now - timedelta(minutes=2)
            db.commit()
        with patch.object(domain_monitor, "SessionLocal", self.sessions), \
                patch.object(domain_monitor, "deliver_pending"), \
                patch.object(domain_monitor, "dns_checks", return_value={"delegation": result("ok", "DNS 正常")}) as dns, \
                patch.object(domain_monitor, "lookup_rdap", return_value=result("ok", "注册状态正常")) as rdap:
            domain_monitor.run_domain_monitor()
            dns.assert_not_called()
            rdap.assert_called_once_with("example.com")
            with self.sessions() as db:
                domain = db.query(MonitoredDomain).one()
                self.assertEqual(domain.last_checked_at, now)
                self.assertGreater(domain.rdap_checked_at, now - timedelta(seconds=1))
                config = db.query(SystemConfig).one()
                config.domain_dns_interval, config.domain_rdap_interval = 1, 30
                domain.last_checked_at = now - timedelta(minutes=2)
                db.commit()
            rdap.reset_mock()
            domain_monitor.run_domain_monitor()
            dns.assert_called_once()
            rdap.assert_not_called()

    def test_saved_confirmation_count_controls_warning_and_recovery(self):
        self.client.put("/api/domains/settings", json={"confirmation_count": 3}).raise_for_status()
        with self.sessions() as db:
            config = db.query(SystemConfig).one()
            domain = db.query(MonitoredDomain).one()
            for expected_level in (0, 0, 1):
                domain_monitor.record_results(db, domain, {"delegation": result("bad", "NS 不一致")}, datetime.now(), config=config)
                self.assertEqual(domain.incident_level, expected_level)
            for expected_level in (1, 1, 0):
                domain_monitor.record_results(db, domain, {"delegation": result("ok", "NS 正常")}, datetime.now(), config=config)
                self.assertEqual(domain.incident_level, expected_level)
            domain_monitor.record_results(db, domain, {"delegation": result("bad", "NS 已确认被改", level=2) | {"immediate": True}}, datetime.now(), config=config)
            self.assertEqual(domain.incident_level, 2)

    def test_custom_expiry_nodes_manual_override_and_empty_nodes(self):
        now = datetime(2026, 11, 19, 12)
        self.client.put("/api/domains/settings", json={"expiry_days": [14, 3]}).raise_for_status()
        with self.sessions() as db:
            config = db.query(SystemConfig).one()
            domain = db.query(MonitoredDomain).one()
            domain.manual_expiry = now.date() + timedelta(days=10)
            for _ in range(2):
                domain_monitor.record_results(db, domain, {}, now, config=config)
            events = db.scalars(select(DomainAlert)).all()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].alert_type, "domain_expiry")
            self.assertIn("14 天内", events[0].message)
            self.assertIn("手动填写", events[0].message)
        check = domain_monitor.expire_check({}, now, now.date() + timedelta(days=1), reminder_days=[])
        self.assertEqual(check["state"], "ok")
        check = domain_monitor.expire_check({}, now, now.date() - timedelta(days=1), reminder_days=[])
        self.assertIn("已经到期", check["detail"])


class DomainSettingsMigrationTest(unittest.TestCase):
    def test_existing_dashboard_trend_limit_is_capped_at_five(self):
        engine = create_engine("sqlite://")
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE system_config (id INTEGER PRIMARY KEY, dashboard_chart_points INTEGER NOT NULL)"
            )
            connection.exec_driver_sql("INSERT INTO system_config VALUES (1, 12), (2, 5), (3, 3)")
        with patch.object(database_migrations, "engine", engine), \
                patch.object(database_migrations.DatabaseMigration, "auto_sync_table_structure", return_value=[]):
            database_migrations.DatabaseMigration.run_migrations()
            with engine.connect() as connection:
                values = connection.exec_driver_sql(
                    "SELECT dashboard_chart_points FROM system_config ORDER BY id"
                ).scalars().all()
        engine.dispose()
        self.assertEqual(values, [5, 5, 3])

    def test_existing_database_gets_defaults_without_copying_host_credentials(self):
        engine = create_engine("sqlite://")
        with engine.begin() as conn:
            conn.exec_driver_sql("CREATE TABLE system_config (id INTEGER PRIMARY KEY, webhook_url VARCHAR(1000))")
            conn.exec_driver_sql("INSERT INTO system_config VALUES (1, ?)", (HOST_URL,))
        sessions = sessionmaker(bind=engine)
        with patch.object(database_migrations, "engine", engine), patch.object(database_migrations, "SessionLocal", sessions):
            database_migrations.DatabaseMigration.auto_sync_table_structure()
            with sessions() as db:
                config = db.query(SystemConfig).one()
                self.assertEqual(config.domain_dns_interval, 1)
                self.assertEqual(config.domain_rdap_interval, 5)
                self.assertEqual(config.domain_confirmation_count, 2)
                self.assertEqual(domain_monitor.expiry_reminder_days(config), (60, 30, 15, 7, 1))
                self.assertEqual(config.webhook_url, HOST_URL)
                self.assertIsNone(config.domain_webhook_url)
            self.assertEqual(database_migrations.DatabaseMigration.auto_sync_table_structure(), [])
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
