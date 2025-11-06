"""
Redis caching middleware for Maximo API responses
Implements cache-aside pattern with TTL management
"""
import json
from typing import Any, Dict, Optional
from functools import wraps

import redis.asyncio as redis

from src.config import settings, CACHE_CONFIG
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CacheManager:
    """Async Redis cache manager"""

    def __init__(self):
        self.enabled = settings.redis_enabled
        self._redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> Optional[redis.Redis]:
        """Get or create Redis connection"""
        if not self.enabled:
            return None

        if self._redis is None:
            try:
                self._redis = await redis.Redis(
                    host=settings.redis_host,
                    port=settings.redis_port,
                    db=settings.redis_db,
                    password=settings.redis_password,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True,
                )
                # Test connection
                await self._redis.ping()
                logger.info("Redis connection established")
            except Exception as e:
                logger.error("Failed to connect to Redis", error=str(e))
                self._redis = None
                self.enabled = False

        return self._redis

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            logger.info("Redis connection closed")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled:
            return None

        try:
            redis_client = await self._get_redis()
            if not redis_client:
                return None

            value = await redis_client.get(key)
            if value:
                logger.debug("Cache hit", key=key)
                return json.loads(value)

            logger.debug("Cache miss", key=key)
            return None

        except Exception as e:
            logger.error("Cache get error", key=key, error=str(e))
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set value in cache with TTL"""
        if not self.enabled:
            return False

        try:
            redis_client = await self._get_redis()
            if not redis_client:
                return False

            serialized = json.dumps(value)
            if ttl:
                await redis_client.setex(key, ttl, serialized)
            else:
                await redis_client.set(key, serialized)

            logger.debug("Cache set", key=key, ttl=ttl)
            return True

        except Exception as e:
            logger.error("Cache set error", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.enabled:
            return False

        try:
            redis_client = await self._get_redis()
            if not redis_client:
                return False

            await redis_client.delete(key)
            logger.debug("Cache delete", key=key)
            return True

        except Exception as e:
            logger.error("Cache delete error", key=key, error=str(e))
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self.enabled:
            return 0

        try:
            redis_client = await self._get_redis()
            if not redis_client:
                return 0

            keys = []
            async for key in redis_client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                deleted = await redis_client.delete(*keys)
                logger.info("Cache pattern delete", pattern=pattern, count=deleted)
                return deleted

            return 0

        except Exception as e:
            logger.error("Cache pattern delete error", pattern=pattern, error=str(e))
            return 0

    async def health_check(self) -> bool:
        """Check if Redis is accessible"""
        if not self.enabled:
            return True  # No Redis, no problem

        try:
            redis_client = await self._get_redis()
            if not redis_client:
                return False

            await redis_client.ping()
            return True

        except Exception as e:
            logger.error("Redis health check failed", error=str(e))
            return False


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


async def close_cache_manager():
    """Close global cache manager instance"""
    global _cache_manager
    if _cache_manager:
        await _cache_manager.close()
        _cache_manager = None


def cached(cache_type: str):
    """
    Decorator for caching function results

    Usage:
        @cached('asset_detail')
        async def get_asset(asset_num: str):
            return await maximo_client.get(f'/asset/{asset_num}')
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key from function name and arguments
            cache_key_parts = [func.__name__]

            # Add positional args
            for arg in args:
                if isinstance(arg, (str, int, float, bool)):
                    cache_key_parts.append(str(arg))

            # Add keyword args (sorted for consistency)
            for k, v in sorted(kwargs.items()):
                if isinstance(v, (str, int, float, bool)):
                    cache_key_parts.append(f"{k}={v}")

            cache_key = ":".join(cache_key_parts)

            # Try to get from cache
            cache_manager = get_cache_manager()
            cached_value = await cache_manager.get(cache_key)

            if cached_value is not None:
                logger.debug("Returning cached result", function=func.__name__, cache_key=cache_key)
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Cache the result
            ttl = CACHE_CONFIG.get(cache_type, {}).get("ttl", 300)
            await cache_manager.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator


def build_cache_key(*parts: str) -> str:
    """Build cache key from parts"""
    return ":".join(str(p) for p in parts)
