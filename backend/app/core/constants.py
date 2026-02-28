"""Application constants to replace magic numbers."""

from typing import Final


class CacheTTL:
    """Cache TTL constants (in seconds)."""
    
    OPTION_CHAIN: Final[int] = 600  # 10 minutes
    HISTORICAL_DATA: Final[int] = 86400  # 24 hours
    EXPIRATIONS: Final[int] = 86400  # 24 hours
    MARKET_QUOTE: Final[int] = 60  # 1 minute
    FINANCIAL_PROFILE: Final[int] = 1800  # 30 minutes per symbol
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


# Report model options for user selection (GET /ai/models).
# Overridable via admin config key "ai_report_models_json" (JSON array of {id, provider, label}).
# Google: Gemini 3 Pro Preview discontinued 2026-03-09; use gemini-3.1-pro-preview. 2.5 Pro still available.
REPORT_MODELS: list[dict[str, str]] = [
    {"id": "gemini-3.1-pro-preview", "provider": "gemini", "label": "Gemini 3.1 Pro Preview (Latest)"},
    {"id": "gemini-3-flash-preview", "provider": "gemini", "label": "Gemini 3 Flash Preview"},
    {"id": "gemini-3-pro-preview", "provider": "gemini", "label": "Gemini 3 Pro Preview (Deprecated Mar 2026)"},
    {"id": "gemini-2.5-pro", "provider": "gemini", "label": "Gemini 2.5 Pro"},
]

# Image generation model options. Overridable via admin config key "ai_image_models_json".
IMAGE_MODELS: list[dict[str, str]] = [
    {"id": "openai/gpt-image-1.5", "provider": "zenmux", "label": "OpenAI GPT Image 1.5"},
    {"id": "google/gemini-3-pro-image-preview", "provider": "zenmux", "label": "Gemini 3 Pro Image"},
]
