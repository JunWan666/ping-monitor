from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from cache import cache_manager
from database import Host, PingRecord, PingStatistics, SessionLocal, SystemConfig, SystemLog
from host_status import ONLINE_PACKET_LOSS_THRESHOLD

logger = logging.getLogger(__name__)


class DataMaintenance:
    @staticmethod
    def log_system_event(
        db: Session,
        log_type: str,
        module: str,
        message: str,
        details: Optional[dict] = None,
    ) -> None:
        try:
            log = SystemLog(
                log_type=log_type,
                module=module,
                message=message,
                details=json.dumps(details, ensure_ascii=False) if details else None,
            )
            db.add(log)
            db.commit()
        except Exception as exc:
            logger.error("记录系统日志失败: %s", exc)
            db.rollback()

    @staticmethod
    def cleanup_old_records(days: int | None = None) -> None:
        db = SessionLocal()
        try:
            if days is None:
                config = db.query(SystemConfig).first()
                days = config.data_retention_days if config else 30

            cutoff_date = datetime.now() - timedelta(days=days)
            count = db.query(PingRecord).filter(PingRecord.created_at < cutoff_date).count()

            if count > 0:
                db.query(PingRecord).filter(PingRecord.created_at < cutoff_date).delete(synchronize_session=False)
                db.commit()
                DataMaintenance.log_system_event(
                    db,
                    log_type="cleanup",
                    module="data_maintenance",
                    message=f"清理了 {count} 条 {days} 天前的 Ping 记录",
                    details={
                        "deleted_count": count,
                        "days": days,
                        "cutoff_date": cutoff_date.isoformat(),
                    },
                )
                cache_manager.invalidate_namespace("dashboard")
                cache_manager.invalidate_namespace("databoard")
                logger.info("数据清理完成，删除记录数: %s", count)
            else:
                logger.info("没有需要清理的 Ping 记录")
        except Exception as exc:
            logger.error("数据清理失败: %s", exc)
            db.rollback()
            DataMaintenance.log_system_event(
                db,
                log_type="error",
                module="data_maintenance",
                message=f"数据清理失败: {exc}",
                details={"error": str(exc)},
            )
        finally:
            db.close()

    @staticmethod
    def aggregate_hourly_stats() -> None:
        db = SessionLocal()
        try:
            last_stat = (
                db.query(PingStatistics)
                .filter(PingStatistics.stat_type == "hourly")
                .order_by(PingStatistics.stat_time.desc())
                .first()
            )

            if last_stat:
                start_time = last_stat.stat_time + timedelta(hours=1)
            else:
                first_record = db.query(PingRecord).order_by(PingRecord.created_at.asc()).first()
                if not first_record:
                    logger.info("没有原始 Ping 数据，跳过小时聚合")
                    return
                start_time = first_record.created_at.replace(minute=0, second=0, microsecond=0)

            current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
            if start_time >= current_hour:
                logger.info("没有新的小时区间需要聚合")
                return

            bucket_expr = DataMaintenance._time_bucket_expr(
                db.bind.dialect.name,
                PingRecord.created_at,
                bucket="hour",
            )

            rows = (
                db.query(
                    PingRecord.host_id.label("host_id"),
                    bucket_expr.label("bucket_time"),
                    func.count(PingRecord.id).label("check_count"),
                    func.sum(case((PingRecord.packet_loss < ONLINE_PACKET_LOSS_THRESHOLD, 1), else_=0)).label("online_count"),
                    func.avg(PingRecord.packet_loss).label("avg_packet_loss"),
                    func.avg(PingRecord.avg_rtt).label("avg_rtt"),
                    func.min(PingRecord.min_rtt).label("min_rtt"),
                    func.max(PingRecord.max_rtt).label("max_rtt"),
                )
                .join(Host, PingRecord.host_id == Host.id)
                .filter(PingRecord.created_at >= start_time, PingRecord.created_at < current_hour)
                .group_by(PingRecord.host_id, bucket_expr)
                .order_by(bucket_expr.asc(), PingRecord.host_id.asc())
                .all()
            )

            aggregated_count = 0
            for row in rows:
                stat_time = DataMaintenance._parse_bucket_time(row.bucket_time, bucket="hour")
                stat = DataMaintenance._upsert_stat(
                    db,
                    host_id=row.host_id,
                    stat_type="hourly",
                    stat_time=stat_time,
                )
                stat.check_count = int(row.check_count or 0)
                stat.online_count = int(row.online_count or 0)
                stat.avg_packet_loss = round(float(row.avg_packet_loss or 0), 2)
                stat.avg_rtt = round(float(row.avg_rtt), 2) if row.avg_rtt is not None else None
                stat.min_rtt = round(float(row.min_rtt), 2) if row.min_rtt is not None else None
                stat.max_rtt = round(float(row.max_rtt), 2) if row.max_rtt is not None else None
                aggregated_count += 1

            if aggregated_count > 0:
                db.commit()
                DataMaintenance.log_system_event(
                    db,
                    log_type="aggregate",
                    module="data_maintenance",
                    message=f"完成小时级数据聚合，生成 {aggregated_count} 条统计记录",
                    details={
                        "aggregated_count": aggregated_count,
                        "start_time": start_time.isoformat(),
                        "end_time": current_hour.isoformat(),
                    },
                )
                cache_manager.invalidate_namespace("databoard")
                logger.info("小时聚合完成，生成记录数: %s", aggregated_count)
            else:
                logger.info("没有新的小时聚合结果")
        except Exception as exc:
            logger.error("小时聚合失败: %s", exc)
            db.rollback()
            DataMaintenance.log_system_event(
                db,
                log_type="error",
                module="data_maintenance",
                message=f"小时聚合失败: {exc}",
                details={"error": str(exc)},
            )
        finally:
            db.close()

    @staticmethod
    def aggregate_daily_stats() -> None:
        db = SessionLocal()
        try:
            last_stat = (
                db.query(PingStatistics)
                .filter(PingStatistics.stat_type == "daily")
                .order_by(PingStatistics.stat_time.desc())
                .first()
            )

            if last_stat:
                start_time = last_stat.stat_time + timedelta(days=1)
            else:
                first_hourly = (
                    db.query(PingStatistics)
                    .filter(PingStatistics.stat_type == "hourly")
                    .order_by(PingStatistics.stat_time.asc())
                    .first()
                )
                if not first_hourly:
                    logger.info("没有小时聚合数据，跳过天聚合")
                    return
                start_time = first_hourly.stat_time.replace(hour=0, minute=0, second=0, microsecond=0)

            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if start_time >= today:
                logger.info("没有新的天区间需要聚合")
                return

            bucket_expr = DataMaintenance._time_bucket_expr(
                db.bind.dialect.name,
                PingStatistics.stat_time,
                bucket="day",
            )
            weighted_rtt_sum = func.sum(
                case(
                    (PingStatistics.avg_rtt.is_not(None), PingStatistics.avg_rtt * PingStatistics.check_count),
                    else_=0.0,
                )
            )
            weighted_rtt_count = func.sum(
                case(
                    (PingStatistics.avg_rtt.is_not(None), PingStatistics.check_count),
                    else_=0,
                )
            )

            rows = (
                db.query(
                    PingStatistics.host_id.label("host_id"),
                    bucket_expr.label("bucket_time"),
                    func.sum(PingStatistics.check_count).label("check_count"),
                    func.sum(PingStatistics.online_count).label("online_count"),
                    (
                        func.sum(PingStatistics.avg_packet_loss * PingStatistics.check_count)
                        / func.sum(PingStatistics.check_count)
                    ).label("avg_packet_loss"),
                    (weighted_rtt_sum / func.nullif(weighted_rtt_count, 0)).label("avg_rtt"),
                    func.min(PingStatistics.min_rtt).label("min_rtt"),
                    func.max(PingStatistics.max_rtt).label("max_rtt"),
                )
                .filter(
                    PingStatistics.stat_type == "hourly",
                    PingStatistics.stat_time >= start_time,
                    PingStatistics.stat_time < today,
                )
                .group_by(PingStatistics.host_id, bucket_expr)
                .order_by(bucket_expr.asc(), PingStatistics.host_id.asc())
                .all()
            )

            aggregated_count = 0
            for row in rows:
                stat_time = DataMaintenance._parse_bucket_time(row.bucket_time, bucket="day")
                stat = DataMaintenance._upsert_stat(
                    db,
                    host_id=row.host_id,
                    stat_type="daily",
                    stat_time=stat_time,
                )
                stat.check_count = int(row.check_count or 0)
                stat.online_count = int(row.online_count or 0)
                stat.avg_packet_loss = round(float(row.avg_packet_loss or 0), 2)
                stat.avg_rtt = round(float(row.avg_rtt), 2) if row.avg_rtt is not None else None
                stat.min_rtt = round(float(row.min_rtt), 2) if row.min_rtt is not None else None
                stat.max_rtt = round(float(row.max_rtt), 2) if row.max_rtt is not None else None
                aggregated_count += 1

            if aggregated_count > 0:
                db.commit()
                DataMaintenance.log_system_event(
                    db,
                    log_type="aggregate",
                    module="data_maintenance",
                    message=f"完成天级数据聚合，生成 {aggregated_count} 条统计记录",
                    details={
                        "aggregated_count": aggregated_count,
                        "start_time": start_time.isoformat(),
                        "end_time": today.isoformat(),
                    },
                )
                cache_manager.invalidate_namespace("databoard")
                logger.info("天聚合完成，生成记录数: %s", aggregated_count)
            else:
                logger.info("没有新的天聚合结果")
        except Exception as exc:
            logger.error("天聚合失败: %s", exc)
            db.rollback()
            DataMaintenance.log_system_event(
                db,
                log_type="error",
                module="data_maintenance",
                message=f"天聚合失败: {exc}",
                details={"error": str(exc)},
            )
        finally:
            db.close()

    @staticmethod
    def _upsert_stat(db: Session, *, host_id: int, stat_type: str, stat_time: datetime) -> PingStatistics:
        stat = (
            db.query(PingStatistics)
            .filter(
                PingStatistics.host_id == host_id,
                PingStatistics.stat_type == stat_type,
                PingStatistics.stat_time == stat_time,
            )
            .first()
        )
        if stat:
            return stat

        stat = PingStatistics(
            host_id=host_id,
            stat_type=stat_type,
            stat_time=stat_time,
            check_count=0,
            online_count=0,
            avg_packet_loss=0,
        )
        db.add(stat)
        db.flush()
        return stat

    @staticmethod
    def _time_bucket_expr(dialect_name: str, column, *, bucket: str):
        if bucket == "hour":
            if dialect_name == "mysql":
                return func.date_format(column, "%Y-%m-%d %H:00:00")
            return func.strftime("%Y-%m-%d %H:00:00", column)

        if dialect_name == "mysql":
            return func.date_format(column, "%Y-%m-%d 00:00:00")
        return func.strftime("%Y-%m-%d 00:00:00", column)

    @staticmethod
    def _parse_bucket_time(value, *, bucket: str) -> datetime:
        if isinstance(value, datetime):
            if bucket == "hour":
                return value.replace(minute=0, second=0, microsecond=0)
            return value.replace(hour=0, minute=0, second=0, microsecond=0)

        fmt = "%Y-%m-%d %H:00:00" if bucket == "hour" else "%Y-%m-%d 00:00:00"
        return datetime.strptime(str(value), fmt)
