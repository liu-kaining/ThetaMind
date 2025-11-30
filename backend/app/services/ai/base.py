"""Base AI provider abstract class for strategy pattern."""

from abc import ABC, abstractmethod
from typing import Any


class BaseAIProvider(ABC):
    """Abstract base class for AI providers (Gemini, DeepSeek, Qwen)."""

    @abstractmethod
    async def generate_report(
        self, strategy_data: dict[str, Any], option_chain: dict[str, Any]
    ) -> str:
        """
        Generate AI analysis report for a strategy.

        Args:
            strategy_data: Strategy configuration (legs, strikes, etc.)
            option_chain: Filtered option chain data

        Returns:
            Markdown-formatted analysis report
        """
        pass

    @abstractmethod
    async def generate_daily_picks(self) -> list[dict[str, Any]]:
        """
        Generate daily AI strategy picks.

        Returns:
            List of strategy recommendation cards
        """
        pass

    @abstractmethod
    def filter_option_chain(
        self, chain_data: dict[str, Any], spot_price: float
    ) -> dict[str, Any]:
        """
        Filter option chain to keep only relevant strikes (ATM ±15%).

        Args:
            chain_data: Full option chain data
            spot_price: Current spot price

        Returns:
            Filtered option chain (only strikes within ±15% of spot)
        """
        pass

