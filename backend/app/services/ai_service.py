"""AI service adapter with provider switching."""

import logging
from typing import Any

from app.core.config import settings
from app.services.ai.base import BaseAIProvider
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.zenmux_provider import ZenMuxProvider
from app.services.ai.registry import ProviderRegistry, PROVIDER_ZENMUX, PROVIDER_GEMINI

logger = logging.getLogger(__name__)


class AIService:
    """AI service with provider switching via registry."""

    def __init__(self) -> None:
        """Initialize AI service with provider from registry based on configuration."""
        # Register all available providers
        ProviderRegistry.register(PROVIDER_ZENMUX, ZenMuxProvider)
        ProviderRegistry.register(PROVIDER_GEMINI, GeminiProvider)
        # Future providers can be registered here:
        # ProviderRegistry.register(PROVIDER_QWEN, QwenProvider)
        # ProviderRegistry.register(PROVIDER_DEEPSEEK, DeepSeekProvider)
        
        # Get provider based on configuration
        provider_name = settings.ai_provider.lower()
        try:
            self._default_provider = ProviderRegistry.get_provider(provider_name)
            if self._default_provider is None:
                logger.error(
                    f"Failed to initialize provider '{provider_name}'. "
                    f"Available providers: {ProviderRegistry.list_providers()}"
                )
                # Try fallback to gemini if zenmux fails
                if provider_name != PROVIDER_GEMINI:
                    logger.info(f"Attempting fallback to {PROVIDER_GEMINI} provider...")
                    self._default_provider = ProviderRegistry.get_provider(PROVIDER_GEMINI)
                    if self._default_provider is None:
                        raise RuntimeError(
                            f"No available AI providers. Requested: {provider_name}, "
                            f"Fallback: {PROVIDER_GEMINI}, Available: {ProviderRegistry.list_providers()}"
                        )
                else:
                    raise RuntimeError(
                        f"Provider '{provider_name}' is not available. "
                        f"Available providers: {ProviderRegistry.list_providers()}"
                    )
            logger.info(f"Using AI provider: {provider_name}")
        except Exception as e:
            logger.error(f"Error initializing AI provider: {e}", exc_info=True)
            raise
        
        # Fallback provider (optional, currently None)
        self._fallback_provider: BaseAIProvider | None = None

    def _get_provider(self, use_fallback: bool = False) -> BaseAIProvider:
        """
        Get AI provider (default or fallback).

        Args:
            use_fallback: If True, use fallback provider

        Returns:
            AI provider instance
        """
        if use_fallback and self._fallback_provider:
            return self._fallback_provider
        return self._default_provider

    async def generate_report(
        self, strategy_data: dict[str, Any], option_chain: dict[str, Any]
    ) -> str:
        """
        Generate strategy analysis report.

        Args:
            strategy_data: Strategy configuration
            option_chain: Option chain data

        Returns:
            Markdown report
        """
        try:
            provider = self._get_provider()
            return await provider.generate_report(strategy_data, option_chain)
        except Exception as e:
            logger.error(f"Default provider failed: {e}", exc_info=True)
            # Try fallback if available
            if self._fallback_provider:
                logger.info("Trying fallback provider")
                return await self._fallback_provider.generate_report(
                    strategy_data, option_chain
                )
            raise

    async def generate_daily_picks(self) -> list[dict[str, Any]]:
        """
        Generate daily strategy picks.

        Returns:
            List of strategy cards

        Raises:
            Exception: If generation fails and no fallback is available
        """
        try:
            provider = self._get_provider()
            picks = await provider.generate_daily_picks()
            
            # Validate picks
            if not picks or len(picks) == 0:
                logger.warning("AI provider returned empty picks list")
                # Try fallback if available
                if self._fallback_provider:
                    logger.info("Trying fallback provider for daily picks")
                    picks = await self._fallback_provider.generate_daily_picks()
                    if not picks or len(picks) == 0:
                        raise ValueError("Both default and fallback providers returned empty picks")
                else:
                    raise ValueError("AI provider returned empty picks and no fallback available")
            
            return picks
        except Exception as e:
            logger.error(f"Failed to generate daily picks: {e}", exc_info=True)
            # Re-raise instead of returning empty list to allow proper error handling
            raise


# Global AI service instance
ai_service = AIService()

