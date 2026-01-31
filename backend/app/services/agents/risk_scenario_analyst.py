"""Risk Scenario Analyst Agent - Analyzes risk scenarios and worst-case outcomes."""

import json
import logging
from typing import Any, Dict

from app.services.agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from app.services.ai.base import BaseAIProvider

logger = logging.getLogger(__name__)


class RiskScenarioAnalyst(BaseAgent):
    """Risk Scenario Analyst - Analyzes risk scenarios and worst-case outcomes.
    
    This agent specializes in:
    - Worst-case scenario analysis
    - Tail risk assessment
    - Stress testing under different market conditions
    - Risk mitigation strategies
    """
    
    def __init__(self, name: str, ai_provider: BaseAIProvider, dependencies: Dict[str, Any]):
        """Initialize Risk Scenario Analyst.
        
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
        return """You are a Senior Risk Management Specialist specializing in options strategy risk analysis.

Your expertise includes:
- Worst-case scenario identification
- Tail risk assessment
- Stress testing under extreme market conditions
- Risk mitigation strategies
- Position sizing and risk management

Your analysis should:
1. Identify worst-case scenarios (maximum loss conditions)
2. Assess tail risk (low-probability, high-impact events)
3. Stress test the strategy under different market conditions
4. Evaluate risk/reward ratios
5. Provide risk mitigation strategies
6. Recommend position sizing based on risk

Be thorough, critical, and focus on protecting capital."""
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute risk scenario analysis.
        
        Args:
            context: Execution context containing strategy_summary and previous analysis results
            
        Returns:
            AgentResult with risk scenario analysis
        """
        try:
            strategy_summary = context.input_data.get("strategy_summary", {})
            
            if not strategy_summary:
                return AgentResult(
                    agent_name=self.name,
                    agent_type=self.agent_type,
                    success=False,
                    data={},
                    error="strategy_summary not provided in context",
                )
            
            # Get previous analysis results if available
            previous_results = {}
            for key in context.input_data.keys():
                if key.startswith("_result_"):
                    agent_name = key.replace("_result_", "")
                    previous_results[agent_name] = context.input_data[key]
            
            # Extract strategy data
            portfolio_greeks = strategy_summary.get("portfolio_greeks", {})
            strategy_metrics = strategy_summary.get("strategy_metrics", {})
            symbol = strategy_summary.get("symbol", "UNKNOWN")
            strategy_name = strategy_summary.get("strategy_name", "Unknown Strategy")
            
            # Format FMP enriched data for risk context (fundamental_profile, iv_context, upcoming_events, sentiment)
            enriched_section = self._format_enriched_risk_context(strategy_summary)
            
            # Build analysis prompt
            prompt = f"""
Analyze risk scenarios for this options strategy:

Strategy: {strategy_name}
Symbol: {symbol}

Strategy Metrics:
- Max Profit: ${strategy_metrics.get('max_profit', 0):.2f}
- Max Loss: ${strategy_metrics.get('max_loss', 0):.2f}
- Probability of Profit: {strategy_metrics.get('pop', 0):.1f}%

Net Greeks:
- Delta: {portfolio_greeks.get('delta', 0):.4f}
- Gamma: {portfolio_greeks.get('gamma', 0):.4f}
- Theta: {portfolio_greeks.get('theta', 0):.4f}
- Vega: {portfolio_greeks.get('vega', 0):.4f}

Previous Analysis Results:
{self._format_previous_results(previous_results)}
{enriched_section}

Provide a comprehensive risk scenario analysis covering:
1. Worst-Case Scenario: Under what specific conditions does this strategy lose maximum money?
2. Tail Risk Assessment: What are the low-probability, high-impact risks?
3. Stress Test Scenarios:
   - What happens if stock moves +10%?
   - What happens if stock moves -10%?
   - What happens if IV crushes by 20%?
   - What happens if time passes (Theta decay)?
4. Risk/Reward Evaluation: Is the potential reward worth the risk?
5. Risk Mitigation Strategies: How can risks be managed or reduced?
6. Position Sizing Recommendation: What position size is appropriate given the risks?
7. Stop-Loss/Exit Strategy: When should the position be closed?
"""
            
            # Call AI for analysis
            analysis = await self._call_ai(prompt, system_prompt=self._role_prompt, context=context)
            
            # Calculate risk score
            risk_score = self._calculate_risk_score(strategy_metrics, portfolio_greeks)
            
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                success=True,
                data={
                    "analysis": analysis,
                    "risk_score": risk_score,
                    "risk_category": self._categorize_risk(risk_score),
                    "strategy_name": strategy_name,
                    "symbol": symbol,
                    "max_loss": strategy_metrics.get("max_loss", 0),
                    "max_profit": strategy_metrics.get("max_profit", 0),
                },
            )
            
        except Exception as e:
            logger.error(f"RiskScenarioAnalyst execution failed: {e}", exc_info=True)
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                success=False,
                data={},
                error=str(e),
            )
    
    def _format_previous_results(self, previous_results: Dict[str, Any]) -> str:
        """Format previous analysis results for prompt."""
        if not previous_results:
            return "No previous analysis results available"
        
        lines = []
        for agent_name, result_data in previous_results.items():
            if isinstance(result_data, dict):
                # Extract key insights
                risk_score = result_data.get("risk_score")
                if risk_score is not None and isinstance(risk_score, (int, float)):
                    lines.append(f"- {agent_name}: Risk Score = {risk_score}")
                
                iv_score = result_data.get("iv_score")
                if iv_score is not None and isinstance(iv_score, (int, float)):
                    lines.append(f"- {agent_name}: IV Score = {iv_score}")
        
        return "\n".join(lines) if lines else "Previous analysis results available but no key metrics extracted"
    
    def _format_enriched_risk_context(self, strategy_summary: Dict[str, Any]) -> str:
        """Format FMP enriched data (fundamental_profile, iv_context, upcoming_events, sentiment) for risk analysis."""
        parts = []
        fp = strategy_summary.get("fundamental_profile")
        if fp and isinstance(fp, dict):
            # Risk-relevant: volatility, risk_metrics, valuation
            risk_metrics = fp.get("risk_metrics") or fp.get("risk")
            volatility = fp.get("volatility")
            valuation = fp.get("valuation") or (fp.get("ratios") or {}).get("valuation")
            sub = {}
            if risk_metrics and isinstance(risk_metrics, dict):
                sub["risk_metrics"] = risk_metrics
            if volatility and isinstance(volatility, dict):
                sub["volatility"] = volatility
            if valuation and isinstance(valuation, dict):
                sub["valuation"] = valuation
            if sub:
                parts.append(f"Fundamental Risk Context: {json.dumps(sub, indent=2, default=str)[:2000]}")
        iv_ctx = strategy_summary.get("iv_context")
        if iv_ctx and isinstance(iv_ctx, dict):
            parts.append(f"IV / Volatility Context: {json.dumps(iv_ctx, indent=2, default=str)}")
        events = strategy_summary.get("upcoming_events") or strategy_summary.get("catalyst") or []
        if events and isinstance(events, list):
            parts.append(f"Upcoming Catalysts (earnings, etc.): {json.dumps(events[:8], indent=2, default=str)}")
        sent = strategy_summary.get("sentiment") or {}
        if sent and isinstance(sent, dict) and sent:
            parts.append(f"Market Sentiment: {json.dumps(sent, indent=2, default=str)[:600]}")
        if not parts:
            return ""
        return "\n\nFundamental & Catalyst Data (FMP - use for tail risk and event-driven stress tests):\n" + "\n\n".join(parts)
    
    def _calculate_risk_score(self, strategy_metrics: Dict[str, Any], greeks: Dict[str, Any]) -> float:
        """Calculate overall risk score (0-10).
        
        Args:
            strategy_metrics: Strategy metrics dictionary
            greeks: Portfolio Greeks dictionary
            
        Returns:
            Risk score (0-10, higher = more risky)
        """
        score = 5.0  # Default medium risk
        
        # Max loss risk
        try:
            max_loss = abs(float(strategy_metrics.get("max_loss", 0)))
            max_profit = abs(float(strategy_metrics.get("max_profit", 0)))
            
            if max_loss > 0:
                risk_reward_ratio = max_loss / max_profit if max_profit > 0 else float("inf")
                if risk_reward_ratio > 3:
                    score += 2.0
                elif risk_reward_ratio > 2:
                    score += 1.0
                elif risk_reward_ratio < 0.5:
                    score -= 1.0
        except (ValueError, TypeError):
            pass  # Skip if metrics invalid
        
        # Greeks risk
        try:
            delta_risk = abs(float(greeks.get("delta", 0)))
            if delta_risk > 0.5:
                score += 1.0
        except (ValueError, TypeError):
            pass
        
        try:
            gamma_risk = abs(float(greeks.get("gamma", 0)))
            if gamma_risk > 0.1:
                score += 0.5
        except (ValueError, TypeError):
            pass
        
        try:
            vega_risk = abs(float(greeks.get("vega", 0)))
            if vega_risk > 100:
                score += 1.0
        except (ValueError, TypeError):
            pass
        
        # Clamp to 0-10 range
        score = max(0.0, min(10.0, score))
        
        return round(score, 1)
    
    def _categorize_risk(self, risk_score: float) -> str:
        """Categorize risk score."""
        if risk_score < 3:
            return "Low Risk"
        elif risk_score < 6:
            return "Medium Risk"
        elif risk_score < 8:
            return "High Risk"
        else:
            return "Very High Risk"
