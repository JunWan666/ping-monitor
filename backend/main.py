from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional

import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from analytics_service import (
    get_dashboard_payload,
    get_databoard_stats_payload,
    get_host_detail_stats_payload,
    get_ping_logs_page,
)
from app_settings import settings
from auth import create_access_token, decode_access_token, get_current_user, get_password_hash, verify_password
from cache import cache_manager
from data_maintenance import DataMaintenance
from database import (
    Alert,
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


class HostUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    alert_threshold: Optional[float] = None


class HostResponse(BaseModel):
    id: int
    name: str
    address: str
    description: Optional[str]
    enabled: bool
    alert_threshold: float
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


def get_or_create_system_config(db: Session) -> SystemConfig:
    config = db.query(SystemConfig).first()
    if config:
        return config

    config = SystemConfig()
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def invalidate_runtime_cache() -> None:
    cache_manager.invalidate_namespace("dashboard")
    cache_manager.invalidate_namespace("databoard")


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


def persist_ping_record(db: Session, host_id: int, result: dict) -> PingRecord:
    record = PingRecord(
        host_id=host_id,
        packet_sent=result["packet_sent"],
        packet_received=result["packet_received"],
        packet_loss=result["packet_loss"],
        min_rtt=result["min_rtt"],
        max_rtt=result["max_rtt"],
        avg_rtt=result["avg_rtt"],
        created_at=datetime.now(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def run_ping_task(host_id: int, host_address: str, packet_count: int, packet_timeout: int) -> None:
    db = SessionLocal()
    try:
        result = PingService.ping_host(host_address, count=packet_count, timeout=packet_timeout)
        persist_ping_record(db, host_id, result)
        invalidate_runtime_cache()
    finally:
        db.close()


@app.on_event("startup")
async def startup_event():
    init_db()

    from database_migrations import DatabaseMigration

    DatabaseMigration.run_migrations()
    init_default_config()
    cache_manager.ensure_connection()
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
async def get_hosts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Host).order_by(Host.id.asc()).all()


@app.post("/api/hosts", response_model=HostResponse)
async def create_host(host: HostCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    existing = db.query(Host).filter(Host.name == host.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="主机名称已存在")

    db_host = Host(**host.dict())
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

    for key, value in update_data.items():
        setattr(host, key, value)

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
        background_tasks.add_task(run_ping_task, host.id, host.address, packet_count, packet_timeout)
        return {
            "message": "Ping 任务已启动",
            "host": host.name,
            "address": host.address,
        }

    result = PingService.ping_host(host.address, count=packet_count, timeout=packet_timeout)
    persist_ping_record(db, host.id, result)
    invalidate_runtime_cache()
    return {"host": host.name, "address": host.address, **result}


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
                )
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
        background_tasks.add_task(run_ping_task, host.id, host.address, packet_count, packet_timeout)

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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    since = datetime.now() - timedelta(hours=hours)
    query = db.query(Alert).filter(Alert.created_at >= since)
    total = query.count()
    items = (
        query.order_by(Alert.created_at.desc(), Alert.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@app.get("/api/dashboard")
async def get_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
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
    current_user: User = Depends(get_current_user),
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


@app.get("/api/system-logs")
async def get_system_logs(
    log_type: Optional[str] = None,
    module: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(SystemLog)
    if log_type:
        query = query.filter(SystemLog.log_type == log_type)
    if module:
        query = query.filter(SystemLog.module == module)

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
