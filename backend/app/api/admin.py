"""Admin API endpoints for system configuration and user management."""

import logging
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import pytz

from app.api.deps import get_current_superuser, get_db
from app.api.endpoints.tasks import create_task_async, TaskResponse
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


class UserUpdateRequest(BaseModel):
    """User update request model."""

    is_pro: bool | None = Field(None, description="Pro subscription status")
    is_superuser: bool | None = Field(None, description="Superuser status")
    plan_expiry_date: datetime | None = Field(None, description="Plan expiry date")


class DailyPicksTriggerResponse(BaseModel):
    """Response model for daily picks trigger."""

    task_id: str = Field(..., description="Task ID for the daily picks generation")
    message: str = Field(..., description="Status message")


# Configuration endpoints
@router.get("/configs", response_model=list[ConfigItem])
async def get_all_configs(
    current_user: Annotated[User, Depends(get_current_superuser)],
) -> list[ConfigItem]:
    """
    Get all system configuration items.

    Requires superuser access.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(SystemConfig))
            configs = result.scalars().all()

            return [
                ConfigItem(
                    key=config.key,
                    value=config.value,
                    description=config.description,
                )
                for config in configs
            ]
    except Exception as e:
        logger.error(f"Error fetching configs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch configs",
        )


@router.get("/configs/{key}", response_model=ConfigItem)
async def get_config(
    key: str,
    current_user: Annotated[User, Depends(get_current_superuser)],
) -> ConfigItem:
    """
    Get a specific configuration item.

    Requires superuser access.
    """
    try:
        value = await config_service.get(key)
        description = await config_service.get_description(key)

        return ConfigItem(key=key, value=value, description=description)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Config key '{key}' not found",
        )
    except Exception as e:
        logger.error(f"Error fetching config {key}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch config",
        )


@router.put("/configs/{key}", response_model=ConfigItem)
async def update_config(
    key: str,
    request: ConfigUpdateRequest,
    current_user: Annotated[User, Depends(get_current_superuser)],
) -> ConfigItem:
    """
    Update a configuration item.

    Requires superuser access.
    """
    try:
        await config_service.set(
            key, request.value, description=request.description, updated_by=current_user.id
        )

        return ConfigItem(
            key=key, value=request.value, description=request.description
        )
    except Exception as e:
        logger.error(f"Error updating config {key}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update config",
        )


@router.delete("/configs/{key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_config(
    key: str,
    current_user: Annotated[User, Depends(get_current_superuser)],
) -> None:
    """
    Delete a configuration item.

    Requires superuser access.
    """
    try:
        await config_service.delete(key, updated_by=current_user.id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Config key '{key}' not found",
        )
    except Exception as e:
        logger.error(f"Error deleting config {key}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete config",
        )


# User management endpoints
@router.get("/users", response_model=list[UserResponse])
async def list_users(
    current_user: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of users"),
    skip: int = Query(0, ge=0, description="Number of users to skip"),
) -> list[UserResponse]:
    """
    List all users (paginated).

    Requires superuser access.
    """
    try:
        result = await db.execute(
            select(User)
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(skip)
        )
        users = result.scalars().all()

        return [
            UserResponse(
                id=user.id,
                email=user.email,
                is_pro=user.is_pro,
                is_superuser=user.is_superuser,
                subscription_id=user.subscription_id,
                plan_expiry_date=user.plan_expiry_date,
                daily_ai_usage=user.daily_ai_usage,
                created_at=user.created_at,
            )
            for user in users
        ]
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
    Get user details by ID.

    Requires superuser access.
    """
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return UserResponse(
            id=user.id,
            email=user.email,
            is_pro=user.is_pro,
            is_superuser=user.is_superuser,
            subscription_id=user.subscription_id,
            plan_expiry_date=user.plan_expiry_date,
            daily_ai_usage=user.daily_ai_usage,
            created_at=user.created_at,
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
    Update user properties.

    Requires superuser access.
    """
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        # Update fields if provided
        if request.is_pro is not None:
            user.is_pro = request.is_pro
        if request.is_superuser is not None:
            user.is_superuser = request.is_superuser
        if request.plan_expiry_date is not None:
            user.plan_expiry_date = request.plan_expiry_date

        await db.commit()
        await db.refresh(user)

        return UserResponse(
            id=user.id,
            email=user.email,
            is_pro=user.is_pro,
            is_superuser=user.is_superuser,
            subscription_id=user.subscription_id,
            plan_expiry_date=user.plan_expiry_date,
            daily_ai_usage=user.daily_ai_usage,
            created_at=user.created_at,
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
                detail="User not found",
            )
        
        # Delete associated data first to avoid foreign key constraint violations
        # Tasks are handled by cascade delete, but strategies and ai_reports are not
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
        
        # Now delete the user (tasks will be deleted by cascade)
        await db.delete(user)
        await db.commit()
        
        logger.info(f"User {user_id} deleted by admin {current_user.id} (deleted {len(strategies)} strategies, {len(reports)} reports)")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user",
        )


# Daily Picks Management
@router.post("/daily-picks/trigger", response_model=DailyPicksTriggerResponse)
async def trigger_daily_picks(
    current_user: Annotated[User, Depends(get_current_superuser)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DailyPicksTriggerResponse:
    """
    Manually trigger daily picks generation.
    
    Creates a system task (user_id=None) to run the daily picks pipeline.
    The task will run asynchronously and can be monitored in Task Center.
    
    Requires superuser access.
    """
    try:
        EST = pytz.timezone("US/Eastern")
        today = datetime.now(EST).date()
        
        # Create system task (user_id=None)
        task = await create_task_async(
            db=db,
            user_id=None,  # System task
            task_type="daily_picks",
            metadata={"date": str(today), "triggered_by": str(current_user.id)},
        )
        await db.commit()
        
        logger.info(f"Daily picks task {task.id} created by admin {current_user.email} for {today}")
        
        return DailyPicksTriggerResponse(
            task_id=str(task.id),
            message=f"Daily picks generation started for {today}. Task ID: {task.id}",
        )
    except Exception as e:
        logger.error(f"Error triggering daily picks: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger daily picks: {str(e)}",
        )
