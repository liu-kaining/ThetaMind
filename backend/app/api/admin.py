"""Admin API endpoints for system configuration and user management."""

import logging
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_superuser, get_db
from app.db.models import SystemConfig, User
from app.db.session import AsyncSessionLocal
from app.services.config_service import config_service

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


# User management models
class UserResponse(BaseModel):
    """User response model for admin endpoints."""

    id: UUID = Field(..., description="User UUID")
    email: str = Field(..., description="User email")
    is_pro: bool = Field(..., description="Pro subscription status")
    is_superuser: bool = Field(..., description="Superuser status")
    subscription_id: str | None = Field(None, description="Subscription ID")
    plan_expiry_date: datetime | None = Field(None, description="Plan expiry date")
    daily_ai_usage: int = Field(..., description="Daily AI usage count")
    created_at: datetime = Field(..., description="Account creation date")
    strategies_count: int = Field(default=0, description="Number of strategies")
    ai_reports_count: int = Field(default=0, description="Number of AI reports")

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    """User update request model."""

    is_pro: bool | None = Field(None, description="Update Pro status")
    is_superuser: bool | None = Field(None, description="Update superuser status")
    plan_expiry_date: datetime | None = Field(None, description="Update plan expiry date")
    daily_ai_usage: int | None = Field(None, ge=0, description="Reset daily AI usage")




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


# ==================== User Management Endpoints ====================


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    current_user: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=100, description="Maximum number of users to return"),
    offset: int = Query(0, ge=0, description="Number of users to skip"),
    search: str | None = Query(None, description="Search by email (case-insensitive)"),
) -> list[UserResponse]:
    """
    List all users with pagination and search.

    Requires superuser access.
    """
    try:
        query = select(User)
        
        # Apply search filter if provided
        if search:
            query = query.where(User.email.ilike(f"%{search}%"))
        
        # Order by created_at descending (newest first)
        query = query.order_by(User.created_at.desc())
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        users = result.scalars().all()
        
        # Get counts for each user
        from app.db.models import Strategy, AIReport
        
        user_responses = []
        for user in users:
            # Count strategies
            strategies_result = await db.execute(
                select(func.count(Strategy.id)).where(Strategy.user_id == user.id)
            )
            strategies_count = strategies_result.scalar() or 0
            
            # Count AI reports
            reports_result = await db.execute(
                select(func.count(AIReport.id)).where(AIReport.user_id == user.id)
            )
            reports_count = reports_result.scalar() or 0
            
            user_responses.append(
                UserResponse(
                    id=user.id,
                    email=user.email,
                    is_pro=user.is_pro,
                    is_superuser=user.is_superuser,
                    subscription_id=user.subscription_id,
                    plan_expiry_date=user.plan_expiry_date,
                    daily_ai_usage=user.daily_ai_usage,
                    created_at=user.created_at,
                    strategies_count=strategies_count,
                    ai_reports_count=reports_count,
                )
            )
        
        return user_responses
    except Exception as e:
        logger.error(f"Error listing users: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users",
        )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Get a specific user by ID.

    Requires superuser access.
    """
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found",
            )
        
        # Get counts
        from app.db.models import Strategy, AIReport
        
        strategies_result = await db.execute(
            select(func.count(Strategy.id)).where(Strategy.user_id == user.id)
        )
        strategies_count = strategies_result.scalar() or 0
        
        reports_result = await db.execute(
            select(func.count(AIReport.id)).where(AIReport.user_id == user.id)
        )
        reports_count = reports_result.scalar() or 0
        
        return UserResponse(
            id=user.id,
            email=user.email,
            is_pro=user.is_pro,
            is_superuser=user.is_superuser,
            subscription_id=user.subscription_id,
            plan_expiry_date=user.plan_expiry_date,
            daily_ai_usage=user.daily_ai_usage,
            created_at=user.created_at,
            strategies_count=strategies_count,
            ai_reports_count=reports_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user",
        )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    current_user: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Update a user's properties.

    Requires superuser access.
    
    Prevents removing superuser status from yourself.
    """
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found",
            )
        
        # Prevent removing superuser status from yourself
        if user_id == current_user.id and request.is_superuser is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove superuser status from yourself",
            )
        
        # Update fields if provided
        if request.is_pro is not None:
            user.is_pro = request.is_pro
        if request.is_superuser is not None:
            user.is_superuser = request.is_superuser
        if request.plan_expiry_date is not None:
            user.plan_expiry_date = request.plan_expiry_date
        if request.daily_ai_usage is not None:
            user.daily_ai_usage = request.daily_ai_usage
        
        await db.commit()
        await db.refresh(user)
        
        # Get counts
        from app.db.models import Strategy, AIReport
        
        strategies_result = await db.execute(
            select(func.count(Strategy.id)).where(Strategy.user_id == user.id)
        )
        strategies_count = strategies_result.scalar() or 0
        
        reports_result = await db.execute(
            select(func.count(AIReport.id)).where(AIReport.user_id == user.id)
        )
        reports_count = reports_result.scalar() or 0
        
        return UserResponse(
            id=user.id,
            email=user.email,
            is_pro=user.is_pro,
            is_superuser=user.is_superuser,
            subscription_id=user.subscription_id,
            plan_expiry_date=user.plan_expiry_date,
            daily_ai_usage=user.daily_ai_usage,
            created_at=user.created_at,
            strategies_count=strategies_count,
            ai_reports_count=reports_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete a user and all associated data.

    Requires superuser access.
    
    Prevents deleting yourself.
    """
    try:
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete yourself",
            )
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found",
            )
        
        # Delete related records first (since foreign keys don't have CASCADE)
        from app.db.models import Strategy, AIReport
        
        # Delete user's strategies
        strategies_result = await db.execute(
            select(Strategy).where(Strategy.user_id == user_id)
        )
        strategies = strategies_result.scalars().all()
        for strategy in strategies:
            await db.delete(strategy)
        
        # Delete user's AI reports
        reports_result = await db.execute(
            select(AIReport).where(AIReport.user_id == user_id)
        )
        reports = reports_result.scalars().all()
        for report in reports:
            await db.delete(report)
        
        # Delete user
        await db.delete(user)
        await db.commit()
        
        logger.info(
            f"User {user_id} ({user.email}) deleted by superuser {current_user.id}. "
            f"Deleted {len(strategies)} strategies and {len(reports)} reports."
        )
        
        logger.info(f"User {user_id} ({user.email}) deleted by superuser {current_user.id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user",
        )

