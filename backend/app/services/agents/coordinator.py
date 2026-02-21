"""Agent Coordinator - Coordinates complex multi-agent workflows."""

import logging
from typing import Any, Callable, Dict, List, Optional

from app.services.agents.base import AgentContext, AgentResult, AgentType
from app.services.agents.executor import AgentExecutor

logger = logging.getLogger(__name__)


class AgentCoordinator:
    """Agent coordinator for managing complex multi-agent workflows.
    
    The coordinator orchestrates multiple agents to accomplish complex tasks.
    It defines workflows that combine parallel and sequential execution.
    
    Example:
        coordinator = AgentCoordinator(executor)
        
        # Coordinate options analysis workflow
        result = await coordinator.coordinate_options_analysis(
            strategy_summary,
            progress_callback
        )
    """
    
    def __init__(self, executor: AgentExecutor):
        """Initialize coordinator.
        
        Args:
            executor: Agent executor instance
        """
        self.executor = executor
        logger.debug("Initialized AgentCoordinator")
    
    async def coordinate_options_analysis(
        self,
        strategy_summary: Dict[str, Any],
        option_chain: Dict[str, Any] | None = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        ai_provider: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Coordinate options strategy analysis workflow.
        
        Workflow:
        1. Phase 1 (Parallel): Greeks analysis, IV analysis, Market context analysis
        2. Phase 2 (Sequential): Risk analysis (depends on Phase 1 results)
        3. Phase 3 (Sequential): Synthesis (combines all results)
        
        Args:
            strategy_summary: Strategy summary dictionary
            option_chain: Full option chain data (optional)
            progress_callback: Optional progress callback
            
        Returns:
            Dictionary with all analysis results
        """
        symbol = strategy_summary.get("symbol", "unknown")
        context = AgentContext(
            task_id=f"options_analysis_{symbol}",
            task_type=AgentType.OPTIONS_ANALYSIS,
            input_data={
                "strategy_summary": strategy_summary,
                "option_chain": option_chain or {},
            },
        )
        
        # Phase 1: Parallel analysis
        if progress_callback:
            progress_callback(10, "Phase 1: Parallel analysis (Greeks, IV, Market)...")
        
        parallel_agents = [
            "options_greeks_analyst",
            "iv_environment_analyst",
            "market_context_analyst",
        ]
        
        parallel_results = await self.executor.execute_parallel(
            agent_names=parallel_agents,
            context=context,
            progress_callback=progress_callback,
            ai_provider=ai_provider,
        )
        
        # Phase 2: Risk analysis (depends on Phase 1)
        if progress_callback:
            progress_callback(60, "Phase 2: Risk scenario analysis...")
        
        # Add parallel results to context for risk analysis
        for agent_name, result in parallel_results.items():
            if result.success:
                context.input_data[f"_result_{agent_name}"] = result.data
        
        risk_result = await self.executor.execute_single(
            "risk_scenario_analyst",
            context,
            progress_callback=progress_callback,
            ai_provider=ai_provider,
        )
        
        # Phase 3: Synthesis
        if progress_callback:
            progress_callback(80, "Phase 3: Synthesizing final report...")
        
        # Add all results to context for synthesis
        context.input_data["_all_results"] = {
            **{k: v.data for k, v in parallel_results.items() if v.success},
            "risk_scenario_analyst": risk_result.data if risk_result.success else None,
        }
        
        synthesis_result = await self.executor.execute_single(
            "options_synthesis_agent",
            context,
            progress_callback=progress_callback,
            ai_provider=ai_provider,
        )
        
        if progress_callback:
            progress_callback(100, "Options analysis complete")
        
        return {
            "parallel_analysis": {
                k: v.data if v.success else None
                for k, v in parallel_results.items()
            },
            "risk_analysis": risk_result.data if risk_result.success else None,
            "synthesis": synthesis_result.data if synthesis_result.success else None,
            "all_results": {
                **{k: v.data for k, v in parallel_results.items() if v.success},
                "risk_scenario_analyst": risk_result.data if risk_result.success else None,
                "options_synthesis_agent": synthesis_result.data if synthesis_result.success else None,
            },
            "metadata": {
                "total_agents": len(parallel_agents) + 2,  # parallel + risk + synthesis
                "successful_agents": sum(
                    1
                    for r in list(parallel_results.values()) + [risk_result, synthesis_result]
                    if r.success
                ),
            },
        }
    
    async def coordinate_stock_screening(
        self,
        criteria: Dict[str, Any],
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> List[Dict[str, Any]]:
        """Coordinate stock screening workflow.
        
        Workflow:
        1. Phase 1: Initial screening (using MarketDataService)
        2. Phase 2: Parallel analysis of candidates (fundamental + technical)
        3. Phase 3: Ranking and recommendation
        
        Args:
            criteria: Screening criteria dictionary
            progress_callback: Optional progress callback
            
        Returns:
            List of ranked stock recommendations
        """
        context = AgentContext(
            task_id=f"stock_screening_{criteria.get('sector', 'all')}",
            task_type=AgentType.STOCK_SCREENING,
            input_data={"criteria": criteria},
        )
        
        # Phase 1: Initial screening
        if progress_callback:
            progress_callback(20, "Phase 1: Initial stock screening...")
        
        screening_result = await self.executor.execute_single(
            "stock_screening_agent",
            context,
            progress_callback=progress_callback,
        )
        
        if not screening_result.success:
            logger.error(f"Stock screening failed: {screening_result.error}")
            return []
        
        candidates = screening_result.data.get("candidates", [])
        if not candidates:
            logger.info("No candidates found from screening")
            return []
        
        # Phase 2: Parallel analysis of candidates
        if progress_callback:
            progress_callback(40, f"Phase 2: Analyzing {len(candidates)} candidates...")
        
        analysis_results = []
        for i, candidate in enumerate(candidates):
            ticker = candidate.get("symbol")
            if not ticker:
                continue
            
            candidate_context = AgentContext(
                task_id=f"{context.task_id}_candidate_{i}",
                task_type=AgentType.FUNDAMENTAL_ANALYSIS,
                input_data={"ticker": ticker},
            )
            
            # Parallel execution of fundamental and technical analysis
            results = await self.executor.execute_parallel(
                agent_names=["fundamental_analyst", "technical_analyst"],
                context=candidate_context,
                progress_callback=progress_callback,
            )
            
            analysis_results.append({
                "candidate": candidate,
                "analysis": {
                    k: (v.data if v.success and v.data else {})
                    for k, v in results.items()
                },
            })
            
            if progress_callback:
                progress = 40 + int((i + 1) / len(candidates) * 40)
                progress_callback(
                    progress,
                    f"Analyzed {i+1}/{len(candidates)} candidates",
                )
        
        # Phase 3: Ranking
        if progress_callback:
            progress_callback(90, "Phase 3: Ranking candidates...")
        
        ranking_context = AgentContext(
            task_id=f"{context.task_id}_ranking",
            task_type=AgentType.RECOMMENDATION,
            input_data={"analysis_results": analysis_results},
        )
        
        ranking_result = await self.executor.execute_single(
            "stock_ranking_agent",
            ranking_context,
            progress_callback=progress_callback,
        )
        
        if progress_callback:
            progress_callback(100, "Stock screening complete")
        
        if ranking_result.success:
            return ranking_result.data.get("ranked_stocks", [])
        else:
            logger.error(f"Stock ranking failed: {ranking_result.error}")
            return []
