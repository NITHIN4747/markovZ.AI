"""
Cache Layer with Redis and in-memory fallback.
"""
import logging
import redis
from app.config import settings

logger = logging.getLogger(__name__)

_memory_cache: dict[str, str] = {}


class CacheClient:
    def __init__(self):
        self._redis = None
        try:
            self._redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception as e:
            logger.warning(f"Could not connect to Redis at {settings.REDIS_URL}: {e}")

    def get(self, key: str) -> str | None:
        if self._redis:
            try:
                return self._redis.get(key)
            except Exception:
                pass
        return _memory_cache.get(key)

    def set(self, key: str, value: str, ex: int | None = None, nx: bool = False) -> bool:
        if self._redis:
            try:
                res = self._redis.set(key, value, ex=ex, nx=nx)
                return bool(res)
            except Exception:
                pass
        if nx and key in _memory_cache:
            return False
        _memory_cache[key] = value
        return True

    def delete(self, key: str):
        if self._redis:
            try:
                self._redis.delete(key)
            except Exception:
                pass
        _memory_cache.pop(key, None)


cache = CacheClient()
