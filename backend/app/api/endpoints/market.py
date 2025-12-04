"""Market data API endpoints."""

import logging
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
from app.services.strategy_engine import StrategyEngine
from sqlalchemy import select, or_, case
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/chain", response_model=OptionChainResponse)
async def get_option_chain(
    symbol: Annotated[str, Query(..., description="Stock symbol (e.g., AAPL)")],
    expiration_date: Annotated[
        str, Query(..., description="Expiration date in YYYY-MM-DD format")
    ],
    current_user: Annotated[User, Depends(get_current_user)],
) -> OptionChainResponse:
    """
    Get option chain for a stock symbol and expiration date.

    Requires authentication. Pro users get real-time data (5s cache),
    Free users get delayed data (15m cache).

    Args:
        symbol: Stock symbol (e.g., AAPL, TSLA)
        expiration_date: Expiration date in YYYY-MM-DD format
        current_user: Authenticated user (from JWT token)

    Returns:
        OptionChainResponse with calls, puts, and spot price

    Raises:
        HTTPException: If market data service is unavailable or invalid parameters
    """
    try:
        # Call tiger service with user's pro status
        chain_data = await tiger_service.get_option_chain(
            symbol=symbol.upper(),
            expiration_date=expiration_date,
            is_pro=current_user.is_pro,
        )

        # Extract data from response
        # Note: Structure depends on Tiger SDK response format
        calls = chain_data.get("calls", [])
        puts = chain_data.get("puts", [])
        spot_price = chain_data.get("spot_price") or chain_data.get("underlying_price")
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
        # Call Tiger SDK's get_stock_briefs method
        # According to Tiger SDK docs: get_stock_briefs(symbols: list[str])
        result = await tiger_service._call_tiger_api_async(
            "get_stock_briefs",
            symbols=[symbol.upper()],
        )

        # Serialize SDK response
        if hasattr(result, "to_dict"):
            quote_data = result.to_dict()
        elif hasattr(result, "__dict__"):
            quote_data = {
                k: v for k, v in result.__dict__.items() if not k.startswith("_")
            }
        elif isinstance(result, (list, tuple)) and len(result) > 0:
            # get_stock_briefs returns a list, get first item
            item = result[0]
            if hasattr(item, "to_dict"):
                quote_data = item.to_dict()
            elif hasattr(item, "__dict__"):
                quote_data = {
                    k: v for k, v in item.__dict__.items() if not k.startswith("_")
                }
            else:
                quote_data = dict(item) if isinstance(item, dict) else {"raw": str(item)}
        elif isinstance(result, dict):
            quote_data = result
        else:
            quote_data = {"raw": str(result)}

        return {
            "symbol": symbol.upper(),
            "data": quote_data,
            "is_pro": current_user.is_pro,
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


@router.get("/search", response_model=list[SymbolSearchResponse])
async def search_symbols(
    q: Annotated[str, Query(..., description="Search query (symbol or company name)")],
    limit: Annotated[int, Query(default=10, ge=1, le=50, description="Maximum number of results")] = 10,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
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

