"""AI service adapter with provider switching."""

import logging
from typing import Any

from app.core.config import settings
from app.services.ai.base import BaseAIProvider
from app.services.ai.gemini_provider import gemini_provider

logger = logging.getLogger(__name__)


class AIService:
    """AI service with fallback provider support."""

    def __init__(self) -> None:
        """Initialize AI service with default provider."""
        self._default_provider: BaseAIProvider = gemini_provider
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

