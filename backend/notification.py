from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
from urllib.parse import quote_plus

import requests

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self) -> None:
        self.serverchan_key = None
        self.webhook_url = None
        self.webhook_secret = None

    def configure(
        self,
        serverchan_key: str | None = None,
        webhook_url: str | None = None,
        webhook_secret: str | None = None,
    ) -> None:
        self.serverchan_key = serverchan_key or None
        self.webhook_url = webhook_url or None
        self.webhook_secret = webhook_secret or None

    def send_serverchan(self, title: str, message: str, alert_type: str = "info") -> bool:
        if not self.serverchan_key:
            return False

        try:
            url = f"https://sctapi.ftqq.com/{self.serverchan_key}.send"
            data = {
                "title": title if not alert_type or alert_type == "info" else f"{title} [{alert_type}]",
                "desp": message,
            }
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                logger.info("Server酱通知发送成功")
                return True
            logger.error("Server酱通知发送失败: %s", response.text)
            return False
        except Exception as exc:
            logger.error("Server酱通知发送异常: %s", exc)
            return False

    def send_webhook(self, message: str, alert_type: str = "info", title: str | None = None) -> bool:
        if not self.webhook_url:
            return False

        try:
            webhook_url = self.webhook_url
            if "oapi.dingtalk.com" in self.webhook_url:
                if self.webhook_secret:
                    timestamp = str(round(time.time() * 1000))
                    secret_enc = self.webhook_secret.encode("utf-8")
                    string_to_sign = f"{timestamp}\n{self.webhook_secret}".encode("utf-8")
                    hmac_code = hmac.new(secret_enc, string_to_sign, digestmod=hashlib.sha256).digest()
                    sign = quote_plus(base64.b64encode(hmac_code))
                    webhook_url = f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"
                payload = {
                    "msgtype": "markdown",
                    "markdown": {
                        "title": title or "Ping 监控通知",
                        "text": message,
                    },
                }
            elif "qyapi.weixin.qq.com" in self.webhook_url:
                payload = {
                    "msgtype": "text",
                    "text": {"content": f"[Ping 监控通知]\n{message}"},
                }
            else:
                payload = {"message": message, "type": alert_type}

            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code != 200:
                logger.error("Webhook 通知发送失败: %s", response.text)
                return False

            if "oapi.dingtalk.com" in self.webhook_url:
                result = response.json()
                if result.get("errcode") != 0:
                    logger.error("钉钉通知发送失败: %s", result.get("errmsg"))
                    return False

            logger.info("Webhook 通知发送成功")
            return True
        except Exception as exc:
            logger.error("Webhook 通知发送异常: %s", exc)
            return False


notifier = NotificationService()
