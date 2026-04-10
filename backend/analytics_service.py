from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from database import Alert, Host, PingRecord, PingStatistics


TIME_RANGE_TO_HOURS = {
    "1h": 1,
    "1d": 24,
    "3d": 72,
    "7d": 168,
    "15d": 360,
    "30d": 720,
}


def get_hours_from_range(time_range: str) -> int:
    return TIME_RANGE_TO_HOURS.get(time_range, 24)


def format_time_for_range(dt: datetime, time_range: str) -> str:
    if time_range == "1h":
        return dt.strftime("%H:%M")
    if time_range in {"1d", "3d"}:
        return dt.strftime("%m/%d %H:%M")
    return dt.strftime("%m/%d")


def _merge_optional_min(current, incoming):
    if incoming is None:
        return current
    if current is None:
        return incoming
    return min(current, incoming)


def _merge_optional_max(current, incoming):
    if incoming is None:
        return current
    if current is None:
        return incoming
    return max(current, incoming)


def get_ping_logs_page(
    db: Session,
    *,
    host_id: Optional[int],
    search: Optional[str],
    status: Optional[str],
    page: int,
    page_size: int,
):
    query = db.query(
        PingRecord.id,
        PingRecord.host_id,
        Host.name.label("host_name"),
        Host.address.label("host_address"),
        Host.alert_threshold.label("alert_threshold"),
        PingRecord.packet_sent,
        PingRecord.packet_received,
        PingRecord.packet_loss,
        PingRecord.min_rtt,
        PingRecord.max_rtt,
        PingRecord.avg_rtt,
        PingRecord.created_at.label("check_time"),
    ).join(Host, PingRecord.host_id == Host.id)

    if host_id:
        query = query.filter(PingRecord.host_id == host_id)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Host.name.like(search_pattern),
                Host.address.like(search_pattern),
            )
        )

    if status == "normal":
        query = query.filter(PingRecord.packet_loss < Host.alert_threshold)
    elif status == "abnormal":
        query = query.filter(PingRecord.packet_loss >= Host.alert_threshold)

    total = query.order_by(None).count()
    offset = (page - 1) * page_size
    items = (
        query.order_by(PingRecord.created_at.desc(), PingRecord.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    logs = []
    for item in items:
        is_normal = item.packet_loss < item.alert_threshold
        logs.append(
            {
                "id": item.id,
                "host_id": item.host_id,
                "host_name": item.host_name,
                "host_address": item.host_address,
                "packet_sent": item.packet_sent,
                "packet_received": item.packet_received,
                "packet_loss": item.packet_loss,
                "min_rtt": item.min_rtt,
                "max_rtt": item.max_rtt,
                "avg_rtt": item.avg_rtt,
                "check_time": item.check_time,
                "status": "正常" if is_normal else "异常",
            }
        )

    return {
        "items": logs,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_dashboard_payload(db: Session):
    total_hosts = db.query(func.count(Host.id)).scalar() or 0
    enabled_hosts = db.query(func.count(Host.id)).filter(Host.enabled.is_(True)).scalar() or 0

    one_hour_ago = datetime.now() - timedelta(hours=1)
    recent_alerts = db.query(func.count(Alert.id)).filter(Alert.created_at >= one_hour_ago).scalar() or 0

    latest_record_subquery = (
        db.query(
            PingRecord.host_id.label("host_id"),
            PingRecord.packet_loss.label("packet_loss"),
            PingRecord.avg_rtt.label("avg_rtt"),
            PingRecord.created_at.label("created_at"),
            func.row_number()
            .over(
                partition_by=PingRecord.host_id,
                order_by=(PingRecord.created_at.desc(), PingRecord.id.desc()),
            )
            .label("row_num"),
        )
        .subquery()
    )

    rows = (
        db.query(
            Host.id,
            Host.name,
            Host.address,
            Host.enabled,
            Host.alert_threshold,
            latest_record_subquery.c.packet_loss,
            latest_record_subquery.c.avg_rtt,
            latest_record_subquery.c.created_at.label("last_check"),
        )
        .outerjoin(
            latest_record_subquery,
            and_(
                Host.id == latest_record_subquery.c.host_id,
                latest_record_subquery.c.row_num == 1,
            ),
        )
        .order_by(Host.id.asc())
        .all()
    )

    host_status = []
    for row in rows:
        if row.last_check is None:
            status = "未知"
        else:
            status = "正常" if row.packet_loss < row.alert_threshold else "异常"

        host_status.append(
            {
                "id": row.id,
                "name": row.name,
                "address": row.address,
                "enabled": row.enabled,
                "status": status,
                "packet_loss": row.packet_loss,
                "avg_rtt": row.avg_rtt,
                "last_check": row.last_check,
            }
        )

    return {
        "total_hosts": total_hosts,
        "enabled_hosts": enabled_hosts,
        "recent_alerts": recent_alerts,
        "host_status": host_status,
    }


def get_databoard_stats_payload(
    db: Session,
    *,
    time_range: str,
    sort_by: str,
    sort_order: str,
):
    hours = get_hours_from_range(time_range)
    since = datetime.now() - timedelta(hours=hours)

    hosts = db.query(Host).filter(Host.enabled.is_(True)).order_by(Host.id.asc()).all()
    host_dict = {host.id: host for host in hosts}
    total_hosts = len(hosts)

    if total_hosts == 0:
        return {
            "total_hosts": 0,
            "avg_online_rate": 0,
            "avg_rtt": 0,
            "avg_packet_loss": 0,
            "host_stats": [],
            "trend_data": [],
        }

    use_aggregated = time_range in {"1d", "3d", "7d", "15d", "30d"}
    stat_type = "daily" if time_range in {"15d", "30d"} else "hourly"

    if use_aggregated:
        stat_rows = (
            db.query(
                PingStatistics.host_id,
                PingStatistics.stat_time,
                PingStatistics.check_count,
                PingStatistics.online_count,
                PingStatistics.avg_packet_loss,
                PingStatistics.avg_rtt,
                PingStatistics.min_rtt,
                PingStatistics.max_rtt,
            )
            .filter(
                PingStatistics.host_id.in_(list(host_dict.keys())),
                PingStatistics.stat_type == stat_type,
                PingStatistics.stat_time >= since,
            )
            .order_by(PingStatistics.stat_time.asc(), PingStatistics.host_id.asc())
            .all()
        )
        if stat_rows:
            return _build_databoard_from_aggregated(
                hosts=hosts,
                stat_rows=stat_rows,
                time_range=time_range,
                sort_by=sort_by,
                sort_order=sort_order,
            )

    record_rows = (
        db.query(
            PingRecord.host_id,
            PingRecord.packet_loss,
            PingRecord.avg_rtt,
            PingRecord.min_rtt,
            PingRecord.max_rtt,
            PingRecord.created_at,
        )
        .join(Host, PingRecord.host_id == Host.id)
        .filter(Host.enabled.is_(True), PingRecord.created_at >= since)
        .order_by(PingRecord.created_at.asc(), PingRecord.id.asc())
        .all()
    )
    return _build_databoard_from_raw(
        hosts=hosts,
        host_dict=host_dict,
        record_rows=record_rows,
        time_range=time_range,
        sort_by=sort_by,
        sort_order=sort_order,
    )


def get_host_detail_stats_payload(db: Session, *, host_id: int, time_range: str):
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        return None

    hours = get_hours_from_range(time_range)
    since = datetime.now() - timedelta(hours=hours)

    use_aggregated = time_range in {"1d", "3d", "7d", "15d", "30d"}
    stat_type = "daily" if time_range in {"15d", "30d"} else "hourly"

    result = []
    if use_aggregated:
        rows = (
            db.query(
                PingStatistics.stat_time,
                PingStatistics.avg_packet_loss,
                PingStatistics.avg_rtt,
                PingStatistics.min_rtt,
                PingStatistics.max_rtt,
            )
            .filter(
                PingStatistics.host_id == host_id,
                PingStatistics.stat_type == stat_type,
                PingStatistics.stat_time >= since,
            )
            .order_by(PingStatistics.stat_time.asc())
            .all()
        )
        if rows:
            for row in rows:
                result.append(
                    {
                        "time": format_time_for_range(row.stat_time, time_range),
                        "packet_loss": row.avg_packet_loss,
                        "avg_rtt": row.avg_rtt or 0,
                        "min_rtt": row.min_rtt or 0,
                        "max_rtt": row.max_rtt or 0,
                    }
                )
            return result

    rows = (
        db.query(
            PingRecord.created_at,
            PingRecord.packet_loss,
            PingRecord.avg_rtt,
            PingRecord.min_rtt,
            PingRecord.max_rtt,
        )
        .filter(PingRecord.host_id == host_id, PingRecord.created_at >= since)
        .order_by(PingRecord.created_at.asc(), PingRecord.id.asc())
        .all()
    )
    for row in rows:
        result.append(
            {
                "time": format_time_for_range(row.created_at, time_range),
                "packet_loss": row.packet_loss,
                "avg_rtt": row.avg_rtt or 0,
                "min_rtt": row.min_rtt or 0,
                "max_rtt": row.max_rtt or 0,
            }
        )
    return result


def _build_databoard_from_aggregated(*, hosts, stat_rows, time_range, sort_by, sort_order):
    host_stats_map: Dict[int, Dict[str, float]] = {}
    trend_groups = defaultdict(list)

    for row in stat_rows:
        trend_groups[row.stat_time].append(row)

        host_entry = host_stats_map.setdefault(
            row.host_id,
            {
                "check_count": 0,
                "online_count": 0,
                "weighted_packet_loss": 0.0,
                "weighted_rtt": 0.0,
                "weighted_rtt_count": 0,
                "min_rtt": None,
                "max_rtt": None,
            },
        )
        host_entry["check_count"] += row.check_count
        host_entry["online_count"] += row.online_count
        host_entry["weighted_packet_loss"] += row.avg_packet_loss * row.check_count
        if row.avg_rtt is not None:
            host_entry["weighted_rtt"] += row.avg_rtt * row.check_count
            host_entry["weighted_rtt_count"] += row.check_count
        host_entry["min_rtt"] = _merge_optional_min(host_entry["min_rtt"], row.min_rtt)
        host_entry["max_rtt"] = _merge_optional_max(host_entry["max_rtt"], row.max_rtt)

    host_stats = []
    total_online_rate = 0.0
    total_avg_rtt = 0.0
    total_avg_packet_loss = 0.0

    for host in hosts:
        entry = host_stats_map.get(host.id)
        if not entry or entry["check_count"] == 0:
            continue

        online_rate = round((entry["online_count"] / entry["check_count"]) * 100, 2)
        avg_packet_loss = round(entry["weighted_packet_loss"] / entry["check_count"], 2)
        avg_rtt = (
            round(entry["weighted_rtt"] / entry["weighted_rtt_count"], 2)
            if entry["weighted_rtt_count"] > 0
            else 0
        )
        min_rtt = round(entry["min_rtt"], 2) if entry["min_rtt"] is not None else 0
        max_rtt = round(entry["max_rtt"], 2) if entry["max_rtt"] is not None else 0

        total_online_rate += online_rate
        total_avg_rtt += avg_rtt
        total_avg_packet_loss += avg_packet_loss

        host_stats.append(
            {
                "id": host.id,
                "name": host.name,
                "address": host.address,
                "check_count": entry["check_count"],
                "online_rate": online_rate,
                "avg_packet_loss": avg_packet_loss,
                "avg_rtt": avg_rtt,
                "min_rtt": min_rtt,
                "max_rtt": max_rtt,
            }
        )

    trend_data = []
    for time_key in sorted(trend_groups.keys()):
        rows = trend_groups[time_key]
        total_check = sum(row.check_count for row in rows)
        if total_check == 0:
            continue
        total_online = sum(row.online_count for row in rows)
        avg_packet_loss = round(sum(row.avg_packet_loss * row.check_count for row in rows) / total_check, 2)

        weighted_rtt = 0.0
        weighted_rtt_count = 0
        for row in rows:
            if row.avg_rtt is not None:
                weighted_rtt += row.avg_rtt * row.check_count
                weighted_rtt_count += row.check_count
        avg_rtt = round(weighted_rtt / weighted_rtt_count, 2) if weighted_rtt_count > 0 else 0

        trend_data.append(
            {
                "time": format_time_for_range(time_key, time_range),
                "avg_packet_loss": avg_packet_loss,
                "avg_rtt": avg_rtt,
                "online_rate": round((total_online / total_check) * 100, 2),
            }
        )

    _sort_host_stats(host_stats, sort_by, sort_order)

    host_count = len(host_stats)
    return {
        "total_hosts": len(hosts),
        "avg_online_rate": round(total_online_rate / host_count, 2) if host_count > 0 else 0,
        "avg_rtt": round(total_avg_rtt / host_count, 2) if host_count > 0 else 0,
        "avg_packet_loss": round(total_avg_packet_loss / host_count, 2) if host_count > 0 else 0,
        "host_stats": host_stats,
        "trend_data": trend_data,
    }


def _build_databoard_from_raw(*, hosts, host_dict, record_rows, time_range, sort_by, sort_order):
    host_stats_map: Dict[int, Dict[str, float]] = {}
    trend_groups = defaultdict(list)
    interval_minutes = 5 if time_range == "1h" else 60

    for row in record_rows:
        host = host_dict.get(row.host_id)
        if not host:
            continue

        host_entry = host_stats_map.setdefault(
            row.host_id,
            {
                "check_count": 0,
                "online_count": 0,
                "packet_loss_sum": 0.0,
                "rtt_sum": 0.0,
                "rtt_count": 0,
                "min_rtt": None,
                "max_rtt": None,
            },
        )
        host_entry["check_count"] += 1
        if row.packet_loss < host.alert_threshold:
            host_entry["online_count"] += 1
        host_entry["packet_loss_sum"] += row.packet_loss
        if row.avg_rtt is not None:
            host_entry["rtt_sum"] += row.avg_rtt
            host_entry["rtt_count"] += 1
        host_entry["min_rtt"] = _merge_optional_min(host_entry["min_rtt"], row.min_rtt)
        host_entry["max_rtt"] = _merge_optional_max(host_entry["max_rtt"], row.max_rtt)

        timestamp = row.created_at.timestamp()
        group_key = int(timestamp // (interval_minutes * 60)) * (interval_minutes * 60)
        trend_groups[group_key].append((row, host.alert_threshold))

    host_stats = []
    total_online_rate = 0.0
    total_avg_rtt = 0.0
    total_avg_packet_loss = 0.0

    for host in hosts:
        entry = host_stats_map.get(host.id)
        if not entry or entry["check_count"] == 0:
            continue

        online_rate = round((entry["online_count"] / entry["check_count"]) * 100, 2)
        avg_packet_loss = round(entry["packet_loss_sum"] / entry["check_count"], 2)
        avg_rtt = round(entry["rtt_sum"] / entry["rtt_count"], 2) if entry["rtt_count"] > 0 else 0
        min_rtt = round(entry["min_rtt"], 2) if entry["min_rtt"] is not None else 0
        max_rtt = round(entry["max_rtt"], 2) if entry["max_rtt"] is not None else 0

        total_online_rate += online_rate
        total_avg_rtt += avg_rtt
        total_avg_packet_loss += avg_packet_loss

        host_stats.append(
            {
                "id": host.id,
                "name": host.name,
                "address": host.address,
                "check_count": entry["check_count"],
                "online_rate": online_rate,
                "avg_packet_loss": avg_packet_loss,
                "avg_rtt": avg_rtt,
                "min_rtt": min_rtt,
                "max_rtt": max_rtt,
            }
        )

    trend_data = []
    for group_key in sorted(trend_groups.keys()):
        items = trend_groups[group_key]
        if not items:
            continue
        avg_packet_loss = round(sum(row.packet_loss for row, _ in items) / len(items), 2)
        valid_rtts = [row.avg_rtt for row, _ in items if row.avg_rtt is not None]
        avg_rtt = round(sum(valid_rtts) / len(valid_rtts), 2) if valid_rtts else 0
        online_count = sum(1 for row, threshold in items if row.packet_loss < threshold)
        trend_data.append(
            {
                "time": format_time_for_range(datetime.fromtimestamp(group_key), time_range),
                "avg_packet_loss": avg_packet_loss,
                "avg_rtt": avg_rtt,
                "online_rate": round((online_count / len(items)) * 100, 2),
            }
        )

    _sort_host_stats(host_stats, sort_by, sort_order)

    host_count = len(host_stats)
    return {
        "total_hosts": len(hosts),
        "avg_online_rate": round(total_online_rate / host_count, 2) if host_count > 0 else 0,
        "avg_rtt": round(total_avg_rtt / host_count, 2) if host_count > 0 else 0,
        "avg_packet_loss": round(total_avg_packet_loss / host_count, 2) if host_count > 0 else 0,
        "host_stats": host_stats,
        "trend_data": trend_data,
    }


def _sort_host_stats(host_stats: List[dict], sort_by: str, sort_order: str) -> None:
    reverse = sort_order == "desc"
    if sort_by not in {"avg_packet_loss", "online_rate", "avg_rtt"}:
        sort_by = "avg_packet_loss"
    host_stats.sort(key=lambda item: item.get(sort_by, 0), reverse=reverse)
