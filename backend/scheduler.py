from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from database import SessionLocal, Host, PingRecord, Alert, SystemConfig
from ping_service import PingService
from datetime import datetime
import logging
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MonitorScheduler:
    """监控调度器"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.ping_service = PingService()
        self.current_interval = 5  # 当前间隔(分钟)
        
    def start(self):
        """启动定时任务"""
        # 每5分钟执行一次监控
        self.scheduler.add_job(
            self.monitor_all_hosts,
            'interval',
            minutes=self.current_interval,
            id='monitor_hosts',
            replace_existing=True
        )
        self.scheduler.start()
        logger.info(f"监控调度器已启动，每{self.current_interval}分钟执行一次")
        
        # 在后台线程中立即执行一次监控（不阻塞启动）
        logger.info("立即执行首次监控...")
        thread = threading.Thread(target=self.monitor_all_hosts, daemon=True)
        thread.start()
    
    def update_interval(self, minutes: int):
        """更新监控间隔"""
        self.current_interval = minutes
        self.scheduler.reschedule_job(
            'monitor_hosts',
            trigger='interval',
            minutes=minutes
        )
        logger.info(f"监控间隔已更新为{minutes}分钟")
    
    def stop(self):
        """停止调度器"""
        self.scheduler.shutdown()
        logger.info("监控调度器已停止")
    
    def monitor_all_hosts(self):
        """监控所有启用的主机（并发执行）"""
        db = SessionLocal()
        try:
            hosts = db.query(Host).filter(Host.enabled == True).all()
            logger.info(f"开始监控 {len(hosts)} 台主机")
            
            # 为每个主机启动独立线程，并发执行
            threads = []
            for host in hosts:
                thread = threading.Thread(
                    target=self._monitor_host_in_thread,
                    args=(host.id, host.name, host.address, host.alert_threshold),
                    daemon=True
                )
                thread.start()
                threads.append(thread)
            
            # 等待所有线程完成（最多等待 60 秒）
            for thread in threads:
                thread.join(timeout=60)
                
        except Exception as e:
            logger.error(f"监控任务执行失败: {str(e)}")
        finally:
            db.close()
    
    def _monitor_host_in_thread(self, host_id: int, host_name: str, host_address: str, alert_threshold: float):
        """在独立线程中监控单个主机"""
        db = SessionLocal()
        try:
            # 重新获取 host 对象（因为是新的数据库会话）
            host = db.query(Host).filter(Host.id == host_id).first()
            if host:
                self.monitor_single_host(db, host)
        except Exception as e:
            logger.error(f"监控主机 {host_name} 线程失败: {str(e)}")
        finally:
            db.close()
    
    def monitor_single_host(self, db: Session, host: Host):
        """监控单个主机"""
        try:
            # 执行ping
            result = self.ping_service.ping_host(host.address, count=10, timeout=2)
            
            # 保存记录
            record = PingRecord(
                host_id=host.id,
                packet_sent=result['packet_sent'],
                packet_received=result['packet_received'],
                packet_loss=result['packet_loss'],
                min_rtt=result['min_rtt'],
                max_rtt=result['max_rtt'],
                avg_rtt=result['avg_rtt'],
                created_at=datetime.now()
            )
            db.add(record)
            db.commit()
            
            # 检查是否需要告警
            should_alert = False
            alert_message = ""
            alert_type = ""
            
            if result['packet_loss'] >= host.alert_threshold:
                should_alert = True
                alert_type = 'packet_loss'
                # 优化后的告警消息格式
                alert_message = (
                    f"主机：{host.name}\n"
                    f"服务器地址：{host.address}\n"
                    f"丢包率：{result['packet_loss']:.0f}%\n"
                    f"告警阈值：{host.alert_threshold:.0f}%\n"
                    f"平均延迟：{result['avg_rtt']:.2f}ms" if result['avg_rtt'] else f"平均延迟：无数据"
                )
                
                alert = Alert(
                    host_id=host.id,
                    host_name=host.name,
                    alert_type=alert_type,
                    message=alert_message,
                    is_sent=False,
                    created_at=datetime.now()
                )
                db.add(alert)
                db.commit()
                db.refresh(alert)
                logger.warning(alert_message)
            
            elif result['status'] == 'unreachable':
                should_alert = True
                alert_type = 'unreachable'
                # 优化后的告警消息格式
                alert_message = (
                    f"主机：{host.name}\n"
                    f"服务器地址：{host.address}\n"
                    f"告警类型：主机无法访问\n"
                    f"丢包率：100%"
                )
                
                alert = Alert(
                    host_id=host.id,
                    host_name=host.name,
                    alert_type=alert_type,
                    message=alert_message,
                    is_sent=False,
                    created_at=datetime.now()
                )
                db.add(alert)
                db.commit()
                db.refresh(alert)
                logger.warning(alert_message)
            
            # 发送通知
            if should_alert:
                self._send_alert_notification(db, alert, alert_message)
                
            logger.info(f"主机 {host.name} 监控完成: 丢包率 {result['packet_loss']}%, 平均延迟 {result['avg_rtt']}ms")
            
        except Exception as e:
            logger.error(f"监控主机 {host.name} 失败: {str(e)}")
    
    def _send_alert_notification(self, db: Session, alert: Alert, message: str):
        """发送告警通知（异步）"""
        # 在新线程中发送通知，不阻塞主监控线程
        thread = threading.Thread(
            target=self._do_send_notification,
            args=(alert.id, message, alert.alert_type),
            daemon=True
        )
        thread.start()
    
    def _do_send_notification(self, alert_id: int, message: str, alert_type: str):
        """实际执行通知发送（后台线程）"""
        db = SessionLocal()
        try:
            from notification import notifier
            from database import SystemConfig
            
            # 获取系统配置
            config = db.query(SystemConfig).first()
            if not config:
                logger.warning("系统配置不存在，无法发送通知")
                return
            
            # 配置通知器
            notifier.configure(
                serverchan_key=config.serverchan_key,
                webhook_url=config.webhook_url,
                webhook_secret=config.webhook_secret
            )
            
            # 发送通知
            success = False
            if config.serverchan_key:
                success = notifier.send_serverchan("告警通知", message)
            elif config.webhook_url:
                success = notifier.send_webhook(message, alert_type=alert_type)
            
            # 更新发送状态
            if success:
                alert = db.query(Alert).filter(Alert.id == alert_id).first()
                if alert:
                    alert.is_sent = True
                    db.commit()
                logger.info(f"告警通知已发送: {message}")
            else:
                logger.error(f"告警通知发送失败: {message}")
                
        except Exception as e:
            logger.error(f"发送告警通知失败: {str(e)}")
        finally:
            db.close()

# 全局调度器实例
scheduler = MonitorScheduler()
