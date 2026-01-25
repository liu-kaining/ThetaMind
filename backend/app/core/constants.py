"""Application constants to replace magic numbers."""

from typing import Final


class CacheTTL:
    """Cache TTL constants (in seconds)."""
    
    OPTION_CHAIN: Final[int] = 600  # 10 minutes
    HISTORICAL_DATA: Final[int] = 86400  # 24 hours
    EXPIRATIONS: Final[int] = 86400  # 24 hours
    MARKET_QUOTE: Final[int] = 60  # 1 minute
    FINANCIAL_PROFILE: Final[int] = 3600  # 1 hour
    OPTIONS_DATA: Final[int] = 600  # 10 minutes


class RetryConfig:
    """Retry configuration constants."""
    
    MAX_RETRIES: Final[int] = 3
    BACKOFF_MULTIPLIER: Final[int] = 2
    INITIAL_WAIT_SECONDS: Final[int] = 2  # seconds


class TimeoutConfig:
    """Timeout configuration constants (in seconds)."""
    
    AI_MODEL_TIMEOUT: Final[int] = 600  # 10 minutes for multi-agent tasks
    TIGER_API_TIMEOUT: Final[int] = 30  # 30 seconds
    REDIS_CONNECTION_TIMEOUT: Final[int] = 5  # 5 seconds
    DATABASE_QUERY_TIMEOUT: Final[int] = 30  # 30 seconds


class FinancialPrecision:
    """Financial calculation precision constants."""
    
    DECIMAL_PLACES: Final[int] = 4  # 4 decimal places for Greeks
    ROUNDING_MODE: Final[str] = "ROUND_HALF_UP"  # Standard financial rounding


class RateLimits:
    """Rate limiting constants."""
    
    WEBHOOK_REQUESTS_PER_MINUTE: Final[int] = 10
    API_REQUESTS_PER_MINUTE: Final[int] = 60
    TIGER_API_CALLS_PER_MINUTE: Final[int] = 10  # Tiger API limit
