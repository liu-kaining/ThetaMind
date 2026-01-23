"""Task management API endpoints."""

import asyncio
import base64
import json
import logging
import uuid
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
    user_id: UUID | None,
    task_type: str,
    metadata: dict[str, Any] | None = None,
) -> Task:
    """
    Create a new task and start processing it asynchronously.

    Args:
        db: Database session
        user_id: User UUID (None for system tasks)
        task_type: Task type (e.g., 'ai_report', 'daily_picks')
        metadata: Optional task metadata

    Returns:
        Created Task instance
    """
    task = Task(
        user_id=user_id,
        task_type=task_type,
        status="PENDING",
        task_metadata=metadata,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)

    # Start background processing with error handling
    async def safe_process_task() -> None:
        """Wrapper to safely process task with error handling."""
        try:
            logger.info(f"Starting background processing for task {task.id} (type: {task_type})")
            await process_task_async(task.id, task_type, metadata, db)
            logger.info(f"Background task {task.id} completed successfully")
        except Exception as e:
            logger.error(f"Background task {task.id} failed to start processing: {e}", exc_info=True)
            # Try to update task status to FAILED if possible
            try:
                from app.db.session import AsyncSessionLocal
                async with AsyncSessionLocal() as error_session:
                    result = await error_session.execute(select(Task).where(Task.id == task.id))
                    error_task = result.scalar_one_or_none()
                    if error_task and error_task.status == "PENDING":
                        error_task.status = "FAILED"
                        error_task.error_message = f"Task failed to start: {str(e)}"
                        error_task.updated_at = datetime.now(timezone.utc)
                        await error_session.commit()
                        logger.info(f"Updated task {task.id} status to FAILED due to startup error")
                    elif error_task:
                        logger.info(f"Task {task.id} status is already {error_task.status}, not updating")
            except Exception as update_error:
                logger.error(f"Failed to update task {task.id} status after startup error: {update_error}", exc_info=True)
    
    # Create and schedule the background task
    try:
        loop = asyncio.get_running_loop()
        background_task = loop.create_task(safe_process_task())
        # Add done callback to log if task completes (or fails)
        def log_task_completion(async_task: asyncio.Task) -> None:
            try:
                async_task.result()  # This will raise if task failed
                logger.debug(f"Background task {task.id} completed successfully")
            except Exception as e:
                # Error already logged in safe_process_task
                logger.debug(f"Background task {task.id} failed: {e}")
        background_task.add_done_callback(log_task_completion)
        logger.info(f"Background task {task.id} scheduled for processing")
    except RuntimeError:
        # No running event loop (shouldn't happen in FastAPI context)
        logger.error(f"No running event loop to schedule task {task.id}")
        # Update task status directly
        task.status = "FAILED"
        task.error_message = "No event loop available to process task"
        task.updated_at = datetime.now(timezone.utc)

    return task


def _calculate_strategy_metrics(
    strategy_data: dict[str, Any],
    option_chain: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Calculate strategy metrics for image generation prompt.
    
    Args:
        strategy_data: Strategy configuration with legs
        option_chain: Optional option chain data for validation
        
    Returns:
        Dictionary with metrics: net_cash_flow, margin, breakeven, max_profit, max_loss
    """
    legs = strategy_data.get("legs", [])
    
    # Calculate net cash flow
    net_cash_flow = 0.0
    for leg in legs:
        premium = float(leg.get("premium", 0))
        quantity = int(leg.get("quantity", 1))
        action = leg.get("action", "buy")
        multiplier = -1 if action == "buy" else 1
        net_cash_flow += premium * quantity * multiplier
    
    # Estimate margin (simplified: use max loss for spreads, or 20% of notional for naked)
    # This is a simplified calculation - real margin depends on broker rules
    spot_price = strategy_data.get("current_price", 0) or (
        option_chain.get("spot_price") if option_chain else 0
    )
    
    margin = 0.0
    if legs:
        # For multi-leg spreads, margin is typically the max loss
        # For naked positions, it's a percentage of notional
        has_naked = False
        max_strike = max((float(leg.get("strike", 0)) for leg in legs), default=0)
        
        # Check if strategy has naked legs
        buy_count = sum(1 for leg in legs if leg.get("action") == "buy")
        sell_count = sum(1 for leg in legs if leg.get("action") == "sell")
        
        if sell_count > buy_count:
            # Has naked positions
            margin = max_strike * 100 * 0.20  # 20% of notional (simplified)
            has_naked = True
        
        # If it's a spread, margin is the spread width
        if not has_naked and len(legs) >= 2:
            strikes = [float(leg.get("strike", 0)) for leg in legs]
            max_strike_val = max(strikes)
            min_strike_val = min(strikes)
            margin = (max_strike_val - min_strike_val) * 100
    
    # Calculate max profit and max loss from payoff at expiration
    # This is a simplified calculation
    max_profit = 0.0
    max_loss = 0.0
    breakeven = 0.0
    
    # Simplified: For credit spreads, max profit = net credit, max loss = spread width - credit
    # For debit spreads, max profit = spread width - debit, max loss = debit
    if net_cash_flow > 0:
        # Credit strategy
        if len(legs) >= 2:
            strikes = [float(leg.get("strike", 0)) for leg in legs]
            spread_width = (max(strikes) - min(strikes)) * 100
            max_profit = net_cash_flow
            max_loss = spread_width - net_cash_flow
            # Breakeven: short strike + credit (for calls) or short strike - credit (for puts)
            # Simplified: use average of strikes
            avg_strike = sum(strikes) / len(strikes)
            breakeven = avg_strike + (net_cash_flow / 100) if legs[0].get("type") == "call" else avg_strike - (net_cash_flow / 100)
    else:
        # Debit strategy
        if len(legs) >= 2:
            strikes = [float(leg.get("strike", 0)) for leg in legs]
            spread_width = (max(strikes) - min(strikes)) * 100
            max_profit = spread_width + net_cash_flow  # net_cash_flow is negative
            max_loss = abs(net_cash_flow)
            # Breakeven: long strike + debit
            buy_legs = [leg for leg in legs if leg.get("action") == "buy"]
            if buy_legs:
                buy_strike = float(buy_legs[0].get("strike", 0))
                breakeven = buy_strike + abs(net_cash_flow / 100)
    
    return {
        "net_cash_flow": round(net_cash_flow, 2),
        "margin": round(margin, 2),
        "breakeven": round(breakeven, 2),
        "max_profit": round(max_profit, 2),
        "max_loss": round(max_loss, 2),
    }


def _add_execution_event(
    history: list[dict[str, Any]] | None,
    event_type: str,
    message: str,
    timestamp: datetime | None = None,
) -> list[dict[str, Any]]:
    """Add an event to execution history."""
    if history is None:
        history = []
    history.append({
        "type": event_type,  # "start", "success", "error", "retry"
        "message": message,
        "timestamp": (timestamp or datetime.now(timezone.utc)).isoformat(),
    })
    return history


async def process_task_async(
    task_id: UUID,
    task_type: str,
    metadata: dict[str, Any] | None,
    db: AsyncSession,
) -> None:
    """
    Process a task asynchronously in the background with retry support.

    Args:
        task_id: Task UUID
        task_type: Task type
        metadata: Task metadata
        db: Database session (will create a new session for processing - this param is not used directly)
    
    Note:
        This function creates its own database session for processing.
        The db parameter is kept for backward compatibility but not used.
    """
    from app.db.session import AsyncSessionLocal
    from app.services.ai_service import ai_service
    from app.core.config import settings
    from app.services.config_service import config_service

    MAX_RETRIES = 3

    async with AsyncSessionLocal() as session:
        try:
            logger.info(f"process_task_async: Starting processing for task {task_id} (type: {task_type})")
            # Get task and initialize execution history
            result = await session.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one_or_none()
            if not task:
                logger.error(f"Task {task_id} not found in database")
                return

            logger.info(f"Task {task_id} found, current status: {task.status}")

            # Check if task is already in a final state (SUCCESS or FAILED)
            if task.status in ["SUCCESS", "FAILED"]:
                logger.info(f"Task {task_id} already in final state: {task.status}, skipping")
                return

            # Initialize execution history if not exists
            if task.execution_history is None:
                task.execution_history = []
            
            # Merge metadata from parameter and task.task_metadata (task_metadata is source of truth after task creation)
            # Priority: task.task_metadata > metadata (from parameter)
            if metadata is None:
                metadata = task.task_metadata or {}
            elif task.task_metadata:
                # Merge: task_metadata takes precedence (may have been updated)
                merged_metadata = {**(metadata or {}), **task.task_metadata}
                metadata = merged_metadata
            
            # Record start time and update status to PROCESSING
            started_at = datetime.now(timezone.utc)
            task.started_at = started_at
            task.status = "PROCESSING"
            task.updated_at = started_at
            task.execution_history = _add_execution_event(
                task.execution_history, "start", "Task processing started", started_at
            )
            await session.commit()
            await session.refresh(task)
            
            logger.info(f"Task {task_id} status updated to PROCESSING")

            # Process based on task type
            if task_type == "ai_report":
                # Import here to avoid circular imports
                strategy_summary = metadata.get("strategy_summary") if metadata else None
                
                # Support legacy format (strategy_data + option_chain) for backward compatibility
                if not strategy_summary:
                    strategy_data = metadata.get("strategy_data") if metadata else None
                    option_chain = metadata.get("option_chain") if metadata else None
                    if strategy_data and option_chain:
                        logger.warning("Using legacy format (strategy_data + option_chain). Please migrate to strategy_summary format.")
                        # Convert legacy format to new format (simplified)
                        strategy_summary = {
                            **strategy_data,
                            "option_chain": option_chain,  # Keep for compatibility
                        }
                
                if not strategy_summary:
                    raise ValueError("Missing strategy_summary in metadata")

                # Get prompt template (will be formatted by AI provider)
                from app.services.ai.zenmux_provider import DEFAULT_REPORT_PROMPT_TEMPLATE
                prompt_template = await config_service.get(
                    "ai.report_prompt_template",
                    default=DEFAULT_REPORT_PROMPT_TEMPLATE
                )
                
                # Record model in task
                task.model_used = settings.zenmux_model if settings.ai_provider == "zenmux" else settings.ai_model_default
                task.execution_history = _add_execution_event(
                    task.execution_history,
                    "info",
                    f"Using AI model: {task.model_used}",
                )
                await session.commit()
                
                # Always use Deep Research mode (quick mode removed due to data accuracy issues)
                use_deep_research = True
                logger.info(f"Task {task_id} - Using Deep Research mode (only mode available)")
                
                # Progress callback for deep research
                # Get the current event loop to ensure we schedule tasks in the correct context
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    # No running loop, can't schedule async operations
                    loop = None
                
                def progress_callback(progress: int, message: str) -> None:
                    """Update task progress in database (sync wrapper for async operations)."""
                    if loop is None:
                        # Can't update progress without a running event loop
                        logger.debug(f"[Deep Research {progress}%] {message} (progress update skipped - no event loop)")
                        return
                    
                    async def _update_progress_async() -> None:
                        # Create a new session for this update to avoid cross-task session usage
                        async with AsyncSessionLocal() as update_session:
                            try:
                                # Re-fetch task in this session
                                result = await update_session.execute(
                                    select(Task).where(Task.id == task_id)
                                )
                                update_task = result.scalar_one_or_none()
                                if not update_task:
                                    logger.warning(f"Task {task_id} not found for progress update")
                                    return
                                
                                # Update task metadata with progress
                                if update_task.task_metadata is None:
                                    update_task.task_metadata = {}
                                update_task.task_metadata["progress"] = progress
                                update_task.task_metadata["current_stage"] = message
                                
                                # Add progress event to execution history
                                if update_task.execution_history is None:
                                    update_task.execution_history = []
                                update_task.execution_history = _add_execution_event(
                                    update_task.execution_history,
                                    "info",
                                    f"[{progress}%] {message}",
                                )
                                
                                update_task.updated_at = datetime.now(timezone.utc)
                                await update_session.commit()
                            except Exception as e:
                                logger.warning(f"Failed to update task progress: {e}")
                                # Don't fail the whole task if progress update fails
                    
                    # Schedule async update using the current event loop
                    try:
                        loop.create_task(_update_progress_async())
                    except Exception as e:
                        logger.warning(f"Failed to schedule progress update: {e}")
                
                # Generate prompt before calling AI service (for logging/debugging)
                # We'll generate the actual prompt that will be used by the AI provider
                # IMPORTANT: Always save the complete strategy_summary JSON, even if prompt generation fails
                try:
                    # Generate the full prompt using the AI provider's format method
                    ai_provider = ai_service._get_provider()
                    if hasattr(ai_provider, '_format_prompt'):
                        # Generate full prompt (this now includes complete strategy_summary JSON at the end)
                        full_prompt = await ai_provider._format_prompt(strategy_summary)
                        task.prompt_used = full_prompt
                        await session.commit()
                        logger.info(f"Task {task_id} - Full prompt saved: {len(full_prompt)} characters")
                    else:
                        # Fallback: save complete strategy summary as JSON
                        complete_prompt = f"""Full Strategy Summary (JSON format):

{json.dumps(strategy_summary, indent=2, default=str)}"""
                        task.prompt_used = complete_prompt
                        await session.commit()
                        logger.info(f"Task {task_id} - Complete strategy summary saved as prompt: {len(complete_prompt)} characters")
                except Exception as prompt_error:
                    logger.warning(f"Task {task_id} - Failed to generate formatted prompt: {prompt_error}. Saving complete strategy_summary JSON instead.", exc_info=True)
                    # CRITICAL: Always save the complete strategy_summary JSON, even if prompt generation fails
                    # This ensures users can see all input data in the Full Prompt tab
                    try:
                        complete_prompt = f"""Full Strategy Summary (JSON format):

{json.dumps(strategy_summary, indent=2, default=str)}

Note: Prompt formatting failed ({str(prompt_error)}), but complete input data is shown above."""
                        task.prompt_used = complete_prompt
                        await session.commit()
                        logger.info(f"Task {task_id} - Complete strategy summary saved as fallback prompt: {len(complete_prompt)} characters")
                    except Exception as fallback_error:
                        logger.error(f"Task {task_id} - Failed to save even fallback prompt: {fallback_error}", exc_info=True)
                        # Last resort: save at least a minimal JSON
                        try:
                            task.prompt_used = json.dumps(strategy_summary, indent=2, default=str)
                            await session.commit()
                        except:
                            pass  # Ignore if this also fails
                
                # Generate report with retry logic
                report_content = None
                last_error = None
                
                for attempt in range(MAX_RETRIES + 1):
                    try:
                        if attempt > 0:
                            wait_time = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                            task.execution_history = _add_execution_event(
                                task.execution_history,
                                "retry",
                                f"Retry attempt {attempt}/{MAX_RETRIES} after {wait_time}s wait",
                            )
                            task.retry_count = attempt
                            await session.commit()
                            await asyncio.sleep(wait_time)
                        
                        # Always use Deep Research mode (quick mode removed)
                        # Pass strategy_summary instead of strategy_data + option_chain
                        logger.info(f"Task {task_id} - Starting Deep Research AI report generation (attempt {attempt + 1})")
                        report_content = await ai_service.generate_deep_research_report(
                            strategy_summary=strategy_summary,
                            progress_callback=progress_callback,
                        )
                        
                        # Validate report content
                        if not report_content or len(report_content) < 100:
                            raise ValueError(f"Generated report is too short or empty: {len(report_content) if report_content else 0} characters")
                        
                        logger.info(f"Task {task_id} - Report generated successfully: {len(report_content)} characters")
                        break  # Success, exit retry loop
                    except Exception as e:
                        last_error = e
                        task.execution_history = _add_execution_event(
                            task.execution_history,
                            "error",
                            f"Attempt {attempt + 1} failed: {str(e)}",
                        )
                        if attempt < MAX_RETRIES:
                            logger.warning(f"Task {task_id} attempt {attempt + 1} failed, will retry: {e}")
                        else:
                            raise  # Re-raise on last attempt

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
                from app.api.endpoints.ai import check_ai_quota

                await check_ai_quota(user, session)

                # Create AI report with current timestamp
                current_time = datetime.now(timezone.utc)
                ai_report = AIReport(
                    user_id=task.user_id,
                    report_content=report_content,
                    model_used=task.model_used or settings.ai_model_default,
                    created_at=current_time,
                )
                session.add(ai_report)
                await session.flush()
                await session.refresh(ai_report)

                # Increment usage (using same logic as direct API endpoint)
                from sqlalchemy import update

                stmt = (
                    update(User)
                    .where(User.id == user.id)
                    .values(daily_ai_usage=User.daily_ai_usage + 1)
                )
                await session.execute(stmt)
                # Refresh user to get updated daily_ai_usage
                await session.refresh(user)

                # Update task - success
                completed_at = datetime.now(timezone.utc)
                task.status = "SUCCESS"
                task.result_ref = str(ai_report.id)
                task.completed_at = completed_at
                task.updated_at = completed_at
                task.execution_history = _add_execution_event(
                    task.execution_history,
                    "success",
                    f"Task completed successfully. Report ID: {ai_report.id}",
                    completed_at,
                )
                await session.commit()
                
                logger.info(
                    f"Task {task_id} completed successfully. "
                    f"Report ID: {ai_report.id}. "
                    f"User daily_ai_usage: {user.daily_ai_usage}"
                )
            elif task_type == "daily_picks":
                # Daily picks generation task (system task)
                from app.services.daily_picks_service import generate_daily_picks_pipeline
                from app.db.models import DailyPick
                import pytz
                
                EST = pytz.timezone("US/Eastern")
                today = datetime.now(EST).date()
                
                # Record start of pipeline
                task.execution_history = _add_execution_event(
                    task.execution_history,
                    "info",
                    "Starting daily picks pipeline: Market Scan -> Strategy Generation -> AI Commentary",
                )
                await session.commit()
                
                # Generate picks
                picks = await generate_daily_picks_pipeline()
                
                # Save to database (upsert by date)
                result = await session.execute(
                    select(DailyPick).where(DailyPick.date == today)
                )
                existing_pick = result.scalar_one_or_none()
                
                if existing_pick:
                    existing_pick.content_json = picks
                    existing_pick.created_at = datetime.now(timezone.utc)
                    await session.commit()
                    await session.refresh(existing_pick)
                else:
                    daily_pick = DailyPick(
                        date=today,
                        content_json=picks,
                    )
                    session.add(daily_pick)
                    await session.commit()
                    await session.refresh(daily_pick)
                
                # Update task - success
                completed_at = datetime.now(timezone.utc)
                task.status = "SUCCESS"
                task.result_ref = json.dumps({"date": str(today), "count": len(picks)})
                task.completed_at = completed_at
                task.updated_at = completed_at
                task.execution_history = _add_execution_event(
                    task.execution_history,
                    "success",
                    f"Daily picks generated successfully. {len(picks)} picks created for {today}",
                    completed_at,
                )
                await session.commit()
                
                logger.info(
                    f"Task {task_id} completed successfully. "
                    f"Generated {len(picks)} daily picks for {today}"
                )
            elif task_type == "multi_agent_report":
                # Multi-agent report generation (async)
                from app.services.ai_service import ai_service
                from app.api.endpoints.ai import check_ai_quota, increment_ai_usage, get_ai_quota_limit
                from app.db.models import AIReport
                from app.core.config import settings
                
                strategy_summary = metadata.get("strategy_summary") if metadata else None
                use_multi_agent = metadata.get("use_multi_agent", True)  # Default to multi-agent for async
                
                if not strategy_summary:
                    raise ValueError("Missing strategy_summary in metadata for multi_agent_report")
                
                # Get user for quota check
                user_id = task.user_id
                if user_id:
                    from sqlalchemy import select
                    from app.db.models import User
                    user_result = await session.execute(select(User).where(User.id == user_id))
                    user = user_result.scalar_one_or_none()
                    if user:
                        # Check quota
                        required_quota = 5 if use_multi_agent else 1
                        await check_ai_quota(user, session, required_quota=required_quota)
                        
                        task.execution_history = _add_execution_event(
                            task.execution_history,
                            "info",
                            f"Quota checked: {required_quota} units required",
                        )
                        await session.commit()
                
                # Record model
                task.model_used = settings.ai_model_default
                task.execution_history = _add_execution_event(
                    task.execution_history,
                    "info",
                    f"Using AI model: {task.model_used} (multi-agent: {use_multi_agent})",
                )
                await session.commit()
                
                # Progress callback for agent workflow
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None
                
                def progress_callback(progress: int, message: str) -> None:
                    """Update task progress in database."""
                    if loop is None:
                        logger.debug(f"[Agent {progress}%] {message} (progress update skipped)")
                        return
                    
                    async def update_progress_async() -> None:
                        try:
                            async with AsyncSessionLocal() as progress_session:
                                progress_result = await progress_session.execute(
                                    select(Task).where(Task.id == task_id)
                                )
                                progress_task = progress_result.scalar_one_or_none()
                                if progress_task:
                                    progress_task.execution_history = _add_execution_event(
                                        progress_task.execution_history,
                                        "progress",
                                        f"[{progress}%] {message}",
                                    )
                                    progress_task.updated_at = datetime.now(timezone.utc)
                                    await progress_session.commit()
                        except Exception as e:
                            logger.warning(f"Failed to update progress for task {task_id}: {e}")
                    
                    if loop:
                        loop.create_task(update_progress_async())
                
                # Generate report using multi-agent system
                task.execution_history = _add_execution_event(
                    task.execution_history,
                    "info",
                    "Starting multi-agent report generation...",
                )
                await session.commit()
                
                report_content = await ai_service.generate_report_with_agents(
                    strategy_summary=strategy_summary,
                    use_multi_agent=use_multi_agent,
                    progress_callback=progress_callback,
                )
                
                # Save report to database
                ai_report = AIReport(
                    user_id=task.user_id,
                    report_content=report_content,
                    model_used=task.model_used,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(ai_report)
                await session.flush()
                await session.refresh(ai_report)
                
                # Update task with result
                task.result_ref = str(ai_report.id)
                task.status = "SUCCESS"
                task.completed_at = datetime.now(timezone.utc)
                task.updated_at = task.completed_at
                task.execution_history = _add_execution_event(
                    task.execution_history,
                    "success",
                    f"Multi-agent report generated successfully. Report ID: {ai_report.id}",
                    task.completed_at,
                )
                
                # Increment quota usage
                if user_id and user:
                    await increment_ai_usage(user, session, quota_units=required_quota)
                    quota_limit = get_ai_quota_limit(user)
                    task.execution_history = _add_execution_event(
                        task.execution_history,
                        "info",
                        f"Quota used: {required_quota}. Usage: {user.daily_ai_usage}/{quota_limit}",
                    )
                
                await session.commit()
                logger.info(f"Task {task_id} completed successfully. Report ID: {ai_report.id}")
                
            elif task_type == "options_analysis_workflow":
                # Options analysis workflow (async)
                from app.services.ai_service import ai_service
                from app.api.endpoints.ai import check_ai_quota, increment_ai_usage
                
                strategy_summary = metadata.get("strategy_summary") if metadata else None
                if not strategy_summary:
                    raise ValueError("Missing strategy_summary in metadata for options_analysis_workflow")
                
                # Get user for quota check
                user_id = task.user_id
                if user_id:
                    from sqlalchemy import select
                    from app.db.models import User
                    user_result = await session.execute(select(User).where(User.id == user_id))
                    user = user_result.scalar_one_or_none()
                    if user:
                        # Check quota (5 units for multi-agent)
                        await check_ai_quota(user, session, required_quota=5)
                
                # Record model
                task.model_used = settings.ai_model_default
                task.execution_history = _add_execution_event(
                    task.execution_history,
                    "info",
                    f"Starting options analysis workflow with {task.model_used}",
                )
                await session.commit()
                
                # Progress callback
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None
                
                def progress_callback(progress: int, message: str) -> None:
                    """Update task progress in database."""
                    if loop is None:
                        return
                    
                    async def update_progress_async() -> None:
                        try:
                            async with AsyncSessionLocal() as progress_session:
                                progress_result = await progress_session.execute(
                                    select(Task).where(Task.id == task_id)
                                )
                                progress_task = progress_result.scalar_one_or_none()
                                if progress_task:
                                    progress_task.execution_history = _add_execution_event(
                                        progress_task.execution_history,
                                        "progress",
                                        f"[{progress}%] {message}",
                                    )
                                    progress_task.updated_at = datetime.now(timezone.utc)
                                    await progress_session.commit()
                        except Exception as e:
                            logger.warning(f"Failed to update progress: {e}")
                    
                    if loop:
                        loop.create_task(update_progress_async())
                
                # Execute workflow
                coordinator = ai_service.agent_coordinator
                if not coordinator:
                    raise RuntimeError("Agent framework is not available")
                
                result = await coordinator.coordinate_options_analysis(
                    strategy_summary,
                    progress_callback,
                )
                
                # Format report
                report_content = ai_service._format_agent_report(result)
                
                # Save report
                from app.db.models import AIReport
                ai_report = AIReport(
                    user_id=task.user_id,
                    report_content=report_content,
                    model_used=task.model_used,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(ai_report)
                await session.flush()
                await session.refresh(ai_report)
                
                # Update task
                task.result_ref = str(ai_report.id)
                task.status = "SUCCESS"
                task.completed_at = datetime.now(timezone.utc)
                task.updated_at = task.completed_at
                
                # Store workflow results in metadata
                workflow_metadata = {
                    "parallel_analysis": result.get("parallel_analysis", {}),
                    "risk_analysis": result.get("risk_analysis"),
                    "synthesis": result.get("synthesis"),
                    "metadata": result.get("metadata", {}),
                }
                if task.task_metadata is None:
                    task.task_metadata = {}
                task.task_metadata["workflow_results"] = workflow_metadata
                
                task.execution_history = _add_execution_event(
                    task.execution_history,
                    "success",
                    f"Options analysis workflow completed. Report ID: {ai_report.id}",
                    task.completed_at,
                )
                
                # Increment quota
                if user_id and user:
                    await increment_ai_usage(user, session, quota_units=5)
                
                await session.commit()
                logger.info(f"Task {task_id} completed. Report ID: {ai_report.id}")
                
            elif task_type == "stock_screening_workflow":
                # Stock screening workflow (async)
                from app.services.ai_service import ai_service
                from app.api.endpoints.ai import check_ai_quota, increment_ai_usage
                
                criteria = metadata.get("criteria") if metadata else None
                if not criteria:
                    raise ValueError("Missing criteria in metadata for stock_screening_workflow")
                
                # Get user for quota check
                user_id = task.user_id
                if user_id:
                    from sqlalchemy import select
                    from app.db.models import User
                    user_result = await session.execute(select(User).where(User.id == user_id))
                    user = user_result.scalar_one_or_none()
                    if user:
                        # Estimate quota (dynamic based on limit)
                        limit = criteria.get("limit", 10)
                        estimated_quota = min(5, 2 + (limit * 2) // 10)
                        await check_ai_quota(user, session, required_quota=estimated_quota)
                
                # Record model
                task.model_used = settings.ai_model_default
                task.execution_history = _add_execution_event(
                    task.execution_history,
                    "info",
                    f"Starting stock screening workflow. Criteria: {criteria}",
                )
                await session.commit()
                
                # Progress callback
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None
                
                def progress_callback(progress: int, message: str) -> None:
                    """Update task progress in database."""
                    if loop is None:
                        return
                    
                    async def update_progress_async() -> None:
                        try:
                            async with AsyncSessionLocal() as progress_session:
                                progress_result = await progress_session.execute(
                                    select(Task).where(Task.id == task_id)
                                )
                                progress_task = progress_result.scalar_one_or_none()
                                if progress_task:
                                    progress_task.execution_history = _add_execution_event(
                                        progress_task.execution_history,
                                        "progress",
                                        f"[{progress}%] {message}",
                                    )
                                    progress_task.updated_at = datetime.now(timezone.utc)
                                    await progress_session.commit()
                        except Exception as e:
                            logger.warning(f"Failed to update progress: {e}")
                    
                    if loop:
                        loop.create_task(update_progress_async())
                
                # Execute workflow
                coordinator = ai_service.agent_coordinator
                if not coordinator:
                    raise RuntimeError("Agent framework is not available")
                
                candidates = await coordinator.coordinate_stock_screening(
                    criteria,
                    progress_callback,
                )
                
                # Store results in task metadata
                if task.task_metadata is None:
                    task.task_metadata = {}
                task.task_metadata["candidates"] = candidates
                task.task_metadata["total_found"] = len(candidates)
                task.task_metadata["filtered_count"] = len(candidates)
                
                # Update task
                task.status = "SUCCESS"
                task.completed_at = datetime.now(timezone.utc)
                task.updated_at = task.completed_at
                task.execution_history = _add_execution_event(
                    task.execution_history,
                    "success",
                    f"Stock screening completed. Found {len(candidates)} candidates",
                    task.completed_at,
                )
                
                # Increment quota
                if user_id and user:
                    limit = criteria.get("limit", 10)
                    estimated_quota = min(5, 2 + (limit * 2) // 10)
                    await increment_ai_usage(user, session, quota_units=estimated_quota)
                
                await session.commit()
                logger.info(f"Task {task_id} completed. Found {len(candidates)} candidates")
                
            elif task_type == "generate_strategy_chart":
                # Image generation task
                from app.services.ai.image_provider import get_image_provider
                from app.db.models import GeneratedImage
                
                strategy_summary = metadata.get("strategy_summary") if metadata else None
                
                # Support legacy format for backward compatibility
                if not strategy_summary:
                    strategy_data = metadata.get("strategy_data") if metadata else None
                    option_chain = metadata.get("option_chain") if metadata else None
                    if strategy_data:
                        logger.warning("Using legacy format for image generation. Please migrate to strategy_summary format.")
                        # Convert to strategy_summary format
                        strategy_summary = strategy_data
                
                if not strategy_summary:
                    raise ValueError("Missing strategy_summary in metadata")
                
                # Extract strategy_data and metrics from strategy_summary
                strategy_data = {
                    "symbol": strategy_summary.get("symbol"),
                    "strategy_name": strategy_summary.get("strategy_name"),
                    "current_price": strategy_summary.get("spot_price"),
                    "legs": strategy_summary.get("legs", []),
                }
                
                # Use strategy_metrics from summary if available, otherwise calculate
                strategy_metrics = strategy_summary.get("strategy_metrics")
                if strategy_metrics and isinstance(strategy_metrics, dict):
                    metrics = {
                        "max_profit": strategy_metrics.get("max_profit", 0),
                        "max_loss": strategy_metrics.get("max_loss", 0),
                        "breakeven": strategy_metrics.get("breakeven_points", [0])[0] if strategy_metrics.get("breakeven_points") else 0,
                        "net_cash_flow": strategy_summary.get("trade_execution", {}).get("net_cost", 0) if isinstance(strategy_summary.get("trade_execution"), dict) else 0,
                        "margin": 0,  # Can be calculated if needed
                    }
                else:
                    # Fallback: calculate metrics (for legacy format)
                    option_chain = metadata.get("option_chain") if metadata else None
                    metrics = _calculate_strategy_metrics(strategy_data, option_chain)
                
                # Record model in task
                task.model_used = settings.ai_image_model
                task.execution_history = _add_execution_event(
                    task.execution_history,
                    "info",
                    f"Using image model: {task.model_used}",
                )
                await session.commit()
                
                # Generate image with retry logic
                image_provider = get_image_provider()
                
                # Build prompt for logging (generate_chart will build it internally, but we want to save it)
                if strategy_summary:
                    prompt = image_provider.construct_image_prompt(strategy_summary=strategy_summary)
                else:
                    # Legacy format
                    prompt = image_provider.construct_image_prompt(strategy_data=strategy_data, metrics=metrics)
                task.prompt_used = prompt
                await session.commit()
                
                image_base64 = None
                last_error = None
                
                for attempt in range(MAX_RETRIES + 1):
                    try:
                        if attempt > 0:
                            wait_time = 2 ** attempt
                            task.execution_history = _add_execution_event(
                                task.execution_history,
                                "retry",
                                f"Retry attempt {attempt}/{MAX_RETRIES} after {wait_time}s wait",
                            )
                            task.retry_count = attempt
                            await session.commit()
                            await asyncio.sleep(wait_time)
                        
                        # Pass strategy data directly - generate_chart will build the prompt internally
                        if strategy_summary:
                            image_base64 = await image_provider.generate_chart(strategy_summary=strategy_summary)
                        else:
                            image_base64 = await image_provider.generate_chart(strategy_data=strategy_data, metrics=metrics)
                        break  # Success
                    except Exception as e:
                        last_error = e
                        task.execution_history = _add_execution_event(
                            task.execution_history,
                            "error",
                            f"Attempt {attempt + 1} failed: {str(e)}",
                        )
                        if attempt < MAX_RETRIES:
                            logger.warning(f"Task {task_id} attempt {attempt + 1} failed, will retry: {e}")
                        else:
                            raise
                
                # Save image to database
                # Note: Only save if user_id is not None (system tasks don't have user_id)
                # For now, we require user_id for image generation tasks
                if not task.user_id:
                    raise ValueError("Image generation tasks require a user_id")
                
                # Check image quota before saving (quota was checked when task was created, but double-check here)
                from app.api.endpoints.ai import check_image_quota
                from app.db.models import User  # Import User in local scope
                user_result = await session.execute(
                    select(User).where(User.id == task.user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    raise ValueError(f"User {task.user_id} not found")
                
                await check_image_quota(user, session)
                
                # Clean base64 data: remove whitespace, newlines, and data URL prefix if present
                cleaned_base64 = image_base64.strip()
                if cleaned_base64.startswith("data:"):
                    # Extract base64 part after comma
                    cleaned_base64 = cleaned_base64.split(",", 1)[-1].strip()
                # Remove any remaining whitespace/newlines
                cleaned_base64 = "".join(cleaned_base64.split())
                
                # Validate base64 format before storing
                try:
                    # Try to decode to validate format
                    test_bytes = base64.b64decode(cleaned_base64, validate=True)
                    if len(test_bytes) < 100:
                        raise ValueError(f"Invalid image data: decoded data too small ({len(test_bytes)} bytes)")
                    
                    # Validate image format (check magic bytes)
                    is_valid_image = False
                    if len(test_bytes) >= 4:
                        if test_bytes[:4] == b'\x89PNG':
                            is_valid_image = True
                            logger.info("Image format: PNG")
                        elif test_bytes[:2] == b'\xff\xd8':
                            is_valid_image = True
                            logger.info("Image format: JPEG")
                        elif test_bytes[:6] in (b'GIF87a', b'GIF89a'):
                            is_valid_image = True
                            logger.info("Image format: GIF")
                        elif test_bytes[:4] == b'RIFF' and len(test_bytes) >= 12 and test_bytes[8:12] == b'WEBP':
                            is_valid_image = True
                            logger.info("Image format: WEBP")
                    
                    if not is_valid_image:
                        first_4_hex = test_bytes[:4].hex()
                        first_4_repr = repr(test_bytes[:4])
                        logger.warning(
                            f"Image data does not match known formats. "
                            f"First 4 bytes (hex): {first_4_hex}, "
                            f"First 4 bytes (repr): {first_4_repr}"
                        )
                        # Check if this looks like double-encoded base64 (base64 string encoded as base64)
                        # If decoded bytes start with 'iVB' (ASCII), it might be double-encoded PNG
                        if test_bytes[:3] == b'iVB' and len(test_bytes) > 10:
                            try:
                                # Check if the decoded bytes are ASCII (looks like base64 string)
                                if all(32 <= b <= 126 for b in test_bytes[:min(100, len(test_bytes))]):
                                    # Try to decode the entire decoded bytes as base64 string
                                    potential_b64_str = test_bytes.decode('utf-8', errors='ignore')
                                    # Try to decode again
                                    try:
                                        # Add padding if needed (base64 strings should be multiple of 4)
                                        padding_needed = (4 - len(potential_b64_str) % 4) % 4
                                        double_decoded = base64.b64decode(potential_b64_str + '=' * padding_needed)
                                        if len(double_decoded) >= 4:
                                            if double_decoded[:4] == b'\x89PNG':
                                                logger.info("Detected and fixed double-encoded PNG base64")
                                                cleaned_base64 = potential_b64_str
                                                test_bytes = double_decoded
                                                is_valid_image = True
                                            elif double_decoded[:2] == b'\xff\xd8':
                                                logger.info("Detected and fixed double-encoded JPEG base64")
                                                cleaned_base64 = potential_b64_str
                                                test_bytes = double_decoded
                                                is_valid_image = True
                                    except Exception as e:
                                        logger.debug(f"Double decode attempt failed: {e}")
                            except Exception as e:
                                logger.debug(f"Double-encoding check failed: {e}")
                        
                        # If still not valid, log warning but don't fail (some formats might still be valid)
                        if not is_valid_image:
                            logger.warning(f"Image format not recognized, but storing anyway. First 4 bytes: {first_4_repr}")
                    
                    logger.info(f"Validated base64 image data: {len(test_bytes)} bytes, base64 length: {len(cleaned_base64)}")
                except base64.binascii.Error as e:
                    logger.error(f"Invalid base64 image data format: {e}, base64 length: {len(cleaned_base64)}, first 50 chars: {cleaned_base64[:50]}")
                    raise ValueError(f"Invalid base64 image data format: {str(e)}")
                except Exception as e:
                    logger.error(f"Invalid base64 image data: {e}, base64 length: {len(cleaned_base64)}")
                    raise ValueError(f"Invalid base64 image data format: {str(e)}")
                
                # Calculate strategy hash for caching (used as filename in R2)
                from app.utils.strategy_hash import calculate_strategy_hash
                strategy_hash = None
                try:
                    # Log strategy summary for debugging
                    logger.debug(f"Calculating hash for strategy_summary: symbol={strategy_summary.get('symbol')}, expiration_date={strategy_summary.get('expiration_date')}, legs_count={len(strategy_summary.get('legs', []))}")
                    strategy_hash = calculate_strategy_hash(strategy_summary)
                    logger.info(f"Calculated strategy hash: {strategy_hash} (will be used as filename in R2)")
                    
                    # Note: We do NOT delete old images when regenerating.
                    # Each task keeps its own image for historical reference.
                    # Strategy details page will show the latest image (by strategy_hash).
                    # Task details page will show the image associated with that specific task.
                except Exception as e:
                    logger.warning(f"Failed to calculate strategy hash: {e}", exc_info=True)
                    # Continue without hash (backward compatibility)
                
                # Generate image ID (used as fallback filename if strategy_hash is not available)
                image_id = uuid.uuid4()
                
                # Determine image format from decoded bytes
                image_format = "png"  # Default
                content_type = "image/png"
                if len(test_bytes) >= 4:
                    if test_bytes[:4] == b'\x89PNG':
                        image_format = "png"
                        content_type = "image/png"
                    elif test_bytes[:2] == b'\xff\xd8':
                        image_format = "jpeg"
                        content_type = "image/jpeg"
                    elif test_bytes[:6] in (b'GIF87a', b'GIF89a'):
                        image_format = "gif"
                        content_type = "image/gif"
                    elif test_bytes[:4] == b'RIFF' and len(test_bytes) >= 12 and test_bytes[8:12] == b'WEBP':
                        image_format = "webp"
                        content_type = "image/webp"
                
                # Upload to R2 (required)
                from app.services.storage.r2_service import get_r2_service
                r2_service = get_r2_service()
                
                if not r2_service.is_enabled():
                    raise ValueError("R2 storage is required but not enabled. Please configure Cloudflare R2.")
                
                # Upload to R2 using decoded bytes
                # Use image_id as filename to ensure each task has its own unique image file
                # Format: strategy_chart/{user_id}/{image_id}.{extension}
                # This prevents overwriting old images when regenerating for the same strategy
                object_key = r2_service.generate_object_key(
                    user_id=str(task.user_id),
                    strategy_hash=None,  # Don't use hash as filename - use image_id instead
                    image_id=str(image_id),  # Use image_id to ensure uniqueness
                    extension=image_format
                )
                r2_url = await r2_service.upload_image(
                    image_data=test_bytes,  # Use decoded bytes, not base64
                    object_key=object_key,
                    content_type=content_type,
                )
                logger.info(f"Image uploaded to R2: {r2_url}")
                
                generated_image = GeneratedImage(
                    id=image_id,
                    user_id=task.user_id,
                    task_id=task.id,
                    base64_data=None,  # No longer storing base64 data, only R2 URLs
                    r2_url=r2_url,  # R2 URL (required)
                    strategy_hash=strategy_hash,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(generated_image)
                await session.flush()
                await session.refresh(generated_image)
                
                # Increment user's daily_image_usage
                from sqlalchemy import update
                stmt = (
                    update(User)
                    .where(User.id == user.id)
                    .values(daily_image_usage=User.daily_image_usage + 1)
                )
                await session.execute(stmt)
                
                # Update task - success
                completed_at = datetime.now(timezone.utc)
                task.status = "SUCCESS"
                task.result_ref = json.dumps({"image_id": str(generated_image.id)})
                task.completed_at = completed_at
                task.updated_at = completed_at
                task.execution_history = _add_execution_event(
                    task.execution_history,
                    "success",
                    f"Task completed successfully. Image ID: {generated_image.id}",
                    completed_at,
                )
                await session.commit()
                
                logger.info(
                    f"Task {task_id} completed successfully. "
                    f"Image ID: {generated_image.id}"
                )
            else:
                raise ValueError(f"Unknown task type: {task_type}")

        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}", exc_info=True)
            # Update task status to FAILED
            try:
                result = await session.execute(select(Task).where(Task.id == task_id))
                task = result.scalar_one_or_none()
                if task:
                    failed_at = datetime.now(timezone.utc)
                    task.status = "FAILED"
                    # Format error message for better user experience
                    error_str = str(e)
                    if "429" in error_str or "quota" in error_str.lower() or "ResourceExhausted" in error_str:
                        task.error_message = "AI service quota exceeded. Please try again later or check your Google API billing."
                    else:
                        task.error_message = error_str
                    task.completed_at = failed_at
                    task.updated_at = failed_at
                    
                    # Add final error to execution history
                    if task.execution_history is None:
                        task.execution_history = []
                    task.execution_history = _add_execution_event(
                        task.execution_history,
                        "error",
                        f"Task failed after {task.retry_count} retries: {task.error_message}",
                        failed_at,
                    )
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
        # Check quota BEFORE creating task for AI-related tasks
        if request.task_type == "ai_report":
            from app.api.endpoints.ai import check_ai_quota
            # Refresh user to get latest usage
            await db.refresh(current_user)
            await check_ai_quota(current_user, db)
        elif request.task_type == "generate_strategy_chart":
            from app.api.endpoints.ai import check_image_quota
            # Refresh user to get latest usage
            await db.refresh(current_user)
            await check_image_quota(current_user, db)
        
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
                metadata=task.task_metadata,  # Fixed: use task_metadata instead of metadata
                execution_history=task.execution_history,
                prompt_used=task.prompt_used,
                model_used=task.model_used,
                started_at=task.started_at,
                retry_count=task.retry_count,
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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching task {task_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch task",
        )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Delete a task by ID and associated resources (images, R2 files).

    Only allows deletion of tasks owned by the authenticated user.
    If the task has associated images, they will be deleted from both database and R2.

    Args:
        task_id: Task UUID
        current_user: Authenticated user (from JWT token)
        db: Database session

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

        # Delete associated images (if any)
        from app.db.models import GeneratedImage
        image_result = await db.execute(
            select(GeneratedImage).where(GeneratedImage.task_id == task_id)
        )
        images = image_result.scalars().all()
        
        if images:
            logger.info(f"Found {len(images)} image(s) associated with task {task_id}, deleting...")
            for image in images:
                # Delete from R2 if r2_url exists
                if image.r2_url:
                    try:
                        from app.services.storage.r2_service import get_r2_service
                        r2_service = get_r2_service()
                        if r2_service.is_enabled():
                            # Extract object key from r2_url
                            # Format: https://assets.thetamind.ai/strategy_chart/{user_id}/{strategy_hash}.{ext}
                            # or: https://pub-xxx.r2.dev/strategy_chart/{user_id}/{strategy_hash}.{ext}
                            r2_url = image.r2_url
                            if not r2_url.startswith("http://") and not r2_url.startswith("https://"):
                                r2_url = f"https://{r2_url}"
                            
                            # Extract object key (path after domain)
                            if "/strategy_chart/" in r2_url:
                                object_key = r2_url.split("/strategy_chart/", 1)[-1]
                                object_key = f"strategy_chart/{object_key}"
                            elif ".r2.dev/" in r2_url:
                                object_key = r2_url.split(".r2.dev/", 1)[-1]
                            else:
                                # Fallback: try to extract path
                                parts = r2_url.split("/", 3)
                                if len(parts) >= 4:
                                    object_key = "/".join(parts[3:])
                                else:
                                    logger.warning(f"Could not extract object key from r2_url: {r2_url}")
                                    object_key = None
                            
                            if object_key:
                                await r2_service.delete_image(object_key)
                                logger.info(f"Deleted image from R2: {object_key}")
                    except Exception as r2_error:
                        logger.warning(f"Failed to delete image from R2: {r2_error}", exc_info=True)
                        # Continue with database deletion even if R2 deletion fails
                
                # Delete from database
                await db.delete(image)
                logger.info(f"Deleted image record {image.id} from database")
            
            await db.flush()  # Flush image deletions before deleting task

        # Delete the task
        await db.delete(task)
        await db.commit()

        logger.info(f"Task {task_id} and associated resources deleted by user {current_user.email}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task",
        )

