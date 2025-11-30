"""Admin API endpoints for system configuration management."""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

# Note: ErrorResponse schema is available in schemas.py but not used in endpoints
# FastAPI automatically handles HTTPException, which is sufficient for error responses
from app.db.models import User
from app.db.session import AsyncSessionLocal, get_db
from app.services.config_service import config_service
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


# Pydantic models for admin endpoints
class ConfigItem(BaseModel):
    """Configuration item model."""

    key: str = Field(..., description="Configuration key")
    value: str = Field(..., description="Configuration value")
    description: str | None = Field(None, description="Optional description")


class ConfigUpdateRequest(BaseModel):
    """Configuration update request model."""

    value: str = Field(..., description="New configuration value")
    description: str | None = Field(None, description="Optional description")


# TODO: Replace with actual auth middleware
# For now, this is a placeholder that accepts user_id as query param (NOT for production!)
# In production, this should extract user_id from JWT token in Authorization header
async def get_current_user_id(
    user_id: str | None = None,  # In production, extract from JWT token
) -> uuid.UUID:
    """
    Temporary dependency to get user ID.

    TODO: Replace with proper JWT auth middleware.
    """
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    try:
        return uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format",
        )


# Dependency to check superuser status
async def require_superuser(
    db: AsyncSession = Depends(get_db),
    current_user_id: uuid.UUID = Depends(get_current_user_id),  # This would come from auth middleware in real implementation
) -> User:
    """
    Dependency to verify user is superuser.

    Args:
        current_user_id: Current user ID (from auth token)
        db: Database session

    Returns:
        User object if superuser

    Raises:
        HTTPException: If user is not superuser
    """
    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == current_user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required",
        )

    return user


@router.get("/configs", response_model=list[ConfigItem])
async def get_all_configs(
    current_user: User = Depends(require_superuser),
) -> list[ConfigItem]:
    """
    Get all system configurations.

    Requires superuser access.
    """
    try:
        configs = await config_service.get_all()
        return [
            ConfigItem(
                key=config["key"],
                value=config["value"],
                description=config["description"],
            )
            for config in configs
        ]
    except Exception as e:
        logger.error(f"Error fetching configs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch configurations",
        )


@router.get("/configs/{key}", response_model=ConfigItem)
async def get_config(
    key: str,
    current_user: User = Depends(require_superuser),
) -> ConfigItem:
    """
    Get a specific configuration value.

    Requires superuser access.
    """
    try:
        value = await config_service.get(key)
        if value is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration key '{key}' not found",
            )

        # Get description from DB
        from sqlalchemy import select
        from app.db.models import SystemConfig

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SystemConfig).where(SystemConfig.key == key)
            )
            config = result.scalar_one_or_none()

        return ConfigItem(
            key=key,
            value=value,
            description=config.description if config else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching config {key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch configuration",
        )


@router.put("/configs/{key}", response_model=ConfigItem)
async def update_config(
    key: str,
    request: ConfigUpdateRequest,
    current_user: User = Depends(require_superuser),
) -> ConfigItem:
    """
    Update a configuration value.

    Requires superuser access.
    """
    try:
        config = await config_service.set(
            key=key,
            value=request.value,
            description=request.description,
            updated_by=current_user.id,
        )

        return ConfigItem(
            key=config.key,
            value=config.value,
            description=config.description,
        )
    except Exception as e:
        logger.error(f"Error updating config {key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration",
        )


@router.delete("/configs/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(
    key: str,
    current_user: User = Depends(require_superuser),
) -> None:
    """
    Delete a configuration entry.

    Requires superuser access.
    """
    try:
        deleted = await config_service.delete(key)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Configuration key '{key}' not found",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting config {key}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete configuration",
        )

