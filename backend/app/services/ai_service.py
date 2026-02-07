"""AI service adapter - Gemini as first and only choice."""

import logging
from typing import Any, Callable, Optional

from app.core.config import settings
from app.services.ai.base import BaseAIProvider
from app.services.ai.gemini_provider import GeminiProvider
# ZenMux disabled - all AI uses Gemini only
# from app.services.ai.zenmux_provider import ZenMuxProvider
from app.services.ai.registry import ProviderRegistry, PROVIDER_GEMINI

logger = logging.getLogger(__name__)


class AIService:
    """AI service - Gemini only (ZenMux disabled)."""

    def __init__(self) -> None:
        """Initialize AI service with Gemini as the only provider."""
        # Register Gemini only (ZenMux disabled)
        ProviderRegistry.register(PROVIDER_GEMINI, GeminiProvider)
        # ProviderRegistry.register(PROVIDER_ZENMUX, ZenMuxProvider)  # ZenMux disabled

        # Always use Gemini - ignore AI_PROVIDER for now
        provider_name = PROVIDER_GEMINI
        try:
            self._default_provider = ProviderRegistry.get_provider(provider_name)
            if self._default_provider is None:
                raise RuntimeError(
                    f"Gemini provider failed to initialize. "
                    f"Available: {ProviderRegistry.list_providers()}"
                )
            logger.info(f"Using AI provider: {provider_name} (Gemini only)")
        except Exception as e:
            logger.error(f"Error initializing AI provider: {e}", exc_info=True)
            raise

        # No fallback provider (ZenMux disabled)
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

    async def generate_strategy_recommendations(
        self,
        option_chain: dict[str, Any],
        strategy_summary: dict[str, Any],
        fundamental_profile: dict[str, Any],
        agent_summaries: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Phase A+: Generate 1-2 recommended option strategies (design §3.1, §3.5).
        """
        provider = self._get_provider()
        if hasattr(provider, "generate_strategy_recommendations"):
            return await provider.generate_strategy_recommendations(
                option_chain=option_chain,
                strategy_summary=strategy_summary,
                fundamental_profile=fundamental_profile,
                agent_summaries=agent_summaries,
            )
        return []

    async def generate_deep_research_report(
        self,
        strategy_summary: dict[str, Any] | None = None,
        strategy_data: dict[str, Any] | None = None,
        option_chain: dict[str, Any] | None = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        agent_summaries: Optional[dict[str, Any]] = None,
        recommended_strategies: Optional[list[dict[str, Any]]] = None,
        internal_preliminary_report: Optional[str] = None,
    ) -> str:
        """
        Generate deep research report using multi-step agentic workflow.
        
        Args:
            internal_preliminary_report: Phase A multi-agent synthesis (foundation for Final Synthesis)
            
        Returns:
            Markdown deep research report (three-part when agent_summaries + recommended_strategies provided)
        """
        try:
            provider = self._get_provider()
            if hasattr(provider, 'generate_deep_research_report'):
                return await provider.generate_deep_research_report(
                    strategy_summary=strategy_summary,
                    strategy_data=strategy_data,
                    option_chain=option_chain,
                    progress_callback=progress_callback,
                    agent_summaries=agent_summaries,
                    recommended_strategies=recommended_strategies,
                    internal_preliminary_report=internal_preliminary_report,
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
                        agent_summaries=agent_summaries,
                        recommended_strategies=recommended_strategies,
                        internal_preliminary_report=internal_preliminary_report,
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
    
    def _build_agent_summaries(self, agent_results: dict[str, Any]) -> dict[str, Any]:
        """Build agent_summaries for Deep Research. Preserves full analysis (up to 1800 chars/agent).
        Design: Deep reports need depth; over-compression was producing shallow output.
        """
        _MAX_PER_AGENT = 1800  # Keep substantial content for Final Synthesis

        def _extract_full(analysis: str) -> str:
            if not analysis or not isinstance(analysis, str):
                return "No analysis available."
            text = analysis.strip()
            return text if len(text) <= _MAX_PER_AGENT else text[:_MAX_PER_AGENT - 3] + "..."

        all_results = agent_results.get("all_results") or {}
        summaries: dict[str, Any] = {}
        agent_map = [
            ("options_greeks_analyst", "options_greeks", "Greeks Analyst"),
            ("iv_environment_analyst", "iv_environment", "IV Environment Analyst"),
            ("market_context_analyst", "market_context", "Market Context Analyst"),
            ("risk_scenario_analyst", "risk_scenario", "Risk Scenario Analyst"),
        ]
        for agent_name, key, _ in agent_map:
            data = all_results.get(agent_name)
            analysis = data.get("analysis", "") if isinstance(data, dict) else ""
            summaries[key] = _extract_full(analysis)
        synthesis_data = all_results.get("options_synthesis_agent")
        internal = ""
        if isinstance(synthesis_data, dict):
            internal = synthesis_data.get("analysis") or synthesis_data.get("recommendation") or ""
        summaries["internal_synthesis_full"] = internal or "Internal synthesis completed."
        return summaries

    async def generate_report_with_agents(
        self,
        strategy_summary: dict[str, Any],
        option_chain: dict[str, Any] | None = None,
        use_multi_agent: bool = True,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> str | dict[str, Any]:
        """Generate report using multi-agent system.
        
        Args:
            strategy_summary: Strategy summary dictionary
            option_chain: Full option chain data (optional)
            use_multi_agent: Whether to use multi-agent system
            progress_callback: Optional progress callback
            
        Returns:
            When use_multi_agent=True: dict with "report_text" (Markdown) and "agent_summaries" (for Deep Research).
            When use_multi_agent=False: str (Markdown report only).
        """
        if use_multi_agent and self.agent_coordinator:
            try:
                logger.info("Starting multi-agent report generation")
                result = await self.agent_coordinator.coordinate_options_analysis(
                    strategy_summary,
                    option_chain=option_chain,
                    progress_callback=progress_callback,
                )
                
                # Log execution summary
                metadata = result.get("metadata", {})
                total_agents = metadata.get("total_agents", 0)
                successful_agents = metadata.get("successful_agents", 0)
                logger.info(
                    f"Multi-agent execution completed: {successful_agents}/{total_agents} agents succeeded"
                )
                
                report_text = self._format_agent_report(result)
                agent_summaries = self._build_agent_summaries(result)
                return {
                    "report_text": report_text,
                    "agent_summaries": agent_summaries,
                    "internal_preliminary_report": report_text,
                }
            except Exception as e:
                logger.error(
                    f"Multi-agent report generation failed: {e}",
                    exc_info=True,
                    extra={
                        "strategy_symbol": strategy_summary.get("symbol", "unknown"),
                        "strategy_name": strategy_summary.get("strategy_name", "unknown"),
                    }
                )
                # No fallback to single-agent; re-raise so task fails clearly
                raise
        else:
            # Fallback to regular report
            logger.debug("Using single-agent report generation")
            report_text = await self.generate_report(
                strategy_summary=strategy_summary,
                option_chain=option_chain,
            )
            return report_text
    
    def _format_agent_report(self, agent_results: dict[str, Any]) -> str:
        """Format agent results into a markdown report.
        
        Args:
            agent_results: Dictionary of agent results from coordinator
            
        Returns:
            Formatted markdown report
        """
        # Try to get synthesis report first (most comprehensive)
        synthesis = agent_results.get("synthesis", {})
        if isinstance(synthesis, dict):
            analysis = synthesis.get("analysis", "")
            if analysis and isinstance(analysis, str):
                return analysis
        
        # Fallback: combine all analyses
        report_sections = []
        
        parallel_analysis = agent_results.get("parallel_analysis", {})
        if isinstance(parallel_analysis, dict):
            for agent_name, data in parallel_analysis.items():
                if data and isinstance(data, dict):
                    analysis = data.get("analysis", "")
                    if analysis and isinstance(analysis, str):
                        report_sections.append(f"## {agent_name.replace('_', ' ').title()}\n\n{analysis}\n")
        
        risk_analysis = agent_results.get("risk_analysis", {})
        if risk_analysis and isinstance(risk_analysis, dict):
            analysis = risk_analysis.get("analysis", "")
            if analysis and isinstance(analysis, str):
                report_sections.append(f"## Risk Analysis\n\n{analysis}\n")
        
        if report_sections:
            return "\n".join(report_sections)
        else:
            return "# Analysis Report\n\nNo analysis data available."


# Global AI service instance
ai_service = AIService()

