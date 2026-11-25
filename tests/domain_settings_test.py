"""Verify domain settings, channel isolation and the runtime behavior they control."""
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
import asyncio
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from aliyun_sms import SmsResult
from auth import get_current_user
from database import Base, DomainAlert, DomainAlertDelivery, MonitoredDomain, SystemConfig, get_db
import database_migrations
from domain_api import router
import domain_monitor
from domain_probes import result

HOST_URL = "https://oapi.dingtalk.com/robot/send?access_token=host-test-only"
DOMAIN_URL = "https://oapi.dingtalk.com/robot/send?access_token=domain-test-only"
REPORT_URL = "https://oapi.dingtalk.com/robot/send?access_token=report-test-only"
SMS_SETTINGS = {
    "sms_access_key_id": "LTAIunittestonly",
    "sms_access_key_secret": "unit-test-secret",
    "sms_sign_name": "测试签名",
    "sms_template_code": "SMS_100000001",
    "sms_phone_numbers": "13800000000\n13900000000",
}


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
            self.assertEqual(self.client.get("/api/domains/notification/status").status_code, 403)
            self.assertEqual(self.client.post("/api/domains/notification/sms/test").status_code, 403)
            send.assert_not_called()

    def test_legacy_notification_and_domain_edits_do_not_erase_new_channels(self):
        endpoint = "/api/domains/notification"
        self.client.put(endpoint, json={"webhook_url": DOMAIN_URL, "webhook_secret": "domain-secret"}).raise_for_status()
        response = self.client.put(endpoint, json=SMS_SETTINGS)
        self.assertEqual(response.json()["webhook_url"], DOMAIN_URL)
        self.assertEqual(response.json()["webhook_secret"], "domain-secret")
        # An older client that only knows DingTalk must not erase SMS.
        response = self.client.put(endpoint, json={"webhook_url": DOMAIN_URL, "webhook_secret": "new-secret"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["sms_template_code"], "SMS_100000001")
        self.assertTrue(response.json()["sms_access_key_secret_set"])
        domain = self.client.get("/api/domains").json()[0]
        domain_path = f"/api/domains/{domain['id']}"
        self.client.patch(f"{domain_path}/state", json={"notify_sms": True}).raise_for_status()
        edited = self.client.put(domain_path, json={
            "name": domain["name"], "expected_ns": domain["expected_ns"], "notify": False,
        })
        edited.raise_for_status()
        self.assertTrue(edited.json()["notify_sms"])
        self.assertFalse(edited.json()["notify"])
        self.assertTrue(self.client.patch(f"{domain_path}/state", json={"notify_sms": None}).json()["notify_sms"])

    def test_sms_settings_keep_the_secret_write_only_and_report_status(self):
        response = self.client.put("/api/domains/notification", json={
            "webhook_url": DOMAIN_URL, "webhook_secret": "domain-secret", **SMS_SETTINGS,
        })
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertNotIn("sms_access_key_secret", body)
        self.assertNotIn("unit-test-secret", response.text)
        self.assertNotIn("unit-test-secret", self.client.get("/api/domains/notification").text)
        self.assertTrue(body["sms_access_key_secret_set"])
        self.assertEqual(body["sms_phone_numbers"], "13800000000\n13900000000")
        self.assertEqual(self.client.get("/api/domains/notification/status").json(), {
            "dingtalk_configured": True, "sms_configured": True,
        })
        with self.sessions() as db:
            config = db.query(SystemConfig).one()
            self.assertEqual(config.sms_access_key_secret, "unit-test-secret")
            self.assertEqual(config.sms_phone_numbers, "13800000000,13900000000")
            self.assertEqual((config.domain_webhook_url, config.domain_webhook_secret), (DOMAIN_URL, "domain-secret"))

        # Saving without a secret keeps the stored one.
        self.client.put("/api/domains/notification", json={
            **SMS_SETTINGS, "sms_access_key_secret": "", "sms_sign_name": "新签名",
        }).raise_for_status()
        with self.sessions() as db:
            config = db.query(SystemConfig).one()
            self.assertEqual((config.sms_access_key_secret, config.sms_sign_name), ("unit-test-secret", "新签名"))

        # Clearing every SMS field turns SMS off and removes the credential.
        cleared = self.client.put("/api/domains/notification", json={key: "" for key in SMS_SETTINGS})
        self.assertEqual(cleared.status_code, 200)
        self.assertFalse(cleared.json()["sms_access_key_secret_set"])
        with self.sessions() as db:
            config = db.query(SystemConfig).one()
            self.assertIsNone(config.sms_access_key_id)
            self.assertIsNone(config.sms_access_key_secret)
        self.assertFalse(self.client.get("/api/domains/notification/status").json()["sms_configured"])

    def test_incomplete_or_invalid_sms_settings_are_rejected(self):
        for change in (
            {"sms_template_code": ""}, {"sms_phone_numbers": ""}, {"sms_access_key_secret": ""},
            {"sms_template_code": "12345"}, {"sms_sign_name": "【测试】"},
            {"sms_phone_numbers": "13800000000,abc"}, {"sms_access_key_id": "bad id!"},
        ):
            with self.subTest(change=change):
                self.assertEqual(self.client.put("/api/domains/notification", json={**SMS_SETTINGS, **change}).status_code, 422)
        with self.sessions() as db:
            self.assertIsNone(db.query(SystemConfig).one().sms_access_key_id)

    def add_queued_sms(self, status="pending"):
        with self.sessions() as db:
            domain = db.query(MonitoredDomain).one()
            domain.notify_sms = True
            event = DomainAlert(
                domain_id=domain.id, domain_name=domain.name, alert_type="domain_critical",
                message="test", delivery_status="no_channel", created_at=datetime.now(),
            )
            db.add(event)
            db.flush()
            delivery = DomainAlertDelivery(
                domain_alert_id=event.id, channel="sms",
                status=status, next_attempt_at=datetime.now(), created_at=datetime.now(),
            )
            db.add(delivery)
            db.commit()
            return delivery.id

    def test_clearing_sms_configuration_stops_pending_delivery_without_replay(self):
        self.client.put("/api/domains/notification", json=SMS_SETTINGS).raise_for_status()
        delivery_id = self.add_queued_sms()
        self.client.put("/api/domains/notification", json={key: "" for key in SMS_SETTINGS}).raise_for_status()
        with self.sessions() as db:
            delivery = db.get(DomainAlertDelivery, delivery_id)
            self.assertEqual(delivery.status, "no_channel")
            self.assertIsNone(delivery.next_attempt_at)

    def test_changing_recipients_keeps_queued_sms_for_the_new_numbers(self):
        self.client.put("/api/domains/notification", json=SMS_SETTINGS).raise_for_status()
        delivery_id = self.add_queued_sms("failed")
        self.client.put("/api/domains/notification", json={"sms_phone_numbers": "13700000000"}).raise_for_status()
        with self.sessions() as db:
            delivery = db.get(DomainAlertDelivery, delivery_id)
            self.assertEqual(delivery.status, "failed")
            self.assertIsNotNone(delivery.next_attempt_at)
            self.assertEqual(db.query(SystemConfig).one().sms_phone_numbers, "13700000000")

    def test_domain_monitor_and_notification_switches_are_independent(self):
        response = self.client.patch("/api/domains/1/state", json={"notify": False})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["enabled"])
        self.assertFalse(response.json()["notify"])

        response = self.client.patch("/api/domains/1/state", json={"enabled": False})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["enabled"])
        self.assertFalse(response.json()["notify"])

        response = self.client.patch("/api/domains/1/state", json={"notify": True})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["enabled"])
        self.assertTrue(response.json()["notify"])

        response = self.client.patch("/api/domains/1/state", json={"enabled": True})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["enabled"])
        self.assertTrue(response.json()["notify"])

    def test_non_admin_cannot_update_domain_switches(self):
        self.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(is_admin=False)
        response = self.client.patch("/api/domains/1/state", json={"enabled": False})
        self.assertEqual(response.status_code, 403)

    def test_bulk_state_update_is_atomic_and_updates_requested_domains_only(self):
        with self.sessions() as db:
            second = MonitoredDomain(name="example.net", expected_ns=["ns.example.net"], records=[])
            db.add(second)
            db.commit()
            second_id = second.id

        response = self.client.patch("/api/domains/bulk-state", json={
            "ids": [1, second_id], "enabled": False, "notify_sms": True,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["updated"], 2)
        self.assertTrue(all(not row["enabled"] and row["notify_sms"] for row in response.json()["items"]))

        response = self.client.patch("/api/domains/bulk-state", json={
            "ids": [1, 999], "notify": False,
        })
        self.assertEqual(response.status_code, 404)
        with self.sessions() as db:
            self.assertTrue(db.get(MonitoredDomain, 1).notify)
            self.assertTrue(db.get(MonitoredDomain, second_id).notify)

    def test_sms_test_uses_the_saved_settings_and_reports_failures(self):
        self.assertEqual(self.client.post("/api/domains/notification/sms/test").status_code, 400)
        self.client.put("/api/domains/notification", json=SMS_SETTINGS).raise_for_status()
        with patch("domain_api.send_configured_sms", return_value=SmsResult(True, biz_id="900")) as send:
            response = self.client.post("/api/domains/notification/sms/test")
        self.assertEqual(response.status_code, 200)
        self.assertIn("2 个号码", response.json()["message"])
        config, params = send.call_args.args
        self.assertEqual(config.sms_template_code, "SMS_100000001")
        self.assertEqual(set(params), {"name", "time", "status", "msg"})
        self.assertEqual(params["status"], "测试")
        with patch("domain_api.send_configured_sms", return_value=SmsResult(False, "isv.SMS_SIGNATURE_ILLEGAL: 签名不合法")):
            response = self.client.post("/api/domains/notification/sms/test")
        self.assertEqual(response.status_code, 502)
        self.assertIn("isv.SMS_SIGNATURE_ILLEGAL", response.json()["detail"])

    def test_sms_test_respects_disabled_external_notification_environment(self):
        self.client.put("/api/domains/notification", json=SMS_SETTINGS).raise_for_status()
        with patch("domain_api.settings.disable_notifications", True), \
                patch("domain_api.settings.allow_test_notifications", False), \
                patch("domain_api.send_configured_sms") as send:
            response = self.client.post("/api/domains/notification/sms/test")
        self.assertEqual(response.status_code, 503)
        self.assertIn("ALLOW_TEST_NOTIFICATIONS", response.json()["detail"])
        send.assert_not_called()

    def test_manual_tests_can_be_allowed_while_automatic_notifications_stay_off(self):
        self.client.put("/api/domains/notification", json={**SMS_SETTINGS, "webhook_url": DOMAIN_URL}).raise_for_status()
        self.client.patch("/api/domains/1/state", json={"notify_sms": True}).raise_for_status()
        with self.sessions() as db:
            domain = db.query(MonitoredDomain).one()
            domain_monitor.queue_alert(db, domain, "domain_critical", "- 权威 DNS：异常", datetime.now())
            db.commit()
        with patch.object(domain_monitor, "SessionLocal", self.sessions), \
                patch("domain_api.settings.disable_notifications", True), \
                patch("domain_api.settings.allow_test_notifications", True), \
                patch("domain_api.send_configured_sms", return_value=SmsResult(True, biz_id="901")) as test_sms, \
                patch("domain_monitor.send_configured_sms") as alert_sms, \
                patch("notification.requests.post") as post:
            post.return_value.status_code = 200
            post.return_value.json.return_value = {"errcode": 0}
            sms = self.client.post("/api/domains/notification/sms/test")
            dingtalk = self.client.post("/api/domains/notification/test", json={"alert_type": "domain_warning"})
            domain_monitor.deliver_pending()   # the automatic path still obeys DISABLE_NOTIFICATIONS
        self.assertEqual((sms.status_code, dingtalk.status_code), (200, 200))
        test_sms.assert_called_once()
        self.assertEqual(post.call_count, 1)
        alert_sms.assert_not_called()
        with self.sessions() as db:
            self.assertEqual(db.query(DomainAlert).one().delivery_status, "pending")
            self.assertEqual(db.query(DomainAlertDelivery).filter_by(channel="sms").one().status, "pending")

    def test_dingtalk_test_reports_disabled_environment_clearly(self):
        self.client.put("/api/domains/notification", json={"webhook_url": DOMAIN_URL}).raise_for_status()
        with patch("domain_api.settings.disable_notifications", True), \
                patch("domain_api.settings.allow_test_notifications", False), \
                patch("notification.requests.post") as post:
            response = self.client.post("/api/domains/notification/test", json={"alert_type": "domain_warning"})
        self.assertEqual(response.status_code, 503)
        post.assert_not_called()

    def test_alert_list_exposes_sms_delivery_separately_from_dingtalk(self):
        with self.sessions() as db:
            domain = db.query(MonitoredDomain).one()
            event = DomainAlert(
                domain_id=domain.id, domain_name=domain.name, alert_type="domain_critical",
                message="confirmed failure", delivery_status="sent", is_sent=True,
                created_at=datetime.now(),
            )
            db.add(event)
            db.flush()
            db.add(DomainAlertDelivery(
                domain_alert_id=event.id, channel="sms",
                status="failed", attempts=2, last_error="isv.MOBILE_NUMBER_ILLEGAL: 号码格式错误", created_at=datetime.now(),
            ))
            db.commit()

            from main import get_alerts
            for source in ("domain", None):
                with self.subTest(source=source):
                    result = asyncio.run(get_alerts(
                        db=db, hours=24, page=1, page_size=20, source=source,
                        current_user=SimpleNamespace(is_admin=True),
                    ))
                    item = result["items"][0]
                    self.assertEqual(item["delivery_status"], "sent")
                    self.assertEqual(item["sms_delivery_status"], "failed")
                    self.assertEqual(item["sms_delivery_error"], "isv.MOBILE_NUMBER_ILLEGAL: 号码格式错误")

    def test_dingtalk_switch_does_not_stop_sms_until_sms_is_off(self):
        self.client.put("/api/domains/notification", json=SMS_SETTINGS).raise_for_status()
        with self.sessions() as db:
            config = db.query(SystemConfig).one()
            domain = db.query(MonitoredDomain).one()
            domain.notify_sms = True
            event = DomainAlert(
                domain_id=domain.id, domain_name=domain.name, alert_type="domain_critical",
                message="test", delivery_status="pending", created_at=datetime.now(),
            )
            db.add(event)
            db.flush()
            delivery = DomainAlertDelivery(
                domain_alert_id=event.id, channel="sms",
                status="pending", next_attempt_at=datetime.now(), created_at=datetime.now(),
            )
            db.add(delivery)
            db.commit()
            delivery_id = delivery.id

        self.client.patch("/api/domains/1/state", json={"notify": False}).raise_for_status()
        with self.sessions() as db:
            self.assertEqual(db.get(DomainAlertDelivery, delivery_id).status, "pending")

        self.client.patch("/api/domains/1/state", json={"notify_sms": False}).raise_for_status()
        with self.sessions() as db:
            delivery = db.get(DomainAlertDelivery, delivery_id)
            self.assertEqual(delivery.status, "disabled")
            self.assertIsNone(delivery.next_attempt_at)

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

    def test_each_notification_preview_uses_its_requested_event_template(self):
        self.client.put("/api/domains/notification", json={
            "webhook_url": DOMAIN_URL, "webhook_secret": "domain-secret",
        }).raise_for_status()
        for alert_type in ("domain_warning", "domain_critical", "domain_recovery", "domain_expiry"):
            with self.subTest(alert_type=alert_type), patch("domain_api.NotificationService") as service:
                service.return_value.send_webhook.return_value = True
                response = self.client.post("/api/domains/notification/test", json={"alert_type": alert_type})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["alert_type"], alert_type)
                send = service.return_value.send_webhook.call_args
                self.assertEqual(send.kwargs["alert_type"], alert_type)
                self.assertIn("模板测试", send.kwargs["title"])
                service.return_value.configure.assert_called_once_with(
                    webhook_url=DOMAIN_URL, webhook_secret="domain-secret",
                )

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
