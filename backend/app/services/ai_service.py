"""AI service adapter with provider switching and multi-agent support."""

import logging
from typing import Any, Callable, Optional

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
        
        # Initialize Agent Framework (lazy loading)
        self._agent_coordinator: Optional[Any] = None
        self._agent_framework_initialized = False

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
        self,
        strategy_summary: dict[str, Any] | None = None,
        strategy_data: dict[str, Any] | None = None,
        option_chain: dict[str, Any] | None = None,
    ) -> str:
        """
        Generate strategy analysis report.

        Args:
            strategy_summary: Complete strategy summary (preferred format)
            strategy_data: Legacy format - Strategy configuration
            option_chain: Legacy format - Option chain data

        Returns:
            Markdown report
        """
        try:
            provider = self._get_provider()
            return await provider.generate_report(
                strategy_summary=strategy_summary,
                strategy_data=strategy_data,
                option_chain=option_chain,
            )
        except Exception as e:
            logger.error(f"Default provider failed: {e}", exc_info=True)
            # Try fallback if available
            if self._fallback_provider:
                logger.info("Trying fallback provider")
                return await self._fallback_provider.generate_report(
                    strategy_summary=strategy_summary,
                    strategy_data=strategy_data,
                    option_chain=option_chain,
                )
            raise

    async def generate_deep_research_report(
        self,
        strategy_summary: dict[str, Any] | None = None,
        strategy_data: dict[str, Any] | None = None,
        option_chain: dict[str, Any] | None = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> str:
        """
        Generate deep research report using multi-step agentic workflow.
        
        Args:
            strategy_summary: Complete strategy summary (preferred format)
            strategy_data: Legacy format - Strategy configuration
            option_chain: Legacy format - Option chain data
            progress_callback: Optional callback(progress_percent, message) for progress updates
            
        Returns:
            Markdown deep research report
        """
        try:
            provider = self._get_provider()
            # Check if provider supports deep research
            if hasattr(provider, 'generate_deep_research_report'):
                return await provider.generate_deep_research_report(
                    strategy_summary=strategy_summary,
                    strategy_data=strategy_data,
                    option_chain=option_chain,
                    progress_callback=progress_callback,
                )
            else:
                # Fallback to regular report
                logger.warning("Provider does not support deep research, using regular report")
                return await provider.generate_report(
                    strategy_summary=strategy_summary,
                    strategy_data=strategy_data,
                    option_chain=option_chain,
                )
        except Exception as e:
            logger.error(f"Deep research generation failed: {e}", exc_info=True)
            # Try fallback if available
            if self._fallback_provider:
                logger.info("Trying fallback provider for deep research")
                if hasattr(self._fallback_provider, 'generate_deep_research_report'):
                    return await self._fallback_provider.generate_deep_research_report(
                        strategy_summary=strategy_summary,
                        strategy_data=strategy_data,
                        option_chain=option_chain,
                        progress_callback=progress_callback,
                    )
                return await self._fallback_provider.generate_report(
                    strategy_summary=strategy_summary,
                    strategy_data=strategy_data,
                    option_chain=option_chain,
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
    
    def _init_agent_framework(self) -> None:
        """Initialize Agent Framework (lazy initialization).
        
        This method sets up the multi-agent system with all dependencies.
        It's called lazily on first use to avoid circular imports.
        """
        if self._agent_framework_initialized:
            return
        
        try:
            from app.services.agents.coordinator import AgentCoordinator
            from app.services.agents.executor import AgentExecutor
            from app.services.agents.registry import AgentRegistry
            from app.services.agents.options_greeks_analyst import OptionsGreeksAnalyst
            from app.services.agents.fundamental_analyst import FundamentalAnalyst
            from app.services.agents.iv_environment_analyst import IVEnvironmentAnalyst
            from app.services.agents.market_context_analyst import MarketContextAnalyst
            from app.services.agents.risk_scenario_analyst import RiskScenarioAnalyst
            from app.services.agents.options_synthesis_agent import OptionsSynthesisAgent
            from app.services.agents.technical_analyst import TechnicalAnalyst
            from app.services.agents.stock_screening_agent import StockScreeningAgent
            from app.services.agents.stock_ranking_agent import StockRankingAgent
            from app.services.agents.base import AgentType
            from app.services.market_data_service import MarketDataService
            from app.services.tiger_service import tiger_service
            
            # Prepare dependencies
            dependencies = {
                "market_data_service": MarketDataService(),
                "tiger_service": tiger_service,
            }
            
            # Create executor
            executor = AgentExecutor(
                ai_provider=self._default_provider,
                dependencies=dependencies,
            )
            
            # Create coordinator
            self._agent_coordinator = AgentCoordinator(executor)
            
            # Register agents
            # Options Analysis Agents
            AgentRegistry.register(
                "options_greeks_analyst",
                OptionsGreeksAnalyst,
                AgentType.OPTIONS_ANALYSIS,
            )
            AgentRegistry.register(
                "iv_environment_analyst",
                IVEnvironmentAnalyst,
                AgentType.OPTIONS_ANALYSIS,
            )
            AgentRegistry.register(
                "market_context_analyst",
                MarketContextAnalyst,
                AgentType.OPTIONS_ANALYSIS,
            )
            AgentRegistry.register(
                "risk_scenario_analyst",
                RiskScenarioAnalyst,
                AgentType.OPTIONS_ANALYSIS,
            )
            AgentRegistry.register(
                "options_synthesis_agent",
                OptionsSynthesisAgent,
                AgentType.OPTIONS_ANALYSIS,
            )
            
            # Fundamental & Technical Analysis Agents
            AgentRegistry.register(
                "fundamental_analyst",
                FundamentalAnalyst,
                AgentType.FUNDAMENTAL_ANALYSIS,
            )
            AgentRegistry.register(
                "technical_analyst",
                TechnicalAnalyst,
                AgentType.TECHNICAL_ANALYSIS,
            )
            
            # Stock Screening & Ranking Agents
            AgentRegistry.register(
                "stock_screening_agent",
                StockScreeningAgent,
                AgentType.STOCK_SCREENING,
            )
            AgentRegistry.register(
                "stock_ranking_agent",
                StockRankingAgent,
                AgentType.RECOMMENDATION,
            )
            
            self._agent_framework_initialized = True
            logger.info("Agent Framework initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Agent Framework: {e}", exc_info=True)
            self._agent_framework_initialized = False
    
    @property
    def agent_coordinator(self) -> Any:
        """Get agent coordinator (lazy initialization)."""
        if not self._agent_framework_initialized:
            self._init_agent_framework()
        return self._agent_coordinator
    
    async def generate_report_with_agents(
        self,
        strategy_summary: dict[str, Any],
        use_multi_agent: bool = True,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> str:
        """Generate report using multi-agent system.
        
        Args:
            strategy_summary: Strategy summary dictionary
            use_multi_agent: Whether to use multi-agent system
            progress_callback: Optional progress callback
            
        Returns:
            Markdown-formatted report
        """
        if use_multi_agent and self.agent_coordinator:
            try:
                result = await self.agent_coordinator.coordinate_options_analysis(
                    strategy_summary,
                    progress_callback,
                )
                return self._format_agent_report(result)
            except Exception as e:
                logger.error(f"Multi-agent report generation failed: {e}", exc_info=True)
                # Fallback to regular report
                logger.info("Falling back to regular report generation")
                return await self.generate_report(strategy_summary=strategy_summary)
        else:
            # Fallback to regular report
            return await self.generate_report(strategy_summary=strategy_summary)
    
    def _format_agent_report(self, agent_results: dict[str, Any]) -> str:
        """Format agent results into a markdown report.
        
        Args:
            agent_results: Dictionary of agent results from coordinator
            
        Returns:
            Formatted markdown report
        """
        synthesis = agent_results.get("synthesis", {})
        if isinstance(synthesis, dict):
            analysis = synthesis.get("analysis", "")
            if analysis:
                return analysis
        
        # Fallback: combine all analyses
        report_sections = []
        
        parallel_analysis = agent_results.get("parallel_analysis", {})
        for agent_name, data in parallel_analysis.items():
            if data and isinstance(data, dict):
                analysis = data.get("analysis", "")
                if analysis:
                    report_sections.append(f"## {agent_name.replace('_', ' ').title()}\n\n{analysis}\n")
        
        risk_analysis = agent_results.get("risk_analysis", {})
        if risk_analysis and isinstance(risk_analysis, dict):
            analysis = risk_analysis.get("analysis", "")
            if analysis:
                report_sections.append(f"## Risk Analysis\n\n{analysis}\n")
        
        if report_sections:
            return "\n".join(report_sections)
        else:
            return "# Analysis Report\n\nNo analysis data available."


# Global AI service instance
ai_service = AIService()

