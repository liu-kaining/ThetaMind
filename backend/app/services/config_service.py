"""System configuration service with Redis caching."""

import json
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SystemConfig
from app.db.session import AsyncSessionLocal
from app.services.cache import cache_service

logger = logging.getLogger(__name__)

# Cache TTL for config values (5 minutes)
CONFIG_CACHE_TTL = 300


class ConfigService:
    """Service for managing system configuration with Redis caching."""

    @staticmethod
    def _get_cache_key(key: str) -> str:
        """Generate cache key for config value."""
        return f"config:{key}"

    @staticmethod
    async def get(key: str, default: str | None = None) -> str | None:
        """
        Get configuration value with Redis caching.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        # Try cache first
        cache_key = ConfigService._get_cache_key(key)
        cached_value = await cache_service.get(cache_key)
        if cached_value is not None:
            logger.debug(f"Config cache HIT for key: {key}")
            return cached_value

        # Cache miss - query database
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(SystemConfig).where(SystemConfig.key == key)
                )
                config = result.scalar_one_or_none()

                if config:
                    value = config.value
                    # Cache the value (config values are not user-specific, so is_pro=False)
                    await cache_service.set(cache_key, value, ttl=CONFIG_CACHE_TTL, is_pro=False)
                    logger.debug(f"Config loaded from DB and cached: {key}")
                    return value
                else:
                    # Cache default value to avoid repeated DB queries
                    # Note: We cache defaults to reduce DB load, but this means missing configs won't be retried
                    if default is not None:
                        await cache_service.set(cache_key, default, ttl=CONFIG_CACHE_TTL, is_pro=False)
                    logger.debug(f"Config key not found: {key}, using default")
                    return default
            except Exception as e:
                logger.error(f"Error fetching config key {key}: {e}", exc_info=True)
                return default

    @staticmethod
    async def set(key: str, value: str, description: str | None = None, updated_by: uuid.UUID | None = None) -> SystemConfig:
        """
        Set configuration value (upsert).

        Args:
            key: Configuration key
            value: Configuration value
            description: Optional description
            updated_by: User ID who updated the config

        Returns:
            SystemConfig instance
        """
        from datetime import datetime, timezone

        async with AsyncSessionLocal() as session:
            try:
                # Try to get existing config
                result = await session.execute(
                    select(SystemConfig).where(SystemConfig.key == key)
                )
                config = result.scalar_one_or_none()

                if config:
                    # Update existing
                    config.value = value
                    config.updated_by = updated_by
                    config.updated_at = datetime.now(timezone.utc)
                    if description:
                        config.description = description
                else:
                    # Create new
                    config = SystemConfig(
                        key=key,
                        value=value,
                        description=description,
                        updated_by=updated_by,
                    )
                    session.add(config)

                await session.commit()
                await session.refresh(config)

                # Invalidate cache
                cache_key = ConfigService._get_cache_key(key)
                await cache_service.delete(cache_key)

                logger.info(f"Config updated: {key}")
                return config
            except Exception as e:
                logger.error(f"Error setting config key {key}: {e}", exc_info=True)
                await session.rollback()
                raise

    @staticmethod
    async def get_all() -> list[dict[str, Any]]:
        """
        Get all configuration entries.

        Returns:
            List of config dictionaries
        """
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(select(SystemConfig))
                configs = result.scalars().all()

                return [
                    {
                        "key": config.key,
                        "value": config.value,
                        "description": config.description,
                        "updated_by": str(config.updated_by) if config.updated_by else None,
                        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
                        "created_at": config.created_at.isoformat(),
                    }
                    for config in configs
                ]
            except Exception as e:
                logger.error(f"Error fetching all configs: {e}", exc_info=True)
                return []

    @staticmethod
    async def delete(key: str) -> bool:
        """
        Delete configuration entry.

        Args:
            key: Configuration key

        Returns:
            True if deleted, False if not found
        """
        async with AsyncSessionLocal() as session:
            try:
                result = await session.execute(
                    select(SystemConfig).where(SystemConfig.key == key)
                )
                config = result.scalar_one_or_none()

                if config:
                    await session.delete(config)
                    await session.commit()

                    # Invalidate cache
                    cache_key = ConfigService._get_cache_key(key)
                    await cache_service.delete(cache_key)

                    logger.info(f"Config deleted: {key}")
                    return True
                return False
            except Exception as e:
                logger.error(f"Error deleting config key {key}: {e}", exc_info=True)
                await session.rollback()
                return False


# Global config service instance
config_service = ConfigService()

