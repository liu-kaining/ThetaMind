"""Redis cache service with TTL management."""

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis cache service with Pro/Free TTL differentiation."""

    def __init__(self) -> None:
        """Initialize Redis connection."""
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self._redis = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            # Allow app to start even if Redis is down (degraded mode)

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()

    async def get(self, key: str) -> Any | None:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self._redis:
            return None

        try:
            value = await self._redis.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"Redis GET error for {key}: {e}")
            return None

    async def set(
        self, key: str, value: Any, ttl: int, is_pro: bool = False
    ) -> None:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (overridden by is_pro)
            is_pro: If True, use Pro TTL (5s), else Free TTL (15m)
        """
        if not self._redis:
            return

        # Pro: 5s TTL, Free: 15m TTL (as per spec)
        actual_ttl = 5 if is_pro else (900 if ttl > 900 else ttl)

        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            await self._redis.setex(key, actual_ttl, value)
        except Exception as e:
            logger.error(f"Redis SET error for {key}: {e}")

    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        if not self._redis:
            return
        try:
            await self._redis.delete(key)
        except Exception as e:
            logger.error(f"Redis DELETE error for {key}: {e}")

    def get_market_chain_key(self, symbol: str, date: str) -> str:
        """
        Generate market chain cache key.

        Args:
            symbol: Stock symbol
            date: Expiration date (YYYY-MM-DD)

        Returns:
            Cache key string
        """
        return f"market:chain:{symbol}:{date}"


# Global cache service instance
cache_service = CacheService()
