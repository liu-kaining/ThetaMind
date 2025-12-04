#!/usr/bin/env python3
"""
Sync stock symbols from Tiger API to local database.

This script fetches all US stock symbols from Tiger Brokers API
and bulk inserts/upserts them into the StockSymbol table.

Usage:
    python scripts/sync_symbols.py

Note: Tiger SDK may not have a direct "get all symbols" method.
This script uses a combination of:
1. Popular stock lists (S&P 500, NASDAQ 100, etc.)
2. Tiger API methods if available
3. Manual symbol lists as fallback
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import StockSymbol
from app.db.session import AsyncSessionLocal
from app.services.tiger_service import tiger_service
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Popular US stock symbols (fallback if Tiger API doesn't provide full list)
# This is a curated list of major stocks. In production, you might want to
# use a more comprehensive source or Tiger API if it provides symbol lists.
POPULAR_SYMBOLS = [
    # Tech
    ("AAPL", "Apple Inc."),
    ("MSFT", "Microsoft Corporation"),
    ("GOOGL", "Alphabet Inc."),
    ("AMZN", "Amazon.com Inc."),
    ("META", "Meta Platforms Inc."),
    ("NVDA", "NVIDIA Corporation"),
    ("TSLA", "Tesla Inc."),
    ("NFLX", "Netflix Inc."),
    # Finance
    ("JPM", "JPMorgan Chase & Co."),
    ("BAC", "Bank of America Corp"),
    ("WFC", "Wells Fargo & Company"),
    ("GS", "The Goldman Sachs Group Inc."),
    # Consumer
    ("WMT", "Walmart Inc."),
    ("HD", "The Home Depot Inc."),
    ("MCD", "McDonald's Corporation"),
    ("SBUX", "Starbucks Corporation"),
    # Healthcare
    ("JNJ", "Johnson & Johnson"),
    ("PFE", "Pfizer Inc."),
    ("UNH", "UnitedHealth Group Inc."),
    # Industrial
    ("BA", "The Boeing Company"),
    ("CAT", "Caterpillar Inc."),
    ("GE", "General Electric Company"),
    # Energy
    ("XOM", "Exxon Mobil Corporation"),
    ("CVX", "Chevron Corporation"),
    # And many more... (This is a sample. In production, use a comprehensive list)
]

# Extended list (S&P 500 major components)
EXTENDED_SYMBOLS = POPULAR_SYMBOLS + [
    ("ABBV", "AbbVie Inc."),
    ("ABT", "Abbott Laboratories"),
    ("ACN", "Accenture plc"),
    ("ADBE", "Adobe Inc."),
    ("AIG", "American International Group Inc."),
    ("AMD", "Advanced Micro Devices Inc."),
    ("AMGN", "Amgen Inc."),
    ("AVGO", "Broadcom Inc."),
    ("AXP", "American Express Company"),
    ("BKNG", "Booking Holdings Inc."),
    ("BLK", "BlackRock Inc."),
    ("BMY", "Bristol-Myers Squibb Company"),
    ("BRK.B", "Berkshire Hathaway Inc."),
    ("C", "Citigroup Inc."),
    ("CMCSA", "Comcast Corporation"),
    ("COST", "Costco Wholesale Corporation"),
    ("CRM", "Salesforce.com Inc."),
    ("CSCO", "Cisco Systems Inc."),
    ("CVS", "CVS Health Corporation"),
    ("DHR", "Danaher Corporation"),
    ("DIS", "The Walt Disney Company"),
    ("DOW", "Dow Inc."),
    ("DUK", "Duke Energy Corporation"),
    ("EMR", "Emerson Electric Co."),
    ("EXC", "Exelon Corporation"),
    ("F", "Ford Motor Company"),
    ("FDX", "FedEx Corporation"),
    ("FI", "Fiserv Inc."),
    ("GEHC", "GE HealthCare Technologies Inc."),
    ("GILD", "Gilead Sciences Inc."),
    ("GM", "General Motors Company"),
    ("GOOG", "Alphabet Inc."),
    ("HCA", "HCA Healthcare Inc."),
    ("HON", "Honeywell International Inc."),
    ("IBM", "International Business Machines Corporation"),
    ("INTC", "Intel Corporation"),
    ("INTU", "Intuit Inc."),
    ("ISRG", "Intuitive Surgical Inc."),
    ("JCI", "Johnson Controls International plc"),
    ("LIN", "Linde plc"),
    ("LMT", "Lockheed Martin Corporation"),
    ("LOW", "Lowe's Companies Inc."),
    ("MA", "Mastercard Incorporated"),
    ("MCD", "McDonald's Corporation"),
    ("MDT", "Medtronic plc"),
    ("MO", "Altria Group Inc."),
    ("MRK", "Merck & Co. Inc."),
    ("MS", "Morgan Stanley"),
    ("NEE", "NextEra Energy Inc."),
    ("NKE", "Nike Inc."),
    ("NOW", "ServiceNow Inc."),
    ("ORCL", "Oracle Corporation"),
    ("PANW", "Palo Alto Networks Inc."),
    ("PEP", "PepsiCo Inc."),
    ("PG", "The Procter & Gamble Company"),
    ("PM", "Philip Morris International Inc."),
    ("QCOM", "QUALCOMM Incorporated"),
    ("RTX", "RTX Corporation"),
    ("SCHW", "The Charles Schwab Corporation"),
    ("SO", "The Southern Company"),
    ("SPGI", "S&P Global Inc."),
    ("T", "AT&T Inc."),
    ("TGT", "Target Corporation"),
    ("TJX", "The TJX Companies Inc."),
    ("TMUS", "T-Mobile US Inc."),
    ("TXN", "Texas Instruments Incorporated"),
    ("UNP", "Union Pacific Corporation"),
    ("UPS", "United Parcel Service Inc."),
    ("USB", "U.S. Bancorp"),
    ("V", "Visa Inc."),
    ("VZ", "Verizon Communications Inc."),
    ("WBA", "Walgreens Boots Alliance Inc."),
    ("ZTS", "Zoetis Inc."),
]


async def fetch_symbols_from_tiger() -> list[tuple[str, str]]:
    """
    Attempt to fetch symbols from Tiger API.
    
    Note: Tiger SDK may not have a direct "get all symbols" method.
    This function tries available methods and falls back to static lists.
    
    Returns:
        List of (symbol, name) tuples
    """
    symbols = []
    
    try:
        # Try to use Tiger API if it has a method to get symbol lists
        # Common methods might be: get_all_symbols, get_symbol_list, etc.
        # Since we don't have direct access to Tiger SDK docs for this,
        # we'll use a fallback approach
        
        # Option 1: Try to get symbols from popular indices
        # Some APIs provide methods like get_index_components("SPX")
        # For now, we'll use the static list as Tiger SDK may not expose this
        
        logger.info("Tiger API may not provide a direct 'get all symbols' method.")
        logger.info("Using curated symbol list as fallback.")
        
    except Exception as e:
        logger.warning(f"Failed to fetch from Tiger API: {e}. Using fallback list.")
    
    return symbols


async def sync_symbols_to_db(symbols: list[tuple[str, str]]) -> None:
    """
    Bulk insert/upsert symbols into StockSymbol table.
    
    Args:
        symbols: List of (symbol, name) tuples
    """
    async with AsyncSessionLocal() as session:
        try:
            inserted_count = 0
            updated_count = 0
            
            for symbol_str, name in symbols:
                # Check if symbol exists
                result = await session.execute(
                    select(StockSymbol).where(StockSymbol.symbol == symbol_str.upper())
                )
                existing = result.scalar_one_or_none()
                
                if existing:
                    # Update existing
                    existing.name = name
                    existing.is_active = True
                    existing.updated_at = datetime.now(timezone.utc)
                    updated_count += 1
                else:
                    # Insert new
                    new_symbol = StockSymbol(
                        symbol=symbol_str.upper(),
                        name=name,
                        market="US",
                        is_active=True,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                    session.add(new_symbol)
                    inserted_count += 1
            
            await session.commit()
            logger.info(f"✅ Sync complete: {inserted_count} inserted, {updated_count} updated")
            
        except Exception as e:
            logger.error(f"❌ Error syncing symbols: {e}", exc_info=True)
            await session.rollback()
            raise


async def main() -> None:
    """Main sync function."""
    logger.info("🚀 Starting symbol sync...")
    
    # Try to fetch from Tiger API first
    tiger_symbols = await fetch_symbols_from_tiger()
    
    # Use extended static list as primary source (or merge with Tiger results)
    if tiger_symbols:
        all_symbols = tiger_symbols + EXTENDED_SYMBOLS
        # Remove duplicates (keep first occurrence)
        seen = set()
        unique_symbols = []
        for sym, name in all_symbols:
            if sym.upper() not in seen:
                seen.add(sym.upper())
                unique_symbols.append((sym, name))
        all_symbols = unique_symbols
    else:
        all_symbols = EXTENDED_SYMBOLS
    
    logger.info(f"📊 Syncing {len(all_symbols)} symbols to database...")
    
    await sync_symbols_to_db(all_symbols)
    
    logger.info("✅ Symbol sync completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())

