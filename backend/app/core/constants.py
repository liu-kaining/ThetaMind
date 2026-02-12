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
# ZenMux slugs: provider/model per https://zenmux.ai/docs/guide/quickstart.html
REPORT_MODELS: list[dict[str, str]] = [
    {"id": "gemini-3-flash-preview", "provider": "gemini", "label": "Gemini 3 Flash (default)"},
    {"id": "gemini-2.5-pro", "provider": "gemini", "label": "Gemini 2.5 Pro"},
    {"id": "z-ai/glm-5", "provider": "zenmux", "label": "Z-AI GLM-5"},
    {"id": "moonshotai/kimi-k2.5", "provider": "zenmux", "label": "Moonshot Kimi K2.5"},
    {"id": "qwen/qwen3-max", "provider": "zenmux", "label": "Qwen3 Max"},
    {"id": "baidu/ernie-5.0-thinking-preview", "provider": "zenmux", "label": "Baidu Ernie 5.0 Thinking"},
    {"id": "google/gemini-3-pro-preview", "provider": "zenmux", "label": "ZenMux · Gemini 3 Pro"},
    {"id": "google/gemini-3-flash-preview", "provider": "zenmux", "label": "ZenMux · Gemini 3 Flash"},
    {"id": "openai/gpt-5.2-pro", "provider": "zenmux", "label": "OpenAI GPT-5.2 Pro"},
    {"id": "openai/gpt-5.1", "provider": "zenmux", "label": "OpenAI GPT-5.1"},
    {"id": "deepseek/deepseek-v3.2", "provider": "zenmux", "label": "DeepSeek V3.2"},
    {"id": "x-ai/grok-4.1-fast", "provider": "zenmux", "label": "xAI Grok 4.1 Fast"},
    {"id": "qwen/qwen3-max-preview", "provider": "zenmux", "label": "Qwen3 Max Preview"},
]

# Image generation model options. Overridable via admin config key "ai_image_models_json".
IMAGE_MODELS: list[dict[str, str]] = [
    {"id": "openai/gpt-image-1.5", "provider": "zenmux", "label": "OpenAI GPT Image 1.5"},
    {"id": "google/gemini-3-pro-image-preview", "provider": "zenmux", "label": "Gemini 3 Pro Image"},
]
