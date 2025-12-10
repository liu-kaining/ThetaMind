"""Task management API endpoints."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.schemas import TaskResponse
from app.db.models import Task, User
from app.db.session import get_db

logger = logging.getLogger(__name__)


class TaskCreateRequest(BaseModel):
    """Task creation request model."""

    task_type: str = Field(..., description="Task type (e.g., 'ai_report')")
    metadata: dict[str, Any] | None = Field(None, description="Additional task metadata")

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def create_task_async(
    db: AsyncSession,
    user_id: UUID,
    task_type: str,
    metadata: dict[str, Any] | None = None,
) -> Task:
    """
    Create a new task and start processing it asynchronously.

    Args:
        db: Database session
        user_id: User UUID
        task_type: Task type (e.g., 'ai_report')
        metadata: Optional task metadata

    Returns:
        Created Task instance
    """
    task = Task(
        user_id=user_id,
        task_type=task_type,
        status="PENDING",
        metadata=metadata,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    # Start background processing
    asyncio.create_task(process_task_async(task.id, task_type, metadata, db))

    return task


async def process_task_async(
    task_id: UUID,
    task_type: str,
    metadata: dict[str, Any] | None,
    db: AsyncSession,
) -> None:
    """
    Process a task asynchronously in the background.

    Args:
        task_id: Task UUID
        task_type: Task type
        metadata: Task metadata
        db: Database session (will create a new session for processing)
    """
    from app.db.session import AsyncSessionLocal
    from app.services.ai_service import ai_service
    from app.core.config import settings

    async with AsyncSessionLocal() as session:
        try:
            # Update task status to PROCESSING
            result = await session.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                logger.error(f"Task {task_id} not found")
                return

            task.status = "PROCESSING"
            task.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(task)

            # Process based on task type
            if task_type == "ai_report":
                # Import here to avoid circular imports
                strategy_data = metadata.get("strategy_data") if metadata else None
                option_chain = metadata.get("option_chain") if metadata else None

                if not strategy_data or not option_chain:
                    raise ValueError("Missing strategy_data or option_chain in metadata")

                # Generate report
                report_content = await ai_service.generate_report(
                    strategy_data=strategy_data,
                    option_chain=option_chain,
                )

                # Save report and update task
                from app.db.models import AIReport, User

                # Get user to increment usage
                user_result = await session.execute(
                    select(User).where(User.id == task.user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    raise ValueError(f"User {task.user_id} not found")

                # Check quota
                from app.api.endpoints.ai import check_ai_quota, increment_ai_usage

                check_ai_quota(user)

                # Create AI report
                ai_report = AIReport(
                    user_id=task.user_id,
                    report_content=report_content,
                    model_used=settings.ai_model_default,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(ai_report)
                await session.flush()
                await session.refresh(ai_report)

                # Increment usage
                from sqlalchemy import update

                stmt = (
                    update(User)
                    .where(User.id == user.id)
                    .values(daily_ai_usage=User.daily_ai_usage + 1)
                )
                await session.execute(stmt)

                # Update task
                task.status = "SUCCESS"
                task.result_ref = str(ai_report.id)
                task.completed_at = datetime.now(timezone.utc)
                task.updated_at = datetime.now(timezone.utc)
                await session.commit()

                logger.info(f"Task {task_id} completed successfully. Report ID: {ai_report.id}")
            else:
                raise ValueError(f"Unknown task type: {task_type}")

        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}", exc_info=True)
            # Update task status to FAILED
            try:
                result = await session.execute(select(Task).where(Task.id == task_id))
                task = result.scalar_one_or_none()
                if task:
                    task.status = "FAILED"
                    task.error_message = str(e)
                    task.completed_at = datetime.now(timezone.utc)
                    task.updated_at = datetime.now(timezone.utc)
                    await session.commit()
            except Exception as update_error:
                logger.error(f"Error updating task {task_id} to FAILED: {update_error}", exc_info=True)


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    request: TaskCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskResponse:
    """
    Create a new background task.

    Args:
        request: Task creation request
        current_user: Authenticated user (from JWT token)
        db: Database session

    Returns:
        TaskResponse with created task
    """
    try:
        task = await create_task_async(
            db=db,
            user_id=current_user.id,
            task_type=request.task_type,
            metadata=request.metadata,
        )
        await db.commit()

        logger.info(f"Task {task.id} created for user {current_user.email}")

        return TaskResponse(
            id=str(task.id),
            task_type=task.task_type,
            status=task.status,
            result_ref=task.result_ref,
            error_message=task.error_message,
            metadata=task.metadata,
            created_at=task.created_at,
            updated_at=task.updated_at,
            completed_at=task.completed_at,
        )

    except Exception as e:
        logger.error(f"Error creating task: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}",
        )


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(20, ge=1, le=100, description="Maximum number of tasks to return"),
    skip: int = Query(0, ge=0, description="Number of tasks to skip"),
) -> list[TaskResponse]:
    """
    List tasks for the authenticated user (paginated).

    Returns only tasks owned by the current user, sorted by created_at DESC.

    Args:
        current_user: Authenticated user (from JWT token)
        db: Database session
        limit: Maximum number of tasks to return (1-100)
        skip: Number of tasks to skip

    Returns:
        List of TaskResponse
    """
    try:
        result = await db.execute(
            select(Task)
            .where(Task.user_id == current_user.id)
            .order_by(Task.created_at.desc())
            .limit(limit)
            .offset(skip)
        )
        tasks = result.scalars().all()

        return [
            TaskResponse(
                id=str(task.id),
                task_type=task.task_type,
                status=task.status,
                result_ref=task.result_ref,
                error_message=task.error_message,
                metadata=task.metadata,
                created_at=task.created_at,
                updated_at=task.updated_at,
                completed_at=task.completed_at,
            )
            for task in tasks
        ]

    except Exception as e:
        logger.error(f"Error listing tasks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tasks",
        )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskResponse:
    """
    Get a specific task by ID.

    Only returns task if it belongs to the authenticated user.

    Args:
        task_id: Task UUID
        current_user: Authenticated user (from JWT token)
        db: Database session

    Returns:
        TaskResponse with full task details

    Raises:
        HTTPException: If task not found or doesn't belong to user
    """
    try:
        result = await db.execute(
            select(Task).where(Task.id == task_id, Task.user_id == current_user.id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        return TaskResponse(
            id=str(task.id),
            task_type=task.task_type,
            status=task.status,
            result_ref=task.result_ref,
            error_message=task.error_message,
            metadata=task.metadata,
            created_at=task.created_at,
            updated_at=task.updated_at,
            completed_at=task.completed_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching task {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch task",
        )

