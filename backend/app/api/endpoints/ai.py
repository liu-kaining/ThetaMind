"""AI analysis API endpoints."""

import logging
from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import UUID

import pytz
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.schemas import AIReportResponse, DailyPickResponse
from app.core.config import settings
from app.db.models import AIReport, DailyPick, User
from app.db.session import AsyncSessionLocal, get_db
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])

# Quota limits
FREE_AI_QUOTA = 1  # Free users: 1 report per day
PRO_AI_QUOTA = 50  # Pro users: 50 reports per day


class StrategyAnalysisRequest(BaseModel):
    """Strategy analysis request model."""

    strategy_data: dict[str, Any] = Field(..., description="Strategy configuration (legs, strikes, etc.)")
    option_chain: dict[str, Any] = Field(..., description="Option chain data for the underlying asset")


def check_ai_quota(user: User) -> None:
    """
    Check if user has remaining AI quota.

    Args:
        user: User model instance

    Raises:
        HTTPException: If quota exceeded (429 Too Many Requests)
    """
    quota_limit = PRO_AI_QUOTA if user.is_pro else FREE_AI_QUOTA

    if user.daily_ai_usage >= quota_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily AI quota exceeded. Limit: {quota_limit} reports per day. "
            f"Current usage: {user.daily_ai_usage}",
        )


async def increment_ai_usage(user: User, db: AsyncSession) -> None:
    """
    Increment user's daily AI usage counter.

    Args:
        user: User model instance
        db: Database session
    """
    stmt = (
        update(User)
        .where(User.id == user.id)
        .values(daily_ai_usage=User.daily_ai_usage + 1)
    )
    await db.execute(stmt)
    await db.commit()
    # Refresh user to get updated daily_ai_usage
    await db.refresh(user)


@router.post("/report", response_model=AIReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_ai_report(
    request: StrategyAnalysisRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIReportResponse:
    """
    Generate AI analysis report for a strategy.

    Flow:
    1. Check user's daily AI quota
    2. Generate report using AI service
    3. Save report to database
    4. Increment user's daily_ai_usage counter

    Args:
        request: Strategy analysis request with strategy_data and option_chain
        current_user: Authenticated user (from JWT token)
        db: Database session

    Returns:
        AIReportResponse with generated report

    Raises:
        HTTPException: If quota exceeded (429) or AI service fails
    """
    # Step 1: Check quota
    check_ai_quota(current_user)

    try:
        # Step 2: Generate report using AI service
        logger.info(f"Generating AI report for user {current_user.email}")
        report_content = await ai_service.generate_report(
            strategy_data=request.strategy_data,
            option_chain=request.option_chain,
        )

        # Step 3: Save report to database
        ai_report = AIReport(
            user_id=current_user.id,
            report_content=report_content,
            model_used=settings.ai_model_default,
            created_at=datetime.now(timezone.utc),
        )
        db.add(ai_report)
        await db.flush()  # Flush to get the ID
        await db.refresh(ai_report)

        # Step 4: Increment usage counter
        await increment_ai_usage(current_user, db)

        logger.info(
            f"AI report generated successfully for user {current_user.email}. "
            f"Usage: {current_user.daily_ai_usage + 1}/{PRO_AI_QUOTA if current_user.is_pro else FREE_AI_QUOTA}"
        )

        return AIReportResponse(
            id=str(ai_report.id),
            report_content=ai_report.report_content,
            model_used=ai_report.model_used,
            created_at=ai_report.created_at,
        )

    except HTTPException:
        # Re-raise HTTP exceptions (e.g., 429 from quota check)
        raise
    except Exception as e:
        logger.error(f"Error generating AI report: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate AI report: {str(e)}",
        )


@router.get("/daily-picks", response_model=DailyPickResponse)
async def get_daily_picks(
    date: str | None = Query(None, description="Date in YYYY-MM-DD format. Defaults to today (EST)"),
) -> DailyPickResponse:
    """
    Get daily AI-generated strategy picks.

    Public endpoint (authentication optional).
    If date is not provided, returns picks for today (EST).

    Args:
        date: Optional date in YYYY-MM-DD format (defaults to today EST)
        current_user: Optional authenticated user (for future filtering)

    Returns:
        DailyPickResponse with strategy picks for the date

    Raises:
        HTTPException: If picks not found for the date
    """
    from datetime import date as date_type

    # Parse date or use today (EST)
    if date:
        try:
            target_date = date_type.fromisoformat(date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD",
            )
    else:
        # Use today in EST (market timezone)
        EST = pytz.timezone("US/Eastern")
        target_date = datetime.now(EST).date()

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(
                select(DailyPick).where(DailyPick.date == target_date)
            )
            daily_pick = result.scalar_one_or_none()

            if not daily_pick:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No daily picks found for date {target_date.isoformat()}",
                )

            return DailyPickResponse(
                date=daily_pick.date.isoformat(),
                content_json=daily_pick.content_json,
                created_at=daily_pick.created_at,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching daily picks: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to fetch daily picks",
            )


@router.get("/reports", response_model=list[AIReportResponse])
async def get_user_reports(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(10, ge=1, le=100, description="Maximum number of reports to return"),
    offset: int = Query(0, ge=0, description="Number of reports to skip"),
) -> list[AIReportResponse]:
    """
    Get user's AI reports (paginated).

    Returns reports for the authenticated user only.

    Args:
        current_user: Authenticated user (from JWT token)
        db: Database session
        limit: Maximum number of reports to return (1-100)
        offset: Number of reports to skip

    Returns:
        List of AIReportResponse
    """
    try:
        result = await db.execute(
            select(AIReport)
            .where(AIReport.user_id == current_user.id)
            .order_by(AIReport.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        reports = result.scalars().all()

        return [
            AIReportResponse(
                id=str(report.id),
                report_content=report.report_content,
                model_used=report.model_used,
                created_at=report.created_at,
            )
            for report in reports
        ]

    except Exception as e:
        logger.error(f"Error fetching user reports: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch reports",
        )


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete an AI report.

    Only allows deleting reports owned by the authenticated user.

    Args:
        report_id: Report UUID
        current_user: Authenticated user (from JWT token)
        db: Database session

    Raises:
        HTTPException: If report not found or doesn't belong to user
    """
    try:
        result = await db.execute(
            select(AIReport).where(
                AIReport.id == report_id, AIReport.user_id == current_user.id
            )
        )
        report = result.scalar_one_or_none()

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found",
            )

        await db.delete(report)
        await db.commit()

        logger.info(f"Report {report_id} deleted by user {current_user.email}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting report {report_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete report",
        )

