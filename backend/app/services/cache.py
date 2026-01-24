"""Redis cache service with TTL management."""

import asyncio
import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis cache service with explicit TTL control."""

    def __init__(self) -> None:
        """Initialize Redis connection."""
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        """Connect to Redis with timeout."""
        try:
            # Add connection timeout (5 seconds) to prevent blocking startup
            self._redis = await asyncio.wait_for(
                aioredis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,  # 5 second connection timeout
                ),
                timeout=5.0,  # Overall timeout
            )
            logger.info("Redis connected successfully")
        except asyncio.TimeoutError:
            logger.warning("Redis connection timeout - continuing without cache")
            self._redis = None
        except Exception as e:
            logger.warning(f"Failed to connect to Redis (continuing anyway): {e}")
            # Allow app to start even if Redis is down (degraded mode)
            self._redis = None

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
            ttl: Time to live in seconds
            is_pro: Reserved for compatibility (no TTL override)
        """
        if not self._redis:
            return
        if ttl <= 0:
            return

        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            await self._redis.setex(key, ttl, value)
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
