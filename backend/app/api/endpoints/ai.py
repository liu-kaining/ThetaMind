"""AI analysis API endpoints."""

import logging
from datetime import datetime, timezone, date
from io import BytesIO
from typing import Annotated, Any
from uuid import UUID

import pytz
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.schemas import AIReportResponse, DailyPickResponse, TaskResponse
from app.core.config import settings
from app.db.models import AIReport, DailyPick, GeneratedImage, Task, User
from app.db.session import AsyncSessionLocal, get_db
from app.services.ai_service import ai_service
from app.services.config_service import config_service
from app.services.report_pdf_service import PdfExportUnavailable, generate_report_pdf
from app.api.endpoints.tasks import create_task_async

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])

# AI report quota (per day, UTC reset).
# One run = 5 units. Free: 5/day (1 run). Pro Monthly: 40/day (8 runs). Pro Yearly: 100/day (20 runs).
#
FREE_AI_QUOTA = 5
FREE_IMAGE_QUOTA = 1
PRO_MONTHLY_AI_QUOTA = 40
PRO_MONTHLY_IMAGE_QUOTA = 10
PRO_YEARLY_AI_QUOTA = 100
PRO_YEARLY_IMAGE_QUOTA = 30


class AIModelInfo(BaseModel):
    """One entry in the list of available report models."""
    id: str
    provider: str
    label: str


class AIModelsResponse(BaseModel):
    """Response for GET /ai/models."""
    models: list[AIModelInfo]


@router.get("/models", response_model=AIModelsResponse)
async def list_report_models(
    _user: Annotated[User | None, Depends(get_current_user)] = None,
) -> AIModelsResponse:
    """
    List available AI models for report generation (from admin config or built-in list).
    User can pass preferred_model_id when creating a report/task to use a specific model.
    ZenMux models are included only when ZENMUX_API_KEY is configured (avoids quota on Google).
    """
    models = await ai_service.get_report_models()
    if not (getattr(settings, "zenmux_api_key", None) or "").strip():
        models = [m for m in models if m["provider"] != "zenmux"]
    return AIModelsResponse(
        models=[AIModelInfo(id=m["id"], provider=m["provider"], label=m["label"]) for m in models]
    )


class StrategyAnalysisRequest(BaseModel):
    """Strategy analysis request model."""

    strategy_summary: dict[str, Any] | None = Field(None, description="Complete strategy summary (preferred format)")
    # Legacy format (for backward compatibility)
    strategy_data: dict[str, Any] | None = Field(None, description="Strategy configuration (legs, strikes, etc.)")
    option_chain: dict[str, Any] | None = Field(None, description="Option chain data for the underlying asset")
    
    # Multi-agent framework support
    use_multi_agent: bool = Field(
        False,
        description="Whether to use multi-agent framework for comprehensive analysis (default: false for backward compatibility). "
        "Multi-agent mode uses 5 specialized agents and consumes 5x API quota."
    )
    agent_config: dict[str, Any] | None = Field(
        None,
        description="Optional agent configuration (timeout, retry, etc.)"
    )
    
    # Async processing support
    async_mode: bool = Field(
        False,
        description="Whether to process asynchronously using Task system (default: false for immediate response). "
        "When true, returns task_id immediately and result can be polled via /api/v1/tasks/{task_id}"
    )
    # Optional: preferred AI model for this report (from GET /ai/models). Uses default if not set.
    preferred_model_id: str | None = Field(
        None,
        description="Optional model id (e.g. gemini-2.5-pro or google/gemini-2.5-pro). See GET /ai/models."
    )


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


async def check_ai_quota(user: User, db: AsyncSession, required_quota: int = 1) -> None:
    """
    Check if user has remaining AI report quota.
    Automatically resets quota if date has changed.

    Units: 1 = simple (single-agent) report, 5 = Deep Research (multi-agent).
    Free users: 5 units/day = 1 run (any type). Pro: 10 (monthly) or 30 (yearly) units/day.

    Raises:
        HTTPException: If quota exceeded (429 Too Many Requests)
    """
    # Check and reset quota if date changed
    await check_and_reset_quota_if_needed(user, db)
    
    quota_limit = get_ai_quota_limit(user)

    if user.daily_ai_usage + required_quota > quota_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily AI report quota insufficient. Limit: {quota_limit} reports per day. "
            f"Current usage: {user.daily_ai_usage}, Required: {required_quota}, "
            f"Available: {quota_limit - user.daily_ai_usage}",
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


async def increment_ai_usage(user: User, db: AsyncSession, quota_units: int = 1) -> None:
    """
    Increment user's daily AI report usage counter.
    Automatically resets quota if date has changed.

    Args:
        user: User model instance
        db: Database session
        quota_units: Number of quota units to increment (1 for single-agent, 5 for multi-agent)
    """
    # Check and reset quota if date changed
    await check_and_reset_quota_if_needed(user, db)
    
    stmt = (
        update(User)
        .where(User.id == user.id)
        .values(daily_ai_usage=User.daily_ai_usage + quota_units)
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


@router.post("/report", response_model=AIReportResponse | TaskResponse, status_code=status.HTTP_201_CREATED)
async def generate_ai_report(
    request: StrategyAnalysisRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIReportResponse | TaskResponse:
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
    # Step 1: Check if async mode is requested
    if request.async_mode:
        # Create async task and return immediately
        from app.api.endpoints.tasks import create_task_async
        from app.api.schemas import TaskResponse
        
        # Determine task type
        use_multi_agent = request.use_multi_agent
        task_type = "multi_agent_report" if use_multi_agent else "ai_report"
        
        # Prepare metadata
        task_metadata = {}
        if request.strategy_summary:
            task_metadata["strategy_summary"] = request.strategy_summary
            task_metadata["use_multi_agent"] = use_multi_agent
            if request.option_chain:
                task_metadata["option_chain"] = request.option_chain
        elif request.strategy_data and request.option_chain:
            task_metadata["strategy_data"] = request.strategy_data
            task_metadata["option_chain"] = request.option_chain
            task_metadata["use_multi_agent"] = False  # Legacy format doesn't support multi-agent
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either strategy_summary or (strategy_data + option_chain) must be provided",
            )
        
        if request.agent_config:
            task_metadata["agent_config"] = request.agent_config
        if request.preferred_model_id:
            task_metadata["preferred_model_id"] = request.preferred_model_id.strip()
        
        # One run = 5 units (unified). No separate "simple report" in UI; fallback still counts as one run.
        required_quota = 5
        try:
            await check_ai_quota(current_user, db, required_quota=required_quota)
        except HTTPException as e:
            if use_multi_agent and e.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                logger.warning(
                    f"Quota insufficient for multi-agent async mode, falling back to single-agent"
                )
                use_multi_agent = False
                required_quota = 5  # One run = 5 units (fallback still counts as one run)
                task_type = "ai_report"
                task_metadata["use_multi_agent"] = False
                await check_ai_quota(current_user, db, required_quota=required_quota)
            else:
                raise
        
        # Create task
        task = await create_task_async(
            db=db,
            user_id=current_user.id,
            task_type=task_type,
            metadata=task_metadata,
        )
        await db.commit()
        
        logger.info(
            f"Created async task {task.id} for user {current_user.email} "
            f"(type: {task_type}, quota: {required_quota})"
        )
        
        # Return task response (not report response)
        return TaskResponse(
            id=str(task.id),
            task_type=task.task_type,
            status=task.status,
            result_ref=task.result_ref,
            error_message=task.error_message,
            metadata=task.task_metadata,
            execution_history=task.execution_history,
            prompt_used=task.prompt_used,
            model_used=task.model_used,
            started_at=task.started_at,
            retry_count=task.retry_count,
            created_at=task.created_at,
            updated_at=task.updated_at,
            completed_at=task.completed_at,
        )
    
    # Step 2: Synchronous mode (existing logic)
    # Determine quota requirements and check
    use_multi_agent = request.use_multi_agent
    required_quota = 5 if use_multi_agent else 1
    
    # Check quota (with required units)
    try:
        await check_ai_quota(current_user, db, required_quota=required_quota)
    except HTTPException as e:
        # If quota insufficient for multi-agent, try to fallback to single-agent
        if use_multi_agent and e.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            logger.warning(
                f"Quota insufficient for multi-agent mode (required: {required_quota}), "
                f"falling back to single-agent mode for user {current_user.email}"
            )
            use_multi_agent = False
            required_quota = 1
            # Re-check quota for single-agent mode
            await check_ai_quota(current_user, db, required_quota=required_quota)
        else:
            raise

    try:
        # Step 2: Generate report using AI service
        mode_str = "multi-agent" if use_multi_agent else "single-agent"
        logger.info(
            f"Generating AI report ({mode_str} mode) for user {current_user.email}. "
            f"Required quota: {required_quota}"
        )
        
        # Prepare metadata for response
        response_metadata: dict[str, Any] = {
            "mode": mode_str,
            "quota_used": required_quota,
        }
        
        # Use strategy_summary if available, otherwise use legacy format
        if request.strategy_summary:
            if use_multi_agent:
                # Multi-agent mode (returns dict with report_text and agent_summaries)
                phase_a_result = await ai_service.generate_report_with_agents(
                    strategy_summary=request.strategy_summary,
                    use_multi_agent=True,
                    option_chain=request.option_chain,
                )
                report_content = (
                    phase_a_result["report_text"]
                    if isinstance(phase_a_result, dict)
                    else phase_a_result
                )
                # Extract agent metadata if available (from coordinator result)
                # Note: This would require modifying _format_agent_report to return metadata
                response_metadata["agents_used"] = [
                    "options_greeks_analyst",
                    "iv_environment_analyst",
                    "market_context_analyst",
                    "risk_scenario_analyst",
                    "options_synthesis_agent",
                ]
            else:
                # Single-agent mode (existing behavior)
                report_content = await ai_service.generate_report(
                    strategy_summary=request.strategy_summary,
                    option_chain=request.option_chain,
                )
        elif request.strategy_data and request.option_chain:
            # Legacy format (backward compatibility) - only supports single-agent
            if use_multi_agent:
                logger.warning(
                    "Multi-agent mode requires strategy_summary format. "
                    "Falling back to single-agent mode for legacy format."
                )
                use_multi_agent = False
                required_quota = 1
                response_metadata["mode"] = "single-agent"
                response_metadata["fallback_reason"] = "Legacy format does not support multi-agent mode"
            
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

        # Step 4: Increment usage counter (with quota units)
        await increment_ai_usage(current_user, db, quota_units=required_quota)

        quota_limit = get_ai_quota_limit(current_user)
        logger.info(
            f"AI report generated successfully ({mode_str} mode) for user {current_user.email}. "
            f"Quota used: {required_quota}, Usage: {current_user.daily_ai_usage}/{quota_limit}"
        )

        return AIReportResponse(
            id=str(ai_report.id),
            report_content=ai_report.report_content,
            model_used=ai_report.model_used,
            created_at=ai_report.created_at,
            metadata=response_metadata,
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
    When ENABLE_DAILY_PICKS is False, returns empty content (feature disabled).

    Args:
        date: Optional date in YYYY-MM-DD format (defaults to today EST)
        current_user: Optional authenticated user (for future filtering)

    Returns:
        DailyPickResponse with strategy picks for the date

    Raises:
        HTTPException: If picks not found for the date
    """
    from datetime import date as date_type

    # Feature flag: DB (Admin Settings) first, then env — same source as GET /config/features
    enabled = await config_service.get_bool("enable_daily_picks", settings.enable_daily_picks)
    if not enabled:
        EST = pytz.timezone("US/Eastern")
        today_est = datetime.now(EST).date()
        return DailyPickResponse(
            date=today_est.isoformat(),
            content_json=[],
            created_at=datetime.now(timezone.utc),
        )

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
                # Return 200 with empty content so frontend can show "No daily picks available yet"
                return DailyPickResponse(
                    date=target_date.isoformat(),
                    content_json=[],
                    created_at=datetime.now(timezone.utc),
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
        if not reports:
            return []

        report_ids = [str(r.id) for r in reports]
        task_result = await db.execute(
            select(Task).where(
                Task.user_id == current_user.id,
                Task.result_ref.in_(report_ids),
            )
        )
        tasks = task_result.scalars().all()
        symbol_by_result_ref: dict[str, str] = {}
        for t in tasks:
            if not t.result_ref:
                continue
            meta = t.task_metadata or {}
            ss = meta.get("strategy_summary") or {}
            sd = meta.get("strategy_data") or {}
            symbol = (
                (ss.get("symbol") if isinstance(ss, dict) else None)
                or (sd.get("symbol") if isinstance(sd, dict) else None)
                or meta.get("symbol")
            )
            if symbol and isinstance(symbol, str) and symbol.strip():
                symbol_by_result_ref[t.result_ref.strip()] = symbol.strip().upper()

        return [
            AIReportResponse(
                id=str(report.id),
                report_content=report.report_content,
                model_used=report.model_used or "",
                created_at=report.created_at,
                symbol=symbol_by_result_ref.get(str(report.id)),
            )
            for report in reports
        ]

    except Exception as e:
        logger.error(f"Error fetching user reports: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch reports",
        )


@router.get("/reports/{report_id}", response_model=AIReportResponse)
async def get_report(
    report_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIReportResponse:
    """Get a single AI report by ID for the authenticated user."""
    try:
        result = await db.execute(
            select(AIReport).where(
                AIReport.id == report_id,
                AIReport.user_id == current_user.id,
            )
        )
        report = result.scalar_one_or_none()
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found",
            )
        symbol: str | None = None
        task_result = await db.execute(
            select(Task).where(
                Task.user_id == current_user.id,
                Task.result_ref == str(report_id),
            )
        )
        task = task_result.scalar_one_or_none()
        if task and task.task_metadata:
            meta = task.task_metadata
            ss = meta.get("strategy_summary") or {}
            sd = meta.get("strategy_data") or {}
            sym = (
                (ss.get("symbol") if isinstance(ss, dict) else None)
                or (sd.get("symbol") if isinstance(sd, dict) else None)
                or meta.get("symbol")
            )
            if sym and isinstance(sym, str) and sym.strip():
                symbol = sym.strip().upper()
        return AIReportResponse(
            id=str(report.id),
            report_content=report.report_content,
            model_used=report.model_used or "",
            created_at=report.created_at,
            metadata=None,
            symbol=symbol,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching report {report_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch report",
        )


@router.get("/reports/{report_id}/pdf")
async def get_report_pdf(
    report_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Export a single AI report as PDF (EC-style, server-side Playwright)."""
    try:
        result = await db.execute(
            select(AIReport).where(
                AIReport.id == report_id,
                AIReport.user_id == current_user.id,
            )
        )
        report = result.scalar_one_or_none()
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report not found",
            )
        dt = report.created_at
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        created_at_str = dt.astimezone(pytz.timezone("US/Eastern")).strftime("%Y-%m-%d %H:%M %Z")
        pdf_bytes = await generate_report_pdf(
            report.report_content or "",
            report.model_used or "N/A",
            created_at_str,
        )
        filename = f"thetamind-report-{report_id}.pdf"
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except PdfExportUnavailable as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(e.args[0]) if e.args else "PDF export is temporarily unavailable.",
        )
    except Exception as e:
        logger.error(f"Error generating PDF for report {report_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report PDF",
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
            if request.option_chain:
                metadata["option_chain"] = request.option_chain
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


# ========== Multi-Agent Framework Endpoints ==========

@router.post("/report/multi-agent", response_model=AIReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_multi_agent_report(
    request: StrategyAnalysisRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIReportResponse:
    """
    Generate AI analysis report using multi-agent framework (dedicated endpoint).
    
    This endpoint is specifically designed for multi-agent analysis.
    It always uses multi-agent mode (equivalent to use_multi_agent=true).
    
    Args:
        request: Strategy analysis request (must include strategy_summary)
        current_user: Authenticated user
        db: Database session
        
    Returns:
        AIReportResponse with multi-agent analysis report
        
    Raises:
        HTTPException: If quota exceeded or AI service fails
    """
    # Force multi-agent mode
    request.use_multi_agent = True
    
    # Use the existing endpoint logic
    return await generate_ai_report(request, current_user, db)


class StockScreeningRequest(BaseModel):
    """Stock screening request model."""
    
    query: str | None = Field(None, description="Natural language query for screening (e.g., 'find me high volatility tech stocks')")
    sector: str | None = Field(None, description="Sector filter (e.g., 'Technology')")
    industry: str | None = Field(None, description="Industry filter")
    market_cap: str | None = Field(None, description="Market cap filter (e.g., 'Large Cap')")
    country: str | None = Field(None, description="Country filter (e.g., 'United States')")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of candidates to analyze")
    min_score: float | None = Field(None, ge=0.0, le=10.0, description="Minimum composite score threshold")
    async_mode: bool = Field(
        False,
        description="Whether to process asynchronously using Task system (default: false). "
        "When true, returns task_id immediately and result can be polled via /api/v1/tasks/{task_id}"
    )


class StockScreeningResponse(BaseModel):
    """Stock screening response model."""
    
    candidates: list[dict[str, Any]] = Field(..., description="List of ranked stock candidates")
    total_found: int = Field(..., description="Total stocks found matching criteria")
    filtered_count: int = Field(..., description="Number of candidates after filtering")
    execution_time_ms: int = Field(..., description="Total execution time in milliseconds")
    metadata: dict[str, Any] = Field(..., description="Execution metadata")


@router.post("/workflows/stock-screening", response_model=StockScreeningResponse | TaskResponse, status_code=status.HTTP_200_OK)
async def screen_stocks(
    request: StockScreeningRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StockScreeningResponse | TaskResponse:
    """
    Screen and rank stocks using multi-agent framework.
    
    Workflow:
    1. Phase 1: Initial screening (using MarketDataService)
    2. Phase 2: Parallel analysis of candidates (fundamental + technical)
    3. Phase 3: Ranking and recommendation
    
    Args:
        request: Stock screening criteria
        current_user: Authenticated user
        db: Database session
        
    Returns:
        StockScreeningResponse with ranked candidates
        
    Raises:
        HTTPException: If screening fails
    """
    import json
    import re
    
    # Process natural language query if provided
    if request.query:
        try:
            logger.info(f"Parsing natural language screening query: '{request.query}'")
            prompt = f"""You are a Stock Screening AI Assistant. Convert the user's natural language query into structured screening criteria.

User query: "{request.query}"

Extract the parameters into a valid JSON object. 
Only use the following keys if they are explicitly mentioned or strongly implied by the user. If not mentioned, set them to null.
- "sector": str (e.g., "Technology", "Healthcare", "Financial Services")
- "industry": str
- "market_cap": str (must be exactly one of: "Mega Cap", "Large Cap", "Mid Cap", "Small Cap", "Micro Cap", "Nano Cap")
- "country": str (default to "United States" if not specified)
- "limit": int (max 50)

Return ONLY valid JSON.
"""
            provider = ai_service._get_provider()
            response_text = await provider.generate_text_response(prompt, json_mode=True) if hasattr(provider, '_call_vertex_generate_content') else await provider.generate_text_response(prompt)
            
            cleaned = re.sub(r"```json\s*|\s*```", "", response_text).strip()
            parsed = json.loads(cleaned)
            
            if parsed.get("sector") is not None: request.sector = parsed["sector"]
            if parsed.get("industry") is not None: request.industry = parsed["industry"]
            if parsed.get("market_cap") is not None: request.market_cap = parsed["market_cap"]
            if parsed.get("country") is not None: request.country = parsed["country"]
            if parsed.get("limit") is not None: request.limit = int(parsed["limit"])
            
            logger.info(f"Parsed NL query into criteria: {parsed}")
        except Exception as e:
            logger.warning(f"Failed to parse NL query '{request.query}': {e}", exc_info=True)
            # Proceed with whatever other structured criteria were provided
            
    # Check if async mode is requested
    if request.async_mode:
        # Create async task and return immediately
        from app.api.endpoints.tasks import create_task_async
        
        # Prepare criteria
        criteria = {
            "sector": request.sector,
            "industry": request.industry,
            "market_cap": request.market_cap,
            "country": request.country,
            "limit": request.limit,
        }
        
        # Check quota before creating task
        estimated_quota = min(5, 2 + (request.limit * 2) // 10)
        await check_ai_quota(current_user, db, required_quota=estimated_quota)
        
        # Prepare metadata
        task_metadata = {
            "criteria": criteria,
            "min_score": request.min_score,
        }
        
        # Create task
        task = await create_task_async(
            db=db,
            user_id=current_user.id,
            task_type="stock_screening_workflow",
            metadata=task_metadata,
        )
        await db.commit()
        
        logger.info(
            f"Created async stock screening task {task.id} for user {current_user.email}"
        )
        
        return TaskResponse(
            id=str(task.id),
            task_type=task.task_type,
            status=task.status,
            result_ref=task.result_ref,
            error_message=task.error_message,
            metadata=task.task_metadata,
            execution_history=task.execution_history,
            prompt_used=task.prompt_used,
            model_used=task.model_used,
            started_at=task.started_at,
            retry_count=task.retry_count,
            created_at=task.created_at,
            updated_at=task.updated_at,
            completed_at=task.completed_at,
        )
    
    # Synchronous mode (existing logic)
    import time
    start_time = time.time()
    
    try:
        # Prepare criteria
        criteria = {
            "sector": request.sector,
            "industry": request.industry,
            "market_cap": request.market_cap,
            "country": request.country,
            "limit": request.limit,
        }
        
        # Check quota (stock screening uses multiple agents, estimate 3-5 quota units)
        # Each candidate analysis uses 2 agents (fundamental + technical)
        # Plus 1 for screening agent, 1 for ranking agent
        estimated_quota = min(5, 2 + (request.limit * 2) // 10)  # Cap at 5 for now
        await check_ai_quota(current_user, db, required_quota=estimated_quota)
        
        logger.info(
            f"Starting stock screening for user {current_user.email}. "
            f"Criteria: {criteria}, Estimated quota: {estimated_quota}"
        )
        
        # Execute stock screening workflow
        coordinator = ai_service.agent_coordinator
        if not coordinator:
            logger.error("Agent framework is not available for stock screening")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Agent framework is not available. Please try again later.",
            )
        
        try:
            candidates = await coordinator.coordinate_stock_screening(criteria)
        except Exception as e:
            logger.error(
                f"Stock screening workflow failed: {e}",
                exc_info=True,
                extra={
                    "user_id": str(current_user.id),
                    "criteria": criteria,
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Stock screening failed: {str(e)}",
            )
        
        # Filter by min_score if provided
        if request.min_score is not None:
            candidates = [
                c for c in candidates
                if c.get("composite_score", 0.0) >= request.min_score
            ]
        
        # Extract metadata
        total_found = len(candidates)
        filtered_count = len(candidates)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Increment usage (use actual quota consumed)
        await increment_ai_usage(current_user, db, quota_units=estimated_quota)
        
        logger.info(
            f"Stock screening completed for user {current_user.email}. "
            f"Found {filtered_count} candidates in {execution_time_ms}ms"
        )
        
        return StockScreeningResponse(
            candidates=candidates,
            total_found=total_found,
            filtered_count=filtered_count,
            execution_time_ms=execution_time_ms,
            metadata={
                "mode": "multi-agent",
                "quota_used": estimated_quota,
                "criteria": criteria,
            },
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in stock screening: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to screen stocks: {str(e)}",
        )


class OptionsAnalysisWorkflowRequest(BaseModel):
    """Options analysis workflow request model."""
    
    strategy_summary: dict[str, Any] = Field(..., description="Complete strategy summary")
    option_chain: dict[str, Any] | None = Field(
        None,
        description="Full option chain data (recommended for deeper analysis)",
    )
    include_metadata: bool = Field(True, description="Whether to include detailed metadata in response")
    async_mode: bool = Field(
        False,
        description="Whether to process asynchronously using Task system (default: false). "
        "When true, returns task_id immediately and result can be polled via /api/v1/tasks/{task_id}"
    )


class OptionsAnalysisWorkflowResponse(BaseModel):
    """Options analysis workflow response model."""
    
    report: str = Field(..., description="Markdown-formatted comprehensive report")
    parallel_analysis: dict[str, Any] = Field(..., description="Results from parallel agents")
    risk_analysis: dict[str, Any] | None = Field(None, description="Risk scenario analysis results")
    synthesis: dict[str, Any] | None = Field(None, description="Synthesis agent results")
    execution_time_ms: int = Field(..., description="Total execution time in milliseconds")
    metadata: dict[str, Any] = Field(..., description="Execution metadata")


@router.post("/workflows/options-analysis", response_model=OptionsAnalysisWorkflowResponse | TaskResponse, status_code=status.HTTP_200_OK)
async def analyze_options_workflow(
    request: OptionsAnalysisWorkflowRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OptionsAnalysisWorkflowResponse | TaskResponse:
    """
    Analyze options strategy using multi-agent workflow (dedicated endpoint).
    
    This endpoint provides detailed workflow results including intermediate agent outputs.
    
    Workflow:
    1. Phase 1 (Parallel): Greeks analysis, IV analysis, Market context analysis
    2. Phase 2 (Sequential): Risk analysis (depends on Phase 1 results)
    3. Phase 3 (Sequential): Synthesis (combines all results)
    
    Args:
        request: Options analysis request with strategy_summary
        current_user: Authenticated user
        db: Database session
        
    Returns:
        OptionsAnalysisWorkflowResponse with detailed workflow results
        
    Raises:
        HTTPException: If quota exceeded or analysis fails
    """
    # Check if async mode is requested
    if request.async_mode:
        # Create async task and return immediately
        from app.api.endpoints.tasks import create_task_async
        
        # Check quota before creating task
        await check_ai_quota(current_user, db, required_quota=5)
        
        # Prepare metadata
        task_metadata = {
            "strategy_summary": request.strategy_summary,
            "include_metadata": request.include_metadata,
        }
        if request.option_chain:
            task_metadata["option_chain"] = request.option_chain
        
        # Create task
        task = await create_task_async(
            db=db,
            user_id=current_user.id,
            task_type="options_analysis_workflow",
            metadata=task_metadata,
        )
        await db.commit()
        
        logger.info(
            f"Created async options analysis workflow task {task.id} for user {current_user.email}"
        )
        
        return TaskResponse(
            id=str(task.id),
            task_type=task.task_type,
            status=task.status,
            result_ref=task.result_ref,
            error_message=task.error_message,
            metadata=task.task_metadata,
            execution_history=task.execution_history,
            prompt_used=task.prompt_used,
            model_used=task.model_used,
            started_at=task.started_at,
            retry_count=task.retry_count,
            created_at=task.created_at,
            updated_at=task.updated_at,
            completed_at=task.completed_at,
        )
    
    # Synchronous mode (existing logic)
    import time
    start_time = time.time()
    
    try:
        # Check quota (multi-agent uses 5 quota units)
        await check_ai_quota(current_user, db, required_quota=5)
        
        logger.info(
            f"Starting options analysis workflow for user {current_user.email}"
        )
        
        # Execute options analysis workflow
        coordinator = ai_service.agent_coordinator
        if not coordinator:
            logger.error("Agent framework is not available for options analysis")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Agent framework is not available. Please try again later.",
            )
        
        try:
            result = await coordinator.coordinate_options_analysis(
                request.strategy_summary,
                option_chain=request.option_chain,
            )
        except Exception as e:
            logger.error(
                f"Options analysis workflow failed: {e}",
                exc_info=True,
                extra={
                    "user_id": str(current_user.id),
                    "symbol": request.strategy_summary.get("symbol", "unknown"),
                }
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Options analysis failed: {str(e)}",
            )
        
        # Format report
        report = ai_service._format_agent_report(result)
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Increment usage
        await increment_ai_usage(current_user, db, quota_units=5)
        
        logger.info(
            f"Options analysis workflow completed for user {current_user.email} "
            f"in {execution_time_ms}ms"
        )
        
        # Prepare metadata
        metadata = {
            "mode": "multi-agent",
            "quota_used": 5,
            "total_agents": result.get("metadata", {}).get("total_agents", 5),
            "successful_agents": result.get("metadata", {}).get("successful_agents", 0),
        }
        
        return OptionsAnalysisWorkflowResponse(
            report=report,
            parallel_analysis=result.get("parallel_analysis", {}),
            risk_analysis=result.get("risk_analysis"),
            synthesis=result.get("synthesis"),
            execution_time_ms=execution_time_ms,
            metadata=metadata if request.include_metadata else {},
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in options analysis workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze options strategy: {str(e)}",
        )


class AgentInfo(BaseModel):
    """Agent information model."""
    
    name: str = Field(..., description="Agent name")
    type: str = Field(..., description="Agent type")
    description: str | None = Field(None, description="Agent description")


class AgentListResponse(BaseModel):
    """Agent list response model."""
    
    agents: list[AgentInfo] = Field(..., description="List of available agents")
    total_count: int = Field(..., description="Total number of agents")


@router.get("/agents/list", response_model=AgentListResponse, status_code=status.HTTP_200_OK)
async def list_agents(
    current_user: Annotated[User, Depends(get_current_user)],
    agent_type: Annotated[str | None, Query(description="Filter by agent type")] = None,
) -> AgentListResponse:
    """
    List all available agents in the system.
    
    Args:
        current_user: Authenticated user
        agent_type: Optional filter by agent type (e.g., 'options_analysis')
        
    Returns:
        AgentListResponse with list of agents
    """
    try:
        from app.services.agents.registry import AgentRegistry
        from app.services.agents.base import AgentType
        
        # Get all registered agents
        all_agents = []
        
        if agent_type:
            # Filter by type
            try:
                agent_type_enum = AgentType(agent_type)
                agent_names = AgentRegistry.list_agents_by_type(agent_type_enum)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid agent type: {agent_type}. Valid types: {[e.value for e in AgentType]}",
                )
        else:
            # Get all agents from all types
            agent_names = []
            for agent_type_enum in AgentType:
                agent_names.extend(AgentRegistry.list_agents_by_type(agent_type_enum))
        
        # Build agent info list
        for agent_name in agent_names:
            try:
                agent_class = AgentRegistry.get_agent_class(agent_name)
                agent_info = AgentInfo(
                    name=agent_name,
                    type=agent_class.agent_type.value if hasattr(agent_class, 'agent_type') else "unknown",
                    description=getattr(agent_class, '__doc__', None),
                )
                all_agents.append(agent_info)
            except Exception as e:
                logger.warning(f"Failed to get info for agent {agent_name}: {e}")
                continue
        
        return AgentListResponse(
            agents=all_agents,
            total_count=len(all_agents),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing agents: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list agents: {str(e)}",
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

