from __future__ import annotations

import asyncio
import uuid
import json
import logging
import os
import re
import socket
from datetime import datetime, timedelta
from typing import Any, List, Optional

import requests
import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from analytics_service import (
    get_dashboard_payload,
    get_databoard_stats_payload,
    get_host_detail_stats_payload,
    get_ping_logs_page,
)
from app_settings import settings
from auth import create_access_token, decode_access_token, get_current_user, get_optional_current_user, get_password_hash, verify_password
from cache import cache_manager
from data_maintenance import DataMaintenance
from database_backup import import_database_backup_sql, iter_database_backup_sql
from database import (
    Alert,
    DataScreenConfig,
    Host,
    PingRecord,
    PingStatistics,
    SessionLocal,
    SystemConfig,
    SystemLog,
    User,
    get_database_backend,
    get_db,
    init_db,
    init_default_config,
)
from ip_location_service import ip_location_service
from notification import notifier
from notification_template import NotificationTemplate
from ping_service import PingService
from scheduler import scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

DEFAULT_CONTROL_CENTER = {
    "name": "北京市",
    "country": "中国",
    "province": "北京市",
    "city": "北京市",
    "isp": "默认监控中心",
    "longitude": 116.4074,
    "latitude": 39.9042,
    "ip": None,
    "source": "default",
}
CONTROL_CENTER_CACHE_TTL = 60 * 30
PUBLIC_IP_CACHE_TTL = 60 * 10
PUBLIC_IP_SOURCES = (
    {"name": "ipip", "url": "https://myip.ipip.net/", "type": "text"},
    {"name": "ipify", "url": "https://api.ipify.org?format=json", "type": "json", "field": "ip"},
    {"name": "jsonip", "url": "https://ipv4.jsonip.com", "type": "json", "field": "ip"},
)
DATABASE_BACKUP_MAX_BYTES = 512 * 1024 * 1024
DATABASE_BACKUP_LOG_LIMIT = 200
DATABASE_IMPORT_JOB_TTL = timedelta(hours=6)
database_import_jobs: dict[str, dict[str, Any]] = {}

app = FastAPI(title="Ping 监控系统", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HostCreate(BaseModel):
    name: str
    address: str
    description: Optional[str] = None
    alert_threshold: float = 20.0
    country: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    isp: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class HostUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    alert_threshold: Optional[float] = None
    country: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    isp: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class HostResponse(BaseModel):
    id: int
    name: str
    address: str
    description: Optional[str]
    enabled: bool
    alert_threshold: float
    resolved_ip: Optional[str]
    country: Optional[str]
    province: Optional[str]
    city: Optional[str]
    isp: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    location_status: str
    created_at: datetime

    class Config:
        from_attributes = True


class PingRecordResponse(BaseModel):
    id: int
    host_id: int
    packet_sent: int
    packet_received: int
    packet_loss: float
    min_rtt: Optional[float]
    max_rtt: Optional[float]
    avg_rtt: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True


class SystemConfigUpdate(BaseModel):
    check_interval: Optional[int] = None
    packet_count: Optional[int] = None
    packet_timeout: Optional[int] = None
    serverchan_key: Optional[str] = None
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    notification_mode: Optional[str] = None
    data_retention_days: Optional[int] = None
    cleanup_time: Optional[str] = None
    aggregate_interval: Optional[int] = None
    dashboard_chart_points: Optional[int] = None
    auto_refresh_location: Optional[bool] = None
    report_webhook_url: Optional[str] = None
    report_webhook_secret: Optional[str] = None
    daily_report_enabled: Optional[bool] = None
    daily_report_time: Optional[str] = None
    weekly_report_enabled: Optional[bool] = None
    weekly_report_time: Optional[str] = None
    monthly_report_enabled: Optional[bool] = None
    monthly_report_time: Optional[str] = None


class SystemConfigResponse(BaseModel):
    id: int
    check_interval: int
    packet_count: int
    packet_timeout: int
    serverchan_key: Optional[str]
    webhook_url: Optional[str]
    webhook_secret: Optional[str]
    notification_mode: str
    data_retention_days: int
    cleanup_time: str
    aggregate_interval: int
    dashboard_chart_points: int
    auto_refresh_location: bool
    report_webhook_url: Optional[str]
    report_webhook_secret: Optional[str]
    daily_report_enabled: bool
    daily_report_time: str
    weekly_report_enabled: bool
    weekly_report_time: str
    monthly_report_enabled: bool
    monthly_report_time: str
    updated_at: datetime

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserPasswordUpdate(BaseModel):
    old_password: str
    new_username: Optional[str] = None
    new_password: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


def append_database_import_log(job: dict[str, Any], message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    logs = job.setdefault("logs", [])
    logs.append(f"[{timestamp}] {message}")
    if len(logs) > DATABASE_BACKUP_LOG_LIMIT:
        del logs[:-DATABASE_BACKUP_LOG_LIMIT]


def update_database_import_job(job_id: str, **changes: Any) -> None:
    job = database_import_jobs.get(job_id)
    if not job:
        return

    message = changes.get("message")
    if message:
        append_database_import_log(job, str(message))

    job.update(changes)
    job["updated_at"] = datetime.now().isoformat(timespec="seconds")


def cleanup_database_import_jobs() -> None:
    cutoff = datetime.now() - DATABASE_IMPORT_JOB_TTL
    for job_id, job in list(database_import_jobs.items()):
        if job.get("status") not in {"completed", "failed"}:
            continue

        try:
            updated_at = datetime.fromisoformat(job.get("updated_at") or job.get("created_at") or "")
        except ValueError:
            updated_at = datetime.now()

        if updated_at < cutoff:
            database_import_jobs.pop(job_id, None)


def get_latest_active_database_import_job() -> dict[str, Any] | None:
    active_jobs = [
        job
        for job in database_import_jobs.values()
        if job.get("status") in {"queued", "running"}
    ]
    if not active_jobs:
        return None

    def get_job_updated_at(job: dict[str, Any]) -> datetime:
        try:
            return datetime.fromisoformat(job.get("updated_at") or job.get("created_at") or "")
        except ValueError:
            return datetime.min

    return max(active_jobs, key=get_job_updated_at)


def calculate_database_import_progress(payload: dict[str, Any]) -> int:
    stage = payload.get("stage")
    total = payload.get("total_statements") or 0

    if stage == "validating":
        return 3
    if stage == "parsing":
        parsed = payload.get("parsed_statements") or 0
        if total:
            return min(25, 5 + int(parsed / total * 20))
        return 10
    if stage == "executing":
        executed = payload.get("executed_statements") or 0
        skipped = payload.get("skipped_statements") or 0
        if total:
            return min(90, 25 + int((executed + skipped) / total * 65))
        return 30
    if stage == "verifying":
        return 95
    if stage == "completed":
        return 100
    return 0


def run_database_import_job(job_id: str, sql_text: str, filename: str, username: str) -> None:
    import_db: Session | None = SessionLocal()
    post_import_db: Session | None = None
    scheduler_was_running = scheduler.scheduler.running

    def on_progress(payload: dict[str, Any]) -> None:
        update_database_import_job(
            job_id,
            **payload,
            progress=calculate_database_import_progress(payload),
        )

    update_database_import_job(
        job_id,
        status="running",
        stage="preparing",
        progress=1,
        message=f"准备导入 {filename}",
    )

    if scheduler_was_running:
        scheduler.scheduler.pause()
        update_database_import_job(job_id, message="已暂停定时任务")

    try:
        result = import_database_backup_sql(import_db, sql_text, progress_callback=on_progress)
        import_db.close()
        import_db = None

        update_database_import_job(
            job_id,
            stage="post_import",
            progress=96,
            message="正在刷新运行配置",
        )
        init_default_config()
        DataMaintenance.backfill_host_latest_metrics()

        post_import_db = SessionLocal()
        config = get_or_create_system_config(post_import_db)
        notifier.configure(
            serverchan_key=config.serverchan_key,
            webhook_url=config.webhook_url,
            webhook_secret=config.webhook_secret,
        )
        if not settings.disable_scheduler:
            scheduler.reload_config()
        invalidate_runtime_cache()

        DataMaintenance.log_system_event(
            post_import_db,
            log_type="info",
            module="database_backup",
            message=f"用户 {username} 导入数据库备份",
            details={
                "filename": filename,
                "executed_statements": result["executed_statements"],
                "skipped_statements": result["skipped_statements"],
                "table_counts": result["table_counts"],
            },
        )

        update_database_import_job(
            job_id,
            status="completed",
            stage="completed",
            progress=100,
            result={"message": "数据库备份导入完成", **result},
            message="导入完成",
        )
    except Exception as exc:
        logger.exception("Database backup import failed: %s", exc)
        update_database_import_job(
            job_id,
            status="failed",
            stage="failed",
            error=str(exc),
            message=f"导入失败：{exc}",
        )
    finally:
        try:
            if scheduler_was_running and scheduler.scheduler.running:
                scheduler.scheduler.resume()
                update_database_import_job(job_id, message="已恢复定时任务")
        finally:
            if import_db is not None:
                import_db.close()
            if post_import_db is not None:
                post_import_db.close()


def get_or_create_system_config(db: Session) -> SystemConfig:
    config = db.query(SystemConfig).first()
    if config:
        return config

    config = SystemConfig()
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def get_or_create_datascreen_config(db: Session) -> DataScreenConfig:
    config = db.query(DataScreenConfig).first()
    if config:
        return config

    config = DataScreenConfig()
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def build_datascreen_payload(db: Session, screen_config: DataScreenConfig) -> dict:
    payload = get_dashboard_payload(db)
    payload["screen_config"] = {
        "brand_name": screen_config.brand_name,
        "refresh_interval": screen_config.refresh_interval,
        "enable_3d": screen_config.enable_3d,
        "enable_animation": screen_config.enable_animation,
        "map_view_angle": screen_config.map_view_angle,
        "particle_count": screen_config.particle_count,
        "show_flow_lines": screen_config.show_flow_lines,
        "theme_color": screen_config.theme_color,
        "public_enabled": screen_config.public_enabled,
    }
    payload["control_center"] = get_control_center_payload()
    return payload


def get_runtime_public_ip() -> str | None:
    cache_key = cache_manager.build_key("runtime_public_ip")
    cached_ip = cache_manager.get_json(cache_key)
    if isinstance(cached_ip, str) and ip_location_service.is_valid_ip(cached_ip) and not ip_location_service.is_private_ip(cached_ip):
        return cached_ip

    for source in PUBLIC_IP_SOURCES:
        try:
            response = requests.get(source["url"], timeout=5)
            response.raise_for_status()
            if source["type"] == "json":
                payload = response.json()
                candidate_ip = str(payload.get(source["field"], "")).strip()
            else:
                match = re.search(r"((?:\d{1,3}\.){3}\d{1,3})", response.text)
                candidate_ip = match.group(1).strip() if match else ""

            if candidate_ip and ip_location_service.is_valid_ip(candidate_ip) and not ip_location_service.is_private_ip(candidate_ip):
                cache_manager.set_json(cache_key, candidate_ip, PUBLIC_IP_CACHE_TTL)
                return candidate_ip
        except Exception as exc:
            logger.warning("获取运行机器公网 IP 失败(%s): %s", source["name"], exc)

    return None


def get_control_center_payload() -> dict:
    cache_key = cache_manager.build_key("datascreen_control_center")
    cached_payload = cache_manager.get_json(cache_key)
    if isinstance(cached_payload, dict):
        return cached_payload

    control_center = DEFAULT_CONTROL_CENTER.copy()
    public_ip = get_runtime_public_ip()
    if not public_ip:
        cache_manager.set_json(cache_key, control_center, CONTROL_CENTER_CACHE_TTL)
        return control_center

    merged_location = None
    sources = []
    location_sources = (
        {
            "name": "baidu-qifu",
            "url": f"https://qifu.baidu.com/api/v1/ip-portrait/brief-info?ip={public_ip}",
            "headers": ip_location_service.BAIDU_REQUEST_HEADERS,
            "parser": ip_location_service.parse_baidu_qifu,
        },
        {
            "name": "ip2location.io",
            "url": f"https://api.ip2location.io/?ip={public_ip}&format=json",
            "headers": None,
            "parser": ip_location_service.parse_ip2location,
        },
    )

    for source in location_sources:
        try:
            response = requests.get(source["url"], headers=source["headers"], timeout=5)
            response.raise_for_status()
            payload = response.json()
            parsed = source["parser"](payload)
            normalized = ip_location_service._normalize_result(parsed)
            if not normalized:
                continue
            merged_location = ip_location_service._merge_result(merged_location, normalized)
            sources.append(source["name"])
        except Exception as exc:
            logger.warning("获取监控中心地理位置失败(%s): %s", source["name"], exc)

    if merged_location:
        location_name = " / ".join(
            [part for part in [merged_location.get("province"), merged_location.get("city")] if part]
        ) or "监控中心"
        control_center.update(
            {
                "name": location_name,
                "country": merged_location.get("country") or control_center["country"],
                "province": merged_location.get("province") or control_center["province"],
                "city": merged_location.get("city") or control_center["city"],
                "isp": merged_location.get("isp") or control_center["isp"],
                "longitude": merged_location.get("longitude") if merged_location.get("longitude") is not None else control_center["longitude"],
                "latitude": merged_location.get("latitude") if merged_location.get("latitude") is not None else control_center["latitude"],
                "ip": public_ip,
                "source": " + ".join(sources) if sources else "default",
            }
        )
    else:
        control_center["ip"] = public_ip

    cache_manager.set_json(cache_key, control_center, CONTROL_CENTER_CACHE_TTL)
    return control_center


def ensure_public_datascreen_enabled(screen_config: DataScreenConfig) -> None:
    if not screen_config.public_enabled:
        raise HTTPException(status_code=403, detail="可视化大屏当前未对游客开放")


def invalidate_runtime_cache() -> None:
    cache_manager.invalidate_namespace("dashboard")
    cache_manager.invalidate_namespace("databoard")
    cache_manager.invalidate_namespace("datascreen_payload")


def is_valid_time_text(value: str) -> bool:
    try:
        hour_text, minute_text = value.split(":")
        hour = int(hour_text)
        minute = int(minute_text)
    except (AttributeError, ValueError):
        return False
    return 0 <= hour <= 23 and 0 <= minute <= 59


def is_dingtalk_webhook(value: str | None) -> bool:
    return bool(value and "oapi.dingtalk.com" in value)


def cache_get_or_set(namespace: str, key_parts: list[str], ttl: int, builder):
    key = cache_manager.build_key(namespace, *key_parts)
    cached = cache_manager.get_json(key)
    if cached is not None:
        return cached
    value = builder()
    cache_manager.set_json(key, value, ttl)
    return value


def get_runtime_ping_settings(db: Session) -> tuple[int, int]:
    config = get_or_create_system_config(db)
    return config.packet_count, config.packet_timeout


LOCATION_FIELDS = ("country", "province", "city", "isp", "latitude", "longitude")
DISPLAY_LOCATION_FIELDS = ("country", "province", "city")


def resolve_host_ip(address: str) -> str:
    try:
        return socket.gethostbyname(address)
    except socket.gaierror:
        return address


def host_has_display_location(host: Host) -> bool:
    return any(getattr(host, field, None) for field in DISPLAY_LOCATION_FIELDS)


def host_has_any_location(host: Host) -> bool:
    return host_has_display_location(host) or host.latitude is not None or host.longitude is not None


def host_needs_location_completion(host: Host) -> bool:
    return not host_has_display_location(host) or host.latitude is None or host.longitude is None


def apply_manual_location_fields(host: Host, payload: dict) -> None:
    for field in LOCATION_FIELDS:
        if field in payload:
            setattr(host, field, payload.get(field))

    if host_has_any_location(host):
        host.location_status = "success"
    elif not getattr(host, "location_status", None):
        host.location_status = "pending"


async def sync_host_location_from_ip(
    host: Host,
    *,
    force_refresh: bool = False,
    overwrite_existing: bool = False,
) -> dict:
    if not host.resolved_ip:
        host.location_status = "failed"
        return {
            "status": "failed",
            "error": "IP 地址为空",
        }

    location = await ip_location_service.get_location(host.resolved_ip, force_refresh=force_refresh)

    if location.get("status") == "success":
        for field in LOCATION_FIELDS:
            new_value = location.get(field)
            current_value = getattr(host, field, None)
            should_write = overwrite_existing or current_value in (None, "")
            if should_write and new_value is not None:
                setattr(host, field, new_value)

        if overwrite_existing and (location.get("latitude") is None or location.get("longitude") is None):
            host.latitude = None
            host.longitude = None

        host.location_status = "success" if host_has_any_location(host) else "failed"
        return location

    if host_has_any_location(host):
        host.location_status = "success"
    else:
        host.location_status = location.get("status", "failed")
    return location


def get_location_sync_policy(config: SystemConfig, host: Host) -> tuple[bool, bool] | None:
    auto_refresh = bool(getattr(config, "auto_refresh_location", False))
    if auto_refresh:
        return True, True
    if host_needs_location_completion(host):
        return False, False
    return None


def ensure_host_resolved_ip(db: Session, host: Host) -> str | None:
    resolved_ip = resolve_host_ip(host.address)
    if host.resolved_ip != resolved_ip:
        host.resolved_ip = resolved_ip
        db.commit()
        db.refresh(host)
    return host.resolved_ip


async def maybe_sync_host_location_after_ping(
    db: Session,
    host: Host,
    *,
    config: SystemConfig | None = None,
) -> dict | None:
    config = config or get_or_create_system_config(db)
    policy = get_location_sync_policy(config, host)
    resolved_ip = ensure_host_resolved_ip(db, host)
    if not resolved_ip or policy is None:
        return None

    force_refresh, overwrite_existing = policy
    try:
        location = await sync_host_location_from_ip(
            host,
            force_refresh=force_refresh,
            overwrite_existing=overwrite_existing,
        )
        db.commit()
        db.refresh(host)
        return location
    except Exception as exc:
        db.rollback()
        logger.warning("Ping 后同步主机 %s 的地理位置失败: %s", host.name, exc)
        return None


def maybe_sync_host_location_after_ping_sync(
    db: Session,
    host: Host,
    *,
    config: SystemConfig | None = None,
) -> dict | None:
    config = config or get_or_create_system_config(db)
    policy = get_location_sync_policy(config, host)
    resolved_ip = ensure_host_resolved_ip(db, host)
    if not resolved_ip or policy is None:
        return None

    force_refresh, overwrite_existing = policy
    try:
        location = asyncio.run(
            sync_host_location_from_ip(
                host,
                force_refresh=force_refresh,
                overwrite_existing=overwrite_existing,
            )
        )
        db.commit()
        db.refresh(host)
        return location
    except Exception as exc:
        db.rollback()
        logger.warning("后台 Ping 后同步主机 %s 的地理位置失败: %s", host.name, exc)
        return None


def update_host_latest_metrics(host: Host, result: dict, checked_at: datetime) -> None:
    host.last_packet_loss = result["packet_loss"]
    host.last_avg_rtt = result["avg_rtt"]
    host.last_check = checked_at
    if result.get("status") == "unreachable" or result["packet_loss"] >= host.alert_threshold:
        host.last_status = "abnormal"
    else:
        host.last_status = "normal"


def persist_ping_record(db: Session, host_id: int, result: dict, host: Host | None = None) -> PingRecord:
    checked_at = datetime.now()
    record = PingRecord(
        host_id=host_id,
        packet_sent=result["packet_sent"],
        packet_received=result["packet_received"],
        packet_loss=result["packet_loss"],
        min_rtt=result["min_rtt"],
        max_rtt=result["max_rtt"],
        avg_rtt=result["avg_rtt"],
        created_at=checked_at,
    )
    db.add(record)
    if host is not None:
        update_host_latest_metrics(host, result, checked_at)
    db.commit()
    db.refresh(record)
    return record


def run_ping_task(host_id: int, packet_count: int, packet_timeout: int) -> None:
    db = SessionLocal()
    try:
        host = db.query(Host).filter(Host.id == host_id).first()
        if not host:
            logger.warning("后台 Ping 任务跳过，主机不存在: %s", host_id)
            return

        result = PingService.ping_host(host.address, count=packet_count, timeout=packet_timeout)
        persist_ping_record(db, host_id, result, host=host)
        config = get_or_create_system_config(db)
        maybe_sync_host_location_after_ping_sync(db, host, config=config)
        invalidate_runtime_cache()
    finally:
        db.close()


@app.on_event("startup")
async def startup_event():
    init_db()

    from database_migrations import DatabaseMigration

    DatabaseMigration.run_migrations()
    init_default_config()
    DataMaintenance.backfill_host_latest_metrics()
    cache_manager.ensure_connection()
    if settings.disable_scheduler:
        logger.info("Scheduler disabled by DISABLE_SCHEDULER")
    else:
        scheduler.start()
    logger.info(
        "应用启动完成，数据库后端: %s，Redis缓存: %s",
        get_database_backend(),
        "enabled" if cache_manager.enabled else "disabled",
    )


@app.on_event("shutdown")
async def shutdown_event():
    scheduler.stop()
    logger.info("应用已关闭")


@app.get("/api/auth/check")
async def check_admin_exists(db: Session = Depends(get_db)):
    user = db.query(User).first()
    return {"has_admin": user is not None}


@app.post("/api/auth/init", response_model=TokenResponse)
async def init_admin(user_data: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="管理员已存在")

    if not user_data.username or len(user_data.username) < 3:
        raise HTTPException(status_code=400, detail="用户名至少需要 3 个字符")
    if not user_data.password or len(user_data.password) < 5:
        raise HTTPException(status_code=400, detail="密码至少需要 5 个字符")

    admin_user = User(
        username=user_data.username,
        password_hash=get_password_hash(user_data.password),
        is_admin=True,
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)

    DataMaintenance.log_system_event(
        db,
        log_type="info",
        module="authentication",
        message=f"初始化管理员账户: {admin_user.username}",
        details={"user_id": admin_user.id, "username": admin_user.username},
    )

    access_token = create_access_token(data={"sub": admin_user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user or not verify_password(user_data.password, user.password_hash):
        DataMaintenance.log_system_event(
            db,
            log_type="warning",
            module="authentication",
            message=f"登录失败: {user_data.username}",
            details={"username": user_data.username, "reason": "invalid_credentials"},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    DataMaintenance.log_system_event(
        db,
        log_type="info",
        module="authentication",
        message=f"用户登录成功: {user.username}",
        details={"user_id": user.id, "username": user.username},
    )

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "is_admin": current_user.is_admin}


@app.put("/api/auth/update-password")
async def update_password(
    user_data: UserPasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(user_data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")

    changes = {}

    if user_data.new_username and user_data.new_username != current_user.username:
        if len(user_data.new_username) < 3:
            raise HTTPException(status_code=400, detail="新用户名至少需要 3 个字符")
        existing = (
            db.query(User)
            .filter(User.username == user_data.new_username, User.id != current_user.id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="用户名已存在")
        current_user.username = user_data.new_username
        changes["username"] = user_data.new_username

    if user_data.new_password:
        if len(user_data.new_password) < 5:
            raise HTTPException(status_code=400, detail="新密码至少需要 5 个字符")
        current_user.password_hash = get_password_hash(user_data.new_password)
        changes["password"] = True

    if not changes:
        raise HTTPException(status_code=400, detail="没有需要更新的内容")

    db.commit()

    DataMaintenance.log_system_event(
        db,
        log_type="info",
        module="authentication",
        message=f"用户 {current_user.id} 更新了账号信息",
        details={"user_id": current_user.id, "changes": list(changes.keys())},
    )
    return {"message": "修改成功"}


@app.get("/api/hosts", response_model=List[HostResponse])
async def get_hosts(current_user: Optional[User] = Depends(get_optional_current_user), db: Session = Depends(get_db)):
    return db.query(Host).order_by(Host.id.asc()).all()


@app.post("/api/hosts", response_model=HostResponse)
async def create_host(host: HostCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(Host).filter(Host.name == host.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="主机名称已存在")

    db_host = Host(
        name=host.name,
        address=host.address,
        description=host.description,
        alert_threshold=host.alert_threshold,
    )

    # 自动解析IP地址
    apply_manual_location_fields(db_host, host.dict())
    db_host.resolved_ip = resolve_host_ip(db_host.address)

    # 自动获取地理位置
    if db_host.resolved_ip and (not host_has_any_location(db_host) or host_needs_location_completion(db_host)):
        await sync_host_location_from_ip(db_host, overwrite_existing=False)

    db.add(db_host)
    db.commit()
    db.refresh(db_host)

    invalidate_runtime_cache()
    DataMaintenance.log_system_event(
        db,
        log_type="info",
        module="host_management",
        message=f"用户 {current_user.username} 添加主机: {db_host.name}",
        details={"host_id": db_host.id, "address": db_host.address},
    )
    return db_host


@app.get("/api/hosts/{host_id}", response_model=HostResponse)
async def get_host(host_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")
    return host


@app.put("/api/hosts/{host_id}", response_model=HostResponse)
async def update_host(
    host_id: int,
    host_update: HostUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")

    update_data = host_update.dict(exclude_unset=True)
    if "name" in update_data and update_data["name"] != host.name:
        existing = db.query(Host).filter(Host.name == update_data["name"], Host.id != host_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="主机名称已存在")

    address_changed = "address" in update_data and update_data["address"] != host.address
    location_fields_updated = any(field in update_data for field in LOCATION_FIELDS)

    for key, value in update_data.items():
        setattr(host, key, value)

    if location_fields_updated:
        host.location_status = "success" if host_has_any_location(host) else "pending"

    if address_changed:
        host.resolved_ip = resolve_host_ip(host.address)

    if host.resolved_ip and (address_changed or location_fields_updated or host_needs_location_completion(host)):
        await sync_host_location_from_ip(host, overwrite_existing=False)

    db.commit()
    db.refresh(host)

    invalidate_runtime_cache()
    DataMaintenance.log_system_event(
        db,
        log_type="info",
        module="host_management",
        message=f"用户 {current_user.username} 更新主机: {host.name}",
        details={"host_id": host.id, "updated_fields": list(update_data.keys())},
    )
    return host


@app.delete("/api/hosts/{host_id}")
async def delete_host(host_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")

    host_name = host.name
    host_address = host.address

    db.query(PingRecord).filter(PingRecord.host_id == host_id).delete(synchronize_session=False)
    db.query(PingStatistics).filter(PingStatistics.host_id == host_id).delete(synchronize_session=False)
    db.query(Alert).filter(Alert.host_id == host_id).delete(synchronize_session=False)
    db.delete(host)
    db.commit()

    invalidate_runtime_cache()
    DataMaintenance.log_system_event(
        db,
        log_type="warning",
        module="host_management",
        message=f"用户 {current_user.username} 删除主机: {host_name}",
        details={"host_id": host_id, "address": host_address},
    )
    return {"message": "删除成功"}


@app.post("/api/hosts/{host_id}/refresh-location")
async def refresh_host_location(
    host_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """手动刷新主机地理位置"""
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")

    # 解析域名为IP地址
    address = host.address
    logger.info(f"开始刷新主机 {host.name} ({address}) 的地理位置")

    try:
        # 尝试解析域名
        ip_address = resolve_host_ip(address)
        logger.info(f"域名 {address} 解析为 IP: {ip_address}")
    except Exception as e:
        # 如果解析失败，假设已经是IP地址
        logger.warning(f"域名解析失败: {e}，假设 {address} 已经是IP地址")
        ip_address = address

    host.resolved_ip = ip_address

    # 获取地理位置
    logger.info(f"正在获取 {ip_address} 的地理位置...")
    location = await sync_host_location_from_ip(
        host,
        force_refresh=True,
        overwrite_existing=True,
    )
    logger.info(f"地理位置获取结果: {location}")

    # 更新主机信息

    db.commit()
    db.refresh(host)

    invalidate_runtime_cache()

    return {
        "message": "地理位置刷新成功",
        "location": {
            "country": host.country,
            "province": host.province,
            "city": host.city,
            "isp": host.isp,
            "status": host.location_status,
            "error": location.get("error"),
        }
    }


@app.post("/api/hosts/{host_id}/refresh-ip")
async def refresh_host_ip(
    host_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """手动刷新主机IP地址"""
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")

    logger.info(f"开始刷新主机 {host.name} ({host.address}) 的IP地址")

    # DNS解析域名为IP
    try:
        resolved_ip = resolve_host_ip(host.address)
        host.resolved_ip = resolved_ip
        config = get_or_create_system_config(db)
        if host.resolved_ip and (config.auto_refresh_location or host_needs_location_completion(host)):
            await sync_host_location_from_ip(
                host,
                force_refresh=bool(config.auto_refresh_location),
                overwrite_existing=bool(config.auto_refresh_location),
            )
        db.commit()
        db.refresh(host)

        invalidate_runtime_cache()

        logger.info(f"成功解析 {host.address} 为 IP: {resolved_ip}")
        return {
            "message": "IP地址刷新成功",
            "resolved_ip": resolved_ip,
            "location_status": host.location_status,
        }
    except Exception as e:
        logger.error(f"解析 {host.address} 失败: {e}")
        return {
            "message": "IP地址解析失败",
            "error": str(e),
            "resolved_ip": None
        }


@app.post("/api/ping/{host_id}")
async def ping_now(
    host_id: int,
    background_tasks: BackgroundTasks,
    background: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")

    packet_count, packet_timeout = get_runtime_ping_settings(db)

    if background and background_tasks:
        background_tasks.add_task(run_ping_task, host.id, packet_count, packet_timeout)
        return {
            "message": "Ping 任务已启动",
            "host": host.name,
            "address": host.address,
        }

    result = PingService.ping_host(host.address, count=packet_count, timeout=packet_timeout)
    persist_ping_record(db, host.id, result, host=host)
    config = get_or_create_system_config(db)
    await maybe_sync_host_location_after_ping(db, host, config=config)
    invalidate_runtime_cache()
    return {
        "host": host.name,
        "address": host.address,
        "resolved_ip": host.resolved_ip,
        "location_status": host.location_status,
        **result,
    }


@app.get("/api/ping-stream/{host_id}")
async def ping_stream(host_id: int, token: str, db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=401, detail="缺少 token")

    try:
        payload = decode_access_token(token)
        if not payload.get("sub"):
            raise HTTPException(status_code=401, detail="无效 token")
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Token 验证失败") from exc

    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")

    packet_count, packet_timeout = get_runtime_ping_settings(db)

    async def event_generator():
        stream_db = SessionLocal()
        summary_event = None
        try:
            for event in PingService.ping_host_stream(host.address, count=packet_count, timeout=packet_timeout):
                if event.get("type") == "summary":
                    summary_event = event
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.05)

            if summary_event:
                stream_host = stream_db.query(Host).filter(Host.id == host_id).first()
                persist_ping_record(
                    stream_db,
                    host.id,
                    {
                        "packet_sent": summary_event["packet_sent"],
                        "packet_received": summary_event["packet_received"],
                        "packet_loss": summary_event["packet_loss"],
                        "min_rtt": summary_event["min_rtt"],
                        "max_rtt": summary_event["max_rtt"],
                        "avg_rtt": summary_event["avg_rtt"],
                    },
                    host=stream_host,
                )
                if stream_host:
                    config = get_or_create_system_config(stream_db)
                    await maybe_sync_host_location_after_ping(stream_db, stream_host, config=config)
                invalidate_runtime_cache()
        except Exception as exc:
            logger.error("流式 Ping 失败: %s", exc)
            yield f"data: {json.dumps({'type': 'error', 'message': f'Ping 失败: {exc}'}, ensure_ascii=False)}\n\n"
        finally:
            stream_db.close()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/ping-all")
async def ping_all(background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    hosts = db.query(Host).filter(Host.enabled.is_(True)).all()
    if not hosts:
        raise HTTPException(status_code=404, detail="没有启用的主机")

    packet_count, packet_timeout = get_runtime_ping_settings(db)
    for host in hosts:
        background_tasks.add_task(run_ping_task, host.id, packet_count, packet_timeout)

    return {
        "message": f"已启动 {len(hosts)} 个主机的 Ping 任务",
        "count": len(hosts),
        "hosts": [host.name for host in hosts],
    }


@app.get("/api/ping/logs")
async def get_ping_logs(
    host_id: Optional[int] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_ping_logs_page(
        db,
        host_id=host_id,
        search=search,
        status=status,
        page=page,
        page_size=page_size,
    )


@app.get("/api/records/{host_id}", response_model=List[PingRecordResponse])
async def get_records(
    host_id: int,
    hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    since = datetime.now() - timedelta(hours=hours)
    return (
        db.query(PingRecord)
        .filter(PingRecord.host_id == host_id, PingRecord.created_at >= since)
        .order_by(PingRecord.created_at.desc(), PingRecord.id.desc())
        .all()
    )


@app.get("/api/alerts")
async def get_alerts(
    hours: int = 24,
    page: int = 1,
    page_size: int = 20,
    keyword: Optional[str] = None,
    alert_type: Optional[str] = None,
    sent_status: Optional[str] = None,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    since = datetime.now() - timedelta(hours=hours)
    query = db.query(Alert).filter(Alert.created_at >= since)

    if keyword:
        search = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                Alert.host_name.ilike(search),
                Alert.message.ilike(search),
            )
        )

    if alert_type:
        query = query.filter(Alert.alert_type == alert_type)

    if sent_status == "sent":
        query = query.filter(Alert.is_sent.is_(True))
    elif sent_status == "unsent":
        query = query.filter(Alert.is_sent.is_(False))

    total = query.count()
    items = (
        query.order_by(Alert.created_at.desc(), Alert.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@app.get("/api/dashboard")
async def get_dashboard(current_user: Optional[User] = Depends(get_optional_current_user), db: Session = Depends(get_db)):
    return cache_get_or_set(
        "dashboard",
        ["summary"],
        settings.cache_ttl_dashboard,
        lambda: get_dashboard_payload(db),
    )


@app.get("/api/databoard/stats/{time_range}")
async def get_databoard_stats(
    time_range: str,
    sort_by: str = "avg_packet_loss",
    sort_order: str = "desc",
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    return cache_get_or_set(
        "databoard",
        ["stats", time_range, sort_by, sort_order],
        settings.cache_ttl_databoard,
        lambda: get_databoard_stats_payload(
            db,
            time_range=time_range,
            sort_by=sort_by,
            sort_order=sort_order,
        ),
    )


@app.get("/api/databoard/host/{host_id}/{time_range}")
async def get_host_detail_stats(
    host_id: int,
    time_range: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    def builder():
        payload = get_host_detail_stats_payload(db, host_id=host_id, time_range=time_range)
        if payload is None:
            raise HTTPException(status_code=404, detail="主机不存在")
        return payload

    return cache_get_or_set(
        "databoard",
        ["host", host_id, time_range],
        settings.cache_ttl_host_detail,
        builder,
    )


@app.get("/api/config", response_model=SystemConfigResponse)
async def get_config(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_or_create_system_config(db)


@app.put("/api/config", response_model=SystemConfigResponse)
async def update_config(
    config_update: SystemConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    config = get_or_create_system_config(db)
    update_data = config_update.dict(exclude_unset=True)

    if "check_interval" in update_data and update_data["check_interval"] < 1:
        raise HTTPException(status_code=400, detail="检测间隔必须大于 0")
    if "packet_count" in update_data and update_data["packet_count"] < 1:
        raise HTTPException(status_code=400, detail="发包数量必须大于 0")
    if "packet_timeout" in update_data and update_data["packet_timeout"] < 1:
        raise HTTPException(status_code=400, detail="超时时间必须大于 0")
    for field_name, field_label in {
        "cleanup_time": "数据清理时间",
        "daily_report_time": "日报发送时间",
        "weekly_report_time": "周报发送时间",
        "monthly_report_time": "月报发送时间",
    }.items():
        if field_name in update_data and update_data[field_name] is not None:
            if not is_valid_time_text(update_data[field_name]):
                raise HTTPException(status_code=400, detail=f"{field_label}格式应为 HH:MM")

    if "report_webhook_url" in update_data and update_data["report_webhook_url"]:
        if not is_dingtalk_webhook(update_data["report_webhook_url"]):
            raise HTTPException(status_code=400, detail="报表机器人仅支持钉钉 Webhook 地址")

    final_report_webhook_url = update_data.get("report_webhook_url", config.report_webhook_url)
    report_enabled_flags = {
        "daily_report_enabled": update_data.get("daily_report_enabled", config.daily_report_enabled),
        "weekly_report_enabled": update_data.get("weekly_report_enabled", config.weekly_report_enabled),
        "monthly_report_enabled": update_data.get("monthly_report_enabled", config.monthly_report_enabled),
    }
    if any(bool(value) for value in report_enabled_flags.values()) and not is_dingtalk_webhook(final_report_webhook_url):
        raise HTTPException(status_code=400, detail="启用日报/周报/月报前，请先配置报表专用钉钉机器人 Webhook 地址")

    for key, value in update_data.items():
        setattr(config, key, value)

    db.commit()
    db.refresh(config)

    notifier.configure(
        serverchan_key=config.serverchan_key,
        webhook_url=config.webhook_url,
        webhook_secret=config.webhook_secret,
    )
    scheduler.reload_config()
    invalidate_runtime_cache()

    DataMaintenance.log_system_event(
        db,
        log_type="info",
        module="system_config",
        message=f"用户 {current_user.username} 更新系统配置",
        details={"updated_fields": list(update_data.keys())},
    )
    return config


@app.post("/api/test-notification/{notification_type}")
async def test_notification(
    notification_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    config = get_or_create_system_config(db)
    notifier.configure(
        serverchan_key=config.serverchan_key,
        webhook_url=config.webhook_url,
        webhook_secret=config.webhook_secret,
    )

    use_markdown = notification_type == "webhook"
    msg_data = NotificationTemplate.get_test_notification(use_markdown=use_markdown)

    if notification_type == "serverchan":
        if not config.serverchan_key:
            raise HTTPException(status_code=400, detail="Server酱未配置")
        success = notifier.send_serverchan(msg_data["title"], msg_data["content"])
    elif notification_type == "webhook":
        if not config.webhook_url:
            raise HTTPException(status_code=400, detail="Webhook 未配置")
        success = notifier.send_webhook(msg_data["content"], title=msg_data["title"])
    else:
        raise HTTPException(status_code=400, detail="不支持的通知类型")

    if not success:
        raise HTTPException(status_code=500, detail="测试通知发送失败")
    return {"message": "测试通知已发送"}


@app.post("/api/reports/{report_type}/send")
async def send_report(
    report_type: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from report_service import ReportService

    try:
        result = ReportService.send_report(
            report_type,
            db=db,
            trigger_source=f"manual:{current_user.username}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return result


@app.get("/api/database/export")
async def export_database_backup(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ping_monitor_backup_{timestamp}.sql"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    return StreamingResponse(
        iter_database_backup_sql(db),
        media_type="application/sql; charset=utf-8",
        headers=headers,
    )


@app.post("/api/database/import")
async def import_database_backup(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    cleanup_database_import_jobs()

    filename = file.filename or ""
    if not filename.lower().endswith(".sql"):
        raise HTTPException(status_code=400, detail="请上传 .sql 备份文件")

    content = await file.read(DATABASE_BACKUP_MAX_BYTES + 1)
    if len(content) > DATABASE_BACKUP_MAX_BYTES:
        raise HTTPException(status_code=413, detail="SQL 备份文件不能超过 512MB")

    try:
        sql_text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="SQL 备份文件必须使用 UTF-8 编码") from exc

    job_id = uuid.uuid4().hex
    database_import_jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "stage": "queued",
        "progress": 0,
        "filename": filename,
        "username": current_user.username,
        "logs": [],
        "result": None,
        "error": None,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    append_database_import_log(database_import_jobs[job_id], f"已创建导入任务：{filename}")
    background_tasks.add_task(run_database_import_job, job_id, sql_text, filename, current_user.username)

    return {
        "job_id": job_id,
        "status": "queued",
        "message": "数据库备份导入任务已开始",
    }


@app.get("/api/database/import/latest")
async def get_latest_database_import_status():
    cleanup_database_import_jobs()

    job = get_latest_active_database_import_job()
    if not job:
        raise HTTPException(status_code=404, detail="当前没有正在导入的任务")
    return job


@app.get("/api/database/import/{job_id}")
async def get_database_import_status(job_id: str):
    cleanup_database_import_jobs()

    job = database_import_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="导入任务不存在")
    return job


@app.get("/api/system-logs")
async def get_system_logs(
    log_type: Optional[str] = None,
    module: Optional[str] = None,
    keyword: Optional[str] = None,
    hours: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(SystemLog)

    if hours:
        since = datetime.now() - timedelta(hours=hours)
        query = query.filter(SystemLog.created_at >= since)

    if log_type:
        query = query.filter(SystemLog.log_type == log_type)
    if module:
        query = query.filter(SystemLog.module == module)
    if keyword:
        search = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                SystemLog.message.ilike(search),
                SystemLog.details.ilike(search),
                SystemLog.module.ilike(search),
            )
        )

    total = query.count()
    items = (
        query.order_by(SystemLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "items": [
            {
                "id": item.id,
                "log_type": item.log_type,
                "module": item.module,
                "message": item.message,
                "details": item.details,
                "created_at": item.created_at,
            }
            for item in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.post("/api/system-logs/cleanup")
async def cleanup_system_logs(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cutoff_date = datetime.now() - timedelta(days=days)
    count = db.query(SystemLog).filter(SystemLog.created_at < cutoff_date).count()
    if count > 0:
        db.query(SystemLog).filter(SystemLog.created_at < cutoff_date).delete(synchronize_session=False)
        db.commit()

    DataMaintenance.log_system_event(
        db,
        log_type="cleanup",
        module="system_logs",
        message=f"清理系统日志 {count} 条",
        details={"deleted_count": count, "days": days},
    )
    return {"message": f"清理了 {count} 条系统日志", "deleted_count": count}


def do_hourly_aggregation() -> None:
    DataMaintenance.aggregate_hourly_stats()


def do_daily_aggregation() -> None:
    DataMaintenance.aggregate_daily_stats()


def do_data_cleanup(days: Optional[int]) -> None:
    DataMaintenance.cleanup_old_records(days=days)


@app.post("/api/data-maintenance/aggregate-hourly")
async def trigger_hourly_aggregation(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    background_tasks.add_task(do_hourly_aggregation)
    return {"message": "小时聚合任务已启动"}


@app.post("/api/data-maintenance/aggregate-daily")
async def trigger_daily_aggregation(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    background_tasks.add_task(do_daily_aggregation)
    return {"message": "天聚合任务已启动"}


@app.post("/api/data-maintenance/cleanup")
async def trigger_data_cleanup(
    background_tasks: BackgroundTasks,
    days: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if days is None:
        config = get_or_create_system_config(db)
        days = config.data_retention_days
    background_tasks.add_task(do_data_cleanup, days)
    return {"message": f"数据清理任务已启动（保留 {days} 天）"}


# ==================== 游客专用 API（无需认证） ====================

@app.get("/api/public/datascreen/status")
async def get_public_datascreen_status(db: Session = Depends(get_db)):
    screen_config = get_or_create_datascreen_config(db)
    return {"enabled": screen_config.public_enabled}


@app.get("/api/public/datascreen")
async def get_public_datascreen(db: Session = Depends(get_db)):
    screen_config = get_or_create_datascreen_config(db)
    ensure_public_datascreen_enabled(screen_config)

    return cache_get_or_set(
        "datascreen_payload",
        ["data"],
        screen_config.refresh_interval,
        lambda: build_datascreen_payload(db, screen_config),
    )


@app.get("/api/public/alerts")
async def get_public_alerts(hours: int = 24, limit: int = 50, db: Session = Depends(get_db)):
    screen_config = get_or_create_datascreen_config(db)
    ensure_public_datascreen_enabled(screen_config)

    since = datetime.now() - timedelta(hours=hours)
    items = (
        db.query(Alert)
        .filter(Alert.created_at >= since)
        .order_by(Alert.created_at.desc(), Alert.id.desc())
        .limit(limit)
        .all()
    )
    return {"items": items, "total": len(items)}


@app.get("/api/datascreen/preview")
async def get_datascreen_preview(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    screen_config = get_or_create_datascreen_config(db)
    return cache_get_or_set(
        "datascreen_payload",
        ["data"],
        screen_config.refresh_interval,
        lambda: build_datascreen_payload(db, screen_config),
    )


# ==================== 可视化配置管理接口 ====================

class DataScreenConfigUpdate(BaseModel):
    brand_name: Optional[str] = None
    refresh_interval: Optional[int] = None
    enable_3d: Optional[bool] = None
    enable_animation: Optional[bool] = None
    map_view_angle: Optional[int] = None
    particle_count: Optional[int] = None
    show_flow_lines: Optional[bool] = None
    theme_color: Optional[str] = None
    public_enabled: Optional[bool] = None


class DataScreenConfigResponse(BaseModel):
    id: int
    brand_name: str
    refresh_interval: int
    enable_3d: bool
    enable_animation: bool
    map_view_angle: int
    particle_count: int
    show_flow_lines: bool
    theme_color: str
    public_enabled: bool
    updated_at: datetime

    class Config:
        from_attributes = True


@app.get("/api/datascreen/config", response_model=DataScreenConfigResponse)
async def get_datascreen_config(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return get_or_create_datascreen_config(db)


@app.put("/api/datascreen/config", response_model=DataScreenConfigResponse)
async def update_datascreen_config(
    config_update: DataScreenConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    config = get_or_create_datascreen_config(db)

    if config_update.brand_name is not None:
        brand_name = config_update.brand_name.strip()
        if len(brand_name) > 60:
            raise HTTPException(status_code=400, detail="大屏名称不能超过 60 个字符")
        config.brand_name = brand_name

    if config_update.refresh_interval is not None:
        if config_update.refresh_interval < 1 or config_update.refresh_interval > 60:
            raise HTTPException(status_code=400, detail="刷新间隔必须在 1-60 秒之间")
        config.refresh_interval = config_update.refresh_interval

    if config_update.enable_3d is not None:
        config.enable_3d = config_update.enable_3d

    if config_update.enable_animation is not None:
        config.enable_animation = config_update.enable_animation

    if config_update.map_view_angle is not None:
        if config_update.map_view_angle < 0 or config_update.map_view_angle > 90:
            raise HTTPException(status_code=400, detail="地图视角必须在 0-90 度之间")
        config.map_view_angle = config_update.map_view_angle

    if config_update.particle_count is not None:
        if config_update.particle_count < 0 or config_update.particle_count > 1000:
            raise HTTPException(status_code=400, detail="粒子数量必须在 0-1000 之间")
        config.particle_count = config_update.particle_count

    if config_update.show_flow_lines is not None:
        config.show_flow_lines = config_update.show_flow_lines

    if config_update.theme_color is not None:
        if config_update.theme_color not in ["blue", "green", "purple", "red", "orange"]:
            raise HTTPException(status_code=400, detail="主题色必须是 blue/green/purple/red/orange 之一")
        config.theme_color = config_update.theme_color

    if config_update.public_enabled is not None:
        config.public_enabled = config_update.public_enabled

    config.updated_at = datetime.now()
    db.commit()
    db.refresh(config)

    cache_manager.invalidate_namespace("datascreen_payload")

    return config


frontend_dist = settings.frontend_dist

if frontend_dist.exists():
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/")
    async def serve_frontend_root():
        return FileResponse(str(frontend_dist / "index.html"))

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")

        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))

        index_path = frontend_dist / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))

        raise HTTPException(status_code=404, detail="前端资源未找到")
else:
    @app.get("/")
    async def root():
        return {
            "message": "Ping 监控系统 API",
            "version": "2.0.0",
            "database_backend": get_database_backend(),
            "cache_enabled": cache_manager.enabled,
        }


if __name__ == "__main__":
    reload_enabled = os.getenv("UVICORN_RELOAD", "false").strip().lower() in {"1", "true", "yes", "on"}
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=reload_enabled)
