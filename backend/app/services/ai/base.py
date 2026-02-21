"""Base AI provider abstract class for strategy pattern."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional


class BaseAIProvider(ABC):
    """Abstract base class for AI providers (Gemini, DeepSeek, Qwen)."""

    async def generate_report(
        self, 
        strategy_summary: dict[str, Any] | None = None,
        strategy_data: dict[str, Any] | None = None,
        option_chain: dict[str, Any] | None = None,
        model_override: Optional[str] = None,
    ) -> str:
        """
        Generate AI analysis report for a strategy.

        Args:
            strategy_summary: Complete strategy summary (preferred format) containing:
                - legs: List of strategy legs with all Greeks and pricing
                - portfolio_greeks: Combined portfolio-level Greeks
                - trade_execution: Trade execution details
                - strategy_metrics: Max profit, max loss, breakeven points
                - payoff_summary: Key payoff diagram points
            strategy_data: Legacy format - Strategy configuration (legs, strikes, etc.)
            option_chain: Legacy format - Filtered option chain data

        Returns:
            Markdown-formatted analysis report
        
        Note:
            Providers should override this method. strategy_summary is preferred.
            If only strategy_data + option_chain provided, convert to strategy_summary format.
        """
        # Default implementation raises - must be overridden
        raise NotImplementedError("Subclasses must implement generate_report")

    async def generate_deep_research_report(
        self,
        strategy_summary: dict[str, Any] | None = None,
        strategy_data: dict[str, Any] | None = None,
        option_chain: dict[str, Any] | None = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        agent_summaries: Optional[dict[str, Any]] = None,
        recommended_strategies: Optional[list[dict[str, Any]]] = None,
        internal_preliminary_report: Optional[str] = None,
        model_override: Optional[str] = None,
    ) -> str:
        """
        Generate deep research report using multi-step agentic workflow (Plan -> Research -> Synthesize).
        
        This method implements a 3-phase workflow:
        1. Planning: Generate critical research questions
        2. Research: Execute Google Search for each question
        3. Synthesis: Combine all research into final report
        
        Args:
            strategy_summary: Complete strategy summary (preferred format)
            strategy_data: Legacy format - Strategy configuration (legs, strikes, etc.)
            option_chain: Legacy format - Filtered option chain data
            progress_callback: Optional callback function(progress_percent, message) for progress updates
            
        Returns:
            Markdown-formatted deep research report
            
        Note:
            Default implementation falls back to generate_report.
            Providers should override this for deep research capability.
        """
        # Default implementation: fallback to regular report
        return await self.generate_report(
            strategy_summary=strategy_summary,
            strategy_data=strategy_data,
            option_chain=option_chain,
            model_override=model_override,
        )

    @abstractmethod
    async def generate_text_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_override: Optional[str] = None,
    ) -> str:
        """
        Generate plain text response for AI agents.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system instruction
            model_override: Optional model ID
            
        Returns:
            Generated text response
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

