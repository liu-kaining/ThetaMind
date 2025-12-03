"""Market data API endpoints."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_user
from app.api.schemas import OptionChainResponse
from app.db.models import User
from app.services.tiger_service import tiger_service

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

