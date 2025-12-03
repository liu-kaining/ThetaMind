import logging
from typing import Any

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
            self._client = QuoteClient(client_config)
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
            logger.info(f"Calling Tiger API (Thread): {method_name} Args: {args}")
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

    async def get_option_chain(
        self, symbol: str, expiration_date: str, is_pro: bool = False
    ) -> dict[str, Any]:
        """
        Get option chain with Smart Caching Strategy.
        
        TTL Strategy:
        - Pro User: 5 seconds (Real-time feel)
        - Free User: 900 seconds (15 mins)
        """
        # 1. Determine Cache Key & TTL
        cache_key = f"market:chain:{symbol}:{expiration_date}"
        ttl = 5 if is_pro else 900

        # 2. Try Cache First
        # Note: Assuming cache_service.get returns parsed JSON or dict
        cached_data = await cache_service.get(cache_key)
        if cached_data:
            # Add metadata flag if it's served from cache (optional)
            if isinstance(cached_data, dict):
                cached_data["_source"] = "cache"
            return cached_data

        # 3. Cache Miss - Call API with Resilience
        try:
            # Official method signature from Tiger SDK docs:
            # get_option_chain(symbol, expiry, option_filter=None, return_greek_value=None, market=None, timezone=None, **kwargs)
            # Docs: https://docs.itigerup.com/docs/quote-option
            # expiry format: String 'YYYY-MM-DD' (e.g., '2019-01-18')
            chain_data = await self._call_tiger_api_async(
                "get_option_chain",
                symbol=symbol,
                expiry=expiration_date,  # String format: 'YYYY-MM-DD'
                market=Market.US,  # Required for US options
                return_greek_value=True,  # Return Greeks (delta, gamma, theta, vega, etc.)
            )
            
            # Serialize SDK response to dict for Redis caching
            if hasattr(chain_data, 'to_dict'):
                serialized_data = chain_data.to_dict()
            elif hasattr(chain_data, '__dict__'):
                # Convert object to dict
                serialized_data = {
                    k: v for k, v in chain_data.__dict__.items()
                    if not k.startswith('_')
                }
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
            logger.error(f"Failed to fetch option chain: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch data from upstream provider"
            )

    async def ping(self) -> bool:
        """Check API connectivity.
        
        Uses get_stock_briefs as a lightweight connectivity test.
        According to Tiger SDK docs, this method accepts a list of symbols.
        """
        try:
            # Use get_stock_briefs as a lightweight connectivity test
            # Docs: https://docs.itigerup.com/docs/quickstart
            # Method signature: get_stock_briefs(symbols: list[str])
            await self._call_tiger_api_async("get_stock_briefs", symbols=['AAPL'])
            return True
        except Exception as e:
            logger.debug(f"Tiger API ping failed: {e}")
            return False

# Singleton instance
tiger_service = TigerService()