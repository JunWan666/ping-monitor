"""
数据维护模块：负责数据清理和聚合统计
"""
from sqlalchemy.orm import Session
from database import SessionLocal, PingRecord, PingStatistics, SystemLog, Host, SystemConfig
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)

class DataMaintenance:
    """数据维护类"""
    
    @staticmethod
    def log_system_event(db: Session, log_type: str, module: str, message: str, details: dict = None):
        """记录系统日志"""
        try:
            log = SystemLog(
                log_type=log_type,
                module=module,
                message=message,
                details=json.dumps(details, ensure_ascii=False) if details else None
            )
            db.add(log)
            db.commit()
        except Exception as e:
            logger.error(f"记录系统日志失败: {e}")
            db.rollback()
    
    @staticmethod
    def cleanup_old_records(days: int = None):
        """
        清理旧的ping记录
        :param days: 保留最近N天的数据，如果为None则从配置读取
        """
        db = SessionLocal()
        try:
            # 从配置读取保留天数
            if days is None:
                config = db.query(SystemConfig).first()
                days = config.data_retention_days if config else 30
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 统计要删除的记录数
            count = db.query(PingRecord).filter(PingRecord.created_at < cutoff_date).count()
            
            if count > 0:
                # 执行删除
                db.query(PingRecord).filter(PingRecord.created_at < cutoff_date).delete()
                db.commit()
                
                # 记录系统日志
                DataMaintenance.log_system_event(
                    db,
                    log_type='cleanup',
                    module='data_maintenance',
                    message=f'清理了 {count} 条 {days} 天前的Ping记录',
                    details={'deleted_count': count, 'days': days, 'cutoff_date': cutoff_date.isoformat()}
                )
                
                logger.info(f"✅ 数据清理完成，删除了 {count} 条记录")
            else:
                logger.info("⏭️ 没有需要清理的数据")
                
        except Exception as e:
            logger.error(f"❌ 数据清理失败: {e}")
            db.rollback()
            DataMaintenance.log_system_event(
                db,
                log_type='error',
                module='data_maintenance',
                message=f'数据清理失败: {str(e)}',
                details={'error': str(e)}
            )
        finally:
            db.close()
    
    @staticmethod
    def aggregate_hourly_stats():
        """按小时聚合统计数据"""
        db = SessionLocal()
        try:
            # 获取最后一次聚合的时间
            last_stat = db.query(PingStatistics).filter(
                PingStatistics.stat_type == 'hourly'
            ).order_by(PingStatistics.stat_time.desc()).first()
            
            # 确定起始时间（上次聚合时间的下一个小时）
            if last_stat:
                start_time = last_stat.stat_time + timedelta(hours=1)
            else:
                # 首次聚合，从最早的记录开始
                first_record = db.query(PingRecord).order_by(PingRecord.created_at).first()
                if not first_record:
                    logger.info("⏭️ 没有数据需要聚合")
                    return
                start_time = first_record.created_at.replace(minute=0, second=0, microsecond=0)
            
            # 只聚合到上一个完整小时
            current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
            
            # 获取所有主机
            hosts = db.query(Host).all()
            aggregated_count = 0
            
            # 按小时遍历
            time_cursor = start_time
            while time_cursor < current_hour:
                next_hour = time_cursor + timedelta(hours=1)
                
                for host in hosts:
                    # 查询该小时内的所有记录
                    records = db.query(PingRecord).filter(
                        PingRecord.host_id == host.id,
                        PingRecord.created_at >= time_cursor,
                        PingRecord.created_at < next_hour
                    ).all()
                    
                    if records:
                        # 计算统计数据
                        check_count = len(records)
                        online_count = sum(1 for r in records if r.packet_loss < host.alert_threshold)
                        avg_packet_loss = sum(r.packet_loss for r in records) / check_count
                        
                        rtts = [r.avg_rtt for r in records if r.avg_rtt is not None]
                        if rtts:
                            avg_rtt = sum(rtts) / len(rtts)
                            min_rtt = min(r.min_rtt for r in records if r.min_rtt is not None)
                            max_rtt = max(r.max_rtt for r in records if r.max_rtt is not None)
                        else:
                            avg_rtt = None
                            min_rtt = None
                            max_rtt = None
                        
                        # 保存统计数据
                        stat = PingStatistics(
                            host_id=host.id,
                            stat_type='hourly',
                            stat_time=time_cursor,
                            check_count=check_count,
                            online_count=online_count,
                            avg_packet_loss=round(avg_packet_loss, 2),
                            avg_rtt=round(avg_rtt, 2) if avg_rtt else None,
                            min_rtt=round(min_rtt, 2) if min_rtt else None,
                            max_rtt=round(max_rtt, 2) if max_rtt else None
                        )
                        db.add(stat)
                        aggregated_count += 1
                
                time_cursor = next_hour
            
            if aggregated_count > 0:
                db.commit()
                
                # 记录系统日志
                DataMaintenance.log_system_event(
                    db,
                    log_type='aggregate',
                    module='data_maintenance',
                    message=f'完成小时级数据聚合，生成 {aggregated_count} 条统计记录',
                    details={
                        'aggregated_count': aggregated_count,
                        'start_time': start_time.isoformat(),
                        'end_time': current_hour.isoformat()
                    }
                )
                
                logger.info(f"✅ 小时级数据聚合完成，生成了 {aggregated_count} 条统计记录")
            else:
                logger.info("⏭️ 没有新数据需要聚合")
                
        except Exception as e:
            logger.error(f"❌ 数据聚合失败: {e}")
            db.rollback()
            DataMaintenance.log_system_event(
                db,
                log_type='error',
                module='data_maintenance',
                message=f'数据聚合失败: {str(e)}',
                details={'error': str(e)}
            )
        finally:
            db.close()
    
    @staticmethod
    def aggregate_daily_stats():
        """按天聚合统计数据"""
        db = SessionLocal()
        try:
            # 获取最后一次聚合的时间
            last_stat = db.query(PingStatistics).filter(
                PingStatistics.stat_type == 'daily'
            ).order_by(PingStatistics.stat_time.desc()).first()
            
            # 确定起始时间
            if last_stat:
                start_time = last_stat.stat_time + timedelta(days=1)
            else:
                # 从小时统计中获取最早的时间
                first_hourly = db.query(PingStatistics).filter(
                    PingStatistics.stat_type == 'hourly'
                ).order_by(PingStatistics.stat_time).first()
                
                if not first_hourly:
                    logger.info("⏭️ 没有小时统计数据，无法生成日统计")
                    return
                    
                start_time = first_hourly.stat_time.replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 只聚合到昨天
            yesterday = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            
            # 获取所有主机
            hosts = db.query(Host).all()
            aggregated_count = 0
            
            # 按天遍历
            time_cursor = start_time
            while time_cursor <= yesterday:
                next_day = time_cursor + timedelta(days=1)
                
                for host in hosts:
                    # 从小时统计中聚合
                    hourly_stats = db.query(PingStatistics).filter(
                        PingStatistics.host_id == host.id,
                        PingStatistics.stat_type == 'hourly',
                        PingStatistics.stat_time >= time_cursor,
                        PingStatistics.stat_time < next_day
                    ).all()
                    
                    if hourly_stats:
                        check_count = sum(s.check_count for s in hourly_stats)
                        online_count = sum(s.online_count for s in hourly_stats)
                        avg_packet_loss = sum(s.avg_packet_loss * s.check_count for s in hourly_stats) / check_count
                        
                        rtts = [(s.avg_rtt, s.check_count) for s in hourly_stats if s.avg_rtt is not None]
                        if rtts:
                            avg_rtt = sum(rtt * count for rtt, count in rtts) / sum(count for _, count in rtts)
                            min_rtt = min(s.min_rtt for s in hourly_stats if s.min_rtt is not None)
                            max_rtt = max(s.max_rtt for s in hourly_stats if s.max_rtt is not None)
                        else:
                            avg_rtt = None
                            min_rtt = None
                            max_rtt = None
                        
                        # 保存统计数据
                        stat = PingStatistics(
                            host_id=host.id,
                            stat_type='daily',
                            stat_time=time_cursor,
                            check_count=check_count,
                            online_count=online_count,
                            avg_packet_loss=round(avg_packet_loss, 2),
                            avg_rtt=round(avg_rtt, 2) if avg_rtt else None,
                            min_rtt=round(min_rtt, 2) if min_rtt else None,
                            max_rtt=round(max_rtt, 2) if max_rtt else None
                        )
                        db.add(stat)
                        aggregated_count += 1
                
                time_cursor = next_day
            
            if aggregated_count > 0:
                db.commit()
                
                # 记录系统日志
                DataMaintenance.log_system_event(
                    db,
                    log_type='aggregate',
                    module='data_maintenance',
                    message=f'完成日级数据聚合，生成 {aggregated_count} 条统计记录',
                    details={
                        'aggregated_count': aggregated_count,
                        'start_time': start_time.isoformat(),
                        'end_time': yesterday.isoformat()
                    }
                )
                
                logger.info(f"✅ 日级数据聚合完成，生成了 {aggregated_count} 条统计记录")
            else:
                logger.info("⏭️ 没有新数据需要聚合")
                
        except Exception as e:
            logger.error(f"❌ 日级数据聚合失败: {e}")
            db.rollback()
            DataMaintenance.log_system_event(
                db,
                log_type='error',
                module='data_maintenance',
                message=f'日级数据聚合失败: {str(e)}',
                details={'error': str(e)}
            )
        finally:
            db.close()
