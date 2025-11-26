import requests
import logging
import time
import hmac
import hashlib
import base64
from urllib.parse import quote_plus
from datetime import datetime

logger = logging.getLogger(__name__)

class NotificationService:
    """通知服务"""
    
    def __init__(self):
        # 这里配置各种通知渠道的密钥
        self.serverchan_key = None  # Server酱密钥
        self.webhook_url = None     # 企业微信/钉钉 Webhook
        self.webhook_secret = None  # 钉钉机器人加签密钥
        self.email_config = None    # 邮件配置
    
    def send_alert(self, message: str, alert_type: str = "warning"):
        """
        发送告警通知
        
        Args:
            message: 告警消息
            alert_type: 告警类型 (warning, error, info)
        """
        # 根据配置发送到不同渠道
        if self.serverchan_key:
            self.send_serverchan(f"Ping监控告警 [{alert_type}]", message, alert_type)
        
        if self.webhook_url:
            self.send_webhook(message, alert_type)
    
    def send_serverchan(self, title: str, message: str, alert_type: str = "info"):
        """发送Server酱通知"""
        if not self.serverchan_key:
            return False
        
        try:
            url = f"https://sctapi.ftqq.com/{self.serverchan_key}.send"
            data = {
                "title": title if not alert_type or alert_type == "info" else f"{title} [{alert_type}]",
                "desp": message
            }
            response = requests.post(url, data=data, timeout=10)
            if response.status_code == 200:
                logger.info("Server酱通知发送成功")
                return True
            else:
                logger.error(f"Server酱通知发送失败: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Server酱通知发送异常: {str(e)}")
            return False
    
    def send_webhook(self, message: str, alert_type: str = "info", title: str = None):
        """发送Webhook通知(企业微信/钉钉)"""
        if not self.webhook_url:
            return False
        
        try:
            # 钉钉格式
            if "oapi.dingtalk.com" in self.webhook_url:
                webhook_url = self.webhook_url
                
                # 如果配置了加签密钥，计算签名
                if self.webhook_secret:
                    timestamp = str(round(time.time() * 1000))
                    secret_enc = self.webhook_secret.encode('utf-8')
                    string_to_sign = f'{timestamp}\n{self.webhook_secret}'
                    string_to_sign_enc = string_to_sign.encode('utf-8')
                    hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                    sign = quote_plus(base64.b64encode(hmac_code))
                    webhook_url = f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"
                
                # 使用Markdown格式
                payload = {
                    "msgtype": "markdown",
                    "markdown": {
                        "title": title or "Ping监控通知",
                        "text": message
                    }
                }
            # 企业微信格式
            elif "qyapi.weixin.qq.com" in self.webhook_url:
                webhook_url = self.webhook_url
                payload = {
                    "msgtype": "text",
                    "text": {
                        "content": f"[Ping监控告警]\n{message}"
                    }
                }
            else:
                webhook_url = self.webhook_url
                payload = {"message": message, "type": alert_type}
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                result = response.json()
                # 钉钉返回结果检查
                if "oapi.dingtalk.com" in self.webhook_url:
                    if result.get('errcode') == 0:
                        logger.info("Webhook通知发送成功")
                        return True
                    else:
                        logger.error(f"Webhook通知发送失败: {result.get('errmsg')}")
                        return False
                else:
                    logger.info("Webhook通知发送成功")
                    return True
            else:
                logger.error(f"Webhook通知发送失败: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Webhook通知发送异常: {str(e)}")
            return False
    
    def configure(self, serverchan_key: str = None, webhook_url: str = None, webhook_secret: str = None):
        """配置通知渠道"""
        if serverchan_key:
            self.serverchan_key = serverchan_key
            logger.info("Server酱已配置")
        
        if webhook_url:
            self.webhook_url = webhook_url
            logger.info("Webhook已配置")
        
        if webhook_secret:
            self.webhook_secret = webhook_secret
            logger.info("Webhook加签密钥已配置")

# 全局通知服务实例
notifier = NotificationService()
