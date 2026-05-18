from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    inspect,
)
from sqlalchemy.orm import declarative_base, sessionmaker

from app_settings import settings


def _create_engine():
    if settings.database_backend == "sqlite":
        return create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
        )

    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=20,
        max_overflow=30,
    )


engine = _create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
Base = declarative_base()


class Host(Base):
    __tablename__ = "hosts"
    __table_args__ = (
        Index("ix_hosts_enabled_created_at", "enabled", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    address = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    alert_threshold = Column(Float, default=20.0, nullable=False)
    last_status = Column(String(50), nullable=True)
    last_packet_loss = Column(Float, nullable=True)
    last_avg_rtt = Column(Float, nullable=True)
    last_check = Column(DateTime, nullable=True)
    resolved_ip = Column(String(50), nullable=True)
    country = Column(String(100), nullable=True)
    province = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    isp = Column(String(200), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_status = Column(String(20), default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class PingRecord(Base):
    __tablename__ = "ping_records"
    __table_args__ = (
        Index("ix_ping_records_host_created_at", "host_id", "created_at"),
        Index("ix_ping_records_created_host", "created_at", "host_id"),
        Index("ix_ping_records_host_id_id", "host_id", "id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(Integer, index=True, nullable=False)
    packet_sent = Column(Integer, nullable=False)
    packet_received = Column(Integer, nullable=False)
    packet_loss = Column(Float, nullable=False)
    min_rtt = Column(Float, nullable=True)
    max_rtt = Column(Float, nullable=True)
    avg_rtt = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.now, index=True, nullable=False)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_host_created_at", "host_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(Integer, index=True, nullable=False)
    host_name = Column(String(255), nullable=False)
    alert_type = Column(String(50), nullable=False)
    message = Column(String(2000), nullable=False)
    is_sent = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.now, index=True, nullable=False)


class SystemConfig(Base):
    __tablename__ = "system_config"

    id = Column(Integer, primary_key=True, index=True)
    check_interval = Column(Integer, default=5, nullable=False)
    packet_count = Column(Integer, default=10, nullable=False)
    packet_timeout = Column(Integer, default=2, nullable=False)
    serverchan_key = Column(String(255), nullable=True)
    webhook_url = Column(String(1000), nullable=True)
    webhook_secret = Column(String(255), nullable=True)
    notification_mode = Column(String(50), default="status_change", nullable=False)
    data_retention_days = Column(Integer, default=30, nullable=False)
    cleanup_time = Column(String(10), default="03:00", nullable=False)
    aggregate_interval = Column(Integer, default=1, nullable=False)
    dashboard_chart_points = Column(Integer, default=12, nullable=False)
    auto_refresh_location = Column(Boolean, default=False, nullable=False)
    report_webhook_url = Column(String(1000), nullable=True)
    report_webhook_secret = Column(String(255), nullable=True)
    daily_report_enabled = Column(Boolean, default=False, nullable=False)
    daily_report_time = Column(String(10), default="09:00", nullable=False)
    weekly_report_enabled = Column(Boolean, default=False, nullable=False)
    weekly_report_time = Column(String(10), default="09:00", nullable=False)
    monthly_report_enabled = Column(Boolean, default=False, nullable=False)
    monthly_report_time = Column(String(10), default="09:00", nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class PingStatistics(Base):
    __tablename__ = "ping_statistics"
    __table_args__ = (
        UniqueConstraint("host_id", "stat_type", "stat_time", name="uq_ping_statistics_host_type_time"),
        Index("ix_ping_statistics_type_time", "stat_type", "stat_time"),
        Index("ix_ping_statistics_host_type_time", "host_id", "stat_type", "stat_time"),
    )

    id = Column(Integer, primary_key=True, index=True)
    host_id = Column(Integer, index=True, nullable=False)
    stat_type = Column(String(20), index=True, nullable=False)
    stat_time = Column(DateTime, index=True, nullable=False)
    check_count = Column(Integer, nullable=False)
    online_count = Column(Integer, nullable=False)
    avg_packet_loss = Column(Float, nullable=False)
    avg_rtt = Column(Float, nullable=True)
    min_rtt = Column(Float, nullable=True)
    max_rtt = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)


class SystemLog(Base):
    __tablename__ = "system_logs"
    __table_args__ = (
        Index("ix_system_logs_type_created_at", "log_type", "created_at"),
        Index("ix_system_logs_module_created_at", "module", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    log_type = Column(String(50), index=True, nullable=False)
    module = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now, index=True, nullable=False)


class DataScreenConfig(Base):
    __tablename__ = "datascreen_config"

    id = Column(Integer, primary_key=True, index=True)
    refresh_interval = Column(Integer, default=5, nullable=False)
    enable_3d = Column(Boolean, default=True, nullable=False)
    enable_animation = Column(Boolean, default=True, nullable=False)
    map_view_angle = Column(Integer, default=45, nullable=False)
    particle_count = Column(Integer, default=100, nullable=False)
    show_flow_lines = Column(Boolean, default=True, nullable=False)
    theme_color = Column(String(20), default="blue", nullable=False)
    public_enabled = Column(Boolean, default=True, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_indexes()


def ensure_indexes() -> None:
    inspector = inspect(engine)
    existing_indexes = {
        table_name: {item["name"] for item in inspector.get_indexes(table_name)}
        for table_name in inspector.get_table_names()
    }
    for table in Base.metadata.tables.values():
        known = existing_indexes.get(table.name, set())
        for index in table.indexes:
            if index.name not in known:
                index.create(bind=engine, checkfirst=True)


def init_default_config() -> None:
    db = SessionLocal()
    try:
        config = db.query(SystemConfig).first()
        if not config:
            config = SystemConfig()
            db.add(config)
            db.commit()

        screen_config = db.query(DataScreenConfig).first()
        if not screen_config:
            screen_config = DataScreenConfig()
            db.add(screen_config)
            db.commit()
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_database_backend() -> str:
    return settings.database_backend


def get_database_url() -> str:
    return settings.database_url
