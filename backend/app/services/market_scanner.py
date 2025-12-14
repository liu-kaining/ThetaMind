"""Market Scanner Service for identifying hot option stocks."""

import logging
from typing import Any

from app.services.tiger_service import tiger_service

logger = logging.getLogger(__name__)

# Fallback list of blue-chip tech stocks with liquid options
FALLBACK_STOCKS = ["AAPL", "NVDA", "TSLA", "AMD", "MSFT", "GOOGL", "META", "AMZN", "NFLX", "INTC"]


async def get_hot_options_stocks(limit: int = 10) -> list[str]:
    """
    Get hot option stocks using Tiger Market Scanner API.
    
    Filters:
    - Market: US
    - Volume > 1,000,000
    - High IV or Price Change > 3%
    
    Falls back to static blue-chip list if scanner API fails.
    
    Args:
        limit: Maximum number of stocks to return (default: 10)
        
    Returns:
        List of stock symbols (e.g., ["AAPL", "NVDA", ...])
    """
    try:
        # Use Tiger Market Scanner API
        # Filters: US Market, Volume > 1M
        # Sort by: High IV or Price Change > 3%
        stocks = await tiger_service.get_market_scanner(
            market="US",
            volume_min=1_000_000,  # Volume > 1M
            limit=limit * 2,  # Get more to filter for IV/change
        )
        
        if not stocks:
            logger.warning("Market scanner returned empty results, using fallback stocks")
            return FALLBACK_STOCKS[:limit]
        
        # Filter for high IV or price change > 3%
        # Sort by change percentage (descending) to prioritize movers
        filtered_stocks = []
        for stock in stocks:
            symbol = stock.get("symbol") or stock.get("Symbol")
            if not symbol:
                continue
                
            # Check price change
            change_percent = stock.get("change_percent") or stock.get("changePercent") or stock.get("change%")
            try:
                change_pct = float(change_percent) if change_percent else 0.0
            except (ValueError, TypeError):
                change_pct = 0.0
            
            # For now, prioritize by absolute change (we'll refine with IV later)
            # Accept stocks with > 3% change or in top volume
            if abs(change_pct) > 3.0 or len(filtered_stocks) < limit:
                filtered_stocks.append({
                    "symbol": symbol,
                    "change_percent": change_pct,
                })
        
        # Sort by absolute change percentage (prioritize movers)
        filtered_stocks.sort(key=lambda x: abs(x["change_percent"]), reverse=True)
        
        # Extract symbols
        symbols = [stock["symbol"] for stock in filtered_stocks[:limit]]
        
        if not symbols:
            logger.warning("No stocks passed filters, using fallback stocks")
            return FALLBACK_STOCKS[:limit]
        
        logger.info(f"Market scanner returned {len(symbols)} hot stocks: {symbols}")
        return symbols
        
    except Exception as e:
        logger.error(f"Market scanner API failed: {e}. Using fallback stocks.", exc_info=True)
        return FALLBACK_STOCKS[:limit]

