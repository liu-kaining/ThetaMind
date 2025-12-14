import asyncio
import logging
from typing import Any

import pandas as pd  # For DataFrame handling in SDK 3.x

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool  # Critical for wrapping sync SDK
from pybreaker import CircuitBreaker, CircuitBreakerError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Tiger Open SDK Imports
from tigeropen.common.consts import Market
from tigeropen.quote.quote_client import QuoteClient
from tigeropen.tiger_open_config import TigerOpenClientConfig
from tigeropen.common.util.signature_utils import read_private_key
from tigeropen.quote.domain.filter import StockFilter, SortFilterData
from tigeropen.common.consts.filter_fields import StockField
from tigeropen.common.consts import SortDirection

from app.core.config import settings
from app.services.cache import cache_service

logger = logging.getLogger(__name__)

# Circuit breaker: Open if 5 failures, stay open for 60s
tiger_circuit_breaker = CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
)


class TigerService:
    """Tiger Brokers API service with resilience patterns."""

    def __init__(self) -> None:
        """Initialize Tiger SDK client.
        
        According to official Tiger SDK docs:
        - Preferred method: Use tiger_openapi_config.properties file via props_path
        - Config file contains: private_key_pk1, tiger_id, account, license, env
        - Python SDK uses PKCS#1 format private key
        Docs: https://docs.itigerup.com/docs/prepare
        """
        try:
            # Initialize TigerOpenClientConfig
            # Option 1: Use props_path if config file is available (preferred method per docs)
            # The props_path should point to the directory containing tiger_openapi_config.properties
            if settings.tiger_props_path:
                client_config = TigerOpenClientConfig(props_path=settings.tiger_props_path)
                logger.info(f"TigerService initialized using config file from: {settings.tiger_props_path}")
            else:
                # Option 2: Set attributes directly (fallback method)
                # Note: According to docs, config file method is preferred
                client_config = TigerOpenClientConfig()
                
                # Set developer information
                client_config.tiger_id = settings.tiger_id
                client_config.account = settings.tiger_account
                
                # Set private key - Python SDK uses PKCS#1 format
                # According to docs, private_key_pk1 in config file is PKCS#1 format
                # If it's a file path, use read_private_key(), otherwise use directly
                if settings.tiger_private_key.startswith('/') or settings.tiger_private_key.endswith('.pem'):
                    # Assume it's a file path - read_private_key handles PKCS#1 format
                    client_config.private_key = read_private_key(settings.tiger_private_key)
                else:
                    # Assume it's the key content as string (PKCS#1 format)
                    client_config.private_key = settings.tiger_private_key
                
                # Set environment (sandbox vs production)
                # According to docs: env=sandbox for testing, env=prod for production
                if settings.tiger_sandbox:
                    client_config.env = 'sandbox'
                else:
                    client_config.env = 'prod'
                
                logger.info("TigerService initialized using direct attribute configuration")
            
            # Set timezone to US/Eastern for US market data
            client_config.timezone = 'US/Eastern'
            
            # Initialize QuoteClient with config
            # Note: QuoteClient automatically calls grab_quote_permission() during initialization
            # This will grab permissions for markets that are enabled in the account
            # According to docs, permissions include: usQuoteBasic, usOptionQuote, hkStockQuoteLv2, etc.
            self._client = QuoteClient(client_config)
            
            # Log permissions grabbed (for debugging)
            try:
                permissions = self._client.permissions
                if permissions:
                    permission_names = [p.get('name', 'unknown') for p in permissions]
                    logger.info(f"TigerService initialized. Permissions grabbed: {', '.join(permission_names)}")
                    
                    # Check for US market permissions
                    us_perms = [p for p in permissions if 'usQuote' in p.get('name', '') or 'usOption' in p.get('name', '')]
                    if not us_perms:
                        logger.warning(
                            "No US market permissions found in grabbed permissions. "
                            "If you have usQuoteBasic/usOptionQuote, they may need to be activated "
                            "in Tiger client first, or the account may need specific configuration."
                        )
                else:
                    logger.warning("TigerService initialized but no permissions were grabbed")
            except Exception as e:
                logger.debug(f"Could not retrieve permissions: {e}")
            
            logger.info("TigerService initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize TigerService: {e}", exc_info=True)
            self._client = None

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    @tiger_circuit_breaker
    async def _call_tiger_api_async(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        Execute sync SDK methods in a thread pool to avoid blocking the async event loop.
        """
        if not self._client:
            raise RuntimeError("Tiger Client not initialized")

        try:
            # Get the method from the client instance
            method = getattr(self._client, method_name)
            
            # Run blocking I/O in thread pool
            logger.info(f"Calling Tiger API (Thread): {method_name} Args: {args}, Kwargs: {kwargs}")
            result = await run_in_threadpool(method, *args, **kwargs)
            return result

        except CircuitBreakerError:
            logger.error(f"Circuit Breaker OPEN. Blocking call to {method_name}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Market data service temporarily unavailable (Circuit Breaker)",
                headers={"Retry-After": "60"},
            )
        except Exception as e:
            logger.error(f"Tiger API Error in {method_name}: {str(e)}", exc_info=True)
            raise e

    async def get_option_expirations(self, symbol: str) -> list[str]:
        """
        Get available option expiration dates for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., AAPL)
            
        Returns:
            List of expiration dates in YYYY-MM-DD format, sorted chronologically
        """
        cache_key = f"market:expirations:{symbol}"
        ttl = 86400  # Cache for 24 hours (expirations don't change frequently)
        
        # Try cache first
        cached_data = await cache_service.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # Call Tiger SDK's get_option_expirations method
            expirations_data = await self._call_tiger_api_async(
                "get_option_expirations",
                symbol.upper(),
            )
            
            # Convert to list of date strings
            expiration_dates = []
            
            # Handle pandas DataFrame (SDK 3.x returns DataFrame)
            if isinstance(expirations_data, pd.DataFrame):
                if not expirations_data.empty and 'date' in expirations_data.columns:
                    # Extract dates from 'date' column (already in YYYY-MM-DD format)
                    dates = expirations_data['date'].dropna().unique()
                    for date_val in dates:
                        if isinstance(date_val, str):
                            # Already string format YYYY-MM-DD
                            if len(date_val) >= 10:
                                expiration_dates.append(date_val[:10])
                        elif pd.notna(date_val):
                            # Convert other types to string
                            expiration_dates.append(str(date_val)[:10])
                else:
                    logger.warning(f"No 'date' column found in expirations DataFrame for {symbol}")
            elif isinstance(expirations_data, (list, tuple)):
                for exp_date in expirations_data:
                    if isinstance(exp_date, (int, float)):
                        # Convert timestamp (milliseconds) to YYYY-MM-DD
                        from datetime import datetime
                        date_obj = datetime.fromtimestamp(exp_date / 1000 if exp_date > 1e10 else exp_date)
                        expiration_dates.append(date_obj.strftime("%Y-%m-%d"))
                    elif isinstance(exp_date, str):
                        # Already a string, use as-is if it's YYYY-MM-DD format
                        if len(exp_date) >= 10:
                            expiration_dates.append(exp_date[:10])
            elif hasattr(expirations_data, '__iter__') and not isinstance(expirations_data, dict):
                # Handle other iterable types (but not dict)
                for exp_date in expirations_data:
                    if isinstance(exp_date, (int, float)):
                        from datetime import datetime
                        date_obj = datetime.fromtimestamp(exp_date / 1000 if exp_date > 1e10 else exp_date)
                        expiration_dates.append(date_obj.strftime("%Y-%m-%d"))
                    elif isinstance(exp_date, str):
                        if len(exp_date) >= 10:
                            expiration_dates.append(exp_date[:10])
            
            # Remove duplicates and sort
            expiration_dates = sorted(list(set(expiration_dates)))
            
            # Ensure we return a list (not numpy array or other types)
            expiration_dates = [str(d) for d in expiration_dates if d]
            
            # Cache the result
            await cache_service.set(cache_key, expiration_dates, ttl=ttl)
            
            logger.info(f"Fetched {len(expiration_dates)} expiration dates for {symbol}: {expiration_dates[:5]}...")
            return expiration_dates
            
        except Exception as e:
            logger.error(f"Failed to fetch option expirations for {symbol}: {e}", exc_info=True)
            # Return empty list on error
            return []
    
    async def get_option_chain(
        self, symbol: str, expiration_date: str, is_pro: bool = False, force_refresh: bool = False
    ) -> dict[str, Any]:
        """
        Get option chain with Smart Caching Strategy.
        
        Cache Strategy (Production Mode):
        - Base TTL: 10 minutes (600s) for ALL users to conserve API quota
        - Option chains are heavy and don't need second-level updates
        - Manual Refresh: Only fetch fresh data if force_refresh=True
        
        Args:
            symbol: Stock symbol (e.g., AAPL)
            expiration_date: Expiration date in YYYY-MM-DD format
            is_pro: User pro status (for future use)
            force_refresh: If True, bypass cache and fetch fresh data from API
        
        Returns:
            Dict with calls, puts, and spot_price
        """
        # 1. Determine Cache Key & TTL
        cache_key = f"market:chain:{symbol}:{expiration_date}"
        ttl = 600  # 10 minutes for all users (conserves API quota)

        # 2. Try Cache First (unless force_refresh is True)
        if not force_refresh:
            cached_data = await cache_service.get(cache_key)
            if cached_data:
                # Add metadata flag if it's served from cache
                if isinstance(cached_data, dict):
                    cached_data["_source"] = "cache"
                return cached_data

        # 3. Cache Miss - Call API with Resilience
        try:
            # Official method signature from Tiger SDK (verified from source code):
            # get_option_chain(self, symbol, expiry, option_filter=None, **kwargs)
            # Docs: https://docs.itigerup.com/docs/quote-option
            # SDK Source Code Analysis:
            # - All kwargs are passed to OptionFilter when option_filter is None
            # - return_greek_value and market are NOT in the actual method signature
            # - These may be handled by the SDK's internal params object or may not be supported in this SDK version
            # Solution: Pass only symbol and expiry, let SDK use defaults
            # If market is required, it may be set in the client config (self._client config)
            # expiry format: String 'YYYY-MM-DD' (e.g., '2019-01-18')
            # Call Tiger SDK's get_option_chain with return_greek_value=True to get Greeks
            # According to docs: return_greek_value (bool): 是否返回希腊值 (Whether to return Greek values)
            # market (Market): Required parameter, supports US/HK
            from tigeropen.common.consts import Market
            
            chain_data = await self._call_tiger_api_async(
                "get_option_chain",
                symbol,  # Positional: symbol
                expiration_date,  # Positional: expiry (String format: 'YYYY-MM-DD')
                None,  # Positional: option_filter (None = no filter)
                return_greek_value=True,  # Request Greeks data (delta, gamma, theta, vega, rho)
                market=Market.US,  # Required: Market (US/HK)
            )
            
            # Serialize SDK response to dict for Redis caching
            # SDK 3.x returns pandas.DataFrame, need to convert to expected format
            if isinstance(chain_data, pd.DataFrame):
                # DataFrame format: need to convert to {calls: [...], puts: [...], spot_price: ...}
                if chain_data.empty:
                    serialized_data = {"calls": [], "puts": [], "spot_price": None}
                else:
                    # Check if DataFrame has underlying_price column (most reliable source)
                    spot_price_from_df = None
                    if 'underlying_price' in chain_data.columns:
                        # Get first non-null underlying_price value
                        underlying_prices = chain_data['underlying_price'].dropna()
                        if len(underlying_prices) > 0:
                            spot_price_from_df = _normalize_number(underlying_prices.iloc[0])
                    elif 'spot_price' in chain_data.columns:
                        spot_prices = chain_data['spot_price'].dropna()
                        if len(spot_prices) > 0:
                            spot_price_from_df = _normalize_number(spot_prices.iloc[0])
                    
                    # Separate calls and puts using 'put_call' column
                    calls_df = chain_data[chain_data['put_call'] == 'CALL'].copy()
                    puts_df = chain_data[chain_data['put_call'] == 'PUT'].copy()
                    
                    # Convert to list of dicts with normalized field names
                    calls = []
                    puts = []
                    
                    # Process calls
                    for _, row in calls_df.iterrows():
                        # Handle strike - may be string or number
                        strike_value = row.get('strike')
                        if isinstance(strike_value, str):
                            # Remove any non-numeric characters except decimal point
                            strike_value = strike_value.replace(',', '').strip()
                        strike = _normalize_number(strike_value)
                        
                        call_dict = {
                            "strike": strike,
                            "bid": _normalize_number(row.get('bid_price'), default=0),
                            "ask": _normalize_number(row.get('ask_price'), default=0),
                            "volume": _normalize_number(row.get('volume'), default=0),
                            "open_interest": _normalize_number(row.get('open_interest'), default=0),
                        }
                        # Add Greeks
                        greeks = {}
                        for greek_name in ["delta", "gamma", "theta", "vega", "rho"]:
                            value = _normalize_number(row.get(greek_name))
                            if value is not None:
                                call_dict[greek_name] = value
                                greeks[greek_name] = value
                        if greeks:
                            call_dict["greeks"] = greeks
                        # Add other fields
                        if pd.notna(row.get('latest_price')):
                            call_dict["latest_price"] = _normalize_number(row.get('latest_price'))
                        # Add implied_volatility (critical for AI analysis and risk assessment)
                        if pd.notna(row.get('implied_vol')):
                            iv_value = _normalize_number(row.get('implied_vol'))
                            if iv_value is not None:
                                call_dict["implied_vol"] = iv_value
                                call_dict["implied_volatility"] = iv_value  # Also include full name
                        if call_dict["strike"] is not None and call_dict["strike"] > 0:
                            calls.append(call_dict)
                    
                    # Process puts
                    for _, row in puts_df.iterrows():
                        # Handle strike - may be string or number
                        strike_value = row.get('strike')
                        if isinstance(strike_value, str):
                            # Remove any non-numeric characters except decimal point
                            strike_value = strike_value.replace(',', '').strip()
                        strike = _normalize_number(strike_value)
                        
                        put_dict = {
                            "strike": strike,
                            "bid": _normalize_number(row.get('bid_price'), default=0),
                            "ask": _normalize_number(row.get('ask_price'), default=0),
                            "volume": _normalize_number(row.get('volume'), default=0),
                            "open_interest": _normalize_number(row.get('open_interest'), default=0),
                        }
                        # Add Greeks
                        greeks = {}
                        for greek_name in ["delta", "gamma", "theta", "vega", "rho"]:
                            value = _normalize_number(row.get(greek_name))
                            if value is not None:
                                put_dict[greek_name] = value
                                greeks[greek_name] = value
                        if greeks:
                            put_dict["greeks"] = greeks
                        # Add other fields
                        if pd.notna(row.get('latest_price')):
                            put_dict["latest_price"] = _normalize_number(row.get('latest_price'))
                        # Add implied_volatility (critical for AI analysis and risk assessment)
                        if pd.notna(row.get('implied_vol')):
                            iv_value = _normalize_number(row.get('implied_vol'))
                            if iv_value is not None:
                                put_dict["implied_vol"] = iv_value
                                put_dict["implied_volatility"] = iv_value  # Also include full name
                        if put_dict["strike"] is not None and put_dict["strike"] > 0:
                            puts.append(put_dict)
                    
                    # Try to get spot price (prioritize direct field from DataFrame)
                    spot_price = None
                    
                    # Method 1: Use underlying_price/spot_price directly from DataFrame (most reliable)
                    if spot_price_from_df and spot_price_from_df > 0:
                        spot_price = spot_price_from_df
                        logger.debug(f"Using underlying_price from DataFrame for {symbol}: ${spot_price:.2f}")
                    
                    # Method 2: Try to infer from ATM options using delta
                    if (spot_price is None or spot_price <= 0) and len(calls) > 0 and len(puts) > 0:
                        # Find ATM options (delta closest to 0.5 for calls, -0.5 for puts)
                        atm_calls = [c for c in calls if c.get('delta') is not None and 0.3 < c.get('delta', 0) < 0.7]
                        atm_puts = [p for p in puts if p.get('delta') is not None and -0.7 < p.get('delta', 0) < -0.3]
                        if atm_calls and atm_puts:
                            # Use the option with delta closest to 0.5/-0.5
                            best_call = min(atm_calls, key=lambda c: abs(c.get('delta', 0) - 0.5))
                            best_put = min(atm_puts, key=lambda p: abs(abs(p.get('delta', 0)) - 0.5))
                            if best_call.get('strike') and best_put.get('strike'):
                                # Average the strikes of ATM options
                                spot_price = (best_call['strike'] + best_put['strike']) / 2
                                logger.debug(f"Using ATM inference for {symbol}: ${spot_price:.2f}")
                    
                    # Method 3: If delta-based inference failed, use median strike of options with volume
                    if (spot_price is None or spot_price <= 0) and len(calls) > 0 and len(puts) > 0:
                        # Get strikes from options with volume > 0
                        call_strikes = [c['strike'] for c in calls if c.get('strike') and c.get('volume', 0) > 0]
                        put_strikes = [p['strike'] for p in puts if p.get('strike') and p.get('volume', 0) > 0]
                        if call_strikes and put_strikes:
                            # Use median of strikes with volume
                            import statistics
                            all_strikes = sorted(call_strikes + put_strikes)
                            if all_strikes:
                                spot_price = statistics.median(all_strikes)
                                logger.debug(f"Using median strike inference for {symbol}: ${spot_price:.2f}")
                    
                    # Method 4: Fallback to get_realtime_price (Sandwich method) - only if all else fails
                    if spot_price is None or spot_price <= 0:
                        try:
                            spot_price = await self.get_realtime_price(symbol)
                            if spot_price:
                                logger.debug(f"Using Sandwich method for {symbol}: ${spot_price:.2f}")
                        except Exception:
                            # If all methods fail, use None
                            spot_price = None
                    
                    serialized_data = {
                        "calls": calls,
                        "puts": puts,
                        "spot_price": spot_price,
                    }
            elif hasattr(chain_data, '__dict__'):
                # Object with attributes (SDK 2.x format or custom object)
                serialized_data = {
                    k: v for k, v in chain_data.__dict__.items()
                    if not k.startswith('_')
                }
                # If it has to_dict method, try that first
                if hasattr(chain_data, 'to_dict'):
                    try:
                        dict_result = chain_data.to_dict()
                        # If to_dict returns a dict (not DataFrame format), use it
                        if isinstance(dict_result, dict) and not any(
                            isinstance(v, dict) and all(isinstance(k, int) for k in v.keys())
                            for v in dict_result.values() if isinstance(v, dict)
                        ):
                            serialized_data = dict_result
                    except Exception:
                        pass
            elif isinstance(chain_data, dict):
                serialized_data = chain_data
            else:
                # Fallback: try to convert to dict
                try:
                    serialized_data = dict(chain_data)
                except (TypeError, ValueError):
                    logger.warning(f"Could not serialize chain_data for {symbol}, caching as string")
                    serialized_data = {"raw": str(chain_data)}

            # 4. Set Cache with is_pro flag for correct TTL
            await cache_service.set(cache_key, serialized_data, ttl=ttl, is_pro=is_pro)
            
            return serialized_data

        except HTTPException:
            # Re-raise HTTP exceptions (like 503 from Circuit Breaker)
            raise
        except Exception as e:
            error_str = str(e)
            logger.error(f"Failed to fetch option chain: {e}", exc_info=True)
            
            # Check for specific permission errors
            if "permission denied" in error_str.lower() or "permissions" in error_str.lower():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Tiger API Permission Error: Your account does not have permission to access US option quote data. Please check your Tiger API permissions (usOptionQuote). Error: {error_str}"
                )
            # Check for rate limit errors
            elif "rate limit" in error_str.lower() or "limiting" in error_str.lower():
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Tiger API Rate Limit: {error_str}"
                )
            # Generic error
            else:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Failed to fetch option chain data from Tiger API: {error_str}"
                )

    async def get_kline_data(
        self, symbol: str, period: str = "day", limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get historical K-line (candlestick) data using Tiger's get_bars method.
        
        This uses Tiger's free quota for historical data.
        
        Args:
            symbol: Stock symbol (e.g., AAPL)
            period: Period type ('day', 'week', 'month', etc.)
            limit: Number of bars to return (default: 100)
            
        Returns:
            List of dicts with format: [{time, open, high, low, close, volume}, ...]
        """
        cache_key = f"market:kline:{symbol}:{period}:{limit}"
        ttl = 3600  # Cache for 1 hour (historical data doesn't change)
        
        # Try cache first
        cached_data = await cache_service.get(cache_key)
        if cached_data:
            return cached_data
        
        try:
            # Call Tiger SDK's get_bars method
            # Method signature: get_bars(symbols, period, limit, **kwargs)
            # Returns: pandas.DataFrame with columns: symbol, time, volume, open, close, high, low, amount
            result = await self._call_tiger_api_async(
                "get_bars",
                symbols=[symbol.upper()],
                period=period,
                limit=limit,
            )
            
            # Transform response to standard format
            kline_data = []
            
            # Handle pandas DataFrame (SDK 3.x returns DataFrame)
            if isinstance(result, pd.DataFrame):
                # Convert DataFrame to list of dicts
                if result.empty:
                    return []
                
                # Convert to records format: [{'time': ..., 'open': ..., ...}, ...]
                bars_list = result.to_dict('records')
                
                for bar_dict in bars_list:
                    # Extract and normalize fields
                    time_value = bar_dict.get('time') or bar_dict.get('Time') or bar_dict.get('timestamp')
                    open_value = _normalize_number(bar_dict.get('open') or bar_dict.get('Open'))
                    high_value = _normalize_number(bar_dict.get('high') or bar_dict.get('High'))
                    low_value = _normalize_number(bar_dict.get('low') or bar_dict.get('Low'))
                    close_value = _normalize_number(bar_dict.get('close') or bar_dict.get('Close'))
                    volume_value = _normalize_number(bar_dict.get('volume') or bar_dict.get('Volume'), default=0)
                    
                    if all(v is not None for v in [time_value, open_value, high_value, low_value, close_value]):
                        # Format time as ISO string or timestamp
                        if isinstance(time_value, (int, float)):
                            # Handle millisecond timestamp (Tiger SDK uses milliseconds)
                            if time_value > 1e10:  # Millisecond timestamp
                                time_value = time_value / 1000
                            from datetime import datetime
                            time_str = datetime.fromtimestamp(time_value).strftime("%Y-%m-%d")
                        elif isinstance(time_value, str):
                            time_str = time_value
                        else:
                            continue
                        
                        kline_data.append({
                            "time": time_str,
                            "open": open_value,
                            "high": high_value,
                            "low": low_value,
                            "close": close_value,
                            "volume": volume_value or 0,
                        })
            # Fallback for other formats (list, dict, etc.)
            elif isinstance(result, (list, tuple)):
                bars = result
                for bar in bars:
                    if isinstance(bar, dict):
                        bar_dict = bar
                    elif hasattr(bar, '__dict__'):
                        bar_dict = {k: v for k, v in bar.__dict__.items() if not k.startswith('_')}
                    elif hasattr(bar, 'to_dict'):
                        bar_dict = bar.to_dict()
                    else:
                        continue
                    
                    # Extract and normalize fields
                    time_value = bar_dict.get('time') or bar_dict.get('Time') or bar_dict.get('timestamp')
                    open_value = _normalize_number(bar_dict.get('open') or bar_dict.get('Open'))
                    high_value = _normalize_number(bar_dict.get('high') or bar_dict.get('High'))
                    low_value = _normalize_number(bar_dict.get('low') or bar_dict.get('Low'))
                    close_value = _normalize_number(bar_dict.get('close') or bar_dict.get('Close'))
                    volume_value = _normalize_number(bar_dict.get('volume') or bar_dict.get('Volume'), default=0)
                    
                    if all(v is not None for v in [time_value, open_value, high_value, low_value, close_value]):
                        # Format time
                        if isinstance(time_value, (int, float)):
                            if time_value > 1e10:  # Millisecond timestamp
                                time_value = time_value / 1000
                            from datetime import datetime
                            time_str = datetime.fromtimestamp(time_value).strftime("%Y-%m-%d")
                        elif isinstance(time_value, str):
                            time_str = time_value
                        else:
                            continue
                        
                        kline_data.append({
                            "time": time_str,
                            "open": open_value,
                            "high": high_value,
                            "low": low_value,
                            "close": close_value,
                            "volume": volume_value or 0,
                        })
            
            # Cache the result
            await cache_service.set(cache_key, kline_data, ttl=ttl)
            
            return kline_data
            
        except Exception as e:
            logger.error(f"Failed to fetch K-line data for {symbol}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch historical data from upstream provider"
            )
    
    async def get_realtime_price(self, symbol: str) -> float | None:
        """
        Estimate real-time price using the "Sandwich" method from option chain.
        
        Algorithm:
        1. Get option chain for nearest expiration
        2. Find highest ITM strike and lowest OTM strike in calls
        3. Estimate price = (ITM_boundary + OTM_boundary) / 2
        
        This avoids expensive Level 1 quote calls.
        
        Args:
            symbol: Stock symbol (e.g., AAPL)
            
        Returns:
            Estimated price or None if inference fails
        """
        try:
            # Step A: Get nearest expiration
            # For now, we'll use a common expiration (next Friday)
            # In production, you might want to fetch available expirations first
            from datetime import datetime, timedelta
            today = datetime.now()
            days_until_friday = (4 - today.weekday() + 7) % 7 or 7
            next_friday = today + timedelta(days=days_until_friday)
            expiration_date = next_friday.strftime("%Y-%m-%d")
            
            # Step B: Fetch option chain for nearest expiration
            chain_data = await self.get_option_chain(
                symbol=symbol.upper(),
                expiration_date=expiration_date,
                is_pro=False,  # Use free tier cache
            )
            
            # Step C: The Sandwich Method
            calls = chain_data.get("calls", []) or []
            if not calls:
                logger.warning(f"No call options found for {symbol} to infer price")
                return None
            
            # Edge case: Check if we have spot_price directly from chain (most reliable)
            spot_price_from_chain = _normalize_number(
                chain_data.get("spot_price") or 
                chain_data.get("underlying_price") or 
                chain_data.get("underlyingPrice")
            )
            if spot_price_from_chain and spot_price_from_chain > 0:
                logger.info(f"Using spot_price from chain for {symbol}: ${spot_price_from_chain:.2f}")
                return spot_price_from_chain
            
            # Find ITM and OTM boundaries using delta
            # For Call options:
            # - ITM: delta > 0.5 (intrinsic value dominates)
            # - OTM: delta < 0.5 (time value dominates)
            highest_itm_strike = None
            lowest_otm_strike = None
            valid_calls_with_delta = 0
            
            for call in calls:
                strike = _normalize_number(call.get("strike") or call.get("strike_price"))
                if strike is None or strike <= 0:
                    continue
                
                # Extract delta from Greeks (handle nested or flat format)
                delta = None
                greeks = call.get("greeks", {})
                if isinstance(greeks, dict):
                    delta = _normalize_number(greeks.get("delta"))
                if delta is None:
                    delta = _normalize_number(call.get("delta"))
                
                # Use delta to determine ITM/OTM
                # Delta > 0.5 for calls means ITM, < 0.5 means OTM
                if delta is not None:
                    valid_calls_with_delta += 1
                    if delta > 0.5:
                        # ITM: current price > strike
                        if highest_itm_strike is None or strike > highest_itm_strike:
                            highest_itm_strike = strike
                    elif delta < 0.5:
                        # OTM: current price < strike
                        if lowest_otm_strike is None or strike < lowest_otm_strike:
                            lowest_otm_strike = strike
            
            # Edge case: No calls with delta found (market closed or data incomplete)
            if valid_calls_with_delta == 0:
                logger.warning(f"No call options with delta found for {symbol}. Market may be closed or data incomplete.")
                # Fallback: Use strike-based estimation (less accurate)
                strikes = [_normalize_number(c.get("strike") or c.get("strike_price")) for c in calls]
                strikes = [s for s in strikes if s is not None and s > 0]
                if strikes:
                    # Assume price is near the middle of strike range
                    avg_strike = sum(strikes) / len(strikes)
                    logger.info(f"Fallback: Estimated price for {symbol} using average strike: ${avg_strike:.2f}")
                    return avg_strike
                return None
            
            # Calculate estimated price
            if highest_itm_strike is not None and lowest_otm_strike is not None:
                estimated_price = (highest_itm_strike + lowest_otm_strike) / 2
                logger.info(f"Inferred price for {symbol}: ${estimated_price:.2f} (ITM: ${highest_itm_strike:.2f}, OTM: ${lowest_otm_strike:.2f})")
                return estimated_price
            elif highest_itm_strike is not None:
                # Only ITM found, estimate slightly above
                estimated_price = highest_itm_strike * 1.02
                logger.info(f"Inferred price for {symbol}: ${estimated_price:.2f} (using ITM boundary only)")
                return estimated_price
            elif lowest_otm_strike is not None:
                # Only OTM found, estimate slightly below
                estimated_price = lowest_otm_strike * 0.98
                logger.info(f"Inferred price for {symbol}: ${estimated_price:.2f} (using OTM boundary only)")
                return estimated_price
            else:
                logger.warning(f"Could not infer price for {symbol}: no ITM/OTM boundaries found (had {valid_calls_with_delta} calls with delta)")
                return None
                
        except Exception as e:
            logger.error(f"Failed to infer price for {symbol}: {e}", exc_info=True)
            return None
    
    async def get_market_scanner(
        self,
        market: str = "US",
        criteria: str | None = None,
        market_value_min: float | None = None,
        volume_min: float | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get market scanner results using Tiger Scanner API.
        
        Uses the official market_scanner method with StockFilter objects.
        Reference: https://docs.itigerup.com/docs/quote-scanner
        
        Args:
            market: Market identifier (default: "US")
            criteria: Scanner criteria (e.g., "high_iv", "top_gainers", "most_active")
            market_value_min: Minimum market cap filter
            volume_min: Minimum volume filter
            limit: Maximum number of results
            
        Returns:
            List of stock dicts with symbol, name, price, change%, etc.
        """
        try:
            # Build filters list
            filters = []
            
            # Market cap filter
            if market_value_min:
                market_cap_filter = StockFilter(
                    StockField.MarketValue,  # Use MarketValue (camelCase as per SDK)
                    filter_min=market_value_min,
                )
                filters.append(market_cap_filter)
            
            # Volume filter
            if volume_min:
                volume_filter = StockFilter(
                    StockField.Volume,  # Use Volume (camelCase as per SDK)
                    filter_min=volume_min,
                )
                filters.append(volume_filter)
            
            # Build sort field based on criteria
            sort_field_data = None
            if criteria:
                criteria_map = {
                    "top_gainers": (StockField.current_ChangeRate, SortDirection.DESC),  # Use current_ChangeRate
                    "top_losers": (StockField.current_ChangeRate, SortDirection.ASC),
                    "most_active": (StockField.Volume, SortDirection.DESC),
                    "high_volume": (StockField.Volume, SortDirection.DESC),
                    # Note: high_iv may not be directly available in StockField
                    # May need to use option-related fields or AccumulateField
                }
                if criteria in criteria_map:
                    field, sort_dir = criteria_map[criteria]
                    sort_field_data = SortFilterData(field=field, sort_dir=sort_dir)
            
            # Default sort by market value if no criteria specified
            if not sort_field_data:
                sort_field_data = SortFilterData(field=StockField.MarketValue, sort_dir=SortDirection.DESC)
            
            # Call market_scanner with pagination
            # Note: SDK version may use 'page' instead of 'cursor_id'
            # Rate limit: 10 calls per minute (per Tiger API docs)
            all_stocks = []
            page = 0
            page_size = min(limit, 200)  # Max page_size is 200 per docs
            collected = 0
            import time
            last_call_time = 0
            min_interval = 6.1  # 6.1 seconds between calls (to stay under 10/min limit)
            
            while collected < limit:
                # Call market_scanner
                # Build kwargs - use page for pagination (SDK signature uses page, not cursor_id)
                # Rate limiting: ensure at least 6.1 seconds between calls
                current_time = time.time()
                time_since_last_call = current_time - last_call_time
                if time_since_last_call < min_interval:
                    sleep_time = min_interval - time_since_last_call
                    logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s before next scanner call")
                    await asyncio.sleep(sleep_time)
                
                scanner_kwargs = {
                    "market": Market.US if market == "US" else market,
                    "page": page,
                    "page_size": page_size,
                }
                
                if filters:
                    scanner_kwargs["filters"] = filters
                if sort_field_data:
                    scanner_kwargs["sort_field_data"] = sort_field_data
                
                try:
                    scanner_result = await self._call_tiger_api_async(
                        "market_scanner",
                        **scanner_kwargs,
                    )
                    last_call_time = time.time()
                except Exception as e:
                    error_str = str(e)
                    # Check for rate limit error
                    if "rate limit" in error_str.lower() or "limiting" in error_str.lower():
                        logger.warning(f"Rate limit hit, waiting 60 seconds before retry...")
                        await asyncio.sleep(60)  # Wait 1 minute
                        last_call_time = time.time()
                        continue  # Retry the same page
                    else:
                        raise  # Re-raise other errors
                
                # Parse result
                if hasattr(scanner_result, 'items'):
                    items = scanner_result.items
                    symbols = scanner_result.symbols if hasattr(scanner_result, 'symbols') else []
                elif isinstance(scanner_result, dict):
                    items = scanner_result.get("items", [])
                    symbols = scanner_result.get("symbols", [])
                else:
                    items = []
                    symbols = []
                
                # Process items
                for item in items:
                    if collected >= limit:
                        break
                    
                    # Extract data from item
                    if hasattr(item, 'symbol'):
                        symbol = item.symbol
                    elif isinstance(item, dict):
                        symbol = item.get("symbol")
                    else:
                        continue
                    
                    # Get other fields
                    if hasattr(item, '__dict__'):
                        item_dict = {k: v for k, v in item.__dict__.items() if not k.startswith('_')}
                    elif isinstance(item, dict):
                        item_dict = item
                    else:
                        item_dict = {}
                    
                    # Extract values from filters if available
                    price = None
                    change = None
                    change_percent = None
                    volume = None
                    market_value = None
                    name = symbol.upper()
                    
                    # Try to get values from item attributes or filter access
                    for attr in ['price', 'last_price', 'close']:
                        if hasattr(item, attr):
                            price = _normalize_number(getattr(item, attr))
                            break
                        elif attr in item_dict:
                            price = _normalize_number(item_dict[attr])
                            break
                    
                    for attr in ['change', 'change_amount']:
                        if hasattr(item, attr):
                            change = _normalize_number(getattr(item, attr))
                            break
                        elif attr in item_dict:
                            change = _normalize_number(item_dict[attr])
                            break
                    
                    for attr in ['change_percent', 'change_rate', 'change_pct']:
                        if hasattr(item, attr):
                            change_percent = _normalize_number(getattr(item, attr))
                            break
                        elif attr in item_dict:
                            change_percent = _normalize_number(item_dict[attr])
                            break
                    
                    for attr in ['volume']:
                        if hasattr(item, attr):
                            volume = _normalize_number(getattr(item, attr), default=0)
                            break
                        elif attr in item_dict:
                            volume = _normalize_number(item_dict[attr], default=0)
                            break
                    
                    for attr in ['market_value', 'market_cap', 'marketCap']:
                        if hasattr(item, attr):
                            market_value = _normalize_number(getattr(item, attr))
                            break
                        elif attr in item_dict:
                            market_value = _normalize_number(item_dict[attr])
                            break
                    
                    # Try to get name from item
                    name = symbol.upper()  # Default fallback
                    for attr in ['name', 'company_name', 'description', 'display_name']:
                        if hasattr(item, attr):
                            attr_value = getattr(item, attr)
                            if attr_value:
                                name = str(attr_value)
                                break
                        elif attr in item_dict and item_dict[attr]:
                            name = str(item_dict[attr])
                            break
                    
                    # Try to access filter values (per Tiger SDK docs, can use item[filter])
                    # This might give us additional data
                    try:
                        if hasattr(item, '__getitem__') and filters:
                            # Try to get market value from filter if available
                            for f in filters:
                                if hasattr(f, 'field') and str(f.field) == 'MarketValue':
                                    try:
                                        filter_value = item[f]
                                        if filter_value is not None:
                                            market_value = _normalize_number(filter_value) or market_value
                                    except (KeyError, TypeError):
                                        pass
                    except Exception:
                        pass  # Ignore errors when accessing filter values
                    
                    all_stocks.append({
                        "symbol": symbol.upper() if symbol else "UNKNOWN",
                        "name": name,
                        "price": price,
                        "change": change,
                        "change_percent": change_percent,
                        "volume": volume,
                        "market_value": market_value,
                    })
                    collected += 1
                
                # Check if we need more pages
                # Check total_page or if we got fewer items than page_size (last page)
                is_last_page = False
                if hasattr(scanner_result, 'total_page'):
                    total_page = scanner_result.total_page
                    current_page = scanner_result.page if hasattr(scanner_result, 'page') else page
                    is_last_page = (current_page + 1 >= total_page) if total_page else (len(items) < page_size)
                elif isinstance(scanner_result, dict):
                    total_page = scanner_result.get("total_page", 0)
                    current_page = scanner_result.get("page", page)
                    is_last_page = (current_page + 1 >= total_page) if total_page else (len(items) < page_size)
                else:
                    # If no pagination info, assume last page if we got fewer items
                    is_last_page = len(items) < page_size
                
                # Break if last page or we have enough
                if is_last_page or collected >= limit:
                    break
                
                # Move to next page
                page += 1
            
            return all_stocks[:limit]
            
        except Exception as e:
            logger.error(f"Failed to fetch market scanner data: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch market scanner data from upstream provider"
            )
    
    async def ping(self) -> bool:
        """Check API connectivity.
        
        Uses get_market_status as a lightweight connectivity test (cheaper than get_stock_briefs).
        """
        try:
            # Use get_market_status as a lightweight connectivity test
            # This is cheaper/free compared to get_stock_briefs
            await self._call_tiger_api_async("get_market_status", Market.US)
            return True
        except Exception as e:
            logger.debug(f"Tiger API ping failed: {e}")
            return False


def _normalize_number(value: Any, default: float | None = None) -> float | None:
    """Helper function to normalize a value to a float number."""
    import math
    if value is None:
        return default
    if isinstance(value, (int, float)):
        if not (math.isnan(value) or math.isinf(value)):
            return float(value)
        return default
    if isinstance(value, str):
        try:
            num = float(value)
            if not (math.isnan(num) or math.isinf(num)):
                return num
        except (ValueError, TypeError):
            pass
    return default

# Singleton instance
tiger_service = TigerService()