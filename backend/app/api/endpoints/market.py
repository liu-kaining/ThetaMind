"""Market data API endpoints."""

import logging
import math
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.api.deps import get_current_user
from app.api.schemas import AnomalyResponse, OptionChainResponse, SymbolSearchResponse
from app.schemas.strategy_recommendation import (
    StrategyRecommendationRequest,
    CalculatedStrategy,
)
from app.db.models import Anomaly, User, StockSymbol
from app.db.session import get_db
from app.services.tiger_service import tiger_service
from app.services.market_data_service import MarketDataService
from fastapi.concurrency import run_in_threadpool
from app.services.strategy_engine import StrategyEngine
from app.services.market_data_service import MarketDataService
from app.core.config import settings
from sqlalchemy import select, or_, case
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["market"])

market_data_service = MarketDataService()


def _normalize_number(value: Any, default: float | None = None) -> float | None:
    """
    Normalize a value to a float number, handling various input types.
    
    Supports:
    - int, float
    - str (numeric strings)
    - None -> returns default or None
    
    Returns None if value cannot be converted to a valid number.
    """
    if value is None:
        return default
    if isinstance(value, (int, float)):
        if not (math.isnan(value) or math.isinf(value)):
            return float(value)
        return default
    if isinstance(value, str):
        try:
            num = float(value)
            if not (math.isnan(num) or math.isinf(num)):
                return num
        except (ValueError, TypeError):
            pass
    return default


@router.get("/chain", response_model=OptionChainResponse)
async def get_option_chain(
    symbol: Annotated[str, Query(..., description="Stock symbol (e.g., AAPL)")],
    expiration_date: Annotated[
        str, Query(..., description="Expiration date in YYYY-MM-DD format")
    ],
    current_user: Annotated[User, Depends(get_current_user)],
    force_refresh: Annotated[
        bool, Query(description="Force refresh from API, bypass cache")
    ] = False,
) -> OptionChainResponse:
    """
    Get option chain for a stock symbol and expiration date.

    Cache Strategy: 10 minutes TTL for all users (to conserve API quota).
    Use force_refresh=true to bypass cache and fetch fresh data.
    
    **Free users cannot use force_refresh=true (real-time feature is Pro-only).**

    Args:
        symbol: Stock symbol (e.g., AAPL, TSLA)
        expiration_date: Expiration date in YYYY-MM-DD format
        current_user: Authenticated user (from JWT token)
        force_refresh: If True, bypass cache and fetch fresh data from API (Pro only)

    Returns:
        OptionChainResponse with calls, puts, and spot price

    Raises:
        HTTPException: If market data service is unavailable, invalid parameters, or free user tries to use force_refresh
    """
    # Free users cannot use real-time features (force_refresh)
    if force_refresh and not current_user.is_pro:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Real-time data refresh is a Pro feature. Please upgrade to Pro to use force_refresh=true.",
        )
    
    try:
        # Call tiger service with user's pro status and force_refresh flag
        chain_data = await tiger_service.get_option_chain(
            symbol=symbol.upper(),
            expiration_date=expiration_date,
            is_pro=current_user.is_pro,
            force_refresh=force_refresh,
        )

        # Normalize data structure
        # Extract and normalize calls
        raw_calls = chain_data.get("calls", []) or []
        calls = []
        for call in raw_calls:
            if not call or not isinstance(call, dict):
                continue
            normalized_call = {
                "strike": _normalize_number(call.get("strike") or call.get("strike_price")),
                "bid": _normalize_number(call.get("bid") or call.get("bid_price"), default=0),
                "ask": _normalize_number(call.get("ask") or call.get("ask_price"), default=0),
                "volume": _normalize_number(call.get("volume"), default=0),
                "open_interest": _normalize_number(call.get("open_interest") or call.get("openInterest"), default=0),
            }
            # Add Greeks (support both flat and nested formats)
            greeks = {}
            if isinstance(call.get("greeks"), dict):
                greeks = call["greeks"]
            for greek_name in ["delta", "gamma", "theta", "vega", "rho"]:
                value = call.get(greek_name) or (greeks.get(greek_name) if greeks else None)
                if value is not None:
                    normalized_value = _normalize_number(value)
                    if normalized_value is not None:
                        normalized_call[greek_name] = normalized_value
                        greeks[greek_name] = normalized_value
            if greeks:
                normalized_call["greeks"] = greeks
            
            # Add implied_volatility (critical for AI analysis)
            implied_vol = call.get("implied_vol") or call.get("implied_volatility") or (greeks.get("implied_vol") if greeks else None)
            if implied_vol is not None:
                normalized_iv = _normalize_number(implied_vol)
                if normalized_iv is not None:
                    normalized_call["implied_volatility"] = normalized_iv
                    normalized_call["implied_vol"] = normalized_iv  # Also keep short name for compatibility
            
            # Only add if strike is valid
            if normalized_call["strike"] is not None and normalized_call["strike"] > 0:
                calls.append(normalized_call)

        # Extract and normalize puts
        raw_puts = chain_data.get("puts", []) or []
        puts = []
        for put in raw_puts:
            if not put or not isinstance(put, dict):
                continue
            normalized_put = {
                "strike": _normalize_number(put.get("strike") or put.get("strike_price")),
                "bid": _normalize_number(put.get("bid") or put.get("bid_price"), default=0),
                "ask": _normalize_number(put.get("ask") or put.get("ask_price"), default=0),
                "volume": _normalize_number(put.get("volume"), default=0),
                "open_interest": _normalize_number(put.get("open_interest") or put.get("openInterest"), default=0),
            }
            # Add Greeks (support both flat and nested formats)
            greeks = {}
            if isinstance(put.get("greeks"), dict):
                greeks = put["greeks"]
            for greek_name in ["delta", "gamma", "theta", "vega", "rho"]:
                value = put.get(greek_name) or (greeks.get(greek_name) if greeks else None)
                if value is not None:
                    normalized_value = _normalize_number(value)
                    if normalized_value is not None:
                        normalized_put[greek_name] = normalized_value
                        greeks[greek_name] = normalized_value
            if greeks:
                normalized_put["greeks"] = greeks
            
            # Add implied_volatility (critical for AI analysis)
            implied_vol = put.get("implied_vol") or put.get("implied_volatility") or (greeks.get("implied_vol") if greeks else None)
            if implied_vol is not None:
                normalized_iv = _normalize_number(implied_vol)
                if normalized_iv is not None:
                    normalized_put["implied_volatility"] = normalized_iv
                    normalized_put["implied_vol"] = normalized_iv  # Also keep short name for compatibility
            
            # Only add if strike is valid
            if normalized_put["strike"] is not None and normalized_put["strike"] > 0:
                puts.append(normalized_put)

        # Extract spot price (support multiple field names)
        spot_price = (
            _normalize_number(chain_data.get("spot_price")) or
            _normalize_number(chain_data.get("underlying_price")) or
            _normalize_number(chain_data.get("underlyingPrice")) or
            None
        )
        source = chain_data.get("_source", "api")

        return OptionChainResponse(
            symbol=symbol.upper(),
            expiration_date=expiration_date,
            calls=calls,
            puts=puts,
            spot_price=spot_price,
            source=source,  # Will be serialized as _source due to alias
        )

    except HTTPException:
        # Re-raise HTTP exceptions from service layer (e.g., 503 from Circuit Breaker)
        raise
    except Exception as e:
        logger.error(f"Error fetching option chain for {symbol}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch option chain: {str(e)}",
        )


@router.get("/quote")
async def get_stock_quote(
    symbol: Annotated[str, Query(..., description="Stock symbol (e.g., AAPL)")],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """
    Get stock quote/brief information using FinanceToolkit (FMP API).
    
    ⚠️ OPTIMIZATION: Uses FinanceToolkit to get complete quote data from FMP API.
    This provides price, change, change_percent, and volume (FMP quote API equivalent).

    Args:
        symbol: Stock symbol (e.g., AAPL, TSLA)
        current_user: Authenticated user (from JWT token)

    Returns:
        Dictionary containing stock quote information:
        - price: Current stock price
        - change: Price change from previous close
        - change_percent: Price change percentage
        - volume: Trading volume

    Raises:
        HTTPException: If market data service is unavailable
    """
    try:
        # ⚠️ OPTIMIZATION: Use FinanceToolkit (FMP API) for complete quote data
        quote_data = await run_in_threadpool(
            market_data_service.get_stock_quote, symbol.upper()
        )
        
        if not quote_data or "error" in quote_data:
            # Fallback: try Tiger API price inference (cost-efficient)
            logger.debug(f"FinanceToolkit quote unavailable for {symbol}, trying Tiger API inference")
            estimated_price = await tiger_service.get_realtime_price(symbol.upper())
            
            if estimated_price is None:
                return {
                    "symbol": symbol.upper(),
                    "data": {
                        "price": None,
                        "change": None,
                        "change_percent": None,
                        "volume": None,
                        "error": "Quote data unavailable. Please try again later.",
                    },
                    "is_pro": current_user.is_pro,
                    "price_source": "unavailable",
                }
            
            # Return estimated price (incomplete data)
            return {
                "symbol": symbol.upper(),
                "data": {
                    "price": estimated_price,
                    "change": None,  # Not available from inference
                    "change_percent": None,
                    "volume": None,
                },
                "is_pro": current_user.is_pro,
                "price_source": "inferred",  # Indicate this is an estimated price
            }
        
        # Return complete quote data from FinanceToolkit (FMP)
        return {
            "symbol": symbol.upper(),
            "data": {
                "price": quote_data.get("price"),
                "change": quote_data.get("change"),
                "change_percent": quote_data.get("change_percent"),
                "volume": quote_data.get("volume"),
            },
            "is_pro": current_user.is_pro,
            "price_source": "fmp",  # Indicate this is from FMP API via FinanceToolkit
        }

    except HTTPException:
        # Re-raise HTTP exceptions from service layer
        raise
    except Exception as e:
        logger.error(f"Error fetching stock quote for {symbol}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch stock quote: {str(e)}",
        )


@router.get("/profile")
async def get_financial_profile(
    symbol: Annotated[str, Query(..., description="Stock symbol (e.g., AAPL)")],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """
    Get financial profile data (fundamental + technical indicators).

    Uses MarketDataService (FMP only via FinanceToolkit).
    """
    try:
        profile = await run_in_threadpool(
            market_data_service.get_financial_profile, symbol.upper()
        )
        return profile or {}
    except Exception as e:
        logger.error(f"Error fetching financial profile for {symbol}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch financial profile: {str(e)}",
        )


@router.get("/search", response_model=list[SymbolSearchResponse])
async def search_symbols(
    q: Annotated[str, Query(..., description="Search query (symbol or company name)")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=50, description="Maximum number of results")] = 10,
) -> list[SymbolSearchResponse]:
    """
    Search stock symbols by symbol or company name.
    
    Fast local database search using ILIKE (case-insensitive).
    Returns top results matching symbol or name.
    
    Args:
        q: Search query (e.g., "AAPL" or "Apple")
        limit: Maximum number of results (default: 10, max: 50)
        current_user: Authenticated user (optional, for future rate limiting)
        db: Database session
        
    Returns:
        List of matching symbols with symbol, name, and market
    """
    if not q or len(q.strip()) < 1:
        return []
    
    search_term = f"%{q.strip().upper()}%"
    
    try:
        # Search in both symbol and name fields using ILIKE
        result = await db.execute(
            select(StockSymbol)
            .where(
                or_(
                    StockSymbol.symbol.ilike(search_term),
                    StockSymbol.name.ilike(search_term),
                ),
                StockSymbol.is_active == True,
                StockSymbol.market == "US",
            )
            .order_by(
                # Prioritize exact symbol matches, then name matches
                case(
                    (StockSymbol.symbol.ilike(q.strip().upper()), 0),
                    (StockSymbol.symbol.ilike(search_term), 1),
                    else_=2,
                ),
                StockSymbol.symbol,
            )
            .limit(limit)
        )
        
        symbols = result.scalars().all()
        
        return [
            SymbolSearchResponse(
                symbol=symbol.symbol,
                name=symbol.name,
                market=symbol.market,
            )
            for symbol in symbols
        ]
        
    except Exception as e:
        logger.error(f"Error searching symbols: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search symbols: {str(e)}",
        )


# ==================== P0: Real-time Trading Core ====================

@router.get("/quotes/batch")
async def get_batch_quotes(
    symbols: Annotated[str, Query(..., description="Comma-separated stock symbols (e.g., AAPL,MSFT,GOOGL)")],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """
    Get real-time quotes for multiple symbols.
    
    ⚠️ P0: Direct FMP API integration for batch stock quotes.
    Essential for monitoring multiple positions simultaneously.
    """
    try:
        # Parse comma-separated symbols
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        if not symbol_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one symbol is required",
            )
        
        quotes = await market_data_service.get_batch_quotes(symbol_list)
        return quotes
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching batch quotes: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch batch quotes: {str(e)}",
        )


@router.get("/historical/{interval}")
async def get_historical_price(
    interval: Annotated[str, Path(..., description="Time interval: 1min, 5min, 15min, 30min, 1hour, 4hour, 1day")],
    symbol: Annotated[str, Query(..., description="Stock symbol (e.g., AAPL)")],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int | None, Query(ge=1, le=10000, description="Maximum number of data points")] = None,
) -> dict[str, Any]:
    """
    Get historical price data with various intervals.
    
    ⚠️ P0: Direct FMP API integration for multi-interval historical data.
    Essential for technical analysis and strategy backtesting.
    
    Supported intervals:
    - 1min: 1-minute intervals (intraday)
    - 5min: 5-minute intervals (intraday)
    - 15min: 15-minute intervals (intraday)
    - 30min: 30-minute intervals (intraday)
    - 1hour: 1-hour intervals (intraday)
    - 4hour: 4-hour intervals (intraday)
    - 1day: Daily intervals (EOD)
    """
    try:
        data = await market_data_service.get_historical_price(
            symbol=symbol.upper(),
            interval=interval.lower(),
            limit=limit,
        )
        return data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error fetching historical price for {symbol} ({interval}): {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch historical price: {str(e)}",
        )


@router.get("/technical/{indicator}")
async def get_technical_indicator(
    indicator: Annotated[str, Path(..., description="Technical indicator: sma, ema, rsi, adx, macd, etc.")],
    symbol: Annotated[str, Query(..., description="Stock symbol (e.g., AAPL)")],
    current_user: Annotated[User, Depends(get_current_user)],
    period_length: Annotated[int, Query(ge=1, le=200, description="Period length for calculation")] = 10,
    timeframe: Annotated[str, Query(description="Time frame: 1min, 5min, 15min, 30min, 1hour, 1day")] = "1day",
) -> dict[str, Any]:
    """
    Get technical indicator data.
    
    ⚠️ P0: Direct FMP API integration for technical indicators.
    Essential for strategy signal generation.
    
    Supported indicators:
    - sma: Simple Moving Average
    - ema: Exponential Moving Average
    - rsi: Relative Strength Index
    - adx: Average Directional Index
    - macd: Moving Average Convergence Divergence
    - bollinger_bands: Bollinger Bands
    - williams: Williams %R
    - standarddeviation: Standard Deviation
    - wma: Weighted Moving Average
    - dema: Double Exponential Moving Average
    - tema: Triple Exponential Moving Average
    """
    try:
        data = await market_data_service.get_technical_indicator(
            symbol=symbol.upper(),
            indicator=indicator.lower(),
            period_length=period_length,
            timeframe=timeframe,
        )
        return data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error fetching technical indicator {indicator} for {symbol}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch technical indicator: {str(e)}",
        )


# ==================== P1: Market Performance & Analyst Data ====================

@router.get("/market/sector-performance")
async def get_sector_performance(
    current_user: Annotated[User, Depends(get_current_user)],
    date: Annotated[str | None, Query(description="Date in YYYY-MM-DD format (optional)")] = None,
) -> dict[str, Any]:
    """
    Get sector performance snapshot.
    
    ⚠️ P1: Direct FMP API integration for real-time sector performance data.
    """
    try:
        performance = await market_data_service.get_sector_performance(date=date)
        return performance
    except Exception as e:
        logger.error(f"Error fetching sector performance: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch sector performance: {str(e)}",
        )


@router.get("/market/industry-performance")
async def get_industry_performance(
    current_user: Annotated[User, Depends(get_current_user)],
    date: Annotated[str | None, Query(description="Date in YYYY-MM-DD format (optional)")] = None,
) -> dict[str, Any]:
    """
    Get industry performance snapshot.
    
    ⚠️ P1: Direct FMP API integration for real-time industry performance data.
    """
    try:
        performance = await market_data_service.get_industry_performance(date=date)
        return performance
    except Exception as e:
        logger.error(f"Error fetching industry performance: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch industry performance: {str(e)}",
        )


@router.get("/market/biggest-gainers")
async def get_biggest_gainers(
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict[str, Any]]:
    """
    Get biggest stock gainers.
    
    ⚠️ P1: Direct FMP API integration for real-time market data.
    """
    try:
        gainers = await market_data_service.get_biggest_gainers()
        return gainers
    except Exception as e:
        logger.error(f"Error fetching biggest gainers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch biggest gainers: {str(e)}",
        )


@router.get("/market/biggest-losers")
async def get_biggest_losers(
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict[str, Any]]:
    """
    Get biggest stock losers.
    
    ⚠️ P1: Direct FMP API integration for real-time market data.
    """
    try:
        losers = await market_data_service.get_biggest_losers()
        return losers
    except Exception as e:
        logger.error(f"Error fetching biggest losers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch biggest losers: {str(e)}",
        )


@router.get("/market/most-actives")
async def get_most_actives(
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict[str, Any]]:
    """
    Get most actively traded stocks.
    
    ⚠️ P1: Direct FMP API integration for real-time market data.
    """
    try:
        actives = await market_data_service.get_most_actives()
        return actives
    except Exception as e:
        logger.error(f"Error fetching most actives: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch most actives: {str(e)}",
        )


# P1.2: Analyst Data Endpoints

@router.get("/analyst/estimates")
async def get_analyst_estimates(
    symbol: Annotated[str, Query(..., description="Stock symbol (e.g., AAPL)")],
    current_user: Annotated[User, Depends(get_current_user)],
    period: Annotated[str, Query(description="Period: 'annual' or 'quarter'")] = "annual",
    limit: Annotated[int, Query(ge=1, le=100, description="Maximum number of estimates")] = 10,
) -> dict[str, Any]:
    """
    Get analyst financial estimates.
    
    ⚠️ P1: Direct FMP API integration for analyst estimates (EPS, Revenue, etc.).
    """
    try:
        estimates = await market_data_service.get_analyst_estimates(
            symbol=symbol.upper(),
            period=period,
            limit=limit,
        )
        return estimates
    except Exception as e:
        logger.error(f"Error fetching analyst estimates for {symbol}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch analyst estimates: {str(e)}",
        )


@router.get("/analyst/price-target")
async def get_price_target_summary(
    symbol: Annotated[str, Query(..., description="Stock symbol (e.g., AAPL)")],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """
    Get price target summary.
    
    ⚠️ P1: Direct FMP API integration for analyst price targets.
    """
    try:
        summary = await market_data_service.get_price_target_summary(symbol.upper())
        return summary
    except Exception as e:
        logger.error(f"Error fetching price target summary for {symbol}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch price target summary: {str(e)}",
        )


@router.get("/analyst/price-target-consensus")
async def get_price_target_consensus(
    symbol: Annotated[str, Query(..., description="Stock symbol (e.g., AAPL)")],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """
    Get price target consensus (high, low, median, consensus).
    
    ⚠️ P1: Direct FMP API integration for analyst price target consensus.
    """
    try:
        consensus = await market_data_service.get_price_target_consensus(symbol.upper())
        return consensus
    except Exception as e:
        logger.error(f"Error fetching price target consensus for {symbol}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch price target consensus: {str(e)}",
        )


@router.get("/analyst/grades")
async def get_stock_grades(
    symbol: Annotated[str, Query(..., description="Stock symbol (e.g., AAPL)")],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[dict[str, Any]]:
    """
    Get stock grades/ratings from analysts.
    
    ⚠️ P1: Direct FMP API integration for analyst grades.
    """
    try:
        grades = await market_data_service.get_stock_grades(symbol.upper())
        return grades
    except Exception as e:
        logger.error(f"Error fetching stock grades for {symbol}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch stock grades: {str(e)}",
        )


@router.get("/analyst/ratings")
async def get_ratings_snapshot(
    symbol: Annotated[str, Query(..., description="Stock symbol (e.g., AAPL)")],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """
    Get ratings snapshot.
    
    ⚠️ P1: Direct FMP API integration for financial ratings snapshot.
    """
    try:
        ratings = await market_data_service.get_ratings_snapshot(symbol.upper())
        return ratings
    except Exception as e:
        logger.error(f"Error fetching ratings snapshot for {symbol}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch ratings snapshot: {str(e)}",
        )


# P1.3: TTM Financial Data Endpoints

@router.get("/financial/key-metrics-ttm")
async def get_key_metrics_ttm(
    symbol: Annotated[str, Query(..., description="Stock symbol (e.g., AAPL)")],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """
    Get trailing twelve months (TTM) key metrics.
    
    ⚠️ P1: Direct FMP API integration for TTM financial metrics.
    """
    try:
        metrics = await market_data_service.get_key_metrics_ttm(symbol.upper())
        return metrics
    except Exception as e:
        logger.error(f"Error fetching key metrics TTM for {symbol}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch key metrics TTM: {str(e)}",
        )


@router.get("/financial/ratios-ttm")
async def get_ratios_ttm(
    symbol: Annotated[str, Query(..., description="Stock symbol (e.g., AAPL)")],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    """
    Get trailing twelve months (TTM) financial ratios.
    
    ⚠️ P1: Direct FMP API integration for TTM financial ratios.
    """
    try:
        ratios = await market_data_service.get_ratios_ttm(symbol.upper())
        return ratios
    except Exception as e:
        logger.error(f"Error fetching ratios TTM for {symbol}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch ratios TTM: {str(e)}",
        )


@router.get("/expirations", response_model=list[str])
async def get_option_expirations(
    symbol: Annotated[str, Query(..., description="Stock symbol (e.g., AAPL)")],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[str]:
    """
    Get available option expiration dates for a stock symbol.
    
    This endpoint returns all available expiration dates for options on the given symbol.
    The dates are sorted chronologically.
    
    Args:
        symbol: Stock symbol (e.g., AAPL, TSLA)
        current_user: Authenticated user (from JWT token)
    
    Returns:
        List of expiration dates in YYYY-MM-DD format, sorted chronologically
    
    Raises:
        HTTPException: If market data service is unavailable
    """
    try:
        expirations = await tiger_service.get_option_expirations(symbol.upper())
        return expirations
    except Exception as e:
        logger.error(f"Error fetching option expirations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch option expirations: {str(e)}",
        )


@router.get("/history")
async def get_historical_data(
    symbol: Annotated[str, Query(..., description="Stock symbol (e.g., AAPL)")],
    current_user: Annotated[User, Depends(get_current_user)],
    period: Annotated[str, Query(description="Period type: 'day', 'week', 'month'")] = "day",
    limit: Annotated[int, Query(ge=1, le=500, description="Number of bars to return")] = 100,
) -> dict[str, Any]:
    """
    Get historical K-line (candlestick) data using Tiger's get_bars method.
    
    Uses Tiger's free quota for historical data. Cached for 1 hour.

    Args:
        symbol: Stock symbol (e.g., AAPL, TSLA)
        current_user: Authenticated user (from JWT token)
        period: Period type ('day', 'week', 'month', default: 'day')
        limit: Number of bars to return (1-500, default: 100)

    Returns:
        Dictionary with symbol and list of candlestick data points
    """
    def _format_fmp_history(raw: dict[str, Any]) -> list[dict[str, Any]]:
        data = raw.get("data") or {}
        if not isinstance(data, dict):
            return []
        rows: list[dict[str, Any]] = []
        for date_key, values in data.items():
            if not isinstance(values, dict):
                continue
            open_value = _normalize_number(values.get("Open") or values.get("open"))
            high_value = _normalize_number(values.get("High") or values.get("high"))
            low_value = _normalize_number(values.get("Low") or values.get("low"))
            close_value = _normalize_number(values.get("Close") or values.get("close"))
            volume_value = _normalize_number(values.get("Volume") or values.get("volume"), default=0)
            if all(v is not None for v in [open_value, high_value, low_value, close_value]):
                rows.append(
                    {
                        "time": str(date_key),
                        "open": open_value,
                        "high": high_value,
                        "low": low_value,
                        "close": close_value,
                        "volume": volume_value or 0,
                    }
                )
        rows.sort(key=lambda r: r.get("time") or "")
        if limit and len(rows) > limit:
            return rows[-limit:]
        return rows

    try:
        # Primary: Tiger's get_bars method (free quota)
        kline_data = await tiger_service.get_kline_data(
            symbol=symbol.upper(),
            period=period,
            limit=limit,
        )
        if kline_data:
            return {
                "symbol": symbol.upper(),
                "data": kline_data,
                "_source": "tiger_bars",
            }
        logger.warning(f"Tiger returned empty historical data for {symbol}, trying FMP fallback")
    except HTTPException as e:
        logger.warning(f"Tiger historical data failed for {symbol}: {e.detail}. Trying FMP fallback.")
    except Exception as e:
        logger.warning(f"Tiger historical data error for {symbol}: {e}. Trying FMP fallback.", exc_info=True)

    try:
        fmp_history = await run_in_threadpool(
            market_data_service.get_historical_data,
            symbol.upper(),
            "daily",
        )
        formatted = _format_fmp_history(fmp_history or {})
        if formatted:
            return {
                "symbol": symbol.upper(),
                "data": formatted,
                "_source": "fmp_history",
            }
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Upstream providers returned no historical data",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching historical data for {symbol}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch historical data: {str(e)}",
        )


@router.get("/historical")
async def get_historical_data_legacy(
    symbol: Annotated[str, Query(..., description="Stock symbol (e.g., AAPL)")],
    current_user: Annotated[User, Depends(get_current_user)],
    days: Annotated[int, Query(ge=1, le=365, description="Number of days of historical data")] = 30,
) -> dict[str, Any]:
    """
    Legacy endpoint for historical data (maintained for backward compatibility).
    
    Maps days parameter to the new /history endpoint format.
    """
    # Convert days to limit (approximate)
    limit = min(days, 500)  # Cap at 500 bars
    return await get_historical_data(
        symbol=symbol,
        current_user=current_user,
        period="day",
        limit=limit,
    )


@router.post("/recommendations", response_model=list[CalculatedStrategy])
async def get_strategy_recommendations(
    request: StrategyRecommendationRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[CalculatedStrategy]:
    """
    Generate algorithmic strategy recommendations based on advanced mathematical logic.

    This endpoint uses Greeks analysis and strict validation rules to recommend
    optimal option strategies. It does NOT call AI models - it's fast, deterministic,
    and financially rigorous.

    Flow:
    1. Fetch real-time option chain (with fresh Greeks)
    2. Instantiate StrategyEngine
    3. Run generation with strict filters
    4. Return valid strategies or warning if none pass filters

    Args:
        request: StrategyRecommendationRequest with symbol, outlook, risk_profile, capital
        current_user: Authenticated user (for pro status and rate limiting)

    Returns:
        List of CalculatedStrategy objects that passed all validation rules

    Raises:
        HTTPException: If market data is unavailable or invalid parameters
    """
    try:
        # Step 1: Fetch real-time option chain
        # Use the expiration_date from request if provided, otherwise we'll need to find optimal
        expiration_date = request.expiration_date
        if not expiration_date:
            # For now, calculate next Friday (common expiration)
            from datetime import datetime, timedelta
            today = datetime.now()
            days_until_friday = (4 - today.weekday()) % 7
            if days_until_friday == 0:
                days_until_friday = 7
            next_friday = today + timedelta(days=days_until_friday)
            expiration_date = next_friday.strftime("%Y-%m-%d")

        # Fetch real-time option chain
        chain_data = await tiger_service.get_option_chain(
            symbol=request.symbol.upper(),
            expiration_date=expiration_date,
            is_pro=current_user.is_pro,
        )

        # Extract spot price
        spot_price = chain_data.get("spot_price") or chain_data.get("underlying_price")
        if not spot_price or spot_price <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Spot price not available for this symbol",
            )

        # Step 2: Instantiate StrategyEngine
        # Initialize StrategyEngine with MarketDataService for FinanceToolkit calculations
        market_data_service = MarketDataService()
        engine = StrategyEngine(market_data_service=market_data_service)

        # Step 3: Run generation
        strategies = engine.generate_strategies(
            chain=chain_data,
            symbol=request.symbol.upper(),
            spot_price=float(spot_price),
            outlook=request.outlook,
            risk_profile=request.risk_profile,
            capital=request.capital,
            expiration_date=expiration_date,
        )

        # Step 4: Return results
        if not strategies:
            # Return empty list with warning message in detail
            logger.info(
                f"No strategies passed strict filters for {request.symbol} "
                f"(outlook: {request.outlook}, risk: {request.risk_profile})"
            )
            # Still return 200 with empty list - client can show message
            return []

        logger.info(
            f"Generated {len(strategies)} valid strategies for {request.symbol}"
        )
        return strategies

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error generating strategy recommendations: {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}",
        )


@router.post("/scanner")
async def get_market_scanner(
    criteria: Annotated[str, Query(..., description="Scanner criteria: 'high_iv', 'top_gainers', 'most_active', 'top_losers', 'high_volume'")],
    current_user: Annotated[User, Depends(get_current_user)],
    market_value_min: Annotated[float | None, Query(description="Minimum market cap filter (e.g., 100000000 for $100M)")] = None,
    volume_min: Annotated[float | None, Query(description="Minimum volume filter (e.g., 500000 for 500K)")] = None,
    limit: Annotated[int, Query(ge=1, le=500, description="Maximum number of results")] = 100,
) -> dict[str, Any]:
    """
    Get market scanner results for discovery.
    
    Uses Tiger Market Scanner API to find stocks based on criteria.
    This powers the "Discovery" tab in the frontend.
    
    Supported Criteria:
    - high_iv: Stocks with high implied volatility
    - top_gainers: Stocks with highest % gain today
    - most_active: Stocks with highest trading volume
    - top_losers: Stocks with highest % loss today
    - high_volume: Stocks with high trading volume
    
    Args:
        criteria: Scanner criteria type
        current_user: Authenticated user (from JWT token)
        market_value_min: Optional minimum market cap filter
        volume_min: Optional minimum volume filter
        limit: Maximum number of results (1-500, default: 100)
    
    Returns:
        Dictionary with criteria and list of stocks with price, change%, etc.
    
    Raises:
        HTTPException: If scanner API fails or invalid criteria
    """
    try:
        # Validate criteria
        valid_criteria = ["high_iv", "top_gainers", "most_active", "top_losers", "high_volume"]
        if criteria not in valid_criteria:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid criteria. Must be one of: {', '.join(valid_criteria)}",
            )
        
        # Call Tiger scanner API
        stocks = await tiger_service.get_market_scanner(
            market="US",
            criteria=criteria,
            market_value_min=market_value_min,
            volume_min=volume_min,
            limit=limit,
        )
        
        return {
            "criteria": criteria,
            "count": len(stocks),
            "stocks": stocks,
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions from service layer
        raise
    except Exception as e:
        logger.error(f"Error fetching market scanner data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch market scanner data: {str(e)}",
        )


@router.get("/anomalies", response_model=list[AnomalyResponse])
async def get_anomalies(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(20, ge=1, le=100, description="Maximum number of anomalies to return"),
    hours: int = Query(1, ge=1, le=24, description="Hours of history to retrieve"),
) -> list[AnomalyResponse]:
    """
    Get recent option anomalies (Anomaly Radar).
    
    Returns anomalies detected in the last N hours, sorted by score (highest first).
    
    Args:
        current_user: Authenticated user
        db: Database session
        limit: Maximum number of anomalies to return (1-100)
        hours: Hours of history to retrieve (1-24)
        
    Returns:
        List of anomalies sorted by score (highest first)
    """
    from datetime import timedelta
    
    try:
        # Calculate cutoff time
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Query anomalies
        result = await db.execute(
            select(Anomaly)
            .where(Anomaly.detected_at >= cutoff)
            .order_by(Anomaly.score.desc(), Anomaly.detected_at.desc())
            .limit(limit)
        )
        anomalies = result.scalars().all()
        
        return [
            AnomalyResponse(
                id=str(anomaly.id),
                symbol=anomaly.symbol,
                anomaly_type=anomaly.anomaly_type,
                score=anomaly.score,
                details=anomaly.details,
                ai_insight=anomaly.ai_insight,
                detected_at=anomaly.detected_at,
            )
            for anomaly in anomalies
        ]
    except Exception as e:
        logger.error(f"Error fetching anomalies: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch anomalies: {str(e)}",
        )

