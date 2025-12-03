from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from database import init_db, get_db, Host, PingRecord, Alert, SystemConfig, User, SystemLog, PingStatistics
from ping_service import PingService
from scheduler import scheduler
from data_maintenance import DataMaintenance
from auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    get_current_user,
    get_optional_current_user
)
import uvicorn
import os
import logging
import json
import asyncio

# 配置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Ping监控系统", version="1.0.0")

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic模型
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

class AlertResponse(BaseModel):
    id: int
    host_id: int
    host_name: str
    alert_type: str
    message: str
    is_sent: bool
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

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    # 1. 创建表结构
    init_db()
    
    # 2. 执行数据库迁移(添加缺失字段)
    from database_migrations import DatabaseMigration
    DatabaseMigration.run_migrations()
    
    # 3. 初始化默认配置
    from database import init_default_config
    init_default_config()
    
    # 4. 启动调度器
    scheduler.start()
    logger.info("✅ 数据库初始化完成")
    logger.info("✅ 监控调度器已启动")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    scheduler.stop()
    logger.info("⏹️ 监控调度器已停止")

# ==================== 认证API ====================

@app.get("/api/auth/check")
async def check_admin_exists(db: Session = Depends(get_db)):
    """检查是否存在管理员"""
    user = db.query(User).first()
    return {"has_admin": user is not None}

@app.post("/api/auth/init", response_model=TokenResponse)
async def init_admin(user_data: UserCreate, db: Session = Depends(get_db)):
    """初始化管理员账户"""
    # 检查是否已经存在管理员
    existing_user = db.query(User).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="管理员已存在")
    
    # 验证用户名和密码
    if not user_data.username or len(user_data.username) < 3:
        raise HTTPException(status_code=400, detail="用户名至少需要3个字符")
    if not user_data.password or len(user_data.password) < 5:
        raise HTTPException(status_code=400, detail="密码至少需要5个字符")
    
    # 创建管理员
    hashed_password = get_password_hash(user_data.password)
    admin_user = User(
        username=user_data.username,
        password_hash=hashed_password,
        is_admin=True
    )
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    # 记录系统日志
    DataMaintenance.log_system_event(
        db,
        log_type='info',
        module='authentication',
        message=f'初始化管理员账户: {admin_user.username}',
        details={'user_id': admin_user.id, 'username': admin_user.username}
    )
    
    # 生成token
    access_token = create_access_token(data={"sub": admin_user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """用户登录"""
    user = db.query(User).filter(User.username == user_data.username).first()
    if not user or not verify_password(user_data.password, user.password_hash):
        # 记录登录失败
        DataMaintenance.log_system_event(
            db,
            log_type='warning',
            module='authentication',
            message=f'登录失败: 用户名 {user_data.username}',
            details={'username': user_data.username, 'reason': 'invalid_credentials'}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 记录登录成功
    DataMaintenance.log_system_event(
        db,
        log_type='info',
        module='authentication',
        message=f'用户 {user.username} 登录成功',
        details={'user_id': user.id, 'username': user.username}
    )
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "is_admin": current_user.is_admin
    }

@app.put("/api/auth/update-password")
async def update_password(user_data: UserPasswordUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """修改用户名和密码"""
    # 验证旧密码
    if not verify_password(user_data.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误"
        )
    
    changes = []
    
    # 更新用户名
    if user_data.new_username:
        if len(user_data.new_username) < 3:
            raise HTTPException(status_code=400, detail="用户名至少需要3个字符")
        # 检查用户名是否已存在（排除当前用户）
        existing_user = db.query(User).filter(User.username == user_data.new_username, User.id != current_user.id).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="用户名已存在")
        old_username = current_user.username
        current_user.username = user_data.new_username
        changes.append(f'用户名: {old_username} -> {user_data.new_username}')
    
    # 更新密码
    if user_data.new_password:
        if len(user_data.new_password) < 5:
            raise HTTPException(status_code=400, detail="密码至少需要5个字符")
        current_user.password_hash = get_password_hash(user_data.new_password)
        changes.append('密码已修改')
    
    db.commit()
    
    # 记录系统日志
    DataMaintenance.log_system_event(
        db,
        log_type='info',
        module='authentication',
        message=f'用户 {current_user.username} 修改了账户信息',
        details={'user_id': current_user.id, 'changes': changes}
    )
    
    return {"message": "修改成功"}

# ==================== 主机管理API ====================

@app.get("/api/hosts", response_model=List[HostResponse])
async def get_hosts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取所有主机"""
    return db.query(Host).all()

@app.post("/api/hosts", response_model=HostResponse)
async def create_host(host: HostCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """添加主机"""
    # 检查名称是否已存在
    existing = db.query(Host).filter(Host.name == host.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="主机名称已存在")
    
    db_host = Host(**host.dict())
    db.add(db_host)
    db.commit()
    db.refresh(db_host)
    
    # 记录系统日志
    DataMaintenance.log_system_event(
        db,
        log_type='info',
        module='host_management',
        message=f'用户 {current_user.username} 添加了主机: {db_host.name} ({db_host.address})',
        details={'host_id': db_host.id, 'host_name': db_host.name, 'address': db_host.address}
    )
    
    return db_host

@app.get("/api/hosts/{host_id}", response_model=HostResponse)
async def get_host(host_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取单个主机"""
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")
    return host

@app.put("/api/hosts/{host_id}", response_model=HostResponse)
async def update_host(host_id: int, host_update: HostUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """更新主机"""
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")
    
    update_data = host_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(host, key, value)
    
    db.commit()
    db.refresh(host)
    
    # 记录系统日志
    DataMaintenance.log_system_event(
        db,
        log_type='info',
        module='host_management',
        message=f'用户 {current_user.username} 更新了主机: {host.name}',
        details={'host_id': host.id, 'updated_fields': list(update_data.keys())}
    )
    
    return host

@app.delete("/api/hosts/{host_id}")
async def delete_host(host_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """删除主机"""
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")
    
    host_name = host.name
    host_address = host.address
    
    # 删除相关记录和告警
    db.query(PingRecord).filter(PingRecord.host_id == host_id).delete()
    db.query(Alert).filter(Alert.host_id == host_id).delete()
    db.delete(host)
    db.commit()
    
    # 记录系统日志
    DataMaintenance.log_system_event(
        db,
        log_type='warning',
        module='host_management',
        message=f'用户 {current_user.username} 删除了主机: {host_name} ({host_address})',
        details={'host_id': host_id, 'host_name': host_name, 'address': host_address}
    )
    
    return {"message": "删除成功"}

# ==================== Ping操作API ====================

def _do_ping(host_id: int, host_address: str, host_name: str):
    """后台执行ping操作"""
    from database import SessionLocal
    db = SessionLocal()
    try:
        result = PingService.ping_host(host_address, count=10)
        
        # 保存记录
        record = PingRecord(
            host_id=host_id,
            packet_sent=result['packet_sent'],
            packet_received=result['packet_received'],
            packet_loss=result['packet_loss'],
            min_rtt=result['min_rtt'],
            max_rtt=result['max_rtt'],
            avg_rtt=result['avg_rtt'],
        )
        db.add(record)
        db.commit()
    finally:
        db.close()

@app.post("/api/ping/{host_id}")
async def ping_now(host_id: int, background: bool = False, background_tasks: BackgroundTasks = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """立即执行ping（支持同步和异步模式）"""
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")
    
    # 如果是后台模式，异步执行
    if background and background_tasks:
        background_tasks.add_task(_do_ping, host.id, host.address, host.name)
        return {
            "message": "Ping任务已启动",
            "host": host.name,
            "address": host.address
        }
    
    # 同步执行并返回结果
    result = PingService.ping_host(host.address, count=10)
    
    # 保存记录
    record = PingRecord(
        host_id=host.id,
        packet_sent=result['packet_sent'],
        packet_received=result['packet_received'],
        packet_loss=result['packet_loss'],
        min_rtt=result['min_rtt'],
        max_rtt=result['max_rtt'],
        avg_rtt=result['avg_rtt'],
    )
    db.add(record)
    db.commit()
    
    return {
        "host": host.name,
        "address": host.address,
        **result
    }

@app.get("/api/ping-stream/{host_id}")
async def ping_stream(host_id: int, token: str = None, db: Session = Depends(get_db)):
    """实时流式Ping（SSE）"""
    # 验证token
    from jose import JWTError, jwt
    from auth import SECRET_KEY, ALGORITHM
    
    if not token:
        raise HTTPException(status_code=401, detail="未提供Token")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="无效的Token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token验证失败")
    
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")
    
    async def event_generator():
        """SSE事件生成器"""
        try:
            # 使用生成器模式获取ping结果
            for event in PingService.ping_host_stream(host.address, count=10):
                # 转换为SSE格式
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                # 给客户端一点时间处理
                await asyncio.sleep(0.1)
            
            # Ping完成后保存记录
            result = PingService.ping_host(host.address, count=10)
            record = PingRecord(
                host_id=host.id,
                packet_sent=result['packet_sent'],
                packet_received=result['packet_received'],
                packet_loss=result['packet_loss'],
                min_rtt=result['min_rtt'],
                max_rtt=result['max_rtt'],
                avg_rtt=result['avg_rtt'],
            )
            db.add(record)
            db.commit()
            
        except Exception as e:
            logger.error(f"Stream ping error: {e}")
            yield f"data: {{\"type\": \"error\", \"message\": \"Ping失败: {str(e)}\"}}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post("/api/ping-all")
async def ping_all(background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """立即ping所有启用的主机（后台异步执行）"""
    hosts = db.query(Host).filter(Host.enabled == True).all()
    if not hosts:
        raise HTTPException(status_code=404, detail="没有启用的主机")
    
    # 为每个主机添加后台任务
    for host in hosts:
        background_tasks.add_task(_do_ping, host.id, host.address, host.name)
    
    return {
        "message": f"已启动 {len(hosts)} 个主机的Ping任务",
        "count": len(hosts),
        "hosts": [host.name for host in hosts]
    }

@app.get("/api/ping/logs")
async def get_ping_logs(
    host_id: Optional[int] = None,
    search: Optional[str] = None,  # 主机名称或地址模糊搜索
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取Ping日志记录（分页、支持状态筛选、支持模糊搜索）"""
    query = db.query(
        PingRecord.id,
        PingRecord.host_id,
        Host.name.label('host_name'),
        Host.address.label('host_address'),
        Host.alert_threshold,
        PingRecord.packet_sent,
        PingRecord.packet_received,
        PingRecord.packet_loss,
        PingRecord.min_rtt,
        PingRecord.max_rtt,
        PingRecord.avg_rtt,
        PingRecord.created_at.label('check_time')
    ).join(Host, PingRecord.host_id == Host.id)
    
    # 如果指定了主机ID，过滤
    if host_id:
        query = query.filter(PingRecord.host_id == host_id)
    
    # 模糊搜索主机名称或地址
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (Host.name.like(search_pattern)) | (Host.address.like(search_pattern))
        )
    
    # 获取所有符合条件的记录（用于状态筛选）
    all_items = query.order_by(PingRecord.created_at.desc()).all()
    
    # 根据状态筛选
    filtered_items = []
    for item in all_items:
        # 判断状态
        is_normal = item.packet_loss < item.alert_threshold
        
        if status == 'normal' and not is_normal:
            continue
        if status == 'abnormal' and is_normal:
            continue
        
        filtered_items.append(item)
    
    # 计算总数
    total = len(filtered_items)
    
    # 分页
    offset = (page - 1) * page_size
    paginated_items = filtered_items[offset:offset + page_size]
    
    # 转换为字典列表
    logs = []
    for item in paginated_items:
        status_text = "正常" if item.packet_loss < item.alert_threshold else "异常"
        
        logs.append({
            'id': item.id,
            'host_id': item.host_id,
            'host_name': item.host_name,
            'host_address': item.host_address,
            'packet_sent': item.packet_sent,
            'packet_received': item.packet_received,
            'packet_loss': item.packet_loss,
            'min_rtt': item.min_rtt,
            'max_rtt': item.max_rtt,
            'avg_rtt': item.avg_rtt,
            'check_time': item.check_time,
            'status': status_text
        })
    
    return {
        'items': logs,
        'total': total,
        'page': page,
        'page_size': page_size
    }

# ==================== 监控数据API ====================

@app.get("/api/records/{host_id}", response_model=List[PingRecordResponse])
async def get_records(
    host_id: int,
    hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取主机监控记录"""
    since = datetime.now() - timedelta(hours=hours)
    records = db.query(PingRecord).filter(
        PingRecord.host_id == host_id,
        PingRecord.created_at >= since
    ).order_by(PingRecord.created_at.desc()).all()
    return records

@app.get("/api/alerts")
async def get_alerts(
    hours: int = 24,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取告警记录（分页）"""
    since = datetime.now() - timedelta(hours=hours)
    query = db.query(Alert).filter(
        Alert.created_at >= since
    )
    
    # 计算总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * page_size
    alerts = query.order_by(Alert.created_at.desc()).offset(offset).limit(page_size).all()
    
    return {
        'items': alerts,
        'total': total,
        'page': page,
        'page_size': page_size
    }

@app.get("/api/dashboard")
async def get_dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取仪表盘数据"""
    total_hosts = db.query(Host).count()
    enabled_hosts = db.query(Host).filter(Host.enabled == True).count()
    
    # 最近1小时的告警数
    one_hour_ago = datetime.now() - timedelta(hours=1)
    recent_alerts = db.query(Alert).filter(Alert.created_at >= one_hour_ago).count()
    
    # 获取每个主机的最新状态
    hosts = db.query(Host).all()
    host_status = []
    
    for host in hosts:
        latest_record = db.query(PingRecord).filter(
            PingRecord.host_id == host.id
        ).order_by(PingRecord.created_at.desc()).first()
        
        if latest_record:
            status = "正常" if latest_record.packet_loss < host.alert_threshold else "异常"
        else:
            status = "未知"
        
        host_status.append({
            "id": host.id,
            "name": host.name,
            "address": host.address,
            "enabled": host.enabled,
            "status": status,
            "packet_loss": latest_record.packet_loss if latest_record else None,
            "avg_rtt": latest_record.avg_rtt if latest_record else None,
            "last_check": latest_record.created_at if latest_record else None
        })
    
    return {
        "total_hosts": total_hosts,
        "enabled_hosts": enabled_hosts,
        "recent_alerts": recent_alerts,
        "host_status": host_status
    }

# ==================== 数据看板API ====================

def _get_hours_from_range(time_range: str) -> int:
    """将时间范围字符串转换为小时数"""
    range_map = {
        '1h': 1,
        '1d': 24,
        '3d': 72,
        '7d': 168,
        '15d': 360,
        '30d': 720
    }
    return range_map.get(time_range, 24)

def _format_time_for_range(dt: datetime, time_range: str) -> str:
    """根据时间范围格式化时间显示"""
    if time_range == '1h':
        return dt.strftime('%H:%M')
    elif time_range in ['1d', '3d']:
        return dt.strftime('%m/%d %H:%M')
    else:
        return dt.strftime('%m/%d')

@app.get("/api/databoard/stats/{time_range}")
async def get_databoard_stats(
    time_range: str,
    sort_by: str = 'avg_packet_loss',  # 排序字段：avg_packet_loss, online_rate, avg_rtt
    sort_order: str = 'desc',  # 排序方向：asc, desc
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取数据看板统计数据（优化版：使用聚合数据）"""
    hours = _get_hours_from_range(time_range)
    since = datetime.now() - timedelta(hours=hours)
    
    # 获取所有启用的主机
    hosts = db.query(Host).filter(Host.enabled == True).all()
    total_hosts = len(hosts)
    
    if total_hosts == 0:
        return {
            "total_hosts": 0,
            "avg_online_rate": 0,
            "avg_rtt": 0,
            "avg_packet_loss": 0,
            "host_stats": [],
            "trend_data": []
        }
    
    # 决定是否使用聚合数据（1天以上使用聚合数据）
    # 优化: 1d/3d也使用hourly聚合数据,提升性能
    use_aggregated = time_range in ['1d', '3d', '7d', '15d', '30d']
    stat_type = 'daily' if time_range in ['15d', '30d'] else 'hourly'
    
    # 计算每个主机的统计数据
    host_stats = []
    total_online_rate = 0
    total_avg_rtt = 0
    total_avg_packet_loss = 0
    
    for host in hosts:
        if use_aggregated:
            # 使用聚合数据
            stats = db.query(PingStatistics).filter(
                PingStatistics.host_id == host.id,
                PingStatistics.stat_type == stat_type,
                PingStatistics.stat_time >= since
            ).all()
            
            if not stats:
                continue
            
            # 从聚合数据计算统计指标
            check_count = sum(s.check_count for s in stats)
            online_count = sum(s.online_count for s in stats)
            online_rate = round((online_count / check_count) * 100, 2) if check_count > 0 else 0
            
            avg_packet_loss = round(sum(s.avg_packet_loss * s.check_count for s in stats) / check_count, 2)
            
            rtts = [(s.avg_rtt, s.check_count) for s in stats if s.avg_rtt is not None]
            if rtts:
                avg_rtt = round(sum(rtt * count for rtt, count in rtts) / sum(count for _, count in rtts), 2)
                min_rtt = round(min(s.min_rtt for s in stats if s.min_rtt is not None), 2)
                max_rtt = round(max(s.max_rtt for s in stats if s.max_rtt is not None), 2)
            else:
                avg_rtt = 0
                min_rtt = 0
                max_rtt = 0
        else:
            # 使用原始数据
            records = db.query(PingRecord).filter(
                PingRecord.host_id == host.id,
                PingRecord.created_at >= since
            ).all()
            
            if not records:
                continue
            
            # 计算统计指标
            check_count = len(records)
            online_count = sum(1 for r in records if r.packet_loss < host.alert_threshold)
            online_rate = round((online_count / check_count) * 100, 2) if check_count > 0 else 0
            
            avg_packet_loss = round(sum(r.packet_loss for r in records) / check_count, 2)
            avg_rtt = round(sum(r.avg_rtt or 0 for r in records) / check_count, 2)
            min_rtt = round(min(r.min_rtt or 999999 for r in records), 2)
            max_rtt = round(max(r.max_rtt or 0 for r in records), 2)
        
        total_online_rate += online_rate
        total_avg_rtt += avg_rtt
        total_avg_packet_loss += avg_packet_loss
        
        host_stats.append({
            "id": host.id,
            "name": host.name,
            "address": host.address,
            "check_count": check_count,
            "online_rate": online_rate,
            "avg_packet_loss": avg_packet_loss,
            "avg_rtt": avg_rtt,
            "min_rtt": min_rtt,
            "max_rtt": max_rtt
        })
    
    # 排序主机数据
    reverse = (sort_order == 'desc')
    if sort_by == 'avg_packet_loss':
        host_stats.sort(key=lambda x: x['avg_packet_loss'], reverse=reverse)
    elif sort_by == 'online_rate':
        host_stats.sort(key=lambda x: x['online_rate'], reverse=reverse)
    elif sort_by == 'avg_rtt':
        host_stats.sort(key=lambda x: x['avg_rtt'], reverse=reverse)
    
    # 计算整体平均值
    host_count = len(host_stats)
    avg_online_rate = round(total_online_rate / host_count, 2) if host_count > 0 else 0
    avg_rtt = round(total_avg_rtt / host_count, 2) if host_count > 0 else 0
    avg_packet_loss = round(total_avg_packet_loss / host_count, 2) if host_count > 0 else 0
    
    # 生成趋势数据
    trend_data = _get_trend_data(db, hosts, since, time_range, use_aggregated, stat_type)
    
    return {
        "total_hosts": total_hosts,
        "avg_online_rate": avg_online_rate,
        "avg_rtt": avg_rtt,
        "avg_packet_loss": avg_packet_loss,
        "host_stats": host_stats,
        "trend_data": trend_data
    }

def _get_trend_data(db: Session, hosts: list, since: datetime, time_range: str, use_aggregated: bool, stat_type: str):
    """生成趋势数据"""
    if use_aggregated:
        # 使用聚合数据
        host_ids = [h.id for h in hosts]
        stats = db.query(PingStatistics).filter(
            PingStatistics.host_id.in_(host_ids),
            PingStatistics.stat_type == stat_type,
            PingStatistics.stat_time >= since
        ).order_by(PingStatistics.stat_time).all()
        
        # 按时间分组
        time_groups = {}
        for stat in stats:
            time_key = stat.stat_time
            if time_key not in time_groups:
                time_groups[time_key] = []
            time_groups[time_key].append(stat)
        
        # 生成趋势数据
        trend_data = []
        for time_key in sorted(time_groups.keys()):
            group_stats = time_groups[time_key]
            
            total_check = sum(s.check_count for s in group_stats)
            total_online = sum(s.online_count for s in group_stats)
            online_rate = round((total_online / total_check) * 100, 2) if total_check > 0 else 0
            
            avg_packet_loss = round(sum(s.avg_packet_loss * s.check_count for s in group_stats) / total_check, 2)
            
            rtts = [(s.avg_rtt, s.check_count) for s in group_stats if s.avg_rtt is not None]
            if rtts:
                avg_rtt = round(sum(rtt * count for rtt, count in rtts) / sum(count for _, count in rtts), 2)
            else:
                avg_rtt = 0
            
            time_str = _format_time_for_range(time_key, time_range)
            trend_data.append({
                "time": time_str,
                "avg_packet_loss": avg_packet_loss,
                "avg_rtt": avg_rtt,
                "online_rate": online_rate
            })
    else:
        # 使用原始数据（仅1小时数据）
        # 构建主机ID到主机对象的字典,避免循环中重复查询
        host_dict = {h.id: h for h in hosts}
        
        all_records = db.query(PingRecord).join(
            Host, PingRecord.host_id == Host.id
        ).filter(
            Host.enabled == True,
            PingRecord.created_at >= since
        ).order_by(PingRecord.created_at).all()
        
        # 根据时间范围确定分组间隔
        if time_range == '1h':
            interval_minutes = 5
        elif time_range == '1d':
            interval_minutes = 60
        elif time_range == '3d':
            interval_minutes = 180
        else:
            interval_minutes = 360
        
        # 按时间分组统计
        time_groups = {}
        for record in all_records:
            timestamp = record.created_at.timestamp()
            group_key = int(timestamp // (interval_minutes * 60)) * (interval_minutes * 60)
            
            if group_key not in time_groups:
                time_groups[group_key] = []
            time_groups[group_key].append(record)
        
        # 生成趋势数据
        trend_data = []
        for timestamp in sorted(time_groups.keys()):
            records = time_groups[timestamp]
            
            if not records:
                continue
            
            dt = datetime.fromtimestamp(timestamp)
            time_str = _format_time_for_range(dt, time_range)
            
            avg_packet_loss = round(sum(r.packet_loss for r in records) / len(records), 2)
            avg_rtt = round(sum(r.avg_rtt or 0 for r in records) / len(records), 2)
            
            # 计算在线率 - 使用预加载的主机信息字典,避免N+1查询
            online_count = 0
            for r in records:
                host = host_dict.get(r.host_id)
                if host and r.packet_loss < host.alert_threshold:
                    online_count += 1
            
            online_rate = round((online_count / len(records)) * 100, 2) if len(records) > 0 else 0
            
            trend_data.append({
                "time": time_str,
                "avg_packet_loss": avg_packet_loss,
                "avg_rtt": avg_rtt,
                "online_rate": online_rate
            })
    
    return trend_data

@app.get("/api/databoard/host/{host_id}/{time_range}")
async def get_host_detail_stats(
    host_id: int,
    time_range: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取单个主机的详细统计数据（优化版：使用聚合数据）"""
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")
    
    hours = _get_hours_from_range(time_range)
    since = datetime.now() - timedelta(hours=hours)
    
    # 决定是否使用聚合数据
    use_aggregated = time_range in ['1d', '3d', '7d', '15d', '30d']
    stat_type = 'daily' if time_range in ['15d', '30d'] else 'hourly'
    
    result = []
    
    if use_aggregated:
        # 使用聚合数据
        stats = db.query(PingStatistics).filter(
            PingStatistics.host_id == host_id,
            PingStatistics.stat_type == stat_type,
            PingStatistics.stat_time >= since
        ).order_by(PingStatistics.stat_time).all()
        
        if not stats:
            return []
        
        # 格式化输出
        for stat in stats:
            time_str = _format_time_for_range(stat.stat_time, time_range)
            result.append({
                "time": time_str,
                "packet_loss": stat.avg_packet_loss,
                "avg_rtt": stat.avg_rtt or 0,
                "min_rtt": stat.min_rtt or 0,
                "max_rtt": stat.max_rtt or 0
            })
    else:
        # 使用原始数据（仅1h）
        records = db.query(PingRecord).filter(
            PingRecord.host_id == host_id,
            PingRecord.created_at >= since
        ).order_by(PingRecord.created_at).all()
        
        if not records:
            return []
        
        # 1小时数据显示所有点
        for record in records:
            time_str = _format_time_for_range(record.created_at, time_range)
            result.append({
                "time": time_str,
                "packet_loss": record.packet_loss,
                "avg_rtt": record.avg_rtt or 0,
                "min_rtt": record.min_rtt or 0,
                "max_rtt": record.max_rtt or 0
            })
    
    return result

# 静态文件服务（生产环境）
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "../frontend/dist")
if os.path.exists(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")
    
    @app.get("/")
    async def serve_frontend():
        """服务前端页面"""
        index_file = os.path.join(FRONTEND_DIST, "index.html")
        return FileResponse(index_file)
else:
    @app.get("/")
    async def root():
        """根路径"""
        return {"message": "Ping监控系统API", "version": "1.0.0"}

# ==================== 系统配置API ====================

@app.get("/api/config", response_model=SystemConfigResponse)
async def get_config(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取系统配置"""
    config = db.query(SystemConfig).first()
    if not config:
        config = SystemConfig()
        db.add(config)
        db.commit()
        db.refresh(config)
    return config

@app.put("/api/config", response_model=SystemConfigResponse)
async def update_config(config_update: SystemConfigUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """更新系统配置"""
    config = db.query(SystemConfig).first()
    if not config:
        config = SystemConfig()
        db.add(config)
    
    update_data = config_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(config, key, value)
    
    db.commit()
    db.refresh(config)
    
    # 记录系统日志
    DataMaintenance.log_system_event(
        db,
        log_type='info',
        module='system_config',
        message=f'用户 {current_user.username} 修改了系统配置',
        details={'updated_fields': list(update_data.keys()), 'config': update_data}
    )
    
    # 重启调度器以应用新配置
    if 'check_interval' in update_data:
        scheduler.update_interval(config.check_interval)
    
    # 更新通知配置
    from notification import notifier
    notifier.configure(
        serverchan_key=config.serverchan_key, 
        webhook_url=config.webhook_url,
        webhook_secret=config.webhook_secret
    )
    
    return config

@app.post("/api/test-notification/{notification_type}")
async def test_notification(notification_type: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """测试通知功能"""
    from notification import notifier
    from notification_template import NotificationTemplate
    
    # 获取配置
    config = db.query(SystemConfig).first()
    if not config:
        raise HTTPException(status_code=404, detail="系统配置不存在")
    
    # 配置通知器
    notifier.configure(
        serverchan_key=config.serverchan_key, 
        webhook_url=config.webhook_url,
        webhook_secret=config.webhook_secret
    )
    
    # 使用模板生成测试通知
    use_markdown = notification_type == 'webhook'  # webhook(钉钉)使用markdown
    msg_data = NotificationTemplate.get_test_notification(use_markdown=use_markdown)
    test_message = msg_data['content']
    test_title = msg_data['title']
    
    try:
        if notification_type == 'serverchan':
            if not config.serverchan_key:
                raise HTTPException(status_code=400, detail="Server酱密钥未配置")
            success = notifier.send_serverchan(test_title, test_message)
            if not success:
                raise HTTPException(status_code=500, detail="Server酱通知发送失败")
        elif notification_type == 'webhook':
            if not config.webhook_url:
                raise HTTPException(status_code=400, detail="Webhook地址未配置")
            success = notifier.send_webhook(test_message, title=test_title)
            if not success:
                raise HTTPException(status_code=500, detail="Webhook通知发送失败")
        else:
            raise HTTPException(status_code=400, detail="不支持的通知类型")
        
        return {"message": "测试通知已发送"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发送测试通知失败: {str(e)}")

# ==================== 系统日志API ====================

@app.get("/api/system-logs")
async def get_system_logs(
    log_type: Optional[str] = None,
    module: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取系统日志（分页、支持筛选）"""
    query = db.query(SystemLog)
    
    # 类型筛选
    if log_type:
        query = query.filter(SystemLog.log_type == log_type)
    
    # 模块筛选
    if module:
        query = query.filter(SystemLog.module == module)
    
    # 计算总数
    total = query.count()
    
    # 分页(按ID降序,最新的在前面)
    offset = (page - 1) * page_size
    logs = query.order_by(SystemLog.id.desc()).offset(offset).limit(page_size).all()
    
    # 转换为字典列表
    items = []
    for log in logs:
        items.append({
            'id': log.id,
            'log_type': log.log_type,
            'module': log.module,
            'message': log.message,
            'details': log.details,
            'created_at': log.created_at
        })
    
    return {
        'items': items,
        'total': total,
        'page': page,
        'page_size': page_size
    }

@app.post("/api/system-logs/cleanup")
async def cleanup_system_logs(
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """清理旧系统日志"""
    cutoff_date = datetime.now() - timedelta(days=days)
    count = db.query(SystemLog).filter(SystemLog.created_at < cutoff_date).count()
    
    if count > 0:
        db.query(SystemLog).filter(SystemLog.created_at < cutoff_date).delete()
        db.commit()
    
    return {
        'message': f'清理了 {count} 条系统日志',
        'deleted_count': count
    }

@app.post("/api/data-maintenance/aggregate-hourly")
async def trigger_hourly_aggregation(
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """手动触发小时级数据聚合"""
    if background_tasks:
        background_tasks.add_task(_do_hourly_aggregation)
        return {'message': '小时级数据聚合任务已启动'}
    else:
        _do_hourly_aggregation()
        return {'message': '小时级数据聚合完成'}

@app.post("/api/data-maintenance/aggregate-daily")
async def trigger_daily_aggregation(
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None
):
    """手动触发日级数据聚合"""
    if background_tasks:
        background_tasks.add_task(_do_daily_aggregation)
        return {'message': '日级数据聚合任务已启动'}
    else:
        _do_daily_aggregation()
        return {'message': '日级数据聚合完成'}

@app.post("/api/data-maintenance/cleanup")
async def trigger_data_cleanup(
    days: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """手动触发数据清理"""
    if days is None:
        # 从配置读取
        config = db.query(SystemConfig).first()
        days = config.data_retention_days if config else 30
    
    if background_tasks:
        background_tasks.add_task(_do_data_cleanup, days)
        return {'message': f'数据清理任务已启动（保留{days}天）'}
    else:
        _do_data_cleanup(days)
        return {'message': f'数据清理完成（保留{days}天）'}

def _do_hourly_aggregation():
    """执行小时级聚合"""
    from data_maintenance import DataMaintenance
    DataMaintenance.aggregate_hourly_stats()

def _do_daily_aggregation():
    """执行日级聚合"""
    from data_maintenance import DataMaintenance
    DataMaintenance.aggregate_daily_stats()

def _do_data_cleanup(days: int):
    """执行数据清理"""
    from data_maintenance import DataMaintenance
    DataMaintenance.cleanup_old_records(days=days)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
