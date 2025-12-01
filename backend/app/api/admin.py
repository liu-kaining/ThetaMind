"""Admin API endpoints for system configuration management."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_superuser
from app.db.models import SystemConfig, User
from app.db.session import AsyncSessionLocal
from app.services.config_service import config_service
from sqlalchemy import select

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




@router.get("/configs", response_model=list[ConfigItem])
async def get_all_configs(
    current_user: Annotated[User, Depends(get_current_superuser)],
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
    current_user: Annotated[User, Depends(get_current_superuser)],
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
    current_user: Annotated[User, Depends(get_current_superuser)],
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
    current_user: Annotated[User, Depends(get_current_superuser)],
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

