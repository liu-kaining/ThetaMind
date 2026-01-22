"""Stock Ranking Agent - Ranks stocks based on analysis results."""

import logging
from typing import Any, Dict, List

from app.services.agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from app.services.ai.base import BaseAIProvider

logger = logging.getLogger(__name__)


class StockRankingAgent(BaseAgent):
    """Stock Ranking Agent - Ranks stocks based on analysis results.
    
    This agent takes analysis results from multiple agents (fundamental, technical)
    and ranks the stocks to provide recommendations.
    """
    
    def __init__(self, name: str, ai_provider: BaseAIProvider, dependencies: Dict[str, Any]):
        """Initialize Stock Ranking Agent.
        
        Args:
            name: Agent name
            ai_provider: AI provider instance
            dependencies: Dictionary of dependencies
        """
        super().__init__(
            name=name,
            agent_type=AgentType.RECOMMENDATION,
            ai_provider=ai_provider,
            dependencies=dependencies,
        )
    
    def _get_role_prompt(self) -> str:
        """Get role definition prompt."""
        return """You are a Stock Ranking Specialist.

Your role is to rank stocks based on comprehensive analysis results
from fundamental and technical analysts.

You will receive:
- Candidate stocks with their fundamental analysis
- Technical analysis for each candidate
- Various scores and metrics

Your task is to:
1. Synthesize all analysis results
2. Calculate composite scores
3. Rank stocks from best to worst
4. Provide clear recommendations with reasoning

Be objective, data-driven, and focus on actionable rankings."""
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute stock ranking.
        
        Args:
            context: Execution context containing analysis_results
            
        Returns:
            AgentResult with ranked stocks
        """
        try:
            analysis_results = context.input_data.get("analysis_results", [])
            
            if not analysis_results:
                return AgentResult(
                    agent_name=self.name,
                    agent_type=self.agent_type,
                    success=False,
                    data={},
                    error="analysis_results not provided in context",
                )
            
            # Build ranking prompt
            prompt = f"""
Rank the following stocks based on their analysis results:

{self._format_analysis_results(analysis_results)}

Provide:
1. Ranked list of stocks (best to worst)
2. Composite score for each stock (0-10)
3. Key reasons for ranking
4. Top 3 recommendations with detailed reasoning

Format as a ranked list with scores and reasoning.
"""
            
            # Call AI for ranking
            ranking_analysis = await self._call_ai(prompt, system_prompt=self._role_prompt, context=context)
            
            # Calculate composite scores
            ranked_stocks = self._calculate_composite_scores(analysis_results)
            
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                success=True,
                data={
                    "analysis": ranking_analysis,
                    "ranked_stocks": ranked_stocks,
                    "top_recommendations": ranked_stocks[:3] if len(ranked_stocks) >= 3 else ranked_stocks,
                    "total_ranked": len(ranked_stocks),
                },
            )
            
        except Exception as e:
            logger.error(f"StockRankingAgent execution failed: {e}", exc_info=True)
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                success=False,
                data={},
                error=str(e),
            )
    
    def _format_analysis_results(self, analysis_results: List[Dict[str, Any]]) -> str:
        """Format analysis results for prompt.
        
        Args:
            analysis_results: List of analysis result dictionaries
            
        Returns:
            Formatted string
        """
        lines = []
        
        for i, result in enumerate(analysis_results):
            candidate = result.get("candidate", {})
            analysis = result.get("analysis", {})
            
            symbol = candidate.get("symbol", f"Stock_{i}")
            
            lines.append(f"\n{symbol}:")
            
            # Fundamental analysis
            fundamental = analysis.get("fundamental_analyst", {})
            if isinstance(fundamental, dict):
                health_score = fundamental.get("health_score")
                if health_score is not None:
                    lines.append(f"  - Health Score: {health_score}")
            
            # Technical analysis
            technical = analysis.get("technical_analyst", {})
            if isinstance(technical, dict):
                technical_score = technical.get("technical_score")
                if technical_score is not None:
                    lines.append(f"  - Technical Score: {technical_score}")
        
        return "\n".join(lines) if lines else "No analysis results available"
    
    def _calculate_composite_scores(self, analysis_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate composite scores and rank stocks.
        
        Args:
            analysis_results: List of analysis result dictionaries
            
        Returns:
            List of ranked stocks with composite scores
        """
        scored_stocks = []
        
        for result in analysis_results:
            candidate = result.get("candidate", {})
            analysis = result.get("analysis", {})
            
            symbol = candidate.get("symbol", "UNKNOWN")
            
            # Calculate composite score
            scores = []
            
            # Fundamental score
            fundamental = analysis.get("fundamental_analyst") or {}
            if isinstance(fundamental, dict):
                health_score = fundamental.get("health_score")
                if health_score is not None and isinstance(health_score, (int, float)):
                    scores.append(float(health_score) / 10.0)  # Convert to 0-1 scale
            
            # Technical score
            technical = analysis.get("technical_analyst") or {}
            if isinstance(technical, dict):
                technical_score = technical.get("technical_score")
                if technical_score is not None and isinstance(technical_score, (int, float)):
                    scores.append(float(technical_score) / 10.0)  # Convert to 0-1 scale
            
            # Calculate average (or weighted average)
            if scores:
                composite_score = sum(scores) / len(scores) * 10.0  # Convert back to 0-10
            else:
                composite_score = 5.0  # Default neutral
            
            scored_stocks.append({
                "symbol": symbol,
                "composite_score": round(composite_score, 1),
                "fundamental_score": fundamental.get("health_score") if isinstance(fundamental, dict) and fundamental else None,
                "technical_score": technical.get("technical_score") if isinstance(technical, dict) and technical else None,
                "rank": 0,  # Will be set after sorting
            })
        
        # Sort by composite score (descending)
        scored_stocks.sort(key=lambda x: x["composite_score"], reverse=True)
        
        # Assign ranks
        for i, stock in enumerate(scored_stocks):
            stock["rank"] = i + 1
        
        return scored_stocks
