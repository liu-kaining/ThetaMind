#!/usr/bin/env python3
"""Quick verification script to check synced symbols."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from app.db.session import AsyncSessionLocal
from app.db.models import StockSymbol

async def verify():
    async with AsyncSessionLocal() as session:
        # Check total active symbols
        result = await session.execute(
            select(func.count(StockSymbol.symbol)).where(StockSymbol.is_active == True)
        )
        total_active = result.scalar()
        print(f"✅ Total active symbols: {total_active}")
        
        # Check specific popular symbols
        popular_symbols = ['AAPL', 'NVDA', 'MSFT', 'TSLA', 'GOOGL', 'AMZN', 'META']
        result = await session.execute(
            select(StockSymbol)
            .where(StockSymbol.symbol.in_(popular_symbols))
            .where(StockSymbol.is_active == True)
        )
        found = result.scalars().all()
        print(f"\n📊 Popular symbols found ({len(found)}/{len(popular_symbols)}):")
        for symbol in found:
            print(f"   ✅ {symbol.symbol}: {symbol.name}")
        
        missing = set(popular_symbols) - {s.symbol for s in found}
        if missing:
            print(f"\n⚠️  Missing symbols: {', '.join(missing)}")
        
        # Sample some random active symbols
        result = await session.execute(
            select(StockSymbol)
            .where(StockSymbol.is_active == True)
            .limit(10)
        )
        samples = result.scalars().all()
        print(f"\n📋 Sample of active symbols (first 10):")
        for symbol in samples:
            print(f"   - {symbol.symbol}: {symbol.name}")

if __name__ == "__main__":
    asyncio.run(verify())

