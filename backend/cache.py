from __future__ import annotations

import json
import logging
import time
from datetime import date, datetime
from typing import Any, Optional

from app_settings import settings

logger = logging.getLogger(__name__)

try:
    import redis
except Exception:  # pragma: no cover - import guard
    redis = None


def _json_default(value: Any):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


class CacheManager:
    def __init__(self) -> None:
        self.enabled = False
        self.client = None
        self._retry_interval_seconds = 5.0
        self._next_retry_at = 0.0

        self.ensure_connection()

    def _cache_is_configured(self) -> bool:
        return bool(settings.enable_cache and settings.redis_url and redis is not None)

    def ensure_connection(self) -> bool:
        if self.enabled and self.client:
            return True

        if not self._cache_is_configured():
            return False

        now = time.monotonic()
        if now < self._next_retry_at:
            return False

        try:
            self.client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
            self.client.ping()
            self.enabled = True
            self._next_retry_at = 0.0
            logger.info("Redis cache enabled")
            return True
        except Exception as exc:  # pragma: no cover - depends on runtime service
            self.client = None
            self.enabled = False
            self._next_retry_at = now + self._retry_interval_seconds
            logger.warning("Redis unavailable, cache disabled: %s", exc)
            return False

    def get_version(self, namespace: str) -> int:
        if not self.ensure_connection():
            return 1
        raw = self.client.get(f"cache:version:{namespace}")
        if raw is None:
            self.client.set(f"cache:version:{namespace}", 1)
            return 1
        try:
            return int(raw)
        except ValueError:
            return 1

    def invalidate_namespace(self, namespace: str) -> None:
        if not self.ensure_connection():
            return
        self.client.incr(f"cache:version:{namespace}")

    def build_key(self, namespace: str, *parts: Any) -> str:
        version = self.get_version(namespace)
        safe_parts = [str(part) for part in parts]
        return ":".join(["cache", namespace, f"v{version}", *safe_parts])

    def get_json(self, key: str) -> Optional[Any]:
        if not self.ensure_connection():
            return None
        raw = self.client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def set_json(self, key: str, value: Any, ttl: int) -> None:
        if not self.ensure_connection():
            return
        payload = json.dumps(value, ensure_ascii=False, default=_json_default)
        self.client.setex(key, ttl, payload)


cache_manager = CacheManager()
