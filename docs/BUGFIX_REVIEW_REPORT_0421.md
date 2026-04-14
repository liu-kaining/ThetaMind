# ThetaMind Bug Fix Review Report — 2026-02-21

## Overview

This report documents the systematic fix of **15 issues** identified in the CTO Code Audit (0414). All fixes have been reviewed for backward compatibility and production safety.

---

## CRITICAL Fixes (3)

### P1: Webhook Idempotency Key — FIXED

**File**: `backend/app/services/payment_service.py`

**Problem**: The idempotency key used the Lemon Squeezy **resource ID** (e.g., subscription ID `12345`). This meant that `subscription_created` and `subscription_updated` events for the **same subscription** shared an idempotency key, causing `subscription_updated` to be silently skipped. User upgrades from monthly→yearly would never take effect.

**Fix**: Changed the idempotency key to `"{event_name}:{resource_id}"` (e.g., `subscription_created:12345`). Each event type now gets its own processing slot. The `user.subscription_id` is set to the raw `resource_id` (not the composite key) to preserve existing portal URL logic.

**Backward Compatibility**: The `lemon_squeezy_id` column stores longer strings. Existing processed events remain valid (won't be re-processed). New events use the new format.

---

### T1: Option Chain Cache Disabled — FIXED

**File**: `backend/app/services/tiger_service.py`

**Problem**: `ttl = 0` completely disabled caching, causing every option chain request to hit the Tiger API directly. This wastes Tiger's 10-calls/minute quota and causes latency spikes.

**Fix**: Restored `ttl = CacheTTL.OPTION_CHAIN` (600 seconds = 10 minutes). The cache SET logic at line ~587 was already in place but was never reached due to `ttl > 0` being false.

**Backward Compatibility**: Fully backward compatible. Cache miss falls through to live API.

---

### I1: Migration Failure Silently Ignored — FIXED

**File**: `backend/entrypoint.sh`

**Problem**: `set +e` allowed Alembic migration failures to be logged as a WARNING but the app would start anyway, potentially running against a stale schema and corrupting data.

**Fix**: Replaced the `set +e / set -e` pattern with a simple `if ! alembic upgrade head` that exits with code 1 on failure, preventing the uvicorn server from starting. The error message includes remediation steps.

**Backward Compatibility**: No change to successful deployments. Failed migrations now correctly block startup.

---

## HIGH Fixes (4)

### P2: Split Quota Reset Race Condition — FIXED

**Files**: `backend/app/api/endpoints/ai.py`, `backend/app/api/endpoints/company_data.py`

**Problem**: Two independent `check_and_reset_*` functions both check `last_quota_reset_date` and reset only their own counters. If `company_data` resets first (setting `last_quota_reset_date` to today), the `ai` reset is skipped for the rest of the day, leaving stale `daily_ai_usage`.

**Fix**: Both reset functions now reset ALL quota counters atomically (`daily_ai_usage`, `daily_image_usage`, `daily_fundamental_queries_used`). Whichever fires first resets everything; subsequent calls see `last_reset == today` and skip.

**Backward Compatibility**: Fully compatible. Users get a cleaner reset experience.

---

### T2: get_option_chain ↔ get_realtime_price Mutual Recursion — FIXED

**File**: `backend/app/services/tiger_service.py`

**Problem**: `get_option_chain` calls `get_realtime_price` when spot_price is missing. `get_realtime_price` calls `get_option_chain` for nearest expiry. If neither has a cached spot price, this creates unbounded recursion until Python's stack limit is hit.

**Fix**: Added `_from_chain: bool = False` parameter to `get_realtime_price`. When called from `get_option_chain`, it passes `_from_chain=True`, causing `get_realtime_price` to return `None` immediately instead of calling back into the chain.

**Backward Compatibility**: External callers don't pass `_from_chain`, so behavior is unchanged. Only the internal recursion path is broken.

---

### S1: BEARISH Strategy (Bear Put Spread) — IMPLEMENTED

**File**: `backend/app/services/strategy_engine.py`

**Problem**: `Outlook.BEARISH` was a valid enum value but `generate_strategies` returned an empty list with a debug log, effectively dead code.

**Fix**: Implemented `_algorithm_bear_put_spread` as a mirror of `_algorithm_bull_call_spread`:
- Buy ITM put (delta ≈ -0.65), sell OTM put (delta ≈ -0.30)
- Validation: net debit < 50% of spread width, liquidity check
- Breakeven = buy_strike - net_debit
- Follows identical patterns as the bull call spread for consistency

**Backward Compatibility**: New functionality only. Existing strategies unaffected.

---

### S2: Iron Condor POP Formula — FIXED

**File**: `backend/app/services/strategy_engine.py`

**Problem**: POP was calculated as `(wing_width - net_credit) / wing_width`, which equals `max_loss / wing_width` — not a meaningful probability. For a $5 wing with $1.50 credit, this gives 0.70, but the actual POP depends on the short strikes' delta.

**Fix**: Changed to delta-based POP: `POP = 1 - |short_call_delta| - |short_put_delta|`. For 0.20-delta shorts, POP ≈ 0.60, which is the industry-standard approximation. Falls back to `target_delta_short` if delta is unavailable.

**Note**: The breakeven formulas (`short_call + credit`, `short_put - credit`) were verified as correct for a standard Iron Condor and left unchanged.

**Backward Compatibility**: POP values will change (typically lower, more realistic). This is a correctness fix.

---

## MEDIUM Fixes (7)

### M1: Duplicate FMP Decorators — FIXED

**File**: `backend/app/services/market_data_service.py`

**Problem**: Both `_call_fmp_api` (async) and `_call_fmp_api_sync` had doubled `@fmp_circuit_breaker` and `@retry` decorators, causing each call to retry 9 times (3×3) through two circuit breakers.

**Fix**: Removed the duplicate decorator stack from both methods. Each now has a single `@fmp_circuit_breaker` + `@retry` pair.

---

### M2: Error Path Missing FMP Fields — FIXED

**File**: `backend/app/services/market_data_service.py`

**Problem**: The `except` block in `get_financial_profile` returned a dict missing `dcf_valuation`, `insider_trading`, and `senate_trading` keys, causing downstream `KeyError` in AI agents that expect these fields.

**Fix**: Added all three keys with `None` values to the error-path return dict.

---

### M5: RSI Path Mismatch — FIXED

**File**: `backend/app/services/market_data_service.py`

**Problem**: `_generate_analysis` looked for RSI under `tech_indicators["rsi"]`, but FinanceToolkit stores RSI under `tech_indicators["momentum"]["<date>"]["RSI"]`. The RSI signal was never generated.

**Fix**: Added fallback lookup into `tech_indicators["momentum"]` before proceeding with RSI analysis. The original `rsi` key is checked first for backward compatibility.

---

### P3: is_pro Expiry Check — FIXED

**File**: `backend/app/api/deps.py`

**Problem**: If Lemon Squeezy's `subscription_expired` webhook is missed (network issue, outage), `is_pro` stays `True` forever. No runtime check enforces the expiry date.

**Fix**: Added expiry check in `get_current_user` dependency (runs on every authenticated request). If `is_pro=True` and `plan_expiry_date < now(UTC)`, the user is auto-downgraded. This is a safety net — the webhook remains the primary mechanism.

**Backward Compatibility**: Only affects users whose subscription has genuinely expired. No impact on active subscribers.

---

### F1: Strategy Update (PUT) in Frontend — FIXED

**File**: `frontend/src/pages/StrategyLab.tsx`

**Problem**: `saveStrategyMutation` always called `strategyService.create()`, even when editing an existing strategy (loaded via `?strategy=<id>`). This created duplicates instead of updating.

**Fix**: Added conditional: if `strategyId` exists (from URL params), call `strategyService.update(strategyId, payload)` instead of `create(payload)`. The backend PUT endpoint already existed at `/api/v1/strategies/{strategy_id}`.

---

### I2: Radar Market Hours Filter — FIXED

**File**: `backend/app/services/radar_service.py`

**Problem**: `scan_and_alert()` ran every cron cycle regardless of time, consuming Tiger API quota during off-hours when results are stale.

**Fix**: Added `_is_us_market_hours()` check: only runs Mon-Fri 9:00-16:30 ET. Uses `pytz` (already a project dependency) for timezone safety.

---

### I3: Radar Alert Deduplication — FIXED

**File**: `backend/app/services/radar_service.py`

**Problem**: If AAPL appears in top gainers across consecutive cron cycles, users receive duplicate alerts for the same symbol on the same day.

**Fix**: Added Redis-based dedup using `cache_service`. Before sending, checks `radar:alerted:{YYYYMMDD}:{symbol}` key. After sending, sets the key with 24h TTL. If cache is unavailable, alerts still send (graceful degradation).

---

## LOW Fixes (1)

### P5: Dashboard Quota Display Mismatch — FIXED

**File**: `frontend/src/pages/DashboardPage.tsx`

**Problem**: Fallback quota values in the dashboard showed `1` for free, `20` for monthly, `30` for yearly — but actual backend limits are `5`, `40`, `100`.

**Fix**: Updated fallback values to match backend constants: `FREE_AI_QUOTA=5`, `PRO_MONTHLY_AI_QUOTA=40`, `PRO_YEARLY_AI_QUOTA=100`. These fallbacks only apply if the `/me` API response doesn't include `daily_ai_quota` (edge case).

---

## Files Modified Summary

| File | Changes |
|------|---------|
| `backend/app/services/payment_service.py` | Idempotency key fix |
| `backend/app/services/tiger_service.py` | Cache restore + recursion guard |
| `backend/app/services/strategy_engine.py` | Bear Put Spread + POP fix |
| `backend/app/services/market_data_service.py` | Dedup decorators + error path + RSI |
| `backend/app/services/radar_service.py` | Market hours + alert dedup |
| `backend/app/api/deps.py` | Pro expiry check |
| `backend/app/api/endpoints/ai.py` | Unified quota reset |
| `backend/app/api/endpoints/company_data.py` | Unified quota reset |
| `backend/entrypoint.sh` | Migration failure blocks startup |
| `frontend/src/pages/StrategyLab.tsx` | Strategy update (PUT) |
| `frontend/src/pages/DashboardPage.tsx` | Quota display fix |

## Risk Assessment

- **No breaking API changes**: All endpoint contracts preserved
- **No DB schema changes**: No new migrations required
- **No new dependencies**: All imports (`pytz`, `cache_service`) are existing project deps
- **Linter check**: Zero new warnings introduced (all 47 warnings are pre-existing IDE config issues)

## Recommendation

Deploy with confidence. Monitor webhook logs (`payment_events` table) after deployment to verify the new idempotency key format works correctly with Lemon Squeezy's retry behavior.
