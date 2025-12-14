#!/usr/bin/env python3
"""
Smart Sync: Sync only Liquid, Optionable Stocks using Tiger Market Scanner API.

This script uses Tiger's Market Scanner to fetch only high-quality stocks:
- Market Cap > $100M
- Volume > 500,000
- Top 2000 stocks by market cap

Usage:
    python scripts/sync_liquid_symbols.py
    
Or via Docker:
    docker-compose exec backend python scripts/sync_liquid_symbols.py
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import StockSymbol
from app.db.session import AsyncSessionLocal
from app.services.tiger_service import tiger_service
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fetch_liquid_symbols_from_scanner() -> list[dict[str, Any]]:
    """
    Fetch liquid, optionable stocks using Tiger Market Scanner API.
    
    Uses the official market_scanner method with StockFilter objects.
    Reference: https://docs.itigerup.com/docs/quote-scanner
    
    Filters:
    - Market: US
    - Market Cap > $100M (market_value > 100,000,000)
    - Volume > 500,000
    - Sort by market_value DESC
    - Limit: Top 2000
    
    Returns:
        List of stock dicts with symbol, name, market_value, volume, etc.
    """
    try:
        logger.info("🔍 Fetching liquid stocks from Tiger Market Scanner...")
        
        # Use TigerService's get_market_scanner method
        # This handles the proper StockFilter construction
        stocks = await tiger_service.get_market_scanner(
            market="US",
            market_value_min=100_000_000,  # Market Cap > $100M
            volume_min=500_000,  # Volume > 500K
            limit=2000,  # Top 2000 stocks
        )
        
        logger.info(f"✅ Fetched {len(stocks)} liquid stocks from scanner")
        return stocks
        
    except Exception as e:
        logger.error(f"❌ Error fetching from scanner: {e}", exc_info=True)
        # Fallback: Return empty list (don't crash, just log)
        logger.warning("⚠️ Scanner API failed, returning empty list. Check Tiger API permissions.")
        return []


async def sync_liquid_symbols_to_db(stocks: list[dict[str, Any]]) -> None:
    """
    Upsert liquid stocks into StockSymbol table.
    
    Marks all synced stocks as is_active=True.
    Marks all other stocks as is_active=False (to hide junk stocks).
    
    Args:
        stocks: List of stock dicts with symbol, name, etc.
    """
    async with AsyncSessionLocal() as session:
        try:
            # Get all symbols that should be active (from scanner)
            active_symbols = {stock["symbol"].upper() for stock in stocks}
            
            inserted_count = 0
            updated_count = 0
            activated_count = 0
            
            # Note: Stock names will be populated from scanner results if available
            # If not available, we use symbol as name (can be enriched later via other APIs)
            
            # Upsert scanned stocks
            for stock in stocks:
                symbol_upper = stock["symbol"].upper()
                name = stock.get("name") or symbol_upper
                
                # Check if symbol exists
                result = await session.execute(
                    select(StockSymbol).where(StockSymbol.symbol == symbol_upper)
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Update existing
                    if existing.name != name or not existing.is_active:
                        existing.name = name
                        existing.is_active = True
                        existing.updated_at = datetime.now(timezone.utc)
                        updated_count += 1
                    else:
                        # Already active and up-to-date
                        pass
                else:
                    # Insert new
                    new_symbol = StockSymbol(
                        symbol=symbol_upper,
                        name=name,
                        market="US",
                        is_active=True,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    session.add(new_symbol)
                    inserted_count += 1
                
                # Commit in batches
                if (inserted_count + updated_count) % 100 == 0:
                    await session.commit()
            
            # Final commit for upserts
            await session.commit()
            
            # Deactivate all other stocks (mark as inactive)
            deactivate_result = await session.execute(
                update(StockSymbol)
                .where(StockSymbol.symbol.notin_(active_symbols))
                .where(StockSymbol.market == "US")
                .values(is_active=False, updated_at=datetime.now(timezone.utc))
            )
            deactivated_count = deactivate_result.rowcount
            await session.commit()
            
            logger.info(
                f"✅ Sync complete:\n"
                f"   - {inserted_count} new symbols inserted\n"
                f"   - {updated_count} existing symbols updated\n"
                f"   - {deactivated_count} symbols deactivated (junk stocks hidden)"
            )
            
        except Exception as e:
            logger.error(f"❌ Error syncing symbols: {e}", exc_info=True)
            await session.rollback()
            raise


async def main() -> None:
    """Main sync function."""
    logger.info("🚀 Starting Smart Sync (Liquid Stocks Only)...")
    logger.info("📊 Filters: Market Cap > $100M, Volume > 500K, Top 2000 by Market Cap")
    
    # Fetch liquid stocks from scanner
    stocks = await fetch_liquid_symbols_from_scanner()
    
    if not stocks:
        logger.warning("⚠️ No stocks fetched from scanner. Check Tiger API permissions and scanner method availability.")
        logger.warning("💡 Tip: Verify that your Tiger account has scanner API permissions enabled.")
        return
    
    logger.info(f"📈 Syncing {len(stocks)} liquid stocks to database...")
    
    # Sync to database
    await sync_liquid_symbols_to_db(stocks)
    
    logger.info("✅ Smart Sync completed successfully!")
    logger.info("💡 All other stocks have been marked as inactive (is_active=False)")


if __name__ == "__main__":
    asyncio.run(main())

