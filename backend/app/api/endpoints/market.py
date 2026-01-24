"""Market data API endpoints."""

import logging
import math
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user
from app.api.schemas import OptionChainResponse, SymbolSearchResponse
from app.schemas.strategy_recommendation import (
    StrategyRecommendationRequest,
    CalculatedStrategy,
)
from app.db.models import User, StockSymbol
from app.db.session import get_db
from app.services.tiger_service import tiger_service
from app.services.market_data_service import MarketDataService
from fastapi.concurrency import run_in_threadpool
from app.services.strategy_engine import StrategyEngine
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
    Get stock quote/brief information.

    Uses Tiger SDK's get_stock_briefs method.
    Requires authentication.

    Args:
        symbol: Stock symbol (e.g., AAPL, TSLA)
        current_user: Authenticated user (from JWT token)

    Returns:
        Dictionary containing stock quote information

    Raises:
        HTTPException: If market data service is unavailable
    """
    try:
        # Use cost-efficient price inference instead of expensive get_stock_briefs
        estimated_price = await tiger_service.get_realtime_price(symbol.upper())
        
        if estimated_price is None:
            # Fallback: try to get price from cached option chain if available
            # But do NOT call get_stock_briefs to avoid bills
            logger.warning(f"Could not infer price for {symbol}, returning None")
            return {
                "symbol": symbol.upper(),
                "data": {
                    "price": None,
                    "error": "Price inference failed. Please try again later.",
                },
                "is_pro": current_user.is_pro,
                "price_source": "inference_failed",
            }

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

    Uses MarketDataService (FMP with Yahoo fallback).
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
        engine = StrategyEngine()

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

