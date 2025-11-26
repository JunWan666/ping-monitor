"""通知消息模板"""
from datetime import datetime


class NotificationTemplate:
    """通知消息模板类"""
    
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
