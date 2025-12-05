#!/usr/bin/env python3
"""Quick script to check stock symbols in database."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from app.db.models import StockSymbol
from app.db.session import AsyncSessionLocal


async def check_symbols():
    async with AsyncSessionLocal() as session:
        # Count total symbols
        result = await session.execute(select(func.count(StockSymbol.symbol)))
        total = result.scalar()
        print(f"✅ Total symbols in database: {total}")
        
        # Show sample symbols
        result2 = await session.execute(select(StockSymbol).limit(10))
        symbols = result2.scalars().all()
        print("\n📊 Sample symbols:")
        for s in symbols:
            print(f"  {s.symbol}: {s.name} ({'Active' if s.is_active else 'Inactive'})")


if __name__ == "__main__":
    asyncio.run(check_symbols())

