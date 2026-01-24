"""IV Environment Analyst Agent - Analyzes implied volatility environment."""

import logging
import math
import statistics
from typing import Any, Dict

from app.services.agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from app.services.ai.base import BaseAIProvider

logger = logging.getLogger(__name__)


class IVEnvironmentAnalyst(BaseAgent):
    """IV Environment Analyst - Analyzes implied volatility environment for options.
    
    This agent specializes in analyzing:
    - IV Rank and IV Percentile
    - Historical vs current IV
    - IV environment assessment (cheap/expensive/fair)
    - Volatility trading opportunities
    """
    
    def __init__(self, name: str, ai_provider: BaseAIProvider, dependencies: Dict[str, Any]):
        """Initialize IV Environment Analyst.
        
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
        return """You are a Senior Volatility Strategist specializing in IV environment analysis.

Your expertise includes:
- IV Rank and IV Percentile interpretation
- Historical volatility vs implied volatility comparison
- IV environment assessment (cheap/expensive/fair)
- Volatility trading opportunities identification
- IV crush risk assessment (especially for earnings)

Your analysis should:
1. Assess current IV environment (cheap/expensive/fair)
2. Compare current IV to historical levels
3. Identify volatility trading opportunities
4. Assess IV crush risk (especially around earnings)
5. Provide actionable recommendations

Be data-driven and focus on practical volatility trading insights."""
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute IV environment analysis.
        
        Args:
            context: Execution context containing strategy_summary or option_chain
            
        Returns:
            AgentResult with IV environment analysis
        """
        try:
            strategy_summary = context.input_data.get("strategy_summary", {})
            option_chain = context.input_data.get("option_chain", {})
            
            # Extract IV data from strategy summary or option chain
            iv_data = self._extract_iv_data(strategy_summary, option_chain)
            
            # Fallback: derive historical volatility from historical prices if available
            if not iv_data.get("historical_volatility"):
                historical_prices = strategy_summary.get("historical_prices", [])
                hv = self._calculate_historical_volatility(historical_prices)
                if hv is not None:
                    iv_data["historical_volatility"] = hv
            
            if not iv_data:
                return AgentResult(
                    agent_name=self.name,
                    agent_type=self.agent_type,
                    success=False,
                    data={},
                    error="IV data not available in context",
                )
            
            symbol = strategy_summary.get("symbol") or option_chain.get("symbol", "UNKNOWN")
            
            # Build analysis prompt
            prompt = f"""
Analyze the implied volatility environment for {symbol}:

Current IV Data:
{self._format_iv_data(iv_data)}

Strategy Context:
- Strategy: {strategy_summary.get('strategy_name', 'Unknown')}
- Expiration: {strategy_summary.get('expiration_date', 'N/A')}

Provide a comprehensive IV environment analysis covering:
1. IV Environment Assessment: Is IV cheap, expensive, or fair?
2. IV Rank/Percentile Interpretation: What does the current IV level mean?
3. Historical Comparison: How does current IV compare to historical levels?
4. Volatility Trading Opportunity: Is this a good time to buy or sell volatility?
5. IV Crush Risk: What's the risk of IV dropping (especially around earnings)?
6. Recommendations: Actionable advice for volatility trading
"""
            
            # Call AI for analysis
            analysis = await self._call_ai(prompt, system_prompt=self._role_prompt, context=context)
            
            # Calculate IV environment score
            iv_score = self._calculate_iv_score(iv_data)
            
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                success=True,
                data={
                    "analysis": analysis,
                    "iv_data": iv_data,
                    "iv_score": iv_score,
                    "iv_category": self._categorize_iv(iv_score),
                    "symbol": symbol,
                },
            )
            
        except Exception as e:
            logger.error(f"IVEnvironmentAnalyst execution failed: {e}", exc_info=True)
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                success=False,
                data={},
                error=str(e),
            )
    
    def _extract_iv_data(self, strategy_summary: Dict[str, Any], option_chain: Dict[str, Any]) -> Dict[str, Any]:
        """Extract IV data from strategy summary or option chain.
        
        Args:
            strategy_summary: Strategy summary dictionary
            option_chain: Option chain dictionary
            
        Returns:
            Dictionary with IV data
        """
        iv_data = {}
        
        # Try to extract from strategy summary first
        if strategy_summary:
            legs = strategy_summary.get("legs", [])
            if legs:
                # Calculate average IV from legs
                iv_values = []
                for leg in legs:
                    if isinstance(leg, dict):
                        iv = leg.get("implied_volatility") or leg.get("implied_vol")
                        if iv and isinstance(iv, (int, float)) and iv > 0:
                            iv_values.append(float(iv))
                
                if iv_values:
                    iv_data["current_iv"] = sum(iv_values) / len(iv_values)
                    iv_data["iv_range"] = {
                        "min": min(iv_values),
                        "max": max(iv_values),
                    }
        
        # Try to extract from option chain
        if option_chain and not iv_data:
            # Look for IV in option chain data
            calls = option_chain.get("calls", [])
            puts = option_chain.get("puts", [])
            
            iv_values = []
            for option in calls + puts:
                if isinstance(option, dict):
                    iv = option.get("implied_volatility") or option.get("implied_vol")
                    if iv and isinstance(iv, (int, float)) and iv > 0:
                        iv_values.append(float(iv))
            
            if iv_values:
                iv_data["current_iv"] = sum(iv_values) / len(iv_values)
                iv_data["iv_range"] = {
                    "min": min(iv_values),
                    "max": max(iv_values),
                }
        
        # Add IV Rank/Percentile if available (from strategy_summary metadata)
        if strategy_summary:
            metadata = strategy_summary.get("metadata", {})
            iv_data["iv_rank"] = metadata.get("iv_rank")
            iv_data["iv_percentile"] = metadata.get("iv_percentile")
            iv_data["historical_volatility"] = metadata.get("historical_volatility")
        
        return iv_data
    
    def _format_iv_data(self, iv_data: Dict[str, Any]) -> str:
        """Format IV data for prompt."""
        lines = []
        
        if "current_iv" in iv_data and iv_data["current_iv"] is not None:
            try:
                lines.append(f"- Current IV: {float(iv_data['current_iv']):.2f}%")
            except (ValueError, TypeError):
                pass
        
        if "iv_range" in iv_data and isinstance(iv_data["iv_range"], dict):
            range_data = iv_data["iv_range"]
            try:
                min_iv = float(range_data.get('min', 0))
                max_iv = float(range_data.get('max', 0))
                lines.append(f"- IV Range: {min_iv:.2f}% - {max_iv:.2f}%")
            except (ValueError, TypeError):
                pass
        
        if "iv_rank" in iv_data and iv_data["iv_rank"] is not None:
            try:
                lines.append(f"- IV Rank: {float(iv_data['iv_rank']):.1f}%")
            except (ValueError, TypeError):
                pass
        
        if "iv_percentile" in iv_data and iv_data["iv_percentile"] is not None:
            try:
                lines.append(f"- IV Percentile: {float(iv_data['iv_percentile']):.1f}%")
            except (ValueError, TypeError):
                pass
        
        if "historical_volatility" in iv_data and iv_data["historical_volatility"] is not None:
            try:
                lines.append(f"- Historical Volatility: {float(iv_data['historical_volatility']):.2f}%")
            except (ValueError, TypeError):
                pass
        
        return "\n".join(lines) if lines else "Limited IV data available"

    def _calculate_historical_volatility(self, historical_prices: Any) -> float | None:
        """Calculate annualized historical volatility from price series."""
        if not isinstance(historical_prices, list) or len(historical_prices) < 2:
            return None
        closes: list[float] = []
        for row in historical_prices:
            if not isinstance(row, dict):
                continue
            close_value = row.get("close")
            if isinstance(close_value, (int, float)) and close_value > 0:
                closes.append(float(close_value))
        if len(closes) < 2:
            return None
        returns: list[float] = []
        for i in range(1, len(closes)):
            prev = closes[i - 1]
            curr = closes[i]
            if prev > 0:
                returns.append((curr / prev) - 1.0)
        if len(returns) < 2:
            return None
        try:
            daily_std = statistics.stdev(returns)
        except statistics.StatisticsError:
            return None
        if not math.isfinite(daily_std):
            return None
        annualized = daily_std * math.sqrt(252) * 100
        return round(annualized, 2)
    
    def _calculate_iv_score(self, iv_data: Dict[str, Any]) -> float:
        """Calculate IV environment score (0-10).
        
        Higher score = more expensive IV (better for selling)
        Lower score = cheaper IV (better for buying)
        
        Args:
            iv_data: IV data dictionary
            
        Returns:
            IV score (0-10)
        """
        score = 5.0  # Default neutral
        
        # IV Rank/Percentile based scoring
        iv_rank = iv_data.get("iv_rank")
        iv_percentile = iv_data.get("iv_percentile")
        
        try:
            if iv_rank is not None and isinstance(iv_rank, (int, float)):
                # IV Rank: 0-100, higher = more expensive
                score = float(iv_rank) / 10.0  # Convert to 0-10 scale
            elif iv_percentile is not None and isinstance(iv_percentile, (int, float)):
                # IV Percentile: 0-100, higher = more expensive
                score = float(iv_percentile) / 10.0
        except (ValueError, TypeError):
            pass  # Keep default score
        
        # Historical comparison
        current_iv = iv_data.get("current_iv")
        historical_vol = iv_data.get("historical_volatility")
        
        try:
            if current_iv is not None and historical_vol is not None:
                current_iv_float = float(current_iv)
                historical_vol_float = float(historical_vol)
                if historical_vol_float > 0:
                    iv_ratio = current_iv_float / historical_vol_float
                    if iv_ratio > 1.3:  # IV significantly higher than HV
                        score += 1.0
                    elif iv_ratio < 0.8:  # IV significantly lower than HV
                        score -= 1.0
        except (ValueError, TypeError, ZeroDivisionError):
            pass  # Skip historical comparison if data invalid
        
        # Clamp to 0-10 range
        score = max(0.0, min(10.0, score))
        
        return round(score, 1)
    
    def _categorize_iv(self, iv_score: float) -> str:
        """Categorize IV score into environment type.
        
        Args:
            iv_score: IV score (0-10)
            
        Returns:
            IV category string
        """
        if iv_score < 3:
            return "Cheap (Good for buying volatility)"
        elif iv_score < 5:
            return "Fair-Low (Slightly cheap)"
        elif iv_score < 7:
            return "Fair-High (Slightly expensive)"
        else:
            return "Expensive (Good for selling volatility)"
