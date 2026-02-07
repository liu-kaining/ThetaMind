"""Options Synthesis Agent - Synthesizes all analysis into final comprehensive report."""

import json
import logging
from typing import Any, Dict

from app.services.agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from app.services.ai.base import BaseAIProvider

logger = logging.getLogger(__name__)


class OptionsSynthesisAgent(BaseAgent):
    """Options Synthesis Agent - Synthesizes all agent analyses into final report.
    
    This agent takes all previous analysis results and creates a comprehensive,
    well-structured final report that combines all insights.
    """
    
    def __init__(self, name: str, ai_provider: BaseAIProvider, dependencies: Dict[str, Any]):
        """Initialize Options Synthesis Agent.
        
        Args:
            name: Agent name
            ai_provider: AI provider instance
            dependencies: Dictionary of dependencies
        """
        super().__init__(
            name=name,
            agent_type=AgentType.OPTIONS_ANALYSIS,
            ai_provider=ai_provider,
            dependencies=dependencies,
        )
    
    def _get_role_prompt(self) -> str:
        """Get role definition prompt."""
        return """You are a Senior Options Strategist and Report Writer.

Your role is to synthesize multiple specialized analyses into a comprehensive,
well-structured investment memo. Always respond in English only; do not use Chinese or any other language.

You will receive:
- Greeks analysis from Options Greeks Analyst
- IV environment analysis from IV Environment Analyst
- Market context analysis from Market Context Analyst
- Risk scenario analysis from Risk Scenario Analyst

Your task is to:
1. Synthesize all analyses into a coherent narrative
2. Identify key insights and patterns across analyses
3. Resolve any contradictions between analyses
4. Create a clear, actionable final recommendation
5. Structure the report professionally (Executive Summary, Analysis, Recommendations)

Be comprehensive, balanced, and focus on actionable insights. Output in English only."""
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute synthesis of all analyses.
        
        Args:
            context: Execution context containing _all_results with all previous analyses
            
        Returns:
            AgentResult with synthesized report
        """
        try:
            all_results = context.input_data.get("_all_results", {})
            strategy_summary = context.input_data.get("strategy_summary", {})
            
            if not all_results:
                return AgentResult(
                    agent_name=self.name,
                    agent_type=self.agent_type,
                    success=False,
                    data={},
                    error="No previous analysis results available for synthesis",
                )
            
            symbol = strategy_summary.get("symbol", "UNKNOWN")
            strategy_name = strategy_summary.get("strategy_name", "Unknown Strategy")
            
            # Extract key insights from each analysis
            # Handle None values from coordinator (when agent fails)
            greeks_analysis = all_results.get("options_greeks_analyst") or {}
            iv_analysis = all_results.get("iv_environment_analyst") or {}
            market_analysis = all_results.get("market_context_analyst") or {}
            risk_analysis = all_results.get("risk_scenario_analyst") or {}
            
            # Ensure all are dictionaries
            if not isinstance(greeks_analysis, dict):
                greeks_analysis = {}
            if not isinstance(iv_analysis, dict):
                iv_analysis = {}
            if not isinstance(market_analysis, dict):
                market_analysis = {}
            if not isinstance(risk_analysis, dict):
                risk_analysis = {}
            
            # Build synthesis prompt
            prompt = f"""
Synthesize all analyses into a comprehensive investment memo for this options strategy:

Strategy: {strategy_name}
Symbol: {symbol}

GREEKS ANALYSIS:
{self._extract_analysis_text(greeks_analysis)}
Risk Score: {greeks_analysis.get('risk_score', 'N/A')}
Risk Category: {greeks_analysis.get('risk_category', 'N/A')}

IV ENVIRONMENT ANALYSIS:
{self._extract_analysis_text(iv_analysis)}
IV Score: {iv_analysis.get('iv_score', 'N/A')}
IV Category: {iv_analysis.get('iv_category', 'N/A')}

MARKET CONTEXT ANALYSIS:
{self._extract_analysis_text(market_analysis)}
Market Score: {market_analysis.get('market_score', 'N/A')}
Market Category: {market_analysis.get('market_category', 'N/A')}

RISK SCENARIO ANALYSIS:
{self._extract_analysis_text(risk_analysis)}
Risk Score: {risk_analysis.get('risk_score', 'N/A')}
Risk Category: {risk_analysis.get('risk_category', 'N/A')}

STRATEGY SUMMARY:
{self._format_strategy_summary(strategy_summary)}

FUNDAMENTAL & CATALYST DATA (FMP):
{self._format_enriched_data(strategy_summary)}

Create a COMPREHENSIVE, IN-DEPTH investment memo. Each section must be substantive (not brief). Minimum ~200 words for Multi-Agent Synthesis and Key Insights each.

## Executive Summary
[4-6 sentences: strategy overview, key risks, main thesis, recommendation. Be substantive.]

## Multi-Agent Analysis Synthesis
[Combine insights from ALL four analyses (Greeks, IV, Market, Risk). Identify patterns, contradictions, and synergies. Attribute key points to each specialist where relevant. MINIMUM 200 words.]

## Key Insights
[Top 5-7 key insights with specific reasoning. Each insight: 2-4 sentences. Draw from Greeks, IV, Market Context, and Risk Scenario.]

## Overall Assessment
[Risk/reward assessment, score 0-10, rationale. 3-5 sentences.]

## Final Recommendation
[Clear recommendation: Strong Buy/Buy/Hold/Sell/Strong Sell. Confidence level and reasoning. 3-5 sentences.]

## Action Items
[3-5 specific action items: entry strategy, exit strategy, risk management, monitoring.]

Format in professional Markdown. Be thorough; this will be the foundation for external research augmentation.
"""
            
            # Call AI for synthesis
            synthesis = await self._call_ai(prompt, system_prompt=self._role_prompt, context=context)
            
            # Calculate overall score
            overall_score = self._calculate_overall_score(all_results)
            
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                success=True,
                data={
                    "analysis": synthesis,
                    "overall_score": overall_score,
                    "recommendation": self._extract_recommendation(synthesis),
                    "symbol": symbol,
                    "strategy_name": strategy_name,
                    "synthesis_metadata": {
                        "greeks_score": greeks_analysis.get("risk_score") if isinstance(greeks_analysis, dict) else None,
                        "iv_score": iv_analysis.get("iv_score") if isinstance(iv_analysis, dict) else None,
                        "market_score": market_analysis.get("market_score") if isinstance(market_analysis, dict) else None,
                        "risk_score": risk_analysis.get("risk_score") if isinstance(risk_analysis, dict) else None,
                    },
                },
            )
            
        except Exception as e:
            logger.error(f"OptionsSynthesisAgent execution failed: {e}", exc_info=True)
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                success=False,
                data={},
                error=str(e),
            )
    
    def _extract_analysis_text(self, analysis_data: Dict[str, Any]) -> str:
        """Extract analysis text from agent result data.
        
        Args:
            analysis_data: Agent result data dictionary (from AgentResult.data)
            
        Returns:
            Analysis text or placeholder
        """
        if isinstance(analysis_data, dict):
            # The data comes from AgentResult.data, which contains the "analysis" field
            analysis = analysis_data.get("analysis", "")
            if analysis and isinstance(analysis, str):
                # Limit length to avoid token overflow
                if len(analysis) > 1000:
                    return analysis[:1000] + "... (truncated)"
                return analysis
        return "Analysis not available"
    
    def _format_strategy_summary(self, strategy_summary: Dict[str, Any]) -> str:
        """Format strategy summary for prompt."""
        lines = []
        
        symbol = strategy_summary.get("symbol", "N/A")
        strategy_name = strategy_summary.get("strategy_name", "N/A")
        expiration = strategy_summary.get("expiration_date", "N/A")
        
        lines.append(f"Symbol: {symbol}")
        lines.append(f"Strategy: {strategy_name}")
        lines.append(f"Expiration: {expiration}")
        
        metrics = strategy_summary.get("strategy_metrics", {})
        if metrics:
            lines.append(f"Max Profit: ${metrics.get('max_profit', 0):.2f}")
            lines.append(f"Max Loss: ${metrics.get('max_loss', 0):.2f}")
            lines.append(f"POP: {metrics.get('pop', 0):.1f}%")
        
        return "\n".join(lines)

    def _format_enriched_data(self, strategy_summary: Dict[str, Any]) -> str:
        """Format enriched FMP data (fundamental_profile, analyst_data, catalysts, sentiment) for prompt."""
        parts = []
        fp = strategy_summary.get("fundamental_profile")
        if fp and isinstance(fp, dict):
            parts.append(f"Fundamental Profile: {json.dumps(fp, indent=2, default=str)[:2500]}")
        ad = strategy_summary.get("analyst_data")
        if ad and isinstance(ad, dict):
            parts.append(f"Analyst Data: {json.dumps(ad, indent=2, default=str)[:1500]}")
        events = strategy_summary.get("upcoming_events") or strategy_summary.get("catalyst") or []
        if events and isinstance(events, list):
            parts.append(f"Upcoming Events: {json.dumps(events[:5], indent=2, default=str)}")
        iv_ctx = strategy_summary.get("iv_context")
        if iv_ctx and isinstance(iv_ctx, dict):
            parts.append(f"IV Context: {json.dumps(iv_ctx, indent=2, default=str)}")
        sent = strategy_summary.get("sentiment") or {}
        if sent and isinstance(sent, dict):
            parts.append(f"Sentiment: {json.dumps(sent, indent=2, default=str)[:800]}")
        return "\n\n".join(parts) if parts else "No enriched fundamental data available"
    
    def _calculate_overall_score(self, all_results: Dict[str, Any]) -> float:
        """Calculate overall strategy score (0-10).
        
        Args:
            all_results: Dictionary of all analysis results
            
        Returns:
            Overall score (0-10, higher = better)
        """
        scores = []
        
        # Collect scores from different analyses
        # Handle None values from coordinator (when agent fails)
        greeks_data = all_results.get("options_greeks_analyst") or {}
        if isinstance(greeks_data, dict):
            risk_score = greeks_data.get("risk_score")
            if risk_score is not None and isinstance(risk_score, (int, float)):
                # Invert risk score (lower risk = higher score)
                scores.append(10.0 - float(risk_score))
        
        iv_data = all_results.get("iv_environment_analyst") or {}
        if isinstance(iv_data, dict):
            iv_score = iv_data.get("iv_score")
            if iv_score is not None and isinstance(iv_score, (int, float)):
                # IV score is already 0-10, use as-is (higher IV = better for selling)
                scores.append(float(iv_score))
        
        market_data = all_results.get("market_context_analyst") or {}
        if isinstance(market_data, dict):
            market_score = market_data.get("market_score")
            if market_score is not None and isinstance(market_score, (int, float)):
                scores.append(float(market_score))
        
        risk_data = all_results.get("risk_scenario_analyst") or {}
        if isinstance(risk_data, dict):
            risk_score = risk_data.get("risk_score")
            if risk_score is not None and isinstance(risk_score, (int, float)):
                # Invert risk score
                scores.append(10.0 - float(risk_score))
        
        # Calculate average
        if scores:
            overall = sum(scores) / len(scores)
        else:
            overall = 5.0  # Default neutral
        
        return round(overall, 1)
    
    def _extract_recommendation(self, synthesis_text: str) -> str:
        """Extract recommendation from synthesis text.
        
        Args:
            synthesis_text: Synthesis report text
            
        Returns:
            Recommendation string
        """
        # Try to extract recommendation from text
        text_lower = synthesis_text.lower()
        
        if "strong buy" in text_lower or "strongly recommend" in text_lower:
            return "Strong Buy"
        elif "buy" in text_lower and "strong" not in text_lower:
            return "Buy"
        elif "hold" in text_lower:
            return "Hold"
        elif "sell" in text_lower and "strong" not in text_lower:
            return "Sell"
        elif "strong sell" in text_lower:
            return "Strong Sell"
        else:
            return "Neutral"
