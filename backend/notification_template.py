"""通知消息模板"""
from datetime import datetime
from html import escape
import re
from zoneinfo import ZoneInfo


def _domain_detail(text: str) -> str:
    """Keep useful DNS evidence while making probe errors readable."""
    translations = {
        "ConnectTimeout": "连接超时",
        "ReadTimeout": "等待响应超时",
        "LifetimeTimeout": "查询超时",
        "Timeout": "查询超时",
        "ConnectionError": "连接失败",
        "SSLError": "安全连接失败",
        "NoNameservers": "没有可用的 DNS 响应",
        "NXDOMAIN": "域名不存在（NXDOMAIN）",
        "SERVFAIL": "解析失败（SERVFAIL）",
        "REFUSED": "查询被拒绝（REFUSED）",
        "server hold": "注册局暂停解析（serverHold）",
        "client hold": "注册商暂停解析（clientHold）",
        "pending delete": "域名待删除（pendingDelete）",
        "redemption period": "域名处于赎回期（redemptionPeriod）",
    }
    pattern = r"\b(?:" + "|".join(re.escape(key) for key in translations) + r")\b"
    return re.sub(pattern, lambda match: translations[match[0]], text)


class NotificationTemplate:
    """通知消息模板类"""

    @staticmethod
    def get_domain_alert(
        domain_name: str,
        alert_type: str,
        message: str,
        created_at: datetime | None = None,
        use_markdown: bool = True,
        is_test: bool = False,
    ) -> dict:
        styles = {
            "domain_critical": ("🔴", "域名异常告警", "🔴 严重", "#FF0000", "已确认检测异常"),
            "domain_warning": ("🟠", "域名监控提醒", "🟠 警告", "#FFA500", "部分检测异常"),
            "domain_recovery": ("✅", "域名恢复正常", "🟢 已恢复", "#00FF00", "已恢复正常"),
            "domain_expiry": ("🟡", "域名到期提醒", "🟡 提醒", "#FFA500", "请及时确认续费"),
        }
        icon, heading, severity, color, status = styles[alert_type]
        title = f"{icon} {heading}"
        if is_test:
            title += "（模板测试）"

        lines = [line.strip().removeprefix("- ").strip() for line in message.splitlines() if line.strip()]
        details = []
        for line in lines:
            label, separator, body = line.partition("：")
            if separator and len(label) <= 30:
                details.append((label, body))
            else:
                details.append(("", line))

        probe_only = alert_type == "domain_warning" and all(
            label.endswith(("探测异常", "查询异常")) for label, _ in details
        ) and bool(details)
        if probe_only:
            status = "探测未完成，状态待确认"

        fields = [("监控域名", domain_name)]
        if details and all(label for label, _ in details):
            fields.append(("检查项目", "、".join(dict.fromkeys(label for label, _ in details))))
        fields.append(("检测结果", status))
        if probe_only:
            fields.append(("影响说明", "探测结果暂缺，尚未确认域名故障"))

        notification_time = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
        status_label = "状态" if alert_type == "domain_recovery" else "告警级别"
        if not use_markdown:
            content = f"{title}\n{status_label}：{severity}\n\n"
            content += "\n".join(f"{key}：{value}" for key, value in fields) + "\n\n"
            content += "\n".join(
                f"{label + '：' if label else ''}{_domain_detail(body)}" for label, body in details
            )
            if is_test:
                content += "\n\n模板验证消息，不代表新发生的故障。"
            if created_at:
                content += f"\n发现时间：{created_at:%Y-%m-%d %H:%M:%S}"
            content += f"\n通知时间：{notification_time}"
            return {"title": title, "content": content}

        content = f"### {title}\n\n> **{status_label}：** {severity}\n\n---\n\n"
        for key, value in fields:
            if key == "监控域名":
                value = f"[{domain_name}](https://{domain_name})"
            elif key == "检测结果":
                value = f"<font color={color}>**{value}**</font>"
            content += f"**{key}：** {value}  \n"

        if details:
            content += "\n---\n\n"
            section = "恢复说明" if alert_type == "domain_recovery" else "到期信息" if alert_type == "domain_expiry" else "异常详情"
            content += f"**{section}**\n\n"
            for label, body in details:
                if label:
                    content += f"**{escape(label)}**  \n"
                for part in re.split(r"[；;]", _domain_detail(body)):
                    if part.strip():
                        content += f"- {escape(part.strip())}\n"
                content += "\n"
        if is_test:
            content += "> 此消息用于验证新版通知模板，不代表新发生的故障。\n\n"
        content += "---\n"
        if created_at:
            content += f"🕒 **发现时间：** {created_at:%Y-%m-%d %H:%M:%S}  \n"
        content += f"📅 **通知时间：** {notification_time}"
        return {"title": title, "content": content}
    
    @staticmethod
    def get_abnormal_alert(host_name: str, host_address: str, packet_loss: float, 
                          alert_threshold: float, avg_rtt: float = None, 
                          use_markdown: bool = True) -> dict:
        """
        异常告警通知模板
        
        Args:
            host_name: 主机名称
            host_address: 主机地址
            packet_loss: 丢包率
            alert_threshold: 告警阈值
            avg_rtt: 平均延迟
            use_markdown: 是否使用Markdown格式
            
        Returns:
            dict: {'title': str, 'content': str}
        """
        if use_markdown:
            # Markdown格式（钉钉）
            title = "🚨 主机异常告警"
            
            # 根据严重程度选择颜色标识
            if packet_loss >= 80:
                severity = "🔴 严重"
                color_emoji = "🔴"
            elif packet_loss >= 50:
                severity = "🟠 警告"
                color_emoji = "🟠"
            else:
                severity = "🟡 提醒"
                color_emoji = "🟡"
            
            content = f"""### {color_emoji} 主机异常告警
            
> **告警级别：** {severity}

---

**主机名称：** {host_name}  
**服务器地址：** [{host_address}](http://{host_address})  
**丢包率：** <font color=#FF0000>**{packet_loss:.0f}%**</font>  
**告警阈值：** {alert_threshold:.0f}%  
"""
            if avg_rtt:
                # 根据延迟设置颜色：<50ms绿色，50-150ms黄色，>150ms红色
                if avg_rtt < 50:
                    rtt_color = "#00FF00"  # 绿色
                elif avg_rtt < 150:
                    rtt_color = "#FFA500"  # 黄色/橙色
                else:
                    rtt_color = "#FF0000"  # 红色
                content += f"**平均延迟：** <font color={rtt_color}>**{avg_rtt:.2f}ms**</font>  \n"
            else:
                content += f"**平均延迟：** <font color=#FF0000>**主机不可达**</font>  \n"
            
            content += f"\n---\n📅 **通知时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
        else:
            # 纯文本格式（Server酱）
            title = "主机异常告警"
            content = (
                f"主机：{host_name}\n"
                f"服务器地址：{host_address}\n"
                f"丢包率：{packet_loss:.0f}%\n"
                f"告警阈值：{alert_threshold:.0f}%\n"
            )
            if avg_rtt:
                content += f"平均延迟：{avg_rtt:.2f}ms\n"
            else:
                content += "平均延迟：主机不可达\n"
            
            content += f"\n通知时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return {'title': title, 'content': content}
    
    @staticmethod
    def get_unreachable_alert(host_name: str, host_address: str, 
                             use_markdown: bool = True) -> dict:
        """
        主机不可达告警模板
        
        Args:
            host_name: 主机名称
            host_address: 主机地址
            use_markdown: 是否使用Markdown格式
            
        Returns:
            dict: {'title': str, 'content': str}
        """
        if use_markdown:
            # Markdown格式（钉钉）
            title = "🔴 主机不可达告警"
            content = f"""### 🔴 主机不可达告警

> **告警级别：** 🔴 严重

---

**主机名称：** {host_name}  
**服务器地址：** [{host_address}](http://{host_address})  
**告警类型：** 主机无法访问  
**丢包率：** <font color=#FF0000>**100%**</font>  
**平均延迟：** <font color=#FF0000>**主机不可达**</font>  

---
📅 **通知时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        else:
            # 纯文本格式
            title = "主机不可达告警"
            content = (
                f"主机：{host_name}\n"
                f"服务器地址：{host_address}\n"
                f"告警类型：主机无法访问\n"
                f"丢包率：100%\n"
                f"平均延迟：主机不可达\n"
                f"\n通知时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        
        return {'title': title, 'content': content}
    
    @staticmethod
    def get_recovery_alert(host_name: str, host_address: str, packet_loss: float,
                          avg_rtt: float = None, use_markdown: bool = True) -> dict:
        """
        恢复正常通知模板
        
        Args:
            host_name: 主机名称
            host_address: 主机地址
            packet_loss: 丢包率
            avg_rtt: 平均延迟
            use_markdown: 是否使用Markdown格式
            
        Returns:
            dict: {'title': str, 'content': str}
        """
        if use_markdown:
            # Markdown格式（钉钉）
            title = "✅ 主机恢复正常"
            content = f"""### ✅ 主机恢复正常

> **状态：** 🟢 已恢复

---

**主机名称：** {host_name}  
**服务器地址：** [{host_address}](http://{host_address})  
**丢包率：** <font color=#00FF00>**{packet_loss:.0f}%**</font>  
"""
            if avg_rtt:
                # 根据延迟设置颜色：<50ms绿色，50-150ms黄色，>150ms红色
                if avg_rtt < 50:
                    rtt_color = "#00FF00"  # 绿色
                elif avg_rtt < 150:
                    rtt_color = "#FFA500"  # 黄色/橙色
                else:
                    rtt_color = "#FF0000"  # 红色
                content += f"**平均延迟：** <font color={rtt_color}>**{avg_rtt:.2f}ms**</font>  \n"
            else:
                content += f"**平均延迟：** <font color=#FF0000>**主机不可达**</font>  \n"
            
            content += f"\n---\n📅 **通知时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            # 纯文本格式
            title = "主机恢复正常"
            content = (
                f"主机：{host_name}\n"
                f"服务器地址：{host_address}\n"
                f"状态：已恢复正常\n"
                f"丢包率：{packet_loss:.0f}%\n"
            )
            if avg_rtt:
                content += f"平均延迟：{avg_rtt:.2f}ms\n"
            else:
                content += "平均延迟：主机不可达\n"
            
            content += f"\n通知时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return {'title': title, 'content': content}
    
    @staticmethod
    def get_test_notification(use_markdown: bool = True) -> dict:
        """
        测试通知模板
        
        Args:
            use_markdown: 是否使用Markdown格式
            
        Returns:
            dict: {'title': str, 'content': str}
        """
        if use_markdown:
            title = "✅ 通知测试"
            content = f"""### ✅ Ping监控系统 - 通知测试

> 如果您收到这条消息，说明通知功能配置正确！

---

📅 **测试时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        else:
            title = "通知测试"
            content = (
                f"Ping监控系统 - 通知测试\n\n"
                f"如果您收到这条消息，说明通知功能配置正确！\n\n"
                f"测试时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        
        return {'title': title, 'content': content}
