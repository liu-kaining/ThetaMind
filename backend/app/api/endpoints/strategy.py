"""Strategy CRUD API endpoints."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.schemas import StrategyRequest, StrategyResponse
from app.db.models import Strategy, User
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/strategies", tags=["strategies"])


@router.post("", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
async def create_strategy(
    request: StrategyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StrategyResponse:
    """
    Create a new strategy for the authenticated user.

    Args:
        request: Strategy creation request with name and legs_json
        current_user: Authenticated user (from JWT token)
        db: Database session

    Returns:
        StrategyResponse with created strategy

    Raises:
        HTTPException: If creation fails
    """
    try:
        strategy = Strategy(
            user_id=current_user.id,
            name=request.name,
            legs_json=request.legs_json,
        )
        db.add(strategy)
        await db.commit()
        await db.refresh(strategy)

        logger.info(f"Strategy '{strategy.name}' created for user {current_user.email}")

        return StrategyResponse(
            id=str(strategy.id),
            name=strategy.name,
            legs_json=strategy.legs_json,
            created_at=strategy.created_at,
        )

    except Exception as e:
        logger.error(f"Error creating strategy: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create strategy: {str(e)}",
        )


@router.get("", response_model=list[StrategyResponse])
async def list_strategies(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(10, ge=1, le=100, description="Maximum number of strategies to return"),
    offset: int = Query(0, ge=0, description="Number of strategies to skip"),
) -> list[StrategyResponse]:
    """
    List strategies for the authenticated user (paginated).

    Returns only strategies owned by the current user.

    Args:
        current_user: Authenticated user (from JWT token)
        db: Database session
        limit: Maximum number of strategies to return (1-100)
        offset: Number of strategies to skip

    Returns:
        List of StrategyResponse
    """
    try:
        result = await db.execute(
            select(Strategy)
            .where(Strategy.user_id == current_user.id)
            .order_by(Strategy.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        strategies = result.scalars().all()

        return [
            StrategyResponse(
                id=str(strategy.id),
                name=strategy.name,
                legs_json=strategy.legs_json,
                created_at=strategy.created_at,
            )
            for strategy in strategies
        ]

    except Exception as e:
        logger.error(f"Error listing strategies: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list strategies",
        )


@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(
    strategy_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StrategyResponse:
    """
    Get a specific strategy by ID.

    Only returns strategy if it belongs to the authenticated user.

    Args:
        strategy_id: Strategy UUID
        current_user: Authenticated user (from JWT token)
        db: Database session

    Returns:
        StrategyResponse

    Raises:
        HTTPException: If strategy not found or doesn't belong to user
    """
    try:
        result = await db.execute(
            select(Strategy).where(
                Strategy.id == strategy_id, Strategy.user_id == current_user.id
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found",
            )

        return StrategyResponse(
            id=str(strategy.id),
            name=strategy.name,
            legs_json=strategy.legs_json,
            created_at=strategy.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching strategy {strategy_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch strategy",
        )


@router.put("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(
    strategy_id: UUID,
    request: StrategyRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StrategyResponse:
    """
    Update a strategy.

    Only allows updating strategies owned by the authenticated user.

    Args:
        strategy_id: Strategy UUID
        request: Strategy update request with name and legs_json
        current_user: Authenticated user (from JWT token)
        db: Database session

    Returns:
        StrategyResponse with updated strategy

    Raises:
        HTTPException: If strategy not found or doesn't belong to user
    """
    try:
        result = await db.execute(
            select(Strategy).where(
                Strategy.id == strategy_id, Strategy.user_id == current_user.id
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found",
            )

        # Update strategy
        strategy.name = request.name
        strategy.legs_json = request.legs_json
        await db.commit()
        await db.refresh(strategy)

        logger.info(f"Strategy '{strategy.name}' updated by user {current_user.email}")

        return StrategyResponse(
            id=str(strategy.id),
            name=strategy.name,
            legs_json=strategy.legs_json,
            created_at=strategy.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating strategy {strategy_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update strategy: {str(e)}",
        )


@router.delete("/{strategy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_strategy(
    strategy_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete a strategy.

    Only allows deleting strategies owned by the authenticated user.

    Args:
        strategy_id: Strategy UUID
        current_user: Authenticated user (from JWT token)
        db: Database session

    Raises:
        HTTPException: If strategy not found or doesn't belong to user
    """
    try:
        result = await db.execute(
            select(Strategy).where(
                Strategy.id == strategy_id, Strategy.user_id == current_user.id
            )
        )
        strategy = result.scalar_one_or_none()

        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Strategy not found",
            )

        await db.delete(strategy)
        await db.commit()

        logger.info(f"Strategy {strategy_id} deleted by user {current_user.email}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting strategy {strategy_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete strategy",
        )

