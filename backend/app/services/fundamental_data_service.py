"""
Company Data / Fundamentals page: aggregate FMP API data by module.

Uses MarketDataService._call_fmp_api only; does not change any existing market/strategy behavior.
Cache: Redis key company_data:{symbol}:{module} with TTL (overview 15 min, rest 1h).
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from app.services.cache import cache_service
from app.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)

# Cache TTL seconds
TTL_OVERVIEW = 900   # 15 min
TTL_DEFAULT = 3600   # 1 h


def _cache_key(symbol: str, module: str) -> str:
    return f"company_data:{symbol.upper()}:{module}"


def _deducted_key(user_id: str, date_str: str) -> str:
    return f"company_data:deducted:{user_id}:{date_str}"


class FundamentalDataService:
    """Fetch and cache FMP data for the Company Data page. One symbol load = one quota unit."""

    def __init__(self, market_data_service: MarketDataService) -> None:
        self._market = market_data_service

    async def _call(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """Call FMP API via MarketDataService. Returns raw JSON (list or dict)."""
        try:
            return await self._market._call_fmp_api(endpoint, params or {})
        except Exception as e:
            err_msg = str(e).strip() or repr(e)
            logger.warning("FMP %s failed: %s", endpoint, err_msg, exc_info=False)
            return None

    async def call_fmp_raising(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """Call FMP API and let ConnectError/RequestError propagate (for search so router can return 503)."""
        return await self._market._call_fmp_api(endpoint, params or {})

    async def _call_safe(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """Return result or empty list/dict on failure."""
        out = await self._call(endpoint, params)
        if out is None:
            return [] if "list" in endpoint or endpoint in (
                "search-symbol", "search-name", "earnings", "dividends", "splits",
                "income-statement", "balance-sheet-statement", "cash-flow-statement",
                "key-metrics", "ratios", "key-metrics-ttm", "ratios-ttm",
                "analyst-estimates", "grades", "grades-historical", "ratings-historical",
                "enterprise-values", "historical-market-capitalization",
                "stock-peers", "key-executives",
                "historical-price-eod/light", "historical-price-eod/full",
                "earnings-calendar",
            ) else {}
        return out

    # ---------- Module A: Overview ----------
    async def fetch_overview(self, symbol: str) -> dict[str, Any]:
        """Profile, quote, price change, market cap, shares float, peers."""
        sym = symbol.upper()
        profile = await self._call_safe("profile", {"symbol": sym})
        quote = await self._call_safe("quote", {"symbol": sym})
        price_change = await self._call_safe("stock-price-change", {"symbol": sym})
        market_cap = await self._call_safe("market-capitalization", {"symbol": sym})
        shares_float = await self._call_safe("shares-float", {"symbol": sym})
        peers = await self._call_safe("stock-peers", {"symbol": sym})

        # Normalize: profile/quote often return list of one item
        if isinstance(profile, list) and len(profile) > 0:
            profile = profile[0]
        elif not isinstance(profile, dict):
            profile = {}
        if isinstance(quote, list) and len(quote) > 0:
            quote = quote[0]
        elif not isinstance(quote, dict):
            quote = {}
        if isinstance(price_change, list) and len(price_change) > 0:
            price_change = price_change[0]
        elif not isinstance(price_change, dict):
            price_change = {}
        if isinstance(market_cap, list) and len(market_cap) > 0:
            market_cap = market_cap[0]
        elif not isinstance(market_cap, dict):
            market_cap = {}
        if isinstance(shares_float, list) and len(shares_float) > 0:
            shares_float = shares_float[0]
        elif not isinstance(shares_float, dict):
            shares_float = {}
        if isinstance(peers, dict) and "peersList" in peers:
            peers = list(peers["peersList"]) if isinstance(peers.get("peersList"), list) else []
        elif not isinstance(peers, list):
            peers = []

        # Next earnings (core catalyst; not prominent in Full fundamentals)
        next_earnings: dict[str, Any] | None = None
        try:
            today = datetime.now(timezone.utc).date()
            end = today + timedelta(days=90)
            cal = await self._call_safe(
                "earnings-calendar",
                {"from": today.isoformat(), "to": end.isoformat()},
            )
            if isinstance(cal, list):
                for item in cal:
                    if isinstance(item, dict) and (item.get("symbol") or "").upper() == sym:
                        next_earnings = item
                        break
        except Exception as e:
            logger.debug("earnings-calendar for overview: %s", e)

        return {
            "profile": profile,
            "quote": quote,
            "stock_price_change": price_change,
            "market_capitalization": market_cap,
            "shares_float": shares_float,
            "peers": peers,
            "next_earnings": next_earnings,
        }

    # ---------- Module B: Valuation ----------
    async def fetch_valuation(self, symbol: str) -> dict[str, Any]:
        """DCF, levered DCF, enterprise values."""
        sym = symbol.upper()
        dcf = await self._call_safe("discounted-cash-flow", {"symbol": sym})
        levered_dcf = await self._call_safe("levered-discounted-cash-flow", {"symbol": sym})
        ev = await self._call_safe("enterprise-values", {"symbol": sym})
        if isinstance(dcf, list) and len(dcf) > 0:
            dcf = dcf[0]
        elif not isinstance(dcf, dict):
            dcf = {}
        if isinstance(levered_dcf, list) and len(levered_dcf) > 0:
            levered_dcf = levered_dcf[0]
        elif not isinstance(levered_dcf, dict):
            levered_dcf = {}
        if not isinstance(ev, list):
            ev = []
        # FMP may use different keys: dcf, DCF, value; leveredDcf, levered_dcf
        def _first_num(d: dict, *keys: str) -> float | None:
            for k in keys:
                v = (d or {}).get(k)
                if v is not None and isinstance(v, (int, float)):
                    return float(v)
            return None
        dcf_val = _first_num(dcf, "dcf", "DCF", "value")
        lev_val = _first_num(levered_dcf, "leveredDcf", "levered_dcf", "dcf", "value")
        if dcf_val is not None:
            dcf = dict(dcf) if isinstance(dcf, dict) else {}
            dcf["dcf"] = dcf_val
        if lev_val is not None:
            levered_dcf = dict(levered_dcf) if isinstance(levered_dcf, dict) else {}
            levered_dcf["leveredDcf"] = lev_val
        return {"dcf": dcf, "levered_dcf": levered_dcf, "enterprise_values": ev}

    # ---------- Module D: Ratios & Key Metrics ----------
    async def fetch_ratios(self, symbol: str) -> dict[str, Any]:
        """Key metrics TTM, ratios TTM, financial scores, owner earnings. Fallback to non-TTM if empty."""
        sym = symbol.upper()
        metrics_ttm = await self._call_safe("key-metrics-ttm", {"symbol": sym})
        ratios_ttm = await self._call_safe("ratios-ttm", {"symbol": sym})
        scores = await self._call_safe("financial-scores", {"symbol": sym})
        owner_earnings = await self._call_safe("owner-earnings", {"symbol": sym})
        if isinstance(metrics_ttm, list) and len(metrics_ttm) > 0:
            metrics_ttm = metrics_ttm[0]
        elif not isinstance(metrics_ttm, dict):
            metrics_ttm = {}
        if isinstance(ratios_ttm, list) and len(ratios_ttm) > 0:
            ratios_ttm = ratios_ttm[0]
        elif not isinstance(ratios_ttm, dict):
            ratios_ttm = {}
        # Fallback: if TTM empty, try annual key-metrics / ratios (take latest)
        if not metrics_ttm and not ratios_ttm:
            metrics_list = await self._call_safe("key-metrics", {"symbol": sym, "limit": 1})
            ratios_list = await self._call_safe("ratios", {"symbol": sym, "limit": 1})
            if isinstance(metrics_list, list) and len(metrics_list) > 0:
                metrics_ttm = metrics_list[0]
            if isinstance(ratios_list, list) and len(ratios_list) > 0:
                ratios_ttm = ratios_list[0]
        if isinstance(scores, list) and len(scores) > 0:
            scores = scores[0]
        elif not isinstance(scores, dict):
            scores = {}
        if isinstance(owner_earnings, list) and len(owner_earnings) > 0:
            owner_earnings = owner_earnings[0]
        elif not isinstance(owner_earnings, dict):
            owner_earnings = {}
        return {
            "key_metrics_ttm": metrics_ttm or {},
            "ratios_ttm": ratios_ttm or {},
            "financial_scores": scores,
            "owner_earnings": owner_earnings,
        }

    # ---------- Module E: Analyst ----------
    async def fetch_analyst(self, symbol: str) -> dict[str, Any]:
        """Estimates, price target summary/consensus, grades consensus, ratings snapshot."""
        sym = symbol.upper()
        estimates = await self._call_safe("analyst-estimates", {"symbol": sym, "period": "annual", "limit": 5})
        pt_summary = await self._call_safe("price-target-summary", {"symbol": sym})
        pt_consensus = await self._call_safe("price-target-consensus", {"symbol": sym})
        grades_consensus = await self._call_safe("grades-consensus", {"symbol": sym})
        ratings = await self._call_safe("ratings-snapshot", {"symbol": sym})
        if isinstance(pt_summary, list) and len(pt_summary) > 0:
            pt_summary = pt_summary[0]
        elif not isinstance(pt_summary, dict):
            pt_summary = {}
        if isinstance(pt_consensus, list) and len(pt_consensus) > 0:
            pt_consensus = pt_consensus[0]
        elif not isinstance(pt_consensus, dict):
            pt_consensus = {}
        if isinstance(grades_consensus, list) and len(grades_consensus) > 0:
            grades_consensus = grades_consensus[0]
        elif not isinstance(grades_consensus, dict):
            grades_consensus = {}
        if isinstance(ratings, list) and len(ratings) > 0:
            ratings = ratings[0]
        elif not isinstance(ratings, dict):
            ratings = {}
        return {
            "analyst_estimates": estimates,
            "price_target_summary": pt_summary,
            "price_target_consensus": pt_consensus,
            "grades_consensus": grades_consensus,
            "ratings_snapshot": ratings,
        }

    # ---------- Module F: Charts (EOD) ----------
    async def fetch_charts(self, symbol: str, limit: int = 500) -> dict[str, Any]:
        """EOD historical price for main chart (same endpoint as Strategy Lab)."""
        sym = symbol.upper()
        params: dict[str, Any] = {"symbol": sym}
        if limit > 0:
            params["limit"] = limit
        eod = await self._call_safe("historical-price-eod/full", params)
        if not isinstance(eod, list):
            eod = []
        return {"historical_eod": eod}

    # ---------- Aggregated fetch (Phase 1 modules) ----------
    async def fetch_modules(
        self, symbol: str, modules: list[str]
    ) -> dict[str, Any]:
        """Fetch multiple modules in parallel. Returns { overview?, valuation?, ratios?, analyst?, charts? }."""
        sym = symbol.upper()
        allowed = {"overview", "valuation", "ratios", "analyst", "charts"}
        to_fetch = [m for m in modules if m in allowed]
        if not to_fetch:
            return {}

        async def get_overview() -> tuple[str, Any]:
            return ("overview", await self.fetch_overview(sym))

        async def get_valuation() -> tuple[str, Any]:
            return ("valuation", await self.fetch_valuation(sym))

        async def get_ratios() -> tuple[str, Any]:
            return ("ratios", await self.fetch_ratios(sym))

        async def get_analyst() -> tuple[str, Any]:
            return ("analyst", await self.fetch_analyst(sym))

        async def get_charts() -> tuple[str, Any]:
            return ("charts", await self.fetch_charts(sym))

        tasks_map = {
            "overview": get_overview,
            "valuation": get_valuation,
            "ratios": get_ratios,
            "analyst": get_analyst,
            "charts": get_charts,
        }
        tasks = [tasks_map[m]() for m in to_fetch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        out: dict[str, Any] = {}
        for r in results:
            if isinstance(r, Exception):
                logger.warning("Fundamental fetch error: %s", r)
                continue
            name, data = r
            out[name] = data
        return out

    # ---------- Cache helpers ----------
    async def get_cached(self, symbol: str, module: str) -> dict[str, Any] | None:
        """Return cached payload for (symbol, module) or None."""
        key = _cache_key(symbol, module)
        val = await cache_service.get(key)
        if val is not None and isinstance(val, dict):
            return val
        return None

    async def set_cached(self, symbol: str, module: str, data: dict[str, Any]) -> None:
        """Store payload in cache. TTL: overview 15 min, else 1h."""
        key = _cache_key(symbol, module)
        ttl = TTL_OVERVIEW if module == "overview" else TTL_DEFAULT
        await cache_service.set(key, data, ttl)

    async def get_cached_full(self, symbol: str) -> dict[str, Any] | None:
        """Return cached full payload for symbol or None."""
        key = _cache_key(symbol, "full")
        val = await cache_service.get(key)
        if val is not None and isinstance(val, dict):
            return val
        return None

    async def set_cached_full(self, symbol: str, data: dict[str, Any]) -> None:
        """Store full payload in cache. TTL 1h."""
        key = _cache_key(symbol, "full")
        await cache_service.set(key, data, TTL_DEFAULT)

    async def was_deducted_today(self, user_id: str, symbol: str) -> bool:
        """True if we already deducted one quota for this user+symbol today (UTC)."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = _deducted_key(str(user_id), date_str)
        val = await cache_service.get(key)
        if val is None:
            return False
        if isinstance(val, list):
            return symbol.upper() in [str(s) for s in val]
        return False

    async def mark_deducted_today(self, user_id: str, symbol: str) -> None:
        """Record that we deducted one quota for this user+symbol today."""
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        key = _deducted_key(str(user_id), date_str)
        val = await cache_service.get(key)
        sym = symbol.upper()
        if val is None or not isinstance(val, list):
            new_list = [sym]
        else:
            new_list = list(val) if sym in [str(s) for s in val] else list(val) + [sym]
        await cache_service.set(key, new_list, 86400 * 2)  # 2 days TTL
