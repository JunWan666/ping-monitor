from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# 数据库文件路径，支持Docker环境
DB_PATH = os.getenv('DB_PATH', './data/ping_monitor.db')
os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else '.', exist_ok=True)

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
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)  # 用户名
    password_hash = Column(String)  # 密码哈希
    is_admin = Column(Boolean, default=True)  # 是否管理员
    created_at = Column(DateTime, default=datetime.now)

def init_db():
    """初始化数据库"""
    Base.metadata.create_all(bind=engine)
    
    # 初始化系统配置
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
