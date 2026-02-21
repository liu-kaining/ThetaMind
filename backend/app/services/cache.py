"""Redis cache service with connection pool and auto-reconnect."""

import asyncio
import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Redis cache service with connection pool, auto-reconnect, and TTL control."""

    def __init__(self) -> None:
        """Initialize Redis connection pool."""
        self._redis: aioredis.Redis | None = None
        self._connection_pool: aioredis.ConnectionPool | None = None

    async def connect(self) -> None:
        """Connect to Redis with connection pool for high performance."""
        try:
            # Create connection pool (reuses connections, prevents connection exhaustion)
            self._connection_pool = aioredis.ConnectionPool.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,  # 5 second connection timeout
                socket_keepalive=True,  # Keep connections alive
                socket_keepalive_options={},  # TCP keepalive options
                retry_on_timeout=True,  # Retry on timeout
                health_check_interval=30,  # Health check every 30 seconds
                max_connections=50,  # Maximum connections in pool
            )
            
            # Create Redis client with connection pool
            self._redis = aioredis.Redis(connection_pool=self._connection_pool)
            
            # Test connection
            await asyncio.wait_for(self._redis.ping(), timeout=5.0)
            logger.info("Redis connected successfully with connection pool")
        except asyncio.TimeoutError:
            logger.warning("Redis connection timeout - continuing without cache")
            self._redis = None
            self._connection_pool = None
        except Exception as e:
            logger.warning(f"Failed to connect to Redis (continuing anyway): {e}")
            # Allow app to start even if Redis is down (degraded mode)
            self._redis = None
            self._connection_pool = None

    async def disconnect(self) -> None:
        """Disconnect from Redis and close connection pool."""
        if self._redis:
            try:
                await self._redis.close()
            except Exception as e:
                logger.warning(f"Error closing Redis client: {e}")
            self._redis = None
        
        if self._connection_pool:
            try:
                await self._connection_pool.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting Redis connection pool: {e}")
            self._connection_pool = None

    async def _ensure_connected(self) -> bool:
        """Ensure Redis connection is alive, reconnect if needed.
        
        Returns:
            True if connected, False otherwise
        """
        if not self._redis:
            await self.connect()
            return self._redis is not None
        
        try:
            # Quick ping to check connection health
            await asyncio.wait_for(self._redis.ping(), timeout=2.0)
            return True
        except Exception:
            logger.warning("Redis connection lost, reconnecting...")
            await self.disconnect()
            await self.connect()
            return self._redis is not None

    async def get(self, key: str) -> Any | None:
        """
        Get value from cache with auto-reconnect.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not await self._ensure_connected():
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
            logger.warning(f"Redis GET error for {key}: {e}")  # Changed to WARNING (not critical)
            # Try to reconnect on next call
            self._redis = None
            return None

    async def set(
        self, key: str, value: Any, ttl: int, is_pro: bool = False
    ) -> None:
        """
        Set value in cache with TTL and auto-reconnect.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            is_pro: Reserved for compatibility (no TTL override)
        """
        if not await self._ensure_connected():
            return
        if ttl <= 0:
            return

        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)

            await self._redis.setex(key, ttl, value)
        except Exception as e:
            logger.warning(f"Redis SET error for {key}: {e}")  # Changed to WARNING
            # Try to reconnect on next call
            self._redis = None

    async def delete(self, key: str) -> None:
        """Delete key from cache with auto-reconnect."""
        if not await self._ensure_connected():
            return
        try:
            await self._redis.delete(key)
        except Exception as e:
            logger.warning(f"Redis DELETE error for {key}: {e}")  # Changed to WARNING
            # Try to reconnect on next call
            self._redis = None

    async def acquire_lock(self, lock_key: str, ttl: int = 3600) -> bool:
        """
        Acquire a distributed lock using Redis SETNX.
        
        Args:
            lock_key: Lock key string
            ttl: Time to live in seconds (lock expiration)
            
        Returns:
            True if lock was successfully acquired, False otherwise
        """
        if not await self._ensure_connected():
            # If Redis is down, we fail open or fail closed?
            # Better to fail closed (False) for locks to prevent concurrent executions
            # if we truly depend on it, but for our case, maybe return True to degrade to memory execution?
            # Wait, if Redis is down, all workers will return False and nothing will run, OR
            # if we return True, all workers will run. For critical tasks, fail closed.
            return False
            
        try:
            # set(name, value, ex=expiry, nx=True)
            # returns True if set, None/False if not set
            result = await self._redis.set(lock_key, "1", ex=ttl, nx=True)
            return bool(result)
        except Exception as e:
            logger.warning(f"Redis SETNX error for lock {lock_key}: {e}")
            self._redis = None
            return False

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
