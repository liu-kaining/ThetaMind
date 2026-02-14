"""
Company Data / Fundamentals page API.

New routes only; does not modify any existing endpoints or behavior.
Quota: Free 2/day, Pro 100/day per user (one query = one symbol load; cache avoids repeat deduction).
"""

import logging
from datetime import datetime, timezone
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import case, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.models import User, StockSymbol
from app.db.session import get_db
from app.services.fundamental_data_service import FundamentalDataService
from app.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/company-data", tags=["company-data"])

FREE_FUNDAMENTAL_QUOTA = 2
PRO_FUNDAMENTAL_QUOTA = 100


def get_fundamental_quota_limit(user: User) -> int:
    return PRO_FUNDAMENTAL_QUOTA if user.is_pro else FREE_FUNDAMENTAL_QUOTA


async def check_and_reset_fundamental_quota_if_needed(user: User, db: AsyncSession) -> None:
    """If last_quota_reset_date is not today (UTC), set daily_fundamental_queries_used=0 and last_quota_reset_date=now."""
    today_utc = datetime.now(timezone.utc).date()
    last_reset = user.last_quota_reset_date.date() if user.last_quota_reset_date else None
    if last_reset is None or last_reset != today_utc:
        stmt = (
            update(User)
            .where(User.id == user.id)
            .values(
                daily_fundamental_queries_used=0,
                last_quota_reset_date=datetime.now(timezone.utc),
            )
        )
        await db.execute(stmt)
        await db.commit()
        await db.refresh(user)


async def ensure_fundamental_quota_and_deduct(
    user: User,
    db: AsyncSession,
    symbol: str,
    fundamental_service: FundamentalDataService,
) -> None:
    """
    Ensure quota is reset if new day; if already deducted for this symbol today, return.
    Else if used >= limit raise 403; else increment daily_fundamental_queries_used and mark symbol deducted.
    """
    await check_and_reset_fundamental_quota_if_needed(user, db)
    already = await fundamental_service.was_deducted_today(str(user.id), symbol)
    if already:
        return
    limit = get_fundamental_quota_limit(user)
    if user.daily_fundamental_queries_used >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Daily Company Data limit reached ({user.daily_fundamental_queries_used}/{limit}). "
            "Upgrade to Pro for 100 queries per day.",
        )
    stmt = (
        update(User)
        .where(User.id == user.id)
        .values(daily_fundamental_queries_used=User.daily_fundamental_queries_used + 1)
    )
    await db.execute(stmt)
    await db.commit()
    await db.refresh(user)
    await fundamental_service.mark_deducted_today(str(user.id), symbol)


# ---------- Response schemas ----------


class CompanyDataQuotaResponse(BaseModel):
    used: int = Field(..., description="Queries used today")
    limit: int = Field(..., description="Daily limit (2 free, 100 pro)")
    is_pro: bool = Field(..., description="Whether user is Pro")


class CompanyDataSearchItem(BaseModel):
    symbol: str
    name: str
    exchange: str | None = None
    type: str | None = None


# ---------- Endpoints ----------


def _get_fundamental_service() -> FundamentalDataService:
    return FundamentalDataService(MarketDataService())


@router.get("/quota", response_model=CompanyDataQuotaResponse)
async def get_quota(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CompanyDataQuotaResponse:
    """Return current user's Company Data quota (used, limit, is_pro). Resets at UTC midnight."""
    await check_and_reset_fundamental_quota_if_needed(current_user, db)
    limit = get_fundamental_quota_limit(current_user)
    return CompanyDataQuotaResponse(
        used=current_user.daily_fundamental_queries_used,
        limit=limit,
        is_pro=current_user.is_pro,
    )


async def _search_symbols_local(
    db: AsyncSession, query: str, limit: int
) -> list[CompanyDataSearchItem]:
    """Fallback: search stock_symbols (same logic as /market/search)."""
    search_term = f"%{query.upper()}%"
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
            case(
                (StockSymbol.symbol == query.strip().upper(), 0),
                (StockSymbol.symbol.ilike(search_term), 1),
                else_=2,
            ),
            StockSymbol.symbol,
        )
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        CompanyDataSearchItem(symbol=s.symbol, name=s.name, exchange=s.market, type=None)
        for s in rows
    ]


@router.get("/search", response_model=list[CompanyDataSearchItem])
async def search(
    q: Annotated[str, Query(..., min_length=1, description="Symbol or company name")],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=30)] = 10,
) -> list[CompanyDataSearchItem]:
    """Search symbols/companies via FMP. Falls back to local DB when FMP is unreachable (e.g. in Docker). Does not consume quota."""
    service = _get_fundamental_service()
    query = q.strip()
    if not query:
        return []

    # Try FMP when key is configured
    if (settings.financial_modeling_prep_key or "").strip():
        try:
            sym_res = await service.call_fmp_raising("search-symbol", {"query": query})
            name_res = await service.call_fmp_raising("search-name", {"query": query})
        except (httpx.ConnectError, httpx.RequestError) as e:
            logger.info(
                "Company Data search: FMP unreachable (%s), falling back to local DB",
                type(e).__name__,
            )
            return await _search_symbols_local(db, query, limit)

        seen: set[str] = set()
        out: list[CompanyDataSearchItem] = []
        for item in (sym_res if isinstance(sym_res, list) else []) + (
            name_res if isinstance(name_res, list) else []
        ):
            if not isinstance(item, dict):
                continue
            sym = (item.get("symbol") or "").strip()
            if not sym or sym in seen:
                continue
            seen.add(sym)
            out.append(
                CompanyDataSearchItem(
                    symbol=sym,
                    name=(item.get("name") or item.get("companyName") or sym),
                    exchange=item.get("exchangeShortName") or item.get("exchange"),
                    type=item.get("type"),
                )
            )
            if len(out) >= limit:
                break
        return out

    # No FMP key: use local DB only
    return await _search_symbols_local(db, query, limit)


@router.get("/overview")
async def get_overview(
    symbol: Annotated[str, Query(..., min_length=1)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Get overview module for symbol. Consumes 1 quota on cache miss (once per symbol per day)."""
    service = _get_fundamental_service()
    sym = symbol.strip().upper()
    if not sym:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Symbol required")
    cached = await service.get_cached(sym, "overview")
    if cached is not None:
        return cached
    await ensure_fundamental_quota_and_deduct(current_user, db, sym, service)
    data = await service.fetch_overview(sym)
    await service.set_cached(sym, "overview", data)
    return data


@router.get("/full")
async def get_full(
    symbol: Annotated[str, Query(..., min_length=1)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    modules: Annotated[
        str | None,
        Query(description="Comma-separated: overview,valuation,ratios,analyst,charts"),
    ] = None,
) -> dict[str, Any]:
    """Get one or more modules for symbol. Consumes 1 quota on cache miss (once per symbol per day)."""
    service = _get_fundamental_service()
    sym = symbol.strip().upper()
    if not sym:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Symbol required")
    requested = [m.strip() for m in (modules or "overview,valuation,ratios,analyst,charts").split(",") if m.strip()]
    if not requested:
        requested = ["overview", "valuation", "ratios", "analyst", "charts"]
    # Single-module request: try full cache only if asking for all default modules
    default_set = {"overview", "valuation", "ratios", "analyst", "charts"}
    use_full_cache = set(requested) == default_set
    if use_full_cache:
        cached = await service.get_cached_full(sym)
        if cached is not None:
            return cached
    else:
        cached = None
    await ensure_fundamental_quota_and_deduct(current_user, db, sym, service)
    data = await service.fetch_modules(sym, requested)
    if use_full_cache:
        await service.set_cached_full(sym, data)
    return data


@router.get("/module/{module_id}")
async def get_module(
    module_id: str,
    symbol: Annotated[str, Query(..., min_length=1)],
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """Get one module (overview, valuation, ratios, analyst, charts). Consumes 1 quota on cache miss."""
    service = _get_fundamental_service()
    sym = symbol.strip().upper()
    if not sym:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Symbol required")
    mid = (module_id or "").strip().lower()
    if mid not in ("overview", "valuation", "ratios", "analyst", "charts"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="module_id must be one of: overview, valuation, ratios, analyst, charts",
        )
    cached = await service.get_cached(sym, mid)
    if cached is not None:
        return cached
    await ensure_fundamental_quota_and_deduct(current_user, db, sym, service)
    fetchers = {
        "overview": service.fetch_overview,
        "valuation": service.fetch_valuation,
        "ratios": service.fetch_ratios,
        "analyst": service.fetch_analyst,
        "charts": service.fetch_charts,
    }
    data = await fetchers[mid](sym)
    await service.set_cached(sym, mid, data)
    return data
