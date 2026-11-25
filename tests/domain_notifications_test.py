"""Run with: python -m unittest discover -s tests -p '*_test.py'."""
from datetime import datetime, timedelta
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

from database import Base, DomainAlert, DomainAlertDelivery, MonitoredDomain, SystemConfig
import aliyun_sms
from aliyun_sms import SmsResult, build_template_param, normalize_phone_numbers
import domain_monitor
from notification_template import NotificationTemplate

DETAIL = "- 父区 NS 委派探测异常：a.zdnscloud.cn Timeout；b.zdnscloud.cn 已返回预期 NS"
CHINESE = "中文通知验证：域名监控与钉钉加签"
KINDS = ("domain_critical", "domain_warning", "domain_recovery", "domain_expiry")


class AliyunSmsTest(unittest.TestCase):
    SEND = dict(
        access_key_id="LTAIunittestonly", access_key_secret="unit-test-secret", sign_name="测试签名",
        template_code="SMS_1", phone_numbers="13800000000\n13900000000", template_param={"name": "example.com"},
    )

    def test_v3_signature_matches_the_documented_example(self):
        # Values and expected signature from the V3 signature document's worked example.
        headers = aliyun_sms.sign_request(
            access_key_id="YourAccessKeyId", access_key_secret="YourAccessKeySecret", method="POST",
            host="ecs.cn-shanghai.aliyuncs.com", action="RunInstances", version="2014-05-26",
            query={"ImageId": "win2019_1809_x64_dtc_zh-cn_40G_alibase_20230811.vhd", "RegionId": "cn-shanghai"},
            date="2023-10-26T10:22:32Z", nonce="3156853299f313e23d1673dc12e1703d",
        )
        self.assertEqual(headers["Authorization"], (
            "ACS3-HMAC-SHA256 Credential=YourAccessKeyId,"
            "SignedHeaders=host;x-acs-action;x-acs-content-sha256;x-acs-date;x-acs-signature-nonce;x-acs-version,"
            "Signature=06563a9e1b43f5dfe96b81484da74bceab24a1d853912eee15083a6f0f3283c0"
        ))

    def test_send_sms_signs_the_request_and_classifies_responses(self):
        def response(status, body):
            reply = Mock(status_code=status)
            reply.json.return_value = body
            return reply

        broken = response(503, None)
        broken.json.side_effect = ValueError
        replies = [
            response(200, {"Code": "OK", "BizId": "900"}),
            response(200, {"Code": "isv.SMS_TEMPLATE_ILLEGAL", "Message": "模板不合法"}),
            response(200, {"Code": "Throttling.User", "Message": "流控"}),
            broken,
        ]
        with patch("aliyun_sms.requests.post", side_effect=replies) as post:
            self.assertEqual(aliyun_sms.send_sms(**self.SEND), SmsResult(True, None, False, "900"))
            self.assertEqual(aliyun_sms.send_sms(**self.SEND), SmsResult(False, "isv.SMS_TEMPLATE_ILLEGAL: 模板不合法", False))
            self.assertEqual(aliyun_sms.send_sms(**self.SEND), SmsResult(False, "Throttling.User: 流控", True))
            self.assertEqual(aliyun_sms.send_sms(**self.SEND), SmsResult(False, "HTTP 503", True))
        call = post.call_args_list[0]
        self.assertTrue(call.args[0].startswith(
            "https://dysmsapi.aliyuncs.com/?PhoneNumbers=13800000000%2C13900000000&SignName=%E6%B5%8B%E8%AF%95"
        ))
        self.assertIn("&TemplateCode=SMS_1&TemplateParam=%7B%22name%22%3A%22example.com%22%7D", call.args[0])
        headers = call.kwargs["headers"]
        self.assertEqual((headers["x-acs-action"], headers["x-acs-version"]), ("SendSms", "2017-05-25"))
        self.assertTrue(headers["Authorization"].startswith("ACS3-HMAC-SHA256 Credential=LTAIunittestonly,"))
        self.assertNotIn("unit-test-secret", call.args[0] + str(headers))
        self.assertIs(call.kwargs["allow_redirects"], False)

    def test_a_read_timeout_is_never_resent_because_the_message_may_be_delivered(self):
        for error, retryable in ((requests.ReadTimeout(), False), (requests.ConnectTimeout(), True), (requests.ConnectionError(), True)):
            with self.subTest(error=type(error).__name__), patch("aliyun_sms.requests.post", side_effect=error):
                outcome = aliyun_sms.send_sms(**self.SEND)
                self.assertFalse(outcome.ok)
                self.assertIs(outcome.retryable, retryable)

    def test_template_variables_follow_the_aliyun_variable_rules(self):
        when = datetime(2026, 11, 25, 9, 5, 7)
        critical = build_template_param(
            "cpolar.top", "domain_critical",
            "- 权威 DNS 解析：ns1.example.net 返回 203.0.113.7\n- 公共 DNS 解析（待复核）：8.8.8.8 超时\n- 权威 DNS 解析：重复",
            when,
        )
        self.assertEqual(critical, {
            "name": "cpolar_top", "time": "2026-11-25 09:05:07", "status": "严重", "msg": "权威 DNS 解析异常、公共 DNS 解析异常",
        })
        # Aliyun answers isv.PARAM_NOT_SUPPORT_URL for anything link-like, bare domains included,
        # and isv.UNSUPPORTED_CONTENT for uncommon symbols such as "·", so dots become a plain "_"
        self.assertEqual(build_template_param("https://www.ping-test.com.cn/x", "domain_warning", "", when)["name"],
                         "www_ping-test_com_cn/x")
        self.assertEqual(build_template_param("xn--fiqs8s.cn", "domain_warning", "", when)["name"], "xn--fiqs8s_cn")
        expiry = build_template_param("cpolar.top", "domain_expiry", "域名将在 30 天内到期（2026-12-25 10:00）", when)
        self.assertEqual((expiry["status"], expiry["msg"]), ("即将到期", "域名将在 30 天内到期（2026-12-25 10:00）"))
        self.assertEqual(build_template_param("x.cn", "domain_expiry", "域名已经到期（2026-11-01）", when)["status"], "已到期")
        warning = build_template_param("a" * 60 + ".com", "domain_warning", "", when)
        self.assertEqual((warning["status"], warning["msg"]), ("警告", "域名检测异常"))
        self.assertTrue(warning["name"].endswith("..."))
        for value in (*critical.values(), *expiry.values(), *warning.values()):
            self.assertTrue(1 <= len(value) <= 35, value)
            self.assertNotRegex(value, r"[0-9A-Za-z]\.[0-9A-Za-z]")
            self.assertNotRegex(value, r"[·•【】〖〗『』「」★※→]")

    def test_phone_numbers_are_normalized_and_validated(self):
        self.assertEqual(
            normalize_phone_numbers(" 13800000000，+8613900000000\n13800000000; 85212345678 "),
            ["13800000000", "+8613900000000", "85212345678"],
        )
        for bad in ("1380000abcd", "12-34", "+"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                normalize_phone_numbers(bad)
        with self.assertRaises(ValueError):
            normalize_phone_numbers(",".join(str(13800000000 + i) for i in range(1001)))


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

    def configure_sms(self, db):
        config = db.query(SystemConfig).one()
        config.sms_access_key_id = "LTAIunittestonly"
        config.sms_access_key_secret = "unit-test-secret"
        config.sms_sign_name = "测试签名"
        config.sms_template_code = "SMS_100000001"
        config.sms_phone_numbers = "13800000000,13900000000"
        return config

    def queue_sms_incident(self, kind="domain_critical", message="- 权威 DNS 解析：异常", *, dingtalk=True, when=None):
        with self.sessions() as db:
            config = self.configure_sms(db)
            domain = db.get(MonitoredDomain, self.domain_id)
            domain.notify = dingtalk
            domain.notify_sms = True
            domain_monitor.queue_alert(db, domain, kind, message, when or datetime.now(), config=config)
            db.commit()

    def test_sms_is_sent_independently_from_dingtalk_with_template_variables(self):
        created = datetime.now().replace(microsecond=0) - timedelta(minutes=1)
        self.queue_sms_incident(message=DETAIL, dingtalk=False, when=created)
        with patch("domain_monitor.NotificationService") as dingtalk, \
                patch("domain_monitor.send_configured_sms", return_value=SmsResult(True, biz_id="900")) as sms:
            domain_monitor.deliver_pending()
            dingtalk.return_value.send_webhook.assert_not_called()
            sms.assert_called_once()
            self.assertEqual(sms.call_args.args[0].sms_template_code, "SMS_100000001")
            # Probe details carry NS host names; the SMS variable only names the failing check.
            self.assertEqual(sms.call_args.args[1], {
                "name": "cpolar_top", "time": created.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "严重", "msg": "父区 NS 委派探测异常",
            })
        with self.sessions() as db:
            event = db.scalars(select(DomainAlert)).one()
            delivery = db.scalars(select(DomainAlertDelivery)).one()
            self.assertEqual(event.delivery_status, "disabled")
            self.assertEqual((delivery.channel, delivery.status, delivery.attempts), ("sms", "sent", 1))
            self.assertIsNone(delivery.next_attempt_at)

    def test_recovery_is_not_sent_by_sms_and_turning_sms_off_cancels_retry(self):
        with self.sessions() as db:
            config = self.configure_sms(db)
            domain = db.get(MonitoredDomain, self.domain_id)
            domain.notify_sms = True
            now = datetime.now()
            domain_monitor.queue_alert(db, domain, "domain_recovery", "恢复正常", now, config=config)
            self.assertEqual(db.scalars(select(DomainAlertDelivery)).all(), [])
            domain_monitor.queue_alert(db, domain, "domain_critical", "- 权威 DNS 解析：异常", now, config=config)
            delivery = db.scalars(select(DomainAlertDelivery)).one()
            delivery.status = "failed"
            delivery.next_attempt_at = now + timedelta(minutes=1)
            domain.notify_sms = False
            from domain_api import sync_sms_deliveries
            sync_sms_deliveries(db, domain)
            db.commit()
        with self.sessions() as db:
            delivery = db.scalars(select(DomainAlertDelivery)).one()
            self.assertEqual(delivery.status, "disabled")
            self.assertIsNone(delivery.next_attempt_at)

    def test_unconfigured_sms_is_recorded_without_sending(self):
        with self.sessions() as db:
            config = db.query(SystemConfig).one()
            domain = db.get(MonitoredDomain, self.domain_id)
            domain.notify_sms = True
            domain_monitor.queue_alert(db, domain, "domain_expiry", "域名将在 30 天内到期（2026-12-25 10:00）", datetime.now(), config=config)
            db.commit()
            delivery = db.scalars(select(DomainAlertDelivery)).one()
            self.assertEqual(delivery.status, "no_channel")
            self.assertIsNone(delivery.next_attempt_at)

    def test_retryable_sms_failure_backs_off_without_resending_dingtalk(self):
        self.queue_sms_incident()
        with patch("domain_monitor.NotificationService") as dingtalk, \
                patch("domain_monitor.send_configured_sms", return_value=SmsResult(False, "Throttling.User: 流控", True)) as sms:
            dingtalk.return_value.send_webhook.return_value = True
            domain_monitor.deliver_pending()
            dingtalk.return_value.send_webhook.assert_called_once()
            sms.assert_called_once()
        with self.sessions() as db:
            event = db.scalars(select(DomainAlert)).one()
            delivery = db.scalars(select(DomainAlertDelivery)).one()
            self.assertEqual(event.delivery_status, "sent")
            self.assertEqual((delivery.status, delivery.attempts), ("failed", 1))
            self.assertEqual(delivery.last_error, "Throttling.User: 流控")
            self.assertIsNotNone(delivery.next_attempt_at)

    def test_configuration_errors_and_read_timeouts_are_not_retried(self):
        for outcome in (
            SmsResult(False, "isv.SMS_TEMPLATE_ILLEGAL: 模板不合法", False),
            SmsResult(False, "阿里云短信接口响应超时，短信可能已发出，未自动重试", False),
        ):
            with self.subTest(error=outcome.error):
                with self.sessions() as db:
                    db.query(DomainAlertDelivery).delete()
                    db.query(DomainAlert).delete()
                    db.commit()
                self.queue_sms_incident(dingtalk=False)
                with patch("domain_monitor.NotificationService"), \
                        patch("domain_monitor.send_configured_sms", return_value=outcome) as sms:
                    domain_monitor.deliver_pending()
                    domain_monitor.deliver_pending()
                    sms.assert_called_once()
                with self.sessions() as db:
                    delivery = db.scalars(select(DomainAlertDelivery)).one()
                    self.assertEqual((delivery.status, delivery.attempts, delivery.last_error), ("failed", 1, outcome.error))
                    self.assertIsNone(delivery.next_attempt_at)

    def test_sms_delivery_stops_after_max_attempts(self):
        self.queue_sms_incident()
        with patch("domain_monitor.NotificationService") as dingtalk, \
                patch("domain_monitor.send_configured_sms", return_value=SmsResult(False, "HTTP 503", True)) as sms:
            dingtalk.return_value.send_webhook.return_value = True
            for _ in range(domain_monitor.SMS_MAX_ATTEMPTS):
                with self.sessions() as db:
                    delivery = db.scalars(select(DomainAlertDelivery)).one()
                    delivery.next_attempt_at = datetime.now() - timedelta(seconds=1)
                    db.commit()
                domain_monitor.deliver_pending()
            self.assertEqual(sms.call_count, domain_monitor.SMS_MAX_ATTEMPTS)
            dingtalk.return_value.send_webhook.assert_called_once()
        with self.sessions() as db:
            delivery = db.scalars(select(DomainAlertDelivery)).one()
            self.assertEqual((delivery.status, delivery.attempts), ("failed", domain_monitor.SMS_MAX_ATTEMPTS))
            self.assertIsNone(delivery.next_attempt_at)

    def test_recovery_supersedes_queued_sms_incident_but_not_expiry(self):
        with self.sessions() as db:
            config = self.configure_sms(db)
            domain = db.get(MonitoredDomain, self.domain_id)
            domain.notify = False  # DingTalk off must not leave a stale SMS retry.
            domain.notify_sms = True
            domain.incident_level = 2
            domain.last_incident_at = datetime.now() - timedelta(minutes=3)
            domain.checks = {"delegation": {
                "state": "bad", "active": 2, "active_detail": "NS 不匹配",
                "streak": 2, "detail": "NS 不匹配",
            }}
            domain_monitor.queue_alert(db, domain, "domain_critical", "旧异常", datetime.now(), config=config)
            db.flush()
            old_delivery = db.scalars(select(DomainAlertDelivery)).one()
            old_delivery.status = "failed"
            old_delivery.next_attempt_at = datetime.now() + timedelta(minutes=1)
            domain_monitor.queue_alert(db, domain, "domain_expiry", "到期提醒", datetime.now(), config=config)
            for _ in range(2):
                domain_monitor.record_results(
                    db, domain, {"delegation": domain_monitor.result("ok", "NS 正常")}, datetime.now(), config=config,
                )
            db.commit()
            deliveries = db.scalars(select(DomainAlertDelivery).order_by(DomainAlertDelivery.id)).all()
            self.assertEqual(len(deliveries), 2)  # the recovery itself is not sent by SMS
            self.assertEqual(deliveries[0].status, "superseded")
            self.assertIsNone(deliveries[0].next_attempt_at)
            self.assertEqual(deliveries[1].status, "pending")  # DNS recovery does not affect expiry.
            self.assertIsNotNone(db.scalars(select(DomainAlert).where(DomainAlert.alert_type == "domain_recovery")).first())

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
