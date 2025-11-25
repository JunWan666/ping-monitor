from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from database import init_db, get_db, Host, PingRecord, Alert, SystemConfig
from ping_service import PingService
from scheduler import scheduler
import uvicorn
import os

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

class SystemConfigResponse(BaseModel):
    id: int
    check_interval: int
    packet_count: int
    packet_timeout: int
    serverchan_key: Optional[str]
    webhook_url: Optional[str]
    webhook_secret: Optional[str]
    updated_at: datetime
    
    class Config:
        from_attributes = True

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    init_db()
    scheduler.start()
    print("✅ 数据库初始化完成")
    print("✅ 监控调度器已启动")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    scheduler.stop()
    print("⏹️ 监控调度器已停止")

# ==================== 主机管理API ====================

@app.get("/api/hosts", response_model=List[HostResponse])
async def get_hosts(db: Session = Depends(get_db)):
    """获取所有主机"""
    return db.query(Host).all()

@app.post("/api/hosts", response_model=HostResponse)
async def create_host(host: HostCreate, db: Session = Depends(get_db)):
    """添加主机"""
    # 检查名称是否已存在
    existing = db.query(Host).filter(Host.name == host.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="主机名称已存在")
    
    db_host = Host(**host.dict())
    db.add(db_host)
    db.commit()
    db.refresh(db_host)
    return db_host

@app.get("/api/hosts/{host_id}", response_model=HostResponse)
async def get_host(host_id: int, db: Session = Depends(get_db)):
    """获取单个主机"""
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")
    return host

@app.put("/api/hosts/{host_id}", response_model=HostResponse)
async def update_host(host_id: int, host_update: HostUpdate, db: Session = Depends(get_db)):
    """更新主机"""
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")
    
    update_data = host_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(host, key, value)
    
    db.commit()
    db.refresh(host)
    return host

@app.delete("/api/hosts/{host_id}")
async def delete_host(host_id: int, db: Session = Depends(get_db)):
    """删除主机"""
    host = db.query(Host).filter(Host.id == host_id).first()
    if not host:
        raise HTTPException(status_code=404, detail="主机不存在")
    
    # 删除相关记录和告警
    db.query(PingRecord).filter(PingRecord.host_id == host_id).delete()
    db.query(Alert).filter(Alert.host_id == host_id).delete()
    db.delete(host)
    db.commit()
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
async def ping_now(host_id: int, background: bool = False, background_tasks: BackgroundTasks = None, db: Session = Depends(get_db)):
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

@app.post("/api/ping-all")
async def ping_all(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
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
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):
    """获取Ping日志记录（分页）"""
    query = db.query(
        PingRecord.id,
        PingRecord.host_id,
        Host.name.label('host_name'),
        Host.address.label('host_address'),
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
    
    # 计算总数
    total = query.count()
    
    # 分页
    offset = (page - 1) * page_size
    items = query.order_by(PingRecord.created_at.desc()).offset(offset).limit(page_size).all()
    
    # 转换为字典列表
    logs = []
    for item in items:
        # 判断状态
        host = db.query(Host).filter(Host.id == item.host_id).first()
        status = "正常" if item.packet_loss < (host.alert_threshold if host else 20) else "异常"
        
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
            'status': status
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
    db: Session = Depends(get_db)
):
    """获取主机监控记录"""
    since = datetime.now() - timedelta(hours=hours)
    records = db.query(PingRecord).filter(
        PingRecord.host_id == host_id,
        PingRecord.created_at >= since
    ).order_by(PingRecord.created_at.desc()).all()
    return records

@app.get("/api/alerts", response_model=List[AlertResponse])
async def get_alerts(
    hours: int = 24,
    db: Session = Depends(get_db)
):
    """获取告警记录"""
    since = datetime.now() - timedelta(hours=hours)
    alerts = db.query(Alert).filter(
        Alert.created_at >= since
    ).order_by(Alert.created_at.desc()).all()
    return alerts

@app.get("/api/dashboard")
async def get_dashboard(db: Session = Depends(get_db)):
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
async def get_config(db: Session = Depends(get_db)):
    """获取系统配置"""
    config = db.query(SystemConfig).first()
    if not config:
        config = SystemConfig()
        db.add(config)
        db.commit()
        db.refresh(config)
    return config

@app.put("/api/config", response_model=SystemConfigResponse)
async def update_config(config_update: SystemConfigUpdate, db: Session = Depends(get_db)):
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
async def test_notification(notification_type: str, db: Session = Depends(get_db)):
    """测试通知功能"""
    from notification import notifier
    
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
    
    # 发送测试通知
    test_message = "Ping监控系统 - 通知测试\n\n如果您收到这条消息，说明通知功能配置正确！"
    
    try:
        if notification_type == 'serverchan':
            if not config.serverchan_key:
                raise HTTPException(status_code=400, detail="Server酱密钥未配置")
            success = notifier.send_serverchan("通知测试", test_message)
            if not success:
                raise HTTPException(status_code=500, detail="Server酱通知发送失败")
        elif notification_type == 'webhook':
            if not config.webhook_url:
                raise HTTPException(status_code=400, detail="Webhook地址未配置")
            success = notifier.send_webhook(test_message)
            if not success:
                raise HTTPException(status_code=500, detail="Webhook通知发送失败")
        else:
            raise HTTPException(status_code=400, detail="不支持的通知类型")
        
        return {"message": "测试通知已发送"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发送测试通知失败: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
