"""Run with: python -m unittest discover -s tests -p '*_test.py'."""
from datetime import datetime
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import requests
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, DomainAlert, MonitoredDomain, SystemConfig
import domain_monitor
from notification_template import NotificationTemplate

DETAIL = "- 父区 NS 委派探测异常：a.zdnscloud.cn Timeout；b.zdnscloud.cn 已返回预期 NS"
CHINESE = "中文通知验证：域名监控与钉钉加签"
KINDS = ("domain_critical", "domain_warning", "domain_recovery", "domain_expiry")


class DomainTemplateTest(unittest.TestCase):
    def test_matches_existing_host_notification_structure(self):
        for kind in KINDS:
            with self.subTest(kind=kind):
                template = NotificationTemplate.get_domain_alert(
                    "cpolar.top", kind, DETAIL, created_at=datetime(2026, 11, 19, 21, 30),
                )
                text = template["content"]
                self.assertTrue(text.startswith("### "))
                self.assertIn("\n> **", text)
                self.assertIn("\n---\n", text)
                self.assertIn("**监控域名：** [cpolar.top]", text)
                self.assertIn("<font color=", text)
                self.assertIn("📅 **通知时间：**", text)
                self.assertIn("发现时间", text)
                self.assertNotIn("????", text)
                self.assertNotIn("Timeout", text)

    def test_probe_failure_does_not_claim_domain_outage(self):
        text = NotificationTemplate.get_domain_alert(
            "cpolar.top", "domain_warning", DETAIL,
        )["content"]
        self.assertIn("尚未确认域名故障", text)
        self.assertIn("查询超时", text)
        self.assertIn("- a.zdnscloud.cn 查询超时", text)
        self.assertIn("- b.zdnscloud.cn 已返回预期 NS", text)

    def test_partial_dns_failure_is_distinct_from_probe_failure(self):
        text = NotificationTemplate.get_domain_alert(
            "cpolar.top", "domain_warning", "- 公共 DNS 解析：阿里公共 DNS NXDOMAIN",
        )["content"]
        self.assertIn("域名不存在（NXDOMAIN）", text)
        self.assertNotIn("尚未确认域名故障", text)

    def test_plain_text_and_test_messages_are_explicit(self):
        template = NotificationTemplate.get_domain_alert(
            "cpolar.top", "domain_warning", CHINESE, use_markdown=False, is_test=True,
        )
        self.assertIn("模板测试", template["title"])
        self.assertIn(CHINESE, template["content"])
        self.assertIn("不代表新发生的故障", template["content"])
        self.assertNotIn("<font", template["content"])
        self.assertNotIn("###", template["content"])

    def test_html_in_probe_details_is_not_rendered_as_markup(self):
        text = NotificationTemplate.get_domain_alert(
            "example.com", "domain_warning", "- 解析证据：<unsafe>",
        )["content"]
        self.assertIn("&lt;unsafe&gt;", text)
        self.assertNotIn("<unsafe>", text)


class DomainNotificationDeliveryTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine, expire_on_commit=False)
        with self.sessions() as db:
            db.add(SystemConfig(
                domain_webhook_url="https://oapi.dingtalk.com/robot/send?access_token=unit-test-only",
                domain_webhook_secret="unit-test-only",
            ))
            domain = MonitoredDomain(
                name="cpolar.top", expected_ns=["vip1.alidns.com"], records=[],
                enabled=True, notify=True, reminder_minutes=0,
            )
            db.add(domain)
            db.commit()
            self.domain_id = domain.id
        self.session_patch = patch.object(domain_monitor, "SessionLocal", self.sessions)
        self.disable_patch = patch.object(domain_monitor.settings, "disable_notifications", False)
        self.session_patch.start()
        self.disable_patch.start()

    def tearDown(self):
        self.disable_patch.stop()
        self.session_patch.stop()
        self.engine.dispose()

    def test_saved_unicode_survives_signed_dingtalk_payload_and_delivery(self):
        for kind in KINDS:
            with self.sessions() as db:
                domain = db.get(MonitoredDomain, self.domain_id)
                domain_monitor.queue_alert(db, domain, kind, CHINESE + "\n" + DETAIL, datetime.now())
                db.commit()
        response = Mock(status_code=200)
        response.json.return_value = {"errcode": 0}
        captured = []

        def receive(url, **kwargs):
            # Exercise Requests' actual JSON serialization too.
            body = requests.Request("POST", url, json=kwargs["json"]).prepare().body
            payload = json.loads(body)
            captured.append((url, payload))
            return response

        with patch("notification.requests.post", side_effect=receive):
            domain_monitor.deliver_pending()
        self.assertEqual(len(captured), 4)
        for url, payload in captured:
            self.assertIn("&timestamp=", url)
            self.assertIn("&sign=", url)
            self.assertEqual(payload["msgtype"], "markdown")
            self.assertIn("中文通知验证", payload["markdown"]["text"])
            self.assertIn("域名监控与钉钉加签", payload["markdown"]["text"])
            self.assertIn("通知时间", payload["markdown"]["text"])
            self.assertNotIn("????", payload["markdown"]["text"])
        with self.sessions() as db:
            rows = db.scalars(select(DomainAlert)).all()
            self.assertTrue(all(row.is_sent and row.delivery_status == "sent" for row in rows))
        with patch("notification.requests.post") as send_again:
            domain_monitor.deliver_pending()
            send_again.assert_not_called()

    def test_dns_probe_failure_still_alerts(self):
        observation = {"state": "unknown", "detail": "ConnectTimeout", "level": 1}
        with self.sessions() as db:
            domain = db.get(MonitoredDomain, self.domain_id)
            for _ in range(2):
                domain_monitor.record_results(db, domain, {"delegation": observation}, datetime.now())
            db.commit()
            event = db.scalars(select(DomainAlert)).one()
            self.assertIn("父区 NS 委派探测异常", event.message)

    def test_repeated_registration_misses_do_not_alert(self):
        now = datetime.now()
        with self.sessions() as db:
            domain = db.get(MonitoredDomain, self.domain_id)
            for state, detail in (("unknown", "等待查询接口响应超时"), ("unknown", "查询接口返回 HTTP 429"),
                                  ("unsupported", "无公开 RDAP")):
                domain_monitor.record_results(db, domain, {
                    "registration": domain_monitor.result(state, detail),
                    "delegation": domain_monitor.result("ok", "NS 一致"),
                }, now, rdap_due=True)
                self.assertEqual(domain.incident_level, 0)
                self.assertNotIn("coverage:registration", domain.checks)
                self.assertEqual(domain.checks["registration"]["state"], state)
            db.commit()
            self.assertEqual(db.scalars(select(DomainAlert)).all(), [])

    def test_legacy_registration_timeout_clears_without_recovery(self):
        now = datetime.now()
        with self.sessions() as db:
            domain = db.get(MonitoredDomain, self.domain_id)
            domain.checks = {"coverage:registration": {"state": "bad", "active": 1}}
            domain.incident_level = 1
            domain.last_incident_at = now
            domain_monitor.record_results(db, domain, {
                "delegation": domain_monitor.result("ok", "NS 一致"),
            }, now)
            db.commit()
            self.assertEqual(domain.incident_level, 0)
            self.assertIsNone(domain.last_incident_at)
            self.assertNotIn("coverage:registration", domain.checks)
            self.assertEqual(db.scalars(select(DomainAlert)).all(), [])

    def test_confirmed_registration_fault_survives_timeout(self):
        now = datetime.now()
        with self.sessions() as db:
            domain = db.get(MonitoredDomain, self.domain_id)
            domain_monitor.record_results(db, domain, {
                "registration": domain_monitor.result("bad", "server hold", level=2) | {"immediate": True},
            }, now, rdap_due=True)
            domain_monitor.record_results(db, domain, {
                "registration": domain_monitor.result("unknown", "等待查询接口响应超时"),
            }, now, rdap_due=True)
            db.commit()
            self.assertEqual(domain.incident_level, 2)
            self.assertEqual(domain.checks["registration"]["active_detail"], "server hold")
            event = db.scalars(select(DomainAlert)).one()
            self.assertEqual(event.alert_type, "domain_critical")
            self.assertNotIn("超时", event.message)

    def test_queued_timeout_notice_is_dropped_but_dns_notice_is_sent(self):
        retired = "- 域名注册状态探测异常：等待查询接口响应超时"
        valid = "- 父区 NS 委派：注册局 NS 与预期不一致"
        with self.sessions() as db:
            domain = db.get(MonitoredDomain, self.domain_id)
            domain_monitor.queue_alert(db, domain, "domain_warning", retired, datetime.now())
            domain_monitor.queue_alert(db, domain, "domain_critical", retired + "\n" + valid, datetime.now())
            db.commit()
        response = Mock(status_code=200)
        response.json.return_value = {"errcode": 0}
        with patch("notification.requests.post", return_value=response) as sent:
            domain_monitor.deliver_pending()
            sent.assert_called_once()
        with self.sessions() as db:
            retired_event, valid_event = db.scalars(select(DomainAlert).order_by(DomainAlert.id)).all()
            self.assertEqual(retired_event.delivery_status, "superseded")
            self.assertIsNone(retired_event.next_attempt_at)
            self.assertEqual(valid_event.delivery_status, "sent")
            self.assertEqual(valid_event.message, valid)


if __name__ == "__main__":
    unittest.main()
