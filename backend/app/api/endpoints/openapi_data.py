import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_openapi_key
from app.api.schemas.openapi_data import (
    CompanyFundamentalsResponse,
    FundamentalHardcoreDTO,
    OptionsContextDTO,
    StockOverviewDTO,
)
from app.services.cache import cache_service
from app.services.fundamental_data_service import FundamentalDataService
from app.services.market_data_service import MarketDataService
from app.services.tiger_service import TigerService

logger = logging.getLogger(__name__)

OPENAPI_OPTIONS_CACHE_TTL = 60
UPSTREAM_ERROR_DETAIL = "Upstream data provider error"

router = APIRouter(prefix="/openapi", tags=["openapi"], include_in_schema=False)


def _get_market_service() -> MarketDataService:
    return MarketDataService()


def _get_fundamental_service(
    market: MarketDataService = Depends(_get_market_service),
) -> FundamentalDataService:
    return FundamentalDataService(market)


def _get_tiger_service() -> TigerService:
    return TigerService()

@router.get(
    "/company/{symbol}/fundamentals",
    response_model=CompanyFundamentalsResponse,
    dependencies=[Depends(get_openapi_key)],
    include_in_schema=False,
)
async def get_company_fundamentals_openapi(
    symbol: str,
    fundamental_service: FundamentalDataService = Depends(_get_fundamental_service),
):
    """
    Get core fundamentals for Notion report.
    Uses FundamentalDataService modules with internal caching.
    """
    sym = symbol.upper()
    try:
        modules = await fundamental_service.fetch_modules(sym, ["overview", "ratios", "analyst"])
        overview_data = modules.get("overview", {})
        ratios_data = modules.get("ratios", {})
        analyst_data = modules.get("analyst", {})

        quote = overview_data.get("quote", {}) or {}
        target = (analyst_data.get("price_target_consensus") or {})
        if isinstance(quote, list) and quote:
            quote = quote[0] if isinstance(quote[0], dict) else {}
        if isinstance(target, list) and target:
            target = target[0] if isinstance(target[0], dict) else {}

        if not quote and not isinstance(overview_data.get("profile"), dict):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No fundamental data found for {sym}",
            )

        def _num(v: Any, default: float = 0.0) -> float:
            if v is None:
                return default
            try:
                return float(v)
            except (TypeError, ValueError):
                return default

        stock_overview = StockOverviewDTO(
            symbol=sym,
            current_price=_num(quote.get("price")),
            low_52w=_num(quote.get("yearLow")),
            high_52w=_num(quote.get("yearHigh")),
            pe_ratio=quote.get("pe") if quote.get("pe") is not None else None,
            analyst_target=target.get("targetMean") if target.get("targetMean") is not None else None,
        )

        metrics_ttm = ratios_data.get("key_metrics_ttm") or {}
        ratios_ttm = ratios_data.get("ratios_ttm") or {}
        if isinstance(metrics_ttm, list) and metrics_ttm and isinstance(metrics_ttm[0], dict):
            metrics_ttm = metrics_ttm[0]
        if isinstance(ratios_ttm, list) and ratios_ttm and isinstance(ratios_ttm[0], dict):
            ratios_ttm = ratios_ttm[0]

        def _opt_float(v: Any) -> float | None:
            if v is None:
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        hardcore = FundamentalHardcoreDTO(
            fcf_yield=_opt_float(metrics_ttm.get("freeCashFlowYieldTTM")),
            roic=_opt_float(metrics_ttm.get("roicTTM")),
            gross_margin=_opt_float(ratios_ttm.get("grossProfitMarginTTM")),
        )

        return CompanyFundamentalsResponse(overview=stock_overview, hardcore=hardcore)

    except HTTPException:
        raise
    except Exception as e:
        logger.error("OpenAPI fundamentals upstream error for %s: %s", sym, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=UPSTREAM_ERROR_DETAIL,
        )

@router.get(
    "/options/{symbol}/volatility-context",
    response_model=OptionsContextDTO,
    dependencies=[Depends(get_openapi_key)],
    include_in_schema=False,
)
async def get_options_volatility_openapi(
    symbol: str,
    tiger_service: TigerService = Depends(_get_tiger_service),
    market_service: MarketDataService = Depends(_get_market_service),
):
    """
    Get IV/HV context for Notion report.
    Adds a mandatory 60s cache layer to protect Tiger API quota.
    """
    sym = symbol.upper()
    cache_key = f"openapi:options:vol:{sym}"
    
    cached = await cache_service.get(cache_key)
    if cached and isinstance(cached, dict):
        return OptionsContextDTO(**cached)

    try:
        expirations = await tiger_service.get_option_expirations(sym)
        if not expirations:
            raise HTTPException(status_code=404, detail=f"No options found for {sym}")

        nearest_exp = expirations[0]
        chain = await tiger_service.get_option_chain(sym, nearest_exp)

        spot = float(chain.get("spot_price") or 0)
        all_options = list(chain.get("calls") or []) + list(chain.get("puts") or [])

        if not all_options:
            raise HTTPException(status_code=404, detail=f"Empty option chain for {sym}")

        def _iv_from_opt(o: dict) -> float | None:
            v = o.get("implied_volatility") or o.get("implied_vol") or o.get("v")
            if v is None:
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        near_atm = []
        if spot > 0:
            for o in all_options:
                s = o.get("strike")
                if s is not None:
                    try:
                        strike = float(s)
                        if abs(strike - spot) / spot < 0.15:
                            near_atm.append(o)
                    except (TypeError, ValueError):
                        pass
        iv_sources = near_atm if near_atm else all_options
        iv_list = [x for x in (_iv_from_opt(o) for o in iv_sources) if x is not None and x > 0]
        avg_iv = (sum(iv_list) / len(iv_list)) if iv_list else 0.0

        def _get_hv() -> float:
            try:
                profile = market_service.get_financial_profile(sym)
                vol_data = profile.get("volatility") or {}
                if isinstance(vol_data, dict):
                    hv = vol_data.get("historical_volatility") or vol_data.get("annualized")
                    if hv is not None:
                        try:
                            return float(hv)
                        except (TypeError, ValueError):
                            pass
                    if isinstance(vol_data.get("error"), str):
                        logger.debug("Volatility error in profile: %s", vol_data["error"])
                return 0.0
            except Exception as e:
                logger.debug("get_financial_profile for HV: %s", e)
                return 0.0

        hv = await asyncio.to_thread(_get_hv)
        if hv <= 0:
            hv = 0.3

        iv_hv_ratio = (avg_iv / hv) if hv > 0 else 0.0

        result = OptionsContextDTO(
            symbol=sym,
            implied_volatility=round(avg_iv, 6),
            historical_volatility=round(hv, 6),
            iv_hv_ratio=round(iv_hv_ratio, 6),
        )

        await cache_service.set(cache_key, result.model_dump(), ttl=OPENAPI_OPTIONS_CACHE_TTL)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("OpenAPI volatility upstream error for %s: %s", sym, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=UPSTREAM_ERROR_DETAIL,
        )
