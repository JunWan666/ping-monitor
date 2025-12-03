from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# 数据库文件路径，支持Docker环境
# 使用绝对路径，确保数据库文件始终保存在项目根目录的data文件夹
import sys
from pathlib import Path

# 获取项目根目录（backend的父目录）
if os.getenv('DB_PATH'):
    # Docker环境使用环境变量
    DB_PATH = os.getenv('DB_PATH')
else:
    # 本地环境：使用项目根目录/data
    PROJECT_ROOT = Path(__file__).parent.parent  # backend的父目录
    DATA_DIR = PROJECT_ROOT / 'data'
    DATA_DIR.mkdir(exist_ok=True)
    DB_PATH = str(DATA_DIR / 'ping_monitor.db')

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Host(Base):
    """监控主机表"""
    __tablename__ = "hosts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)  # 主机名称
    address = Column(String)  # IP或域名
    description = Column(String, nullable=True)  # 描述
    enabled = Column(Boolean, default=True)  # 是否启用
    alert_threshold = Column(Float, default=20.0)  # 丢包率告警阈值(%)
    last_status = Column(String, nullable=True)  # 上次状态: normal, abnormal, unknown
    created_at = Column(DateTime, default=datetime.now)

class PingRecord(Base):
    """Ping记录表"""
    __tablename__ = "ping_records"
    
    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(Integer, index=True)
    packet_sent = Column(Integer)  # 发送包数
    packet_received = Column(Integer)  # 接收包数
    packet_loss = Column(Float)  # 丢包率(%)
    min_rtt = Column(Float, nullable=True)  # 最小延迟(ms)
    max_rtt = Column(Float, nullable=True)  # 最大延迟(ms)
    avg_rtt = Column(Float, nullable=True)  # 平均延迟(ms)
    created_at = Column(DateTime, default=datetime.now, index=True)

class Alert(Base):
    """告警记录表"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(Integer, index=True)
    host_name = Column(String)
    alert_type = Column(String)  # packet_loss, timeout, unreachable
    message = Column(String)
    is_sent = Column(Boolean, default=False)  # 是否已发送通知
    created_at = Column(DateTime, default=datetime.now, index=True)

class SystemConfig(Base):
    """系统配置表"""
    __tablename__ = "system_config"
    
    id = Column(Integer, primary_key=True, index=True)
    check_interval = Column(Integer, default=5)  # 检测间隔(分钟)
    packet_count = Column(Integer, default=10)  # 每次发送包数
    packet_timeout = Column(Integer, default=2)  # 超时时间(秒)
    serverchan_key = Column(String, nullable=True)  # Server酱密钥
    webhook_url = Column(String, nullable=True)  # Webhook地址
    webhook_secret = Column(String, nullable=True)  # Webhook加签密钥(钉钉)
    notification_mode = Column(String, default='status_change')  # 通知模式: status_change(状态转换时), every_time(每次异常)
    # 数据维护配置
    data_retention_days = Column(Integer, default=30)  # 原始数据保留天数
    cleanup_time = Column(String, default='03:00')  # 数据清理时间(HH:MM)
    aggregate_interval = Column(Integer, default=1)  # 聚合间隔(小时)
    dashboard_chart_points = Column(Integer, default=12)  # 仪表盘趋势图显示的检测次数
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)  # 用户名
    password_hash = Column(String)  # 密码哈希
    is_admin = Column(Boolean, default=True)  # 是否管理员
    created_at = Column(DateTime, default=datetime.now)

class PingStatistics(Base):
    """聚合统计表（按小时/天聚合）"""
    __tablename__ = "ping_statistics"
    
    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(Integer, index=True)
    stat_type = Column(String, index=True)  # 'hourly' 或 'daily'
    stat_time = Column(DateTime, index=True)  # 统计时间点
    check_count = Column(Integer)  # 检测次数
    online_count = Column(Integer)  # 在线次数
    avg_packet_loss = Column(Float)  # 平均丢包率
    avg_rtt = Column(Float, nullable=True)  # 平均延迟
    min_rtt = Column(Float, nullable=True)  # 最小延迟
    max_rtt = Column(Float, nullable=True)  # 最大延迟
    created_at = Column(DateTime, default=datetime.now)

class SystemLog(Base):
    """系统日志表"""
    __tablename__ = "system_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    log_type = Column(String, index=True)  # 'info', 'warning', 'error', 'cleanup', 'aggregate'
    module = Column(String)  # 模块名称
    message = Column(Text)  # 日志内容
    details = Column(Text, nullable=True)  # 详细信息（JSON格式）
    created_at = Column(DateTime, default=datetime.now, index=True)

def init_db():
    """初始化数据库"""
    # 只创建不存在的表，不删除现有数据
    Base.metadata.create_all(bind=engine)

def init_default_config():
    """初始化默认配置（在迁移后执行）"""
    db = SessionLocal()
    try:
        config = db.query(SystemConfig).first()
        if not config:
            config = SystemConfig()
            db.add(config)
            db.commit()
    finally:
        db.close()

def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
