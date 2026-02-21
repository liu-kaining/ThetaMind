"""Task management API endpoints."""

import asyncio
import base64
import json
import logging
import uuid
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.api.deps import get_current_user
from app.api.schemas import TaskResponse
from app.core.constants import FinancialPrecision, RetryConfig
from app.db.models import Task, User
from app.db.session import AsyncSessionLocal, get_db

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
    await db.commit()  # Must commit before scheduling so worker can find the task

    # Start background processing with error handling
    async def safe_process_task() -> None:
        """Wrapper to safely process task with error handling."""
        try:
            logger.info(f"Starting background processing for task {task.id} (type: {task_type})")
            # ⚠️ db parameter is deprecated, pass None
            await process_task_async(task.id, task_type, metadata, None)
            logger.info(f"Background task {task.id} completed successfully")
        except Exception as e:
            logger.error(f"Background task {task.id} failed to start processing: {e}", exc_info=True)
            # Try to update task status to FAILED if possible
            try:
                from app.db.session import AsyncSessionLocal
                async with AsyncSessionLocal() as error_session:
                    result = await error_session.execute(select(Task).where(Task.id == task.id))
                    error_task = result.scalar_one_or_none()
                    if error_task and error_task.status in ("PENDING", "PROCESSING"):
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


def _format_portfolio_greeks_for_display(portfolio_greeks: dict[str, Any]) -> str:
    """Format portfolio Greeks for display: all numeric values to 2 decimal places."""
    if not portfolio_greeks:
        return "N/A"
    greek_keys = ["delta", "gamma", "theta", "vega", "rho"]
    parts: list[str] = []
    for key in greek_keys:
        val = portfolio_greeks.get(key)
        if isinstance(val, (int, float)):
            parts.append(f"'{key}': {round(float(val), 2)}")
        elif val is not None:
            parts.append(f"'{key}': {val}")
    return "{" + ", ".join(parts) + "}" if parts else "N/A"


def _build_input_summary(
    strategy_summary: dict[str, Any] | None,
    option_chain: dict[str, Any] | None = None,
) -> tuple[str, bool]:
    """Build a concise input summary and data quality flag."""
    if not strategy_summary:
        return "## Input Summary (Verified)\n\nNo strategy summary provided.\n", True

    spot_price = strategy_summary.get("spot_price")
    if spot_price is None and option_chain:
        spot_price = option_chain.get("spot_price")

    legs = strategy_summary.get("legs", []) or []
    iv_values: list[float] = []
    open_interest_total = 0.0
    for leg in legs:
        if not isinstance(leg, dict):
            continue
        iv = leg.get("implied_volatility") or leg.get("implied_vol")
        if isinstance(iv, (int, float)) and iv > 0:
            iv_values.append(float(iv))
        oi = leg.get("open_interest")
        if isinstance(oi, (int, float)) and oi > 0:
            open_interest_total += float(oi)

    avg_iv = sum(iv_values) / len(iv_values) if iv_values else None
    portfolio_greeks = strategy_summary.get("portfolio_greeks") or {}
    greeks_present = any(
        isinstance(portfolio_greeks.get(key), (int, float)) and portfolio_greeks.get(key) != 0
        for key in ["delta", "gamma", "theta", "vega", "rho"]
    )

    historical_prices = strategy_summary.get("historical_prices", []) or []
    recent_change = None
    if isinstance(historical_prices, list) and len(historical_prices) >= 2:
        closes: list[float] = []
        for row in historical_prices:
            if isinstance(row, dict):
                close_value = row.get("close")
                if isinstance(close_value, (int, float)) and close_value > 0:
                    closes.append(float(close_value))
        if len(closes) >= 2:
            recent_change = (closes[-1] / closes[0] - 1.0) * 100

    data_anomaly = not greeks_present
    lines = [
        "## Input Summary (Verified)",
        f"- Spot: {round(spot_price, 2) if isinstance(spot_price, (int, float)) else (spot_price if spot_price is not None else 'N/A')}",
        f"- IV (avg from legs): {round(avg_iv, 2) if avg_iv is not None else 'N/A'}",
        f"- Portfolio Greeks: {_format_portfolio_greeks_for_display(portfolio_greeks)}",
        f"- Total OI (legs): {round(open_interest_total, 2) if open_interest_total > 0 else 'N/A'}",
        f"- Recent Change: {round(recent_change, 2)}%" if recent_change is not None else "- Recent Change: N/A",
    ]
    if data_anomaly:
        lines.append(
            "\n**Data Quality Alert:** Greeks missing or zero. "
            "Strategy judgment confidence reduced until data integrity is restored."
        )
    return "\n".join(lines) + "\n", data_anomaly


def _ensure_portfolio_greeks(
    strategy_summary: dict[str, Any], 
    option_chain: dict[str, Any] | None = None
) -> None:
    """Ensure portfolio_greeks exists by deriving from legs if missing.
    
    If legs don't have greeks, attempts to extract from option_chain.
    
    Args:
        strategy_summary: Strategy summary dictionary (modified in place)
        option_chain: Optional option chain data to extract greeks from
    """
    if strategy_summary.get("portfolio_greeks"):
        # Validate that portfolio_greeks has at least one non-zero value
        pg = strategy_summary["portfolio_greeks"]
        if isinstance(pg, dict) and any(
            isinstance(pg.get(key), (int, float)) and pg.get(key) != 0
            for key in ["delta", "gamma", "theta", "vega", "rho"]
        ):
            return  # Already has valid greeks
    
    legs = strategy_summary.get("legs", []) or []
    if not isinstance(legs, list) or not legs:
        return
    
    def get_greek_from_chain(strike: float, option_type: str, greek_name: str) -> float:
        """Extract greek value from option_chain if available."""
        if not option_chain:
            return 0.0
        option_list = option_chain.get("calls" if option_type.lower() == "call" else "puts", [])
        if not isinstance(option_list, list):
            return 0.0
        for option in option_list:
            if not isinstance(option, dict):
                continue
            option_strike = option.get("strike")
            if isinstance(option_strike, (int, float)) and abs(float(option_strike) - float(strike)) < 0.01:
                # Found matching strike
                greeks = option.get("greeks", {})
                if isinstance(greeks, dict):
                    value = greeks.get(greek_name)
                else:
                    value = option.get(greek_name)
                if isinstance(value, (int, float)):
                    return float(value)
        return 0.0
    
    # Use Decimal for high-precision financial calculations
    # This prevents floating-point precision errors in financial calculations
    total_delta = Decimal('0')
    total_gamma = Decimal('0')
    total_theta = Decimal('0')
    total_vega = Decimal('0')
    total_rho = Decimal('0')
    
    # Precision settings for rounding
    precision = Decimal('0.0001')  # 4 decimal places for Greeks
    
    for leg in legs:
        if not isinstance(leg, dict):
            continue
        
        # Try to get greeks from leg first, then from option_chain
        strike = leg.get("strike")
        option_type = leg.get("type", "call")
        action = leg.get("action", "buy")
        
        # Convert to Decimal for precision
        quantity = Decimal(str(leg.get("quantity") or 1))
        sign = Decimal('1' if action == "buy" else '-1')
        multiplier = Decimal('-1' if option_type.lower() == "put" else '1')
        
        # Get greeks from leg or option_chain (convert to Decimal)
        delta = leg.get("delta")
        if delta is None or (isinstance(delta, (int, float)) and delta == 0):
            if isinstance(strike, (int, float)):
                delta = get_greek_from_chain(float(strike), option_type, "delta")
            else:
                delta = 0.0
        delta = Decimal(str(delta or 0))
        
        gamma = leg.get("gamma")
        if gamma is None or (isinstance(gamma, (int, float)) and gamma == 0):
            if isinstance(strike, (int, float)):
                gamma = get_greek_from_chain(float(strike), option_type, "gamma")
            else:
                gamma = 0.0
        gamma = Decimal(str(gamma or 0))
        
        theta = leg.get("theta")
        if theta is None or (isinstance(theta, (int, float)) and theta == 0):
            if isinstance(strike, (int, float)):
                theta = get_greek_from_chain(float(strike), option_type, "theta")
            else:
                theta = 0.0
        theta = Decimal(str(theta or 0))
        
        vega = leg.get("vega")
        if vega is None or (isinstance(vega, (int, float)) and vega == 0):
            if isinstance(strike, (int, float)):
                vega = get_greek_from_chain(float(strike), option_type, "vega")
            else:
                vega = 0.0
        vega = Decimal(str(vega or 0))
        
        rho = leg.get("rho")
        if rho is None or (isinstance(rho, (int, float)) and rho == 0):
            if isinstance(strike, (int, float)):
                rho = get_greek_from_chain(float(strike), option_type, "rho")
            else:
                rho = 0.0
        rho = Decimal(str(rho or 0))
        
        # Calculate with Decimal precision
        total_delta += delta * sign * multiplier * quantity
        total_gamma += gamma * sign * quantity
        total_theta += theta * sign * quantity
        total_vega += vega * sign * quantity
        total_rho += rho * sign * multiplier * quantity
    
    # Convert back to float for storage (database may not support Decimal)
    # But use Decimal for all calculations to maintain precision
    strategy_summary["portfolio_greeks"] = {
        "delta": float(total_delta.quantize(precision, rounding=ROUND_HALF_UP)),
        "gamma": float(total_gamma.quantize(precision, rounding=ROUND_HALF_UP)),
        "theta": float(total_theta.quantize(precision, rounding=ROUND_HALF_UP)),
        "vega": float(total_vega.quantize(precision, rounding=ROUND_HALF_UP)),
        "rho": float(total_rho.quantize(precision, rounding=ROUND_HALF_UP)),
    }


async def _run_data_enrichment(strategy_summary: dict[str, Any]) -> None:
    """Enrich strategy_summary with FMP data (fundamental_profile, analyst_data, etc.) for multi-agent and Deep Research.
    Writes into strategy_summary in place. Does not raise on failure so task can continue.
    """
    symbol = (strategy_summary.get("symbol") or "").strip().upper()
    if not symbol:
        logger.warning("Data enrichment skipped: no symbol in strategy_summary")
        return
    from app.services.market_data_service import MarketDataService
    service = MarketDataService()
    # Fundamental profile (sync, run in thread; timeout to avoid hang on SSL/Yahoo errors in Docker)
    try:
        profile = await asyncio.wait_for(
            asyncio.to_thread(service.get_financial_profile, symbol),
            timeout=90.0,
        )
        if profile and isinstance(profile, dict):
            strategy_summary["fundamental_profile"] = profile
            logger.info(f"Data enrichment: fundamental_profile injected for {symbol}")
        else:
            strategy_summary["fundamental_profile"] = {}
    except asyncio.TimeoutError:
        logger.warning(f"Data enrichment (fundamental_profile) timed out for {symbol} (SSL/Yahoo may fail in Docker)")
        strategy_summary["fundamental_profile"] = {}
    except Exception as e:
        logger.warning(f"Data enrichment (fundamental_profile) failed for {symbol}: {e}", exc_info=True)
        strategy_summary["fundamental_profile"] = {}
    # Analyst data (async FMP calls; optional per design §2.2)
    try:
        estimates = await service.get_analyst_estimates(symbol, period="quarter", limit=5)
        price_target = await service.get_price_target_summary(symbol)
        if isinstance(estimates, dict) and "error" not in estimates:
            strategy_summary["analyst_data"] = strategy_summary.get("analyst_data") or {}
            strategy_summary["analyst_data"]["estimates"] = estimates
        if isinstance(price_target, dict) and "error" not in price_target:
            strategy_summary["analyst_data"] = strategy_summary.get("analyst_data") or {}
            strategy_summary["analyst_data"]["price_target"] = price_target
        if strategy_summary.get("analyst_data"):
            logger.info(f"Data enrichment: analyst_data injected for {symbol}")
    except Exception as e:
        logger.warning(f"Data enrichment (analyst_data) failed for {symbol}: {e}", exc_info=True)
        if "analyst_data" not in strategy_summary:
            strategy_summary["analyst_data"] = {}
    # iv_context from fundamental_profile/volatility (design §2.2)
    try:
        profile = strategy_summary.get("fundamental_profile") or {}
        vol = profile.get("volatility") or {}
        if isinstance(vol, dict) and "error" not in vol:
            annualized = vol.get("annualized")
            if annualized is None and vol:
                # _dataframe_to_dict may return nested {ticker: {date: value}} or similar
                for k, v in vol.items():
                    if isinstance(v, (int, float)):
                        annualized = float(v)
                        break
                    if isinstance(v, dict):
                        for vv in v.values() if hasattr(v, "values") else []:
                            if isinstance(vv, (int, float)):
                                annualized = float(vv)
                                break
                        if annualized is not None:
                            break
            if annualized is not None:
                pct = float(annualized) * 100.0 if float(annualized) < 2 else float(annualized)
                strategy_summary["iv_context"] = {
                    "historical_volatility": annualized,
                    "historical_volatility_pct": round(pct, 2),
                    "source": "fundamental_profile",
                }
                strategy_summary["iv_context"]["summary"] = (
                    f"Historical volatility (annualized): {strategy_summary['iv_context']['historical_volatility_pct']}%."
                )
                logger.info(f"Data enrichment: iv_context injected for {symbol}")
        if "iv_context" not in strategy_summary:
            strategy_summary["iv_context"] = {}
    except Exception as e:
        logger.warning(f"Data enrichment (iv_context) failed for {symbol}: {e}", exc_info=True)
        if "iv_context" not in strategy_summary:
            strategy_summary["iv_context"] = {}
    # upcoming_events / catalyst from FMP earnings calendar (design §2.2)
    try:
        start_date = (datetime.now(timezone.utc).date()).strftime("%Y-%m-%d")
        end_date = (datetime.now(timezone.utc).date() + timedelta(days=90)).strftime("%Y-%m-%d")
        earnings_raw = await service._call_fmp_api(
            "earnings-calendar",
            params={"from": start_date, "to": end_date},
        )
        if isinstance(earnings_raw, dict) and (
            "Error Message" in earnings_raw or "error" in str(earnings_raw).lower()
        ):
            earnings_raw = []
        if isinstance(earnings_raw, list):
            events = [e for e in earnings_raw if (e.get("symbol") or "").upper() == symbol]
            strategy_summary["upcoming_events"] = events[:20]
            strategy_summary["catalyst"] = events[:10]
            if events:
                logger.info(f"Data enrichment: upcoming_events/catalyst injected for {symbol} ({len(events)} events)")
        if "upcoming_events" not in strategy_summary:
            strategy_summary["upcoming_events"] = []
        if "catalyst" not in strategy_summary:
            strategy_summary["catalyst"] = []
    except Exception as e:
        logger.warning(f"Data enrichment (upcoming_events) failed for {symbol}: {e}", exc_info=True)
        if "upcoming_events" not in strategy_summary:
            strategy_summary["upcoming_events"] = []
        if "catalyst" not in strategy_summary:
            strategy_summary["catalyst"] = []
    # historical_prices when missing (design §2.2): last ~60 days for technical/volatility (timeout: SSL/Yahoo in Docker)
    try:
        hp = strategy_summary.get("historical_prices")
        if not hp or (isinstance(hp, list) and len(hp) < 2):
            hist = await asyncio.wait_for(
                asyncio.to_thread(service.get_historical_data, symbol, "daily"),
                timeout=60.0,
            )
            data = (hist or {}).get("data") or {}
            if isinstance(data, dict) and data:
                rows = []
                # Data may be {date: {Open, High, Low, Close, Volume}} or {metric: {date: value}}
                items = list(data.items())
                first_key, first_val = items[0], items[0][1] if items else (None, None)
                looks_like_date_key = (
                    first_key
                    and isinstance(first_key, str)
                    and (len(str(first_key)) >= 8 and str(first_key)[:4].isdigit())
                )
                if looks_like_date_key and isinstance(first_val, dict):
                    # Standard: date -> OHLCV dict
                    sorted_items = sorted(items, key=lambda x: str(x[0]))
                    for date_str, row in sorted_items[-60:]:
                        if isinstance(row, dict):
                            rows.append({
                                "date": str(date_str) if date_str else "",
                                "open": row.get("Open") or row.get("open"),
                                "high": row.get("High") or row.get("high"),
                                "low": row.get("Low") or row.get("low"),
                                "close": row.get("Close") or row.get("close"),
                                "volume": row.get("Volume") or row.get("volume"),
                            })
                elif isinstance(first_val, dict):
                    # Inverted: metric -> {date: value}; reconstruct OHLCV by date
                    dates_set: set[str] = set()
                    for _, inner in items:
                        if isinstance(inner, dict):
                            dates_set.update(str(k) for k in inner.keys() if k)
                    ohlcv_keys = {"open", "high", "low", "close", "volume"}
                    for date_str in sorted(dates_set)[-60:]:
                        row = {}
                        for metric_key, date_vals in items:
                            if isinstance(date_vals, dict):
                                v = date_vals.get(date_str)
                                if v is not None:
                                    mk = str(metric_key).lower()
                                    if mk in ohlcv_keys:
                                        row[mk] = v
                        if row.get("close") is not None:
                            rows.append({
                                "date": date_str,
                                "open": row.get("open"),
                                "high": row.get("high"),
                                "low": row.get("low"),
                                "close": row.get("close"),
                                "volume": row.get("volume"),
                            })
                if rows:
                    strategy_summary["historical_prices"] = rows
                    logger.info(f"Data enrichment: historical_prices injected for {symbol} ({len(rows)} days)")
        if "historical_prices" not in strategy_summary:
            strategy_summary["historical_prices"] = []
    except asyncio.TimeoutError:
        logger.warning(f"Data enrichment (historical_prices) timed out for {symbol} (SSL/Yahoo may fail in Docker)")
        if "historical_prices" not in strategy_summary:
            strategy_summary["historical_prices"] = []
    except Exception as e:
        logger.warning(f"Data enrichment (historical_prices) failed for {symbol}: {e}", exc_info=True)
        if "historical_prices" not in strategy_summary:
            strategy_summary["historical_prices"] = []
    # sentiment / market_sentiment: FMP stock news summary if available (design §2.2)
    try:
        news_raw = await service._call_fmp_api(
            "news/stock",
            params={"symbols": symbol, "limit": 5},
        )
        if isinstance(news_raw, dict) and (
            "Error Message" in news_raw or "error" in str(news_raw).lower()
        ):
            news_raw = []
        if isinstance(news_raw, list) and news_raw:
            strategy_summary["sentiment"] = {"recent_news": news_raw[:5]}
            strategy_summary["market_sentiment"] = "See sentiment.recent_news for latest headlines."
            logger.info(f"Data enrichment: sentiment (news) injected for {symbol}")
        if "sentiment" not in strategy_summary:
            strategy_summary["sentiment"] = {}
        if "market_sentiment" not in strategy_summary:
            strategy_summary["market_sentiment"] = None
    except Exception as e:
        logger.warning(f"Data enrichment (sentiment) failed for {symbol}: {e}", exc_info=True)
        if "sentiment" not in strategy_summary:
            strategy_summary["sentiment"] = {}
        if "market_sentiment" not in strategy_summary:
            strategy_summary["market_sentiment"] = None


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


def _get_multi_agent_stages_initial() -> list[dict[str, Any]]:
    """Return initial stages structure for multi_agent_report (design §5.2)."""
    return [
        {
            "id": "data_enrichment",
            "name": "Data Enrichment",
            "status": "pending",
            "started_at": None,
            "ended_at": None,
            "message": None,
        },
        {
            "id": "phase_a",
            "name": "Multi-Agent Analysis",
            "status": "pending",
            "started_at": None,
            "ended_at": None,
            "message": None,
            "sub_stages": [
                {"id": "greeks", "name": "Greeks Analyst", "status": "pending"},
                {"id": "iv", "name": "IV Environment", "status": "pending"},
                {"id": "market", "name": "Market Context", "status": "pending"},
                {"id": "risk", "name": "Risk Scenario", "status": "pending"},
                {"id": "synthesis", "name": "Internal Synthesis", "status": "pending"},
            ],
        },
        {
            "id": "phase_a_plus",
            "name": "Strategy Recommendation",
            "status": "pending",
            "started_at": None,
            "ended_at": None,
            "message": None,
        },
        {
            "id": "phase_b",
            "name": "Deep Research",
            "status": "pending",
            "started_at": None,
            "ended_at": None,
            "message": None,
            "sub_stages": [
                {"id": "planning", "name": "Planning", "status": "pending"},
                {"id": "research", "name": "Research (4 questions)", "status": "pending"},
                {"id": "synthesis", "name": "Final Synthesis", "status": "pending"},
            ],
        },
    ]


def _update_stage(
    task: Task,
    stage_id: str,
    status: str,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
    message: str | None = None,
    set_sub_stages_status: str | None = None,
) -> None:
    """Update one stage in task_metadata.stages by id (design §5.2). Mutates task in place.
    Must flag task_metadata modified so SQLAlchemy persists the JSON change on commit.
    """
    if task.task_metadata is None:
        task.task_metadata = {}
    stages = task.task_metadata.get("stages")
    if not stages:
        return
    for s in stages:
        if s.get("id") == stage_id:
            s["status"] = status
            if started_at is not None:
                s["started_at"] = started_at.isoformat()
            if ended_at is not None:
                s["ended_at"] = ended_at.isoformat()
            if message is not None:
                s["message"] = message
            if set_sub_stages_status and "sub_stages" in s:
                for sub in s.get("sub_stages", []):
                    sub["status"] = set_sub_stages_status
            break
    flag_modified(task, "task_metadata")


# Map executor agent names to phase_a sub_stage ids (for live UI updates)
_AGENT_NAME_TO_PHASE_A_SUB_STAGE = {
    "options_greeks_analyst": "greeks",
    "iv_environment_analyst": "iv",
    "market_context_analyst": "market",
    "risk_scenario_analyst": "risk",
    "options_synthesis_agent": "synthesis",
}


async def _update_phase_a_sub_stage_async(task_id: UUID, sub_stage_id: str, status: str) -> None:
    """Update one Phase A sub_stage status in DB so UI shows running/success per agent."""
    from app.db.session import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as progress_session:
            progress_result = await progress_session.execute(select(Task).where(Task.id == task_id))
            progress_task = progress_result.scalar_one_or_none()
            if not progress_task or not progress_task.task_metadata:
                return
            stages = progress_task.task_metadata.get("stages") or []
            for s in stages:
                if s.get("id") != "phase_a" or "sub_stages" not in s:
                    continue
                for sub in s.get("sub_stages", []):
                    if sub.get("id") == sub_stage_id:
                        sub["status"] = status
                        break
                break
            flag_modified(progress_task, "task_metadata")
            progress_task.updated_at = datetime.now(timezone.utc)
            await progress_session.commit()
    except Exception as e:
        logger.warning("Failed to update phase_a sub_stage for task %s: %s", task_id, e)


async def _update_phase_b_sub_stage_async(task_id: UUID, sub_stage_id: str, status: str) -> None:
    """Update one Phase B (Deep Research) sub_stage status in DB for UI."""
    from app.db.session import AsyncSessionLocal
    try:
        async with AsyncSessionLocal() as progress_session:
            progress_result = await progress_session.execute(select(Task).where(Task.id == task_id))
            progress_task = progress_result.scalar_one_or_none()
            if not progress_task or not progress_task.task_metadata:
                return
            stages = progress_task.task_metadata.get("stages") or []
            for s in stages:
                if s.get("id") != "phase_b" or "sub_stages" not in s:
                    continue
                for sub in s.get("sub_stages", []):
                    if sub.get("id") == sub_stage_id:
                        sub["status"] = status
                        break
                break
            flag_modified(progress_task, "task_metadata")
            progress_task.updated_at = datetime.now(timezone.utc)
            await progress_session.commit()
    except Exception as e:
        logger.warning("Failed to update phase_b sub_stage for task %s: %s", task_id, e)


async def _update_task_status_failed(
    task_id: UUID,
    error_message: str,
    session: AsyncSession | None = None,
) -> None:
    """Update task status to FAILED using independent session.
    
    This function uses its own database session to avoid nested transaction issues.
    
    Args:
        task_id: Task UUID
        error_message: Error message (will be truncated to 500 chars)
        session: Optional existing session (if None, creates new one)
    """
    from app.db.session import AsyncSessionLocal
    
    if session is not None:
        # Use provided session (caller manages transaction)
        try:
            result = await session.execute(select(Task).where(Task.id == task_id))
            task = result.scalar_one_or_none()
            if task:
                failed_at = datetime.now(timezone.utc)
                task.status = "FAILED"
                task.error_message = error_message[:500] if error_message else "Unknown error"
                task.completed_at = failed_at
                task.updated_at = failed_at
                
                if task.execution_history is None:
                    task.execution_history = []
                task.execution_history = _add_execution_event(
                    task.execution_history,
                    "error",
                    f"Task failed: {error_message[:200]}",
                    failed_at,
                )
                # Note: Caller must commit
                logger.info(f"Task {task_id} status updated to FAILED (using existing session)")
        except Exception as update_error:
            logger.critical(
                f"CRITICAL: Failed to update task {task_id} status: {update_error}",
                exc_info=True,
            )
    else:
        # Create new session (this function manages transaction)
        async with AsyncSessionLocal() as new_session:
            try:
                result = await new_session.execute(select(Task).where(Task.id == task_id))
                task = result.scalar_one_or_none()
                if task:
                    failed_at = datetime.now(timezone.utc)
                    task.status = "FAILED"
                    task.error_message = error_message[:500] if error_message else "Unknown error"
                    task.completed_at = failed_at
                    task.updated_at = failed_at
                    
                    if task.execution_history is None:
                        task.execution_history = []
                    task.execution_history = _add_execution_event(
                        task.execution_history,
                        "error",
                        f"Task failed: {error_message[:200]}",
                        failed_at,
                    )
                    await new_session.commit()
                    logger.info(f"Task {task_id} status updated to FAILED")
                else:
                    logger.warning(f"Task {task_id} not found when updating status to FAILED")
            except Exception as update_error:
                # Critical: If we can't update the task status, log heavily
                logger.critical(
                    f"CRITICAL: Failed to update task {task_id} status after error. "
                    f"Original error: {error_message}, Update error: {update_error}",
                    exc_info=True,
                    extra={
                        "task_id": str(task_id),
                        "original_error": error_message,
                        "update_error": str(update_error),
                    }
                )
                await new_session.rollback()
                # Consider sending alert to monitoring service (Sentry, PagerDuty, etc.)


async def _handle_ai_report_task(
    task_id: UUID,
    task: Task,
    metadata: dict[str, Any] | None,
    session: AsyncSession
) -> None:
    from app.services.ai_service import ai_service
    from app.core.config import settings
    from app.services.config_service import config_service
    MAX_RETRIES = RetryConfig.MAX_RETRIES
    # Import here to avoid circular imports
    strategy_summary = metadata.get("strategy_summary") if metadata else None
    option_chain = metadata.get("option_chain") if metadata else None

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
    _ensure_portfolio_greeks(strategy_summary, option_chain)
    # Data enrichment for single-report path (§6.4: leverage Tiger/FMP data)
    await _run_data_enrichment(strategy_summary)
    if task.task_metadata is not None:
        flag_modified(task, "task_metadata")

    # Get prompt template (will be formatted by AI provider)
    from app.services.ai.gemini_provider import DEFAULT_REPORT_PROMPT_TEMPLATE
    prompt_template = await config_service.get(
        "ai.report_prompt_template",
        default=DEFAULT_REPORT_PROMPT_TEMPLATE
    )
    # Record model in task (supports Gemini and ZenMux)
    provider = ai_service._get_provider()
    task.model_used = getattr(provider, "model_name", None) or settings.ai_model_default
    task.execution_history = _add_execution_event(
        task.execution_history,
        "info",
        f"Using AI provider: {ai_service._default_provider_name}, model: {task.model_used}",
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
                wait_time = RetryConfig.INITIAL_WAIT_SECONDS * (RetryConfig.BACKOFF_MULTIPLIER ** attempt)
                task.execution_history = _add_execution_event(
                    task.execution_history,
                    "retry",
                    f"Retry attempt {attempt}/{MAX_RETRIES} after {wait_time}s wait",
                )
                task.retry_count = attempt
                await session.commit()
                await asyncio.sleep(wait_time)
        
            # Always use Deep Research mode (quick mode removed)
            preferred_model_id = (metadata or {}).get("preferred_model_id")
            logger.info(f"Task {task_id} - Starting Deep Research AI report generation (attempt {attempt + 1})")
            report_content = await ai_service.generate_deep_research_report(
                strategy_summary=strategy_summary,
                option_chain=option_chain,
                progress_callback=progress_callback,
                preferred_model_id=preferred_model_id,
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
    input_summary, data_anomaly = _build_input_summary(strategy_summary, option_chain)
    if data_anomaly:
        input_summary += "\n**Confidence Adjustment:** Reduced due to missing Greeks.\n"
    report_content = f"{input_summary}\n{report_content}"
    from app.db.models import AIReport, User

    # Get user to increment usage
    user_result = await session.execute(
        select(User).where(User.id == task.user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise ValueError(f"User {task.user_id} not found")

    # One run = 5 units (same as Deep Research). UI only exposes one report type; fallback still counts as one run.
    from app.api.endpoints.ai import check_ai_quota

    await check_ai_quota(user, session, required_quota=5)

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

    # One run = 5 units (unified with Deep Research). Fallback to simple report still counts as one run.
    from app.api.endpoints.ai import increment_ai_usage

    await increment_ai_usage(user, session, quota_units=5)

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


async def _handle_daily_picks_task(
    task_id: UUID,
    task: Task,
    metadata: dict[str, Any] | None,
    session: AsyncSession
) -> None:
    from app.services.ai_service import ai_service
    from app.core.config import settings
    from app.services.config_service import config_service
    MAX_RETRIES = RetryConfig.MAX_RETRIES
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


async def _handle_anomaly_scan_task(
    task_id: UUID,
    task: Task,
    metadata: dict[str, Any] | None,
    session: AsyncSession
) -> None:
    from app.services.ai_service import ai_service
    from app.core.config import settings
    from app.services.config_service import config_service
    MAX_RETRIES = RetryConfig.MAX_RETRIES
    # Anomaly scan task (system task)
    from app.services.anomaly_service import AnomalyService
    from app.db.models import Anomaly
    from sqlalchemy import delete
    import pytz

    try:
        service = AnomalyService()
        anomalies = await service.detect_anomalies()
    
        if not anomalies:
            logger.debug("No anomalies detected in this scan")
            task.status = "SUCCESS"
            task.result_ref = json.dumps({"count": 0})
            completed_at = datetime.now(timezone.utc)
            task.completed_at = completed_at
            task.updated_at = completed_at
            await session.commit()
            return
        
        # Save to database
        from datetime import timezone as tz
        cutoff = datetime.now(tz.utc) - timedelta(hours=1)
        await session.execute(
            delete(Anomaly).where(Anomaly.detected_at < cutoff)
        )
    
        # Deduplication: get symbols detected in the last 10 minutes to avoid duplicates
        ten_mins_ago = datetime.now(tz.utc) - timedelta(minutes=10)
        existing_result = await session.execute(
            select(Anomaly.symbol, Anomaly.anomaly_type)
            .where(Anomaly.detected_at >= ten_mins_ago)
        )
        existing_anomalies = {
            (r.symbol, r.anomaly_type) for r in existing_result.all()
        }
    
        added_count = 0
        for anomaly in anomalies:
            sym = anomaly['symbol']
            atype = anomaly['type']
        
            # Skip if we already recorded this type of anomaly for this symbol recently
            if (sym, atype) in existing_anomalies:
                continue
            
            anomaly_record = Anomaly(
                symbol=sym,
                anomaly_type=atype,
                score=int(anomaly.get('score', 0)),
                details=anomaly.get('details', {}),
                ai_insight=anomaly.get('ai_insight'),
                detected_at=datetime.now(tz.utc)
            )
            session.add(anomaly_record)
            added_count += 1
        
        await session.commit()
    
        task.status = "SUCCESS"
        task.result_ref = json.dumps({"count": added_count, "detected": len(anomalies)})
        completed_at = datetime.now(timezone.utc)
        task.completed_at = completed_at
        task.updated_at = completed_at
        task.execution_history = _add_execution_event(
            task.execution_history,
            "success",
            f"Anomalies scanned successfully. Found {len(anomalies)}.",
            completed_at,
        )
        await session.commit()
        logger.info(f"✅ Task {task_id} completed: Anomalies detected: {len(anomalies)}")
    except Exception as e:
        logger.error(f"❌ Failed to process anomaly scan task: {e}", exc_info=True)
        task.status = "FAILED"
        task.error_message = str(e)
        task.updated_at = datetime.now(timezone.utc)
        await session.commit()


async def _handle_multi_agent_report_task(
    task_id: UUID,
    task: Task,
    metadata: dict[str, Any] | None,
    session: AsyncSession
) -> None:
    from app.services.ai_service import ai_service
    from app.core.config import settings
    from app.services.config_service import config_service
    MAX_RETRIES = RetryConfig.MAX_RETRIES
    # Full pipeline per spec: Data Enrichment → Phase A → Phase A+ → Phase B (Deep Research)
    from app.services.ai_service import ai_service
    from app.api.endpoints.ai import check_ai_quota, increment_ai_usage, get_ai_quota_limit
    from app.db.models import AIReport
    from app.core.config import settings

    strategy_summary = metadata.get("strategy_summary") if metadata else None
    option_chain = metadata.get("option_chain") if metadata else None
    use_multi_agent = metadata.get("use_multi_agent", True)  # Default to multi-agent for async

    if not strategy_summary:
        raise ValueError("Missing strategy_summary in metadata for multi_agent_report")
    # Fetch option_chain from Tiger when missing (design §2.2)
    if option_chain is None:
        symbol = (strategy_summary.get("symbol") or "").strip().upper()
        expiration_date = (
            strategy_summary.get("expiration_date")
            or strategy_summary.get("expiry")
            or ""
        )
        if isinstance(expiration_date, (datetime, date)):
            expiration_date = expiration_date.strftime("%Y-%m-%d")
        else:
            expiration_date = (expiration_date or "").strip() if isinstance(expiration_date, str) else ""
        if symbol and expiration_date:
            try:
                from app.services.tiger_service import tiger_service
                option_chain = await tiger_service.get_option_chain(
                    symbol, expiration_date
                )
                if option_chain and (
                    option_chain.get("calls") is not None
                    or option_chain.get("puts") is not None
                ):
                    if task.task_metadata is None:
                        task.task_metadata = {}
                    task.task_metadata["option_chain"] = option_chain
                    task.updated_at = datetime.now(timezone.utc)
                    await session.commit()
                    logger.info(
                        f"Fetched option_chain from Tiger for {symbol} {expiration_date}"
                    )
                else:
                    option_chain = None
            except Exception as tiger_err:
                logger.warning(
                    f"Failed to fetch option_chain from Tiger for {symbol} {expiration_date}: {tiger_err}",
                    exc_info=True,
                )
        else:
            logger.warning(
                "Cannot fetch option_chain: missing symbol or expiration_date in strategy_summary"
            )
    _ensure_portfolio_greeks(strategy_summary, option_chain)
    # Initialize task_metadata.stages for UI (design §5.2)
    if task.task_metadata is None:
        task.task_metadata = {}
    if not task.task_metadata.get("stages"):
        task.task_metadata["stages"] = _get_multi_agent_stages_initial()
        task.task_metadata["progress"] = 0
        task.task_metadata["current_stage"] = "Data Enrichment..."
        flag_modified(task, "task_metadata")
        task.updated_at = datetime.now(timezone.utc)
        await session.commit()
    # Data Enrichment: inject fundamental_profile etc. (design §2.2)
    # Note: _run_data_enrichment catches all exceptions internally and never raises.
    now_de = datetime.now(timezone.utc)
    _update_stage(task, "data_enrichment", "running", started_at=now_de)
    flag_modified(task, "task_metadata")
    task.updated_at = now_de
    await session.commit()
    await _run_data_enrichment(strategy_summary)
    # Persist enriched strategy_summary (fundamental_profile, analyst_data, etc.) so Input Data tab shows it
    if task.task_metadata is not None:
        flag_modified(task, "task_metadata")
    now_de_end = datetime.now(timezone.utc)
    _update_stage(task, "data_enrichment", "success", ended_at=now_de_end)
    flag_modified(task, "task_metadata")
    task.updated_at = now_de_end
    await session.commit()

    # Get user for quota check
    user_id = task.user_id
    user = None
    required_quota = 5 if use_multi_agent else 1
    if user_id:
        from app.db.models import User
        user_result = await session.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()
        if user:
            await check_ai_quota(user, session, required_quota=required_quota)
        
            task.execution_history = _add_execution_event(
                task.execution_history,
                "info",
                f"Quota checked: {required_quota} units required",
            )
            flag_modified(task, "execution_history")
            await session.commit()

    # Record model
    task.model_used = settings.ai_model_default
    task.execution_history = _add_execution_event(
        task.execution_history,
        "info",
        f"Using AI model: {task.model_used} (multi-agent: {use_multi_agent})",
    )
    flag_modified(task, "execution_history")
    await session.commit()

    # Progress callback: update execution_history and task_metadata (progress, current_stage)
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    def _emit_progress(progress: int, message: str) -> None:
        if loop is None:
            logger.debug(f"[{progress}%] {message} (progress update skipped)")
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
                        if progress_task.task_metadata is None:
                            progress_task.task_metadata = {}
                        progress_task.task_metadata["progress"] = progress
                        progress_task.task_metadata["current_stage"] = message
                        progress_task.updated_at = datetime.now(timezone.utc)
                        await progress_session.commit()
            except Exception as e:
                logger.warning(f"Failed to update progress for task {task_id}: {e}")
        loop.create_task(update_progress_async())

    # Phase A callback: scale coordinator 0-100 to task 5-45; update sub_stages for UI
    def phase_a_progress_callback(progress: int, message: str) -> None:
        scaled = 5 + int(progress * 0.4)
        _emit_progress(scaled, f"Phase A: {message}")
        # Live-update Multi-Agent sub_stages (Greeks, IV, Market, Risk, Synthesis)
        # Support both "Agent name: status" and "Agent name status" (executor uses space)
        if loop and message.startswith("Agent "):
            rest = message[6:].strip()  # after "Agent "
            agent_name = None
            status = None
            if ": " in rest:
                part0, rest = rest.split(": ", 1)
                agent_name = part0.strip()
                rest_lower = rest.lower()
            else:
                parts = rest.rsplit(maxsplit=1)
                if len(parts) == 2:
                    agent_name, suffix = parts
                    rest_lower = suffix.lower()
                else:
                    rest_lower = rest.lower()
            if not agent_name:
                agent_name = rest.split()[0] if rest.split() else None
            if rest_lower:
                if "started" in rest_lower or "initializing" in rest_lower or "executing" in rest_lower:
                    status = "running"
                elif "succeeded" in rest_lower or "completed" in rest_lower:
                    status = "success"
                elif "failed" in rest_lower:
                    status = "failed"
            if status and agent_name:
                sub_id = _AGENT_NAME_TO_PHASE_A_SUB_STAGE.get(agent_name)
                if sub_id:
                    loop.create_task(_update_phase_a_sub_stage_async(task_id, sub_id, status))

    # Phase B callback: scale deep research 0-100 to task 50-100; update sub_stages for UI
    def phase_b_progress_callback(progress: int, message: str) -> None:
        scaled = 50 + int(progress * 0.5)
        _emit_progress(scaled, f"Phase B: {message}")
        # Live-update Deep Research sub_stages (Planning, Research, Synthesis)
        if loop and message:
            m = message.lower()
            if "planning research" in m or ("planning" in m and "questions" in m):
                loop.create_task(_update_phase_b_sub_stage_async(task_id, "planning", "running"))
            elif "generated" in m and "research questions" in m:
                loop.create_task(_update_phase_b_sub_stage_async(task_id, "planning", "success"))
                loop.create_task(_update_phase_b_sub_stage_async(task_id, "research", "running"))
            elif "researching" in m and "parallel" in m:
                loop.create_task(_update_phase_b_sub_stage_async(task_id, "research", "running"))
            elif "research phase completed" in m or "synthesizing final" in m:
                loop.create_task(_update_phase_b_sub_stage_async(task_id, "research", "success"))
                loop.create_task(_update_phase_b_sub_stage_async(task_id, "synthesis", "running"))
            elif "deep research report completed" in m or "report completed" in m:
                loop.create_task(_update_phase_b_sub_stage_async(task_id, "synthesis", "success"))

    # Data Enrichment done (0-5%); Phase A (5-45%)
    _emit_progress(5, "Phase A: Multi-agent analysis...")
    now_a = datetime.now(timezone.utc)
    _update_stage(task, "phase_a", "running", started_at=now_a)
    task.updated_at = now_a
    task.execution_history = _add_execution_event(
        task.execution_history,
        "info",
        "Starting Phase A: Multi-agent report generation...",
    )
    await session.commit()

    # Phase A with timeout 8 min (all 5 agents: Greeks, IV, Market, Risk, Synthesis)
    PHASE_A_TIMEOUT = 480
    try:
        phase_a_result = await asyncio.wait_for(
            ai_service.generate_report_with_agents(
                strategy_summary=strategy_summary,
                use_multi_agent=use_multi_agent,
                option_chain=option_chain,
                progress_callback=phase_a_progress_callback,
            ),
            timeout=PHASE_A_TIMEOUT,
        )
    except asyncio.TimeoutError:
        now_a_end = datetime.now(timezone.utc)
        _update_stage(task, "phase_a", "failed", ended_at=now_a_end, message="Phase A timed out (8 min)")
        task.updated_at = now_a_end
        await session.commit()
        raise ValueError("Multi-agent analysis timed out (8 min)") from None
    if isinstance(phase_a_result, dict):
        agent_summaries = phase_a_result.get("agent_summaries") or {}
        internal_preliminary_report = phase_a_result.get("internal_preliminary_report") or phase_a_result.get("report_text") or ""
    else:
        agent_summaries = {}
        internal_preliminary_report = ""

    if task.task_metadata is None:
        task.task_metadata = {}
    task.task_metadata["agent_summaries"] = agent_summaries
    now_a_end = datetime.now(timezone.utc)
    await session.refresh(task)  # pick up sub_stage updates from progress callbacks
    _update_stage(task, "phase_a", "success", ended_at=now_a_end, set_sub_stages_status="success")
    task.updated_at = now_a_end
    await session.commit()
    _emit_progress(45, "Phase A+: Strategy recommendation...")
    now_a_plus = datetime.now(timezone.utc)
    _update_stage(task, "phase_a_plus", "running", started_at=now_a_plus)
    task.updated_at = now_a_plus
    await session.commit()

    # Phase A+: Strategy recommendation (45-50%)
    fundamental_profile = strategy_summary.get("fundamental_profile") or {}
    recommended_strategies: list[dict[str, Any]] = []
    if option_chain and agent_summaries:
        try:
            recommended_strategies = await ai_service.generate_strategy_recommendations(
                option_chain=option_chain,
                strategy_summary=strategy_summary,
                fundamental_profile=fundamental_profile,
                agent_summaries=agent_summaries,
            )
        except Exception as e:
            logger.warning(f"Phase A+ strategy recommendation failed: {e}", exc_info=True)
    task.task_metadata["recommended_strategies"] = recommended_strategies
    now_a_plus_end = datetime.now(timezone.utc)
    _update_stage(task, "phase_a_plus", "success", ended_at=now_a_plus_end)
    task.updated_at = now_a_plus_end
    await session.commit()
    _emit_progress(50, "Phase B: Deep Research (planning, research, synthesis)...")
    now_b = datetime.now(timezone.utc)
    _update_stage(task, "phase_b", "running", started_at=now_b)
    task.updated_at = now_b
    await session.commit()

    # Phase B: Deep Research (planning + 4 research + synthesis); synthesis alone can take ~15–20 min
    PHASE_B_TIMEOUT = 1800  # 30 min total
    preferred_model_id = (metadata or {}).get("preferred_model_id")
    try:
        phase_b_result = await asyncio.wait_for(
            ai_service.generate_deep_research_report(
                strategy_summary=strategy_summary,
                option_chain=option_chain,
                progress_callback=phase_b_progress_callback,
                agent_summaries=agent_summaries,
                recommended_strategies=recommended_strategies,
                internal_preliminary_report=internal_preliminary_report,
                preferred_model_id=preferred_model_id,
            ),
            timeout=PHASE_B_TIMEOUT,
        )
    except asyncio.TimeoutError:
        now_b_end = datetime.now(timezone.utc)
        _update_stage(
            task, "phase_b", "failed",
            ended_at=now_b_end,
            message="Phase B timed out (30 min)",
            set_sub_stages_status="failed",
        )
        task.updated_at = now_b_end
        await session.commit()
        raise ValueError("Deep Research timed out (30 min)") from None
    if isinstance(phase_b_result, dict):
        report_content = phase_b_result.get("report") or ""
        task.task_metadata["research_questions"] = phase_b_result.get("research_questions") or []
        full_prompt = phase_b_result.get("full_prompt")
        if full_prompt:
            task.prompt_used = full_prompt
            logger.info(f"Task {task_id} - Deep Research full prompt saved: {len(full_prompt)} chars")
    else:
        report_content = phase_b_result or ""
    input_summary, data_anomaly = _build_input_summary(strategy_summary, option_chain)
    if data_anomaly:
        input_summary += "\n**Confidence Adjustment:** Reduced due to missing Greeks.\n"
    report_content = f"{input_summary}\n{report_content}"

    now_b_end = datetime.now(timezone.utc)
    await session.refresh(task)  # pick up Phase B sub_stage updates from progress callbacks
    _update_stage(task, "phase_b", "success", ended_at=now_b_end, set_sub_stages_status="success")

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

    # Update task with result and final task_metadata (stages for UI)
    task.result_ref = str(ai_report.id)
    task.status = "SUCCESS"
    task.completed_at = datetime.now(timezone.utc)
    task.updated_at = task.completed_at
    task.task_metadata["progress"] = 100
    task.task_metadata["current_stage"] = "Complete"
    # stages already updated with started_at/ended_at/sub_stages; do not overwrite
    task.execution_history = _add_execution_event(
        task.execution_history,
        "success",
        f"Full pipeline completed. Report ID: {ai_report.id}",
        task.completed_at,
    )

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



async def _handle_options_analysis_workflow_task(
    task_id: UUID,
    task: Task,
    metadata: dict[str, Any] | None,
    session: AsyncSession
) -> None:
    from app.services.ai_service import ai_service
    from app.core.config import settings
    from app.services.config_service import config_service
    MAX_RETRIES = RetryConfig.MAX_RETRIES
    # Options analysis workflow (async)
    from app.services.ai_service import ai_service
    from app.api.endpoints.ai import check_ai_quota, increment_ai_usage

    strategy_summary = metadata.get("strategy_summary") if metadata else None
    option_chain = metadata.get("option_chain") if metadata else None
    if not strategy_summary:
        raise ValueError("Missing strategy_summary in metadata for options_analysis_workflow")
    _ensure_portfolio_greeks(strategy_summary, option_chain)

    # Get user for quota check
    user_id = task.user_id
    if user_id:
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
        option_chain=option_chain,
        progress_callback=progress_callback,
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



async def _handle_stock_screening_workflow_task(
    task_id: UUID,
    task: Task,
    metadata: dict[str, Any] | None,
    session: AsyncSession
) -> None:
    from app.services.ai_service import ai_service
    from app.core.config import settings
    from app.services.config_service import config_service
    MAX_RETRIES = RetryConfig.MAX_RETRIES
    # Stock screening workflow (async)
    from app.services.ai_service import ai_service
    from app.api.endpoints.ai import check_ai_quota, increment_ai_usage

    criteria = metadata.get("criteria") if metadata else None
    if not criteria:
        raise ValueError("Missing criteria in metadata for stock_screening_workflow")

    # Get user for quota check
    user_id = task.user_id
    if user_id:
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
        progress_callback=progress_callback,
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



async def _handle_generate_strategy_chart_task(
    task_id: UUID,
    task: Task,
    metadata: dict[str, Any] | None,
    session: AsyncSession
) -> None:
    from app.services.ai_service import ai_service
    from app.core.config import settings
    from app.services.config_service import config_service
    MAX_RETRIES = RetryConfig.MAX_RETRIES
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


async def process_task_async(
    task_id: UUID,
    task_type: str,
    metadata: dict[str, Any] | None,
    # ⚠️ DEPRECATED: db parameter is ignored. This function creates its own session.
    # Will be removed in v2.0. Do not pass db parameter.
    db: AsyncSession | None = None,  # Deprecated, ignored
) -> None:
    """
    Process a task asynchronously in the background with retry support.

    Args:
        task_id: Task UUID
        task_type: Task type
        metadata: Task metadata
        db: DEPRECATED - Ignored. This function creates its own database session.
    
    Note:
        This function creates its own database session for processing.
        The db parameter is deprecated and will be removed in v2.0.
        All database operations use an internally created session.
    """
    from app.db.session import AsyncSessionLocal
    from app.services.ai_service import ai_service
    from app.core.config import settings
    from app.services.config_service import config_service

    MAX_RETRIES = RetryConfig.MAX_RETRIES

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
                await _handle_ai_report_task(task_id, task, metadata, session)
            elif task_type == "daily_picks":
                await _handle_daily_picks_task(task_id, task, metadata, session)
            elif task_type == "anomaly_scan":
                await _handle_anomaly_scan_task(task_id, task, metadata, session)
            elif task_type == "multi_agent_report":
                await _handle_multi_agent_report_task(task_id, task, metadata, session)
            elif task_type == "options_analysis_workflow":
                await _handle_options_analysis_workflow_task(task_id, task, metadata, session)
            elif task_type == "stock_screening_workflow":
                await _handle_stock_screening_workflow_task(task_id, task, metadata, session)
            elif task_type == "generate_strategy_chart":
                await _handle_generate_strategy_chart_task(task_id, task, metadata, session)
            else:
                raise ValueError(f"Unknown task type: {task_type}")

        except (ValueError, TypeError, KeyError) as e:
            # Business logic errors - validation, type errors, missing keys
            logger.warning(f"Task {task_id} validation/type error: {e}", exc_info=True)
            await session.rollback()
            # Use independent session to update status (avoid nested transaction issues)
            await _update_task_status_failed(task_id, str(e), session=None)
            raise
        except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
            # Network errors - can be retried
            logger.error(f"Task {task_id} network error: {e}", exc_info=True)
            await session.rollback()
            await _update_task_status_failed(task_id, f"Network error: {str(e)}", session=None)
            raise  # Let retry mechanism handle
        except Exception as e:
            # Unknown errors - log with full context
            logger.critical(f"Task {task_id} unexpected error: {e}", exc_info=True)
            await session.rollback()
            # Use independent session to update status
            await _update_task_status_failed(task_id, str(e), session=None)
            raise
        # ⚠️ CRITICAL: Never catch BaseException (KeyboardInterrupt, SystemExit) - let them propagate
        # This ensures the application can be properly shut down with Ctrl+C


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
    limit: int = Query(20, ge=1, le=200, description="Maximum number of tasks to return"),
    skip: int = Query(0, ge=0, description="Number of tasks to skip"),
    result_ref: str | None = Query(None, description="Filter by result_ref (e.g. report ID for One-Click Load)"),
) -> list[TaskResponse]:
    """
    List tasks for the authenticated user (paginated).

    Returns only tasks owned by the current user, sorted by created_at DESC.
    When result_ref is provided (e.g. report ID), returns the task that produced that result (for recommended_strategies).

    Args:
        current_user: Authenticated user (from JWT token)
        db: Database session
        limit: Maximum number of tasks to return (1-200)
        skip: Number of tasks to skip
        result_ref: Optional filter by result_ref (e.g. AI report ID)

    Returns:
        List of TaskResponse
    """
    try:
        stmt = select(Task).where(Task.user_id == current_user.id)
        if result_ref:
            stmt = stmt.where(Task.result_ref == result_ref)
        stmt = stmt.order_by(Task.created_at.desc()).limit(limit).offset(skip)
        result = await db.execute(stmt)
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

