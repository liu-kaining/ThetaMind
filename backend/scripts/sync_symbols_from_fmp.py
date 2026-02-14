#!/usr/bin/env python3
"""
Sync stock symbols from FMP (Financial Modeling Prep) to local stock_symbols table.

This fills the local DB with a full symbol list so Strategy Lab search (and any
consumer of /api/v1/market/search) can find many more symbols. Run from a machine
that can reach FMP (e.g. your laptop or a server with outbound internet). The
database can be local or remote; once synced, all clients (including Docker
backend) will see the data.

FMP endpoints used:
- stock-list: comprehensive list of symbols (equities, ETFs, etc.)
- actively-trading-list (optional): currently trading symbols

Usage:
    # From repo root, with .env loaded (FINANCIAL_MODELING_PREP_KEY, DATABASE_URL)
    cd backend && poetry run python scripts/sync_symbols_from_fmp.py

    # Only US equities (recommended to keep search relevant)
    cd backend && poetry run python scripts/sync_symbols_from_fmp.py --us-only

    # Docker (if container can reach FMP)
    docker compose run --rm --no-deps --entrypoint "" backend python scripts/sync_symbols_from_fmp.py --us-only
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import StockSymbol
from app.db.session import AsyncSessionLocal
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FMP_BASE = "https://financialmodelingprep.com/stable"
# Exchanges we treat as US for market="US"
US_EXCHANGES = frozenset({"NASDAQ", "NYSE", "AMEX", "BATS", "OTC", "NASDAQ CAPITAL MARKET", "NYSE MKT", "NYSE ARCA"})


def _market_from_exchange(exchange: str | None) -> str:
    """Return 'US' for US exchanges, else 'OTHER' (so --us-only can filter)."""
    if not exchange:
        return "US"
    ex = (exchange or "").upper().strip()
    if ex in US_EXCHANGES:
        return "US"
    if "NASDAQ" in ex or "NYSE" in ex or "AMEX" in ex:
        return "US"
    return "OTHER"


async def fetch_fmp_stock_list() -> list[dict]:
    """Fetch full symbol list from FMP stock-list. Returns list of dicts with symbol, name, exchange."""
    key = (settings.financial_modeling_prep_key or "").strip()
    if not key:
        raise RuntimeError("FINANCIAL_MODELING_PREP_KEY is not set. Add it to .env and try again.")
    url = f"{FMP_BASE}/stock-list"
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.get(url, params={"apikey": key})
        r.raise_for_status()
        data = r.json()
    if not isinstance(data, list):
        logger.warning("FMP stock-list did not return a list: %s", type(data))
        return []
    return data


async def fetch_fmp_actively_trading() -> list[dict]:
    """Fetch actively trading list from FMP (smaller set, good as supplement)."""
    key = (settings.financial_modeling_prep_key or "").strip()
    if not key:
        return []
    url = f"{FMP_BASE}/actively-trading-list"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url, params={"apikey": key})
            r.raise_for_status()
            data = r.json()
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning("FMP actively-trading-list failed: %s", e)
        return []


async def sync_to_db(
    session: AsyncSession,
    rows: list[tuple[str, str, str]],
    batch_size: int = 500,
) -> tuple[int, int]:
    """
    Upsert (symbol, name, market) into StockSymbol. Only add/update; do not deactivate others.
    Returns (inserted_count, updated_count).
    """
    inserted = 0
    updated = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        for symbol_upper, name, market in batch:
            result = await session.execute(select(StockSymbol).where(StockSymbol.symbol == symbol_upper))
            existing = result.scalar_one_or_none()
            if existing:
                if existing.name != name or existing.market != market or not existing.is_active:
                    existing.name = name
                    existing.market = market
                    existing.is_active = True
                    existing.updated_at = datetime.now(timezone.utc)
                    updated += 1
            else:
                session.add(
                    StockSymbol(
                        symbol=symbol_upper,
                        name=name,
                        market=market,
                        is_active=True,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                    )
                )
                inserted += 1
        await session.commit()
    return inserted, updated


async def main(us_only: bool) -> None:
    logger.info("Fetching symbol list from FMP stock-list...")
    raw = await fetch_fmp_stock_list()
    logger.info("FMP returned %s symbols", len(raw))

    # Optional: merge with actively-trading for extra names
    extra = await fetch_fmp_actively_trading()
    if extra:
        by_symbol = {str(item.get("symbol", "")).upper(): item for item in raw}
        for item in extra:
            sym = str(item.get("symbol", "")).upper()
            if sym and sym not in by_symbol:
                by_symbol[sym] = item
        raw = list(by_symbol.values())
        logger.info("After merging actively-trading: %s symbols", len(raw))

    seen: set[str] = set()
    rows: list[tuple[str, str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        symbol = (item.get("symbol") or "").strip()
        if not symbol:
            continue
        symbol_upper = symbol.upper()
        if symbol_upper in seen:
            continue
        seen.add(symbol_upper)
        name = (item.get("name") or item.get("companyName") or symbol_upper)[:255]
        exchange = item.get("exchangeShortName") or item.get("exchange") or ""
        market = _market_from_exchange(exchange)
        if us_only and market != "US":
            continue
        rows.append((symbol_upper, name, market))

    logger.info("Upserting %s symbols to database (us_only=%s)...", len(rows), us_only)
    async with AsyncSessionLocal() as session:
        inserted, updated = await sync_to_db(session, rows)
    logger.info("Done. Inserted: %s, Updated: %s", inserted, updated)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sync stock symbols from FMP to local DB")
    parser.add_argument(
        "--us-only",
        action="store_true",
        help="Only sync symbols from US exchanges (NASDAQ, NYSE, AMEX, etc.)",
    )
    args = parser.parse_args()
    asyncio.run(main(us_only=args.us_only))
