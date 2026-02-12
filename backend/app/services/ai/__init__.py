"""AI service providers with strategy pattern. Default: Gemini; ZenMux supported."""

from app.services.ai.base import BaseAIProvider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.zenmux_provider import ZenMuxProvider
from app.services.ai.registry import (
    ProviderRegistry,
    PROVIDER_GEMINI,
    PROVIDER_ZENMUX,
    PROVIDER_QWEN,
    PROVIDER_DEEPSEEK,
)

__all__ = [
    "BaseAIProvider",
    "GeminiProvider",
    "ZenMuxProvider",
    "ProviderRegistry",
    "PROVIDER_GEMINI",
    "PROVIDER_ZENMUX",
    "PROVIDER_QWEN",
    "PROVIDER_DEEPSEEK",
]

