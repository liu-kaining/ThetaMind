"""AI analysis API endpoints."""

import logging
from datetime import datetime, timezone, date
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
from app.db.models import AIReport, DailyPick, GeneratedImage, User
from app.db.session import AsyncSessionLocal, get_db
from app.services.ai_service import ai_service
from app.api.endpoints.tasks import create_task_async

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])

# Quota limits
# Free users: 1 report per day, 1 image per day
FREE_AI_QUOTA = 1  # Reports per day
FREE_IMAGE_QUOTA = 1  # Images per day

# Pro Monthly users ($9.9/month): 10 reports per day, 10 images per day
PRO_MONTHLY_AI_QUOTA = 10  # Reports per day
PRO_MONTHLY_IMAGE_QUOTA = 10  # Images per day

# Pro Yearly users ($599/year): 30 reports per day, 30 images per day
PRO_YEARLY_AI_QUOTA = 30  # Reports per day
PRO_YEARLY_IMAGE_QUOTA = 30  # Images per day


class StrategyAnalysisRequest(BaseModel):
    """Strategy analysis request model."""

    strategy_summary: dict[str, Any] | None = Field(None, description="Complete strategy summary (preferred format)")
    # Legacy format (for backward compatibility)
    strategy_data: dict[str, Any] | None = Field(None, description="Strategy configuration (legs, strikes, etc.)")
    option_chain: dict[str, Any] | None = Field(None, description="Option chain data for the underlying asset")


def get_ai_quota_limit(user: User) -> int:
    """
    Get AI report quota limit for user based on subscription type.
    
    Args:
        user: User model instance
        
    Returns:
        Quota limit (reports per day)
    """
    if not user.is_pro:
        return FREE_AI_QUOTA
    
    # Check subscription type
    if user.subscription_type == "yearly":
        return PRO_YEARLY_AI_QUOTA
    elif user.subscription_type == "monthly":
        return PRO_MONTHLY_AI_QUOTA
    else:
        # Default to monthly for existing Pro users without subscription_type
        return PRO_MONTHLY_AI_QUOTA


def get_image_quota_limit(user: User) -> int:
    """
    Get image generation quota limit for user based on subscription type.
    
    Args:
        user: User model instance
        
    Returns:
        Quota limit (images per day)
    """
    if not user.is_pro:
        return FREE_IMAGE_QUOTA
    
    # Check subscription type
    if user.subscription_type == "yearly":
        return PRO_YEARLY_IMAGE_QUOTA
    elif user.subscription_type == "monthly":
        return PRO_MONTHLY_IMAGE_QUOTA
    else:
        # Default to monthly for existing Pro users without subscription_type
        return PRO_MONTHLY_IMAGE_QUOTA


async def check_and_reset_quota_if_needed(user: User, db: AsyncSession) -> None:
    """
    Check if quota needs to be reset based on date, and reset if needed.
    
    Args:
        user: User model instance
        db: Database session
    """
    today_utc = datetime.now(timezone.utc).date()
    last_reset_date = user.last_quota_reset_date.date() if user.last_quota_reset_date else None
    
    # If last_reset_date is None or different from today, reset quota
    if last_reset_date is None or last_reset_date != today_utc:
        stmt = (
            update(User)
            .where(User.id == user.id)
            .values(
                daily_ai_usage=0,
                daily_image_usage=0,
                last_quota_reset_date=datetime.now(timezone.utc)
            )
        )
        await db.execute(stmt)
        await db.commit()
        await db.refresh(user)
        logger.info(f"Reset daily quota for user {user.id} (date changed from {last_reset_date} to {today_utc})")


async def check_ai_quota(user: User, db: AsyncSession) -> None:
    """
    Check if user has remaining AI report quota.
    Automatically resets quota if date has changed.

    Args:
        user: User model instance
        db: Database session

    Raises:
        HTTPException: If quota exceeded (429 Too Many Requests)
    """
    # Check and reset quota if date changed
    await check_and_reset_quota_if_needed(user, db)
    
    quota_limit = get_ai_quota_limit(user)

    if user.daily_ai_usage >= quota_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily AI report quota exceeded. Limit: {quota_limit} reports per day. "
            f"Current usage: {user.daily_ai_usage}",
        )


async def check_image_quota(user: User, db: AsyncSession) -> None:
    """
    Check if user has remaining image generation quota.
    Automatically resets quota if date has changed.

    Args:
        user: User model instance
        db: Database session

    Raises:
        HTTPException: If quota exceeded (429 Too Many Requests)
    """
    # Check and reset quota if date changed
    await check_and_reset_quota_if_needed(user, db)
    
    quota_limit = get_image_quota_limit(user)

    if user.daily_image_usage >= quota_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily image generation quota exceeded. Limit: {quota_limit} images per day. "
            f"Current usage: {user.daily_image_usage}",
        )


async def increment_ai_usage(user: User, db: AsyncSession) -> None:
    """
    Increment user's daily AI report usage counter.
    Automatically resets quota if date has changed.

    Args:
        user: User model instance
        db: Database session
    """
    # Check and reset quota if date changed
    await check_and_reset_quota_if_needed(user, db)
    
    stmt = (
        update(User)
        .where(User.id == user.id)
        .values(daily_ai_usage=User.daily_ai_usage + 1)
    )
    await db.execute(stmt)
    await db.commit()
    # Refresh user to get updated daily_ai_usage
    await db.refresh(user)


async def increment_image_usage(user: User, db: AsyncSession) -> None:
    """
    Increment user's daily image generation usage counter.
    Automatically resets quota if date has changed.

    Args:
        user: User model instance
        db: Database session
    """
    # Check and reset quota if date changed
    await check_and_reset_quota_if_needed(user, db)
    
    stmt = (
        update(User)
        .where(User.id == user.id)
        .values(daily_image_usage=User.daily_image_usage + 1)
    )
    await db.execute(stmt)
    await db.commit()
    # Refresh user to get updated daily_image_usage
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
    await check_ai_quota(current_user, db)

    try:
        # Step 2: Generate report using AI service
        logger.info(f"Generating AI report for user {current_user.email}")
        
        # Use strategy_summary if available, otherwise use legacy format
        if request.strategy_summary:
            report_content = await ai_service.generate_report(
                strategy_summary=request.strategy_summary,
            )
        elif request.strategy_data and request.option_chain:
            # Legacy format (backward compatibility)
            logger.warning("Using legacy format for direct report generation. Please migrate to strategy_summary format.")
            report_content = await ai_service.generate_report(
                strategy_data=request.strategy_data,
                option_chain=request.option_chain,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either strategy_summary or (strategy_data + option_chain) must be provided",
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

        quota_limit = get_ai_quota_limit(current_user)
        logger.info(
            f"AI report generated successfully for user {current_user.email}. "
            f"Usage: {current_user.daily_ai_usage + 1}/{quota_limit}"
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
        
        # Check if it's a Google API quota error
        error_str = str(e)
        if "429" in error_str or "quota" in error_str.lower() or "ResourceExhausted" in error_str:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI service quota exceeded. Please try again later or check your Google API billing. "
                       "For more information, visit: https://ai.google.dev/gemini-api/docs/rate-limits",
            )
        
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


@router.post("/chart", status_code=status.HTTP_201_CREATED)
async def generate_strategy_chart(
    request: StrategyAnalysisRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Generate AI strategy chart image.

    Free users: 1 image per day
    Pro Monthly users: 10 images per day
    Pro Yearly users: 30 images per day

    Creates an async task to generate a professional strategy visualization.

    Args:
        request: Strategy analysis request with strategy_data and option_chain
        current_user: Authenticated user (from JWT token)
        db: Database session

    Returns:
        Dictionary with task_id

    Raises:
        HTTPException: If quota exceeded (429) or task creation fails
    """
    # Check image quota (all users have quota, but free users have lower limit)
    await check_image_quota(current_user, db)

    try:
        # Create task for new generation (user explicitly requested)
        # Note: We don't auto-check for cached images here - that should be done
        # via the /chart/by-hash/{strategy_hash} endpoint if needed
        from app.api.endpoints.tasks import create_task_async
        from app.api.schemas import TaskResponse
        
        # Use strategy_summary if available, otherwise use legacy format
        metadata = {}
        if request.strategy_summary:
            metadata["strategy_summary"] = request.strategy_summary
        elif request.strategy_data and request.option_chain:
            # Legacy format
            logger.warning("Using legacy format for chart generation. Please migrate to strategy_summary format.")
            metadata["strategy_data"] = request.strategy_data
            metadata["option_chain"] = request.option_chain
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either strategy_summary or (strategy_data + option_chain) must be provided",
            )
        
        task = await create_task_async(
            db=db,
            user_id=current_user.id,
            task_type="generate_strategy_chart",
            metadata=metadata,
        )
        await db.commit()

        logger.info(f"Chart generation task {task.id} created for user {current_user.email}")

        return {"task_id": str(task.id), "image_id": None, "cached": False}

    except Exception as e:
        logger.error(f"Error creating chart generation task: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create chart generation task: {str(e)}",
        )


@router.get("/chart/info/{image_id}")
async def get_strategy_chart_info(
    image_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str | None]:
    """
    Get strategy chart image info including r2_url.
    
    Returns image metadata including r2_url if available, allowing frontend
    to display images directly from R2 without backend download.
    
    Args:
        image_id: Generated image UUID
        current_user: Authenticated user (from JWT token)
        db: Database session
        
    Returns:
        Dictionary with r2_url if available, or None
        
    Raises:
        HTTPException: If image not found or doesn't belong to user
    """
    try:
        result = await db.execute(
            select(GeneratedImage).where(
                GeneratedImage.id == image_id,
                GeneratedImage.user_id == current_user.id,
            )
        )
        image = result.scalar_one_or_none()
        
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found",
            )
        
        # Return r2_url if available (with https:// prefix if missing)
        r2_url = None
        if image.r2_url:
            r2_url = image.r2_url
            if not r2_url.startswith("http://") and not r2_url.startswith("https://"):
                r2_url = f"https://{r2_url}"
        
        return {"r2_url": r2_url, "image_id": str(image.id)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching image info {image_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch image info",
        )


@router.get("/chart/by-hash/{strategy_hash}")
async def get_strategy_chart_by_hash(
    strategy_hash: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str | None]:
    """
    Get existing strategy chart image by strategy hash.
    
    This endpoint allows checking if a chart has already been generated
    for a specific strategy configuration, enabling image caching/reuse.
    
    Args:
        strategy_hash: SHA256 hash of the strategy (from calculate_strategy_hash)
        current_user: Authenticated user (from JWT token)
        db: Database session
        
    Returns:
        Dictionary with image_id if found, or {"image_id": None} if not found
        
    Raises:
        HTTPException: If hash format is invalid
    """
    # Validate hash format (SHA256 hex string should be 64 characters)
    if len(strategy_hash) != 64 or not all(c in "0123456789abcdef" for c in strategy_hash.lower()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid strategy hash format. Expected 64-character hex string.",
        )
    
    try:
        result = await db.execute(
            select(GeneratedImage).where(
                GeneratedImage.strategy_hash == strategy_hash.lower(),
                GeneratedImage.user_id == current_user.id,
            ).order_by(GeneratedImage.created_at.desc()).limit(1)
        )
        image = result.scalar_one_or_none()
        
        if image:
            logger.info(f"Found existing image for strategy hash {strategy_hash[:16]}...")
            # Return both image_id and r2_url if available (for direct display)
            result = {"image_id": str(image.id)}
            if image.r2_url:
                # Ensure r2_url has https:// prefix
                r2_url = image.r2_url
                if not r2_url.startswith("http://") and not r2_url.startswith("https://"):
                    r2_url = f"https://{r2_url}"
                result["r2_url"] = r2_url
            return result
        else:
            logger.debug(f"No existing image found for strategy hash {strategy_hash[:16]}...")
            return {"image_id": None}
            
    except Exception as e:
        logger.error(f"Error querying image by hash: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query image: {str(e)}",
        )


@router.get("/chart/{image_id}")
async def get_strategy_chart(
    image_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Get generated strategy chart image.

    If image is stored in R2, returns a redirect to the R2 URL (faster).
    Otherwise, returns the image as binary data from database.

    Args:
        image_id: Generated image UUID
        current_user: Authenticated user (from JWT token)
        db: Database session

    Returns:
        RedirectResponse to R2 URL if available, or binary image data

    Raises:
        HTTPException: If image not found or doesn't belong to user
    """
    try:
        result = await db.execute(
            select(GeneratedImage).where(
                GeneratedImage.id == image_id,
                GeneratedImage.user_id == current_user.id,
            )
        )
        image = result.scalar_one_or_none()

        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found",
            )

        # All images are now stored in R2, return redirect to R2 URL
        if not image.r2_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image R2 URL not found",
            )
        
        # Ensure r2_url has https:// prefix
        r2_url = image.r2_url
        if not r2_url.startswith("http://") and not r2_url.startswith("https://"):
            r2_url = f"https://{r2_url}"
        
        from fastapi.responses import RedirectResponse
        logger.info(f"Redirecting to R2 URL: {r2_url}")
        return RedirectResponse(url=r2_url, status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching image {image_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch image",
        )


@router.get("/chart/{image_id}/download")
async def download_strategy_chart(
    image_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Download generated strategy chart image as binary data.
    
    This endpoint proxies the image from R2 to avoid CORS issues when downloading.
    The image is fetched from R2 and returned as binary data with appropriate headers.

    Args:
        image_id: Generated image UUID
        current_user: Authenticated user (from JWT token)
        db: Database session

    Returns:
        Response with image binary data and Content-Disposition header for download

    Raises:
        HTTPException: If image not found or doesn't belong to user
    """
    try:
        result = await db.execute(
            select(GeneratedImage).where(
                GeneratedImage.id == image_id,
                GeneratedImage.user_id == current_user.id,
            )
        )
        image = result.scalar_one_or_none()

        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found",
            )

        if not image.r2_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image R2 URL not found",
            )
        
        # Extract object_key from r2_url
        # Format: https://assets.thetamind.ai/strategy_chart/{user_id}/{image_id}.{ext}
        # or: https://pub-xxx.r2.dev/strategy_chart/{user_id}/{image_id}.{ext}
        r2_url = image.r2_url
        if not r2_url.startswith("http://") and not r2_url.startswith("https://"):
            r2_url = f"https://{r2_url}"
        
        object_key = None
        if "/strategy_chart/" in r2_url:
            object_key = r2_url.split("/strategy_chart/", 1)[-1]
            object_key = f"strategy_chart/{object_key}"
        elif ".r2.dev/" in r2_url:
            object_key = r2_url.split(".r2.dev/", 1)[-1]
        else:
            # Fallback: try to extract path after domain
            from urllib.parse import urlparse
            parsed = urlparse(r2_url)
            if parsed.path.startswith("/"):
                object_key = parsed.path[1:]  # Remove leading slash
        
        if not object_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not extract object key from R2 URL",
            )
        
        # Download image from R2 using R2 service
        from app.services.storage.r2_service import get_r2_service
        r2_service = get_r2_service()
        
        if not r2_service.is_enabled():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="R2 storage is not enabled",
            )
        
        try:
            image_data = await r2_service.get_image(object_key)
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found in R2 storage",
            )
        except Exception as e:
            logger.error(f"Failed to download image from R2: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download image: {str(e)}",
            )
        
        # Determine content type from file extension
        content_type = "image/png"  # Default
        if object_key.endswith(".jpg") or object_key.endswith(".jpeg"):
            content_type = "image/jpeg"
        elif object_key.endswith(".gif"):
            content_type = "image/gif"
        elif object_key.endswith(".webp"):
            content_type = "image/webp"
        
        from fastapi.responses import Response
        return Response(
            content=image_data,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="ThetaMind_Strategy_Chart_{image_id}.png"',
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading image {image_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download image",
        )

