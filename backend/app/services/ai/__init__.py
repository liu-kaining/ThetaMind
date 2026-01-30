"""AI service providers with strategy pattern. Gemini only (ZenMux disabled)."""

from app.services.ai.base import BaseAIProvider
from app.services.ai.gemini_provider import GeminiProvider
# ZenMux disabled - all AI uses Gemini only
# from app.services.ai.zenmux_provider import ZenMuxProvider
from app.services.ai.registry import (
    ProviderRegistry,
    PROVIDER_GEMINI,
    PROVIDER_QWEN,
    PROVIDER_DEEPSEEK,
)

__all__ = [
    "BaseAIProvider",
    "GeminiProvider",
    "ProviderRegistry",
    "PROVIDER_GEMINI",
    "PROVIDER_QWEN",
    "PROVIDER_DEEPSEEK",
]

