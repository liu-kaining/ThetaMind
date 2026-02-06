"""Options Greeks Analyst Agent - Analyzes options strategy Greeks exposure."""

import logging
from typing import Any, Dict

from app.services.agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from app.services.ai.base import BaseAIProvider

logger = logging.getLogger(__name__)


class OptionsGreeksAnalyst(BaseAgent):
    """Options Greeks Analyst - Analyzes strategy's Greeks risk exposure.
    
    This agent specializes in analyzing the Greeks (Delta, Gamma, Theta, Vega)
    of an options strategy and providing risk assessment.
    """
    
    def __init__(self, name: str, ai_provider: BaseAIProvider, dependencies: Dict[str, Any]):
        """Initialize Options Greeks Analyst.
        
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
        return """You are a Senior Options Strategist specializing in Greeks analysis.

Your expertise includes:
- Delta: Directional risk assessment and bias analysis
- Gamma: Acceleration risk (pin risk, gamma scalping implications)
- Theta: Time decay analysis and theta efficiency
- Vega: Volatility sensitivity and IV risk assessment

Your analysis should:
1. Assess risk for each Greek individually
2. Identify key risk factors and warning signs
3. Provide actionable recommendations for risk management
4. Consider the interaction between different Greeks

Be professional, objective, and focus on practical risk management. Respond in English only; do not use Chinese."""
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute Greeks analysis.
        
        Args:
            context: Execution context containing strategy_summary
            
        Returns:
            AgentResult with Greeks analysis
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
            
            # Extract Greeks from strategy summary
            portfolio_greeks = strategy_summary.get("portfolio_greeks", {})
            greeks = {
                "delta": portfolio_greeks.get("delta", 0),
                "gamma": portfolio_greeks.get("gamma", 0),
                "theta": portfolio_greeks.get("theta", 0),
                "vega": portfolio_greeks.get("vega", 0),
            }
            
            # Extract strategy information
            strategy_name = strategy_summary.get("strategy_name", "Unknown Strategy")
            symbol = strategy_summary.get("symbol", "Unknown")
            strategy_metrics = strategy_summary.get("strategy_metrics", {})
            
            # Build analysis prompt
            prompt = f"""
Analyze the Greeks exposure for this options strategy:

Strategy: {strategy_name}
Symbol: {symbol}

Net Greeks:
- Delta: {greeks['delta']:.4f}
- Gamma: {greeks['gamma']:.4f}
- Theta: {greeks['theta']:.4f}
- Vega: {greeks['vega']:.4f}

Strategy Metrics:
- Max Profit: ${strategy_metrics.get('max_profit', 0):.2f}
- Max Loss: ${strategy_metrics.get('max_loss', 0):.2f}
- Probability of Profit: {strategy_metrics.get('pop', 0):.1f}%

Provide a comprehensive Greeks risk analysis covering:
1. Delta Analysis: Directional bias and risk
2. Gamma Analysis: Acceleration risk and pin risk
3. Theta Analysis: Time decay efficiency
4. Vega Analysis: Volatility sensitivity
5. Overall Risk Assessment: Combined risk score (0-10)
6. Key Recommendations: Actionable risk management advice
"""
            
            # Call AI for analysis
            analysis = await self._call_ai(prompt, system_prompt=self._role_prompt, context=context)
            
            # Calculate risk score
            risk_score = self._calculate_risk_score(greeks, strategy_metrics)
            
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                success=True,
                data={
                    "analysis": analysis,
                    "greeks": greeks,
                    "risk_score": risk_score,
                    "risk_category": self._categorize_risk(risk_score),
                    "strategy_name": strategy_name,
                    "symbol": symbol,
                },
            )
            
        except Exception as e:
            logger.error(f"OptionsGreeksAnalyst execution failed: {e}", exc_info=True)
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                success=False,
                data={},
                error=str(e),
            )
    
    def _calculate_risk_score(self, greeks: Dict[str, float], metrics: Dict[str, Any]) -> float:
        """Calculate overall risk score based on Greeks.
        
        Args:
            greeks: Dictionary of Greeks values
            metrics: Strategy metrics
            
        Returns:
            Risk score (0-10, higher = more risky)
        """
        score = 5.0  # Default medium risk
        
        # Delta risk: High absolute delta = directional risk
        try:
            delta_risk = abs(float(greeks.get("delta", 0)))
            if delta_risk > 0.5:
                score += 1.5
            elif delta_risk > 0.3:
                score += 0.5
        except (ValueError, TypeError):
            pass
        
        # Gamma risk: High absolute gamma = acceleration risk
        try:
            gamma_risk = abs(float(greeks.get("gamma", 0)))
            if gamma_risk > 0.1:
                score += 1.0
        except (ValueError, TypeError):
            pass
        
        # Theta risk: Negative theta (collecting) is generally good, but high theta can indicate high risk
        try:
            theta = float(greeks.get("theta", 0))
            if theta < -50:  # High negative theta (collecting a lot)
                score -= 0.5  # Lower risk (collecting premium)
            elif theta > 10:  # Positive theta (paying premium)
                score += 1.0  # Higher risk
        except (ValueError, TypeError):
            pass
        
        # Vega risk: High absolute vega = volatility risk
        try:
            vega_risk = abs(float(greeks.get("vega", 0)))
            if vega_risk > 100:
                score += 1.5
            elif vega_risk > 50:
                score += 0.5
        except (ValueError, TypeError):
            pass
        
        # Max loss risk: High max loss relative to max profit
        try:
            max_profit = abs(float(metrics.get("max_profit", 0)))
            max_loss = abs(float(metrics.get("max_loss", 0)))
            if max_loss > 0:
                risk_reward_ratio = max_loss / max_profit if max_profit > 0 else float("inf")
                if risk_reward_ratio > 3:
                    score += 1.0
                elif risk_reward_ratio > 2:
                    score += 0.5
        except (ValueError, TypeError, ZeroDivisionError):
            pass
        
        # Clamp to 0-10 range
        score = max(0.0, min(10.0, score))
        
        return round(score, 1)
    
    def _categorize_risk(self, risk_score: float) -> str:
        """Categorize risk score into risk level.
        
        Args:
            risk_score: Risk score (0-10)
            
        Returns:
            Risk category string
        """
        if risk_score < 3:
            return "Low"
        elif risk_score < 6:
            return "Medium"
        elif risk_score < 8:
            return "High"
        else:
            return "Very High"
