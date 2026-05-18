from __future__ import annotations

import os
from pathlib import Path
from typing import List


def _get_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class AppSettings:
    def __init__(self) -> None:
        self.project_root = Path(__file__).resolve().parent.parent
        self.data_dir = self.project_root / "data"
        self.data_dir.mkdir(exist_ok=True)

        self.database_url = self._resolve_database_url()
        self.database_backend = self._detect_backend(self.database_url)

        self.redis_url = os.getenv("REDIS_URL", "").strip() or None
        self.enable_cache = _get_bool("ENABLE_CACHE", True)
        self.disable_notifications = _get_bool("DISABLE_NOTIFICATIONS", False)
        self.disable_scheduler = _get_bool("DISABLE_SCHEDULER", False)

        self.cache_ttl_dashboard = _get_int("CACHE_TTL_DASHBOARD", 15)
        self.cache_ttl_databoard = _get_int("CACHE_TTL_DATABOARD", 45)
        self.cache_ttl_host_detail = _get_int("CACHE_TTL_HOST_DETAIL", 30)

        self.jwt_secret_key = os.getenv(
            "JWT_SECRET_KEY",
            "ping-monitor-secret-key-change-in-production",
        )
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expire_minutes = _get_int("JWT_EXPIRE_MINUTES", 60 * 24 * 7)

        cors_origins = os.getenv("CORS_ORIGINS", "*").strip()
        if cors_origins == "*":
            self.cors_origins: List[str] = ["*"]
        else:
            self.cors_origins = [item.strip() for item in cors_origins.split(",") if item.strip()]

        self.frontend_dist = self.project_root / "frontend" / "dist"

    def _resolve_database_url(self) -> str:
        database_url = os.getenv("DATABASE_URL", "").strip()
        if database_url:
            return database_url

        db_path = os.getenv("DB_PATH", "").strip()
        if db_path:
            return self._sqlite_url_from_path(Path(db_path))

        return self._sqlite_url_from_path(self.data_dir / "ping_monitor.db")

    @staticmethod
    def _detect_backend(database_url: str) -> str:
        if database_url.startswith("sqlite"):
            return "sqlite"
        if database_url.startswith("mysql"):
            return "mysql"
        return "unknown"

    @staticmethod
    def _sqlite_url_from_path(path: Path) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path.resolve().as_posix()}"


settings = AppSettings()
