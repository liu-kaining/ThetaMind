"""Market Context Analyst Agent - Analyzes market environment and context."""

import logging
from typing import Any, Dict

from app.services.agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from app.services.ai.base import BaseAIProvider
from app.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)


class MarketContextAnalyst(BaseAgent):
    """Market Context Analyst - Analyzes market environment and context.
    
    This agent uses MarketDataService to analyze:
    - Market fundamentals (financial ratios, valuation)
    - Technical indicators (trend, momentum)
    - Market sentiment and news
    - Overall market environment assessment
    """
    
    def __init__(self, name: str, ai_provider: BaseAIProvider, dependencies: Dict[str, Any]):
        """Initialize Market Context Analyst.
        
        Args:
            name: Agent name
            ai_provider: AI provider instance
            dependencies: Dictionary of dependencies (must include market_data_service)
        """
        super().__init__(
            name=name,
            agent_type=AgentType.OPTIONS_ANALYSIS,
            ai_provider=ai_provider,
            dependencies=dependencies,
        )
        self.market_data_service: MarketDataService = self._get_dependency("market_data_service")
    
    def _get_role_prompt(self) -> str:
        """Get role definition prompt."""
        return """You are a Senior Market Strategist specializing in market context analysis.

Your expertise includes:
- Market fundamentals assessment
- Technical analysis and trend identification
- Market sentiment evaluation
- Overall market environment assessment
- Options strategy market fit analysis

Your analysis should:
1. Assess overall market environment (bullish/bearish/neutral)
2. Evaluate fundamental strength/weakness
3. Identify technical trends and patterns
4. Assess market sentiment
5. Evaluate how the options strategy fits the current market context

Be comprehensive, objective, and focus on actionable insights."""
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute market context analysis.
        
        Args:
            context: Execution context containing strategy_summary or ticker
            
        Returns:
            AgentResult with market context analysis
        """
        try:
            # Get ticker from context
            strategy_summary = context.input_data.get("strategy_summary", {})
            ticker = strategy_summary.get("symbol") or context.input_data.get("ticker")
            
            if not ticker:
                return AgentResult(
                    agent_name=self.name,
                    agent_type=self.agent_type,
                    success=False,
                    data={},
                    error="ticker or symbol not provided in context",
                )
            
            # Fetch market data using MarketDataService
            logger.debug(f"Fetching market data for {ticker}")
            profile = self.market_data_service.get_financial_profile(ticker)
            
            if not profile:
                return AgentResult(
                    agent_name=self.name,
                    agent_type=self.agent_type,
                    success=False,
                    data={},
                    error=f"Failed to fetch market data for {ticker}",
                )
            
            # Extract key data
            ratios = profile.get("ratios", {})
            technical_indicators = profile.get("technical_indicators", {})
            analysis = profile.get("analysis", {})
            historical_prices = strategy_summary.get("historical_prices", [])
            
            # Build analysis prompt
            prompt = f"""
Analyze the market context for {ticker} in relation to this options strategy:

Strategy: {strategy_summary.get('strategy_name', 'Unknown')}
Expiration: {strategy_summary.get('expiration_date', 'N/A')}

Market Fundamentals:
{self._format_fundamentals(ratios)}

Technical Indicators:
{self._format_technical_indicators(technical_indicators)}

Historical Price Context:
{self._format_historical_prices(historical_prices)}

Existing Analysis:
{self._format_existing_analysis(analysis)}

Provide a comprehensive market context analysis covering:
1. Overall Market Environment: Bullish/Bearish/Neutral assessment
2. Fundamental Strength: Company financial health and valuation
3. Technical Trends: Price trends, momentum, support/resistance
4. Market Sentiment: Current market mood and sentiment
5. Strategy Fit: How well does this options strategy fit the current market context?
6. Key Catalysts: Upcoming events that could impact the strategy
7. Recommendations: Market-based recommendations for the strategy
"""
            
            # Call AI for analysis
            ai_analysis = await self._call_ai(prompt, system_prompt=self._role_prompt, context=context)
            
            # Extract market scores
            market_score = self._calculate_market_score(profile)
            
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                success=True,
                data={
                    "analysis": ai_analysis,
                    "ticker": ticker,
                    "market_score": market_score,
                    "market_category": self._categorize_market(market_score),
                    "fundamentals_summary": self._extract_fundamentals_summary(ratios),
                    "technical_summary": self._extract_technical_summary(technical_indicators),
                },
            )
            
        except Exception as e:
            logger.error(f"MarketContextAnalyst execution failed: {e}", exc_info=True)
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                success=False,
                data={},
                error=str(e),
            )
    
    def _format_fundamentals(self, ratios: Dict[str, Any]) -> str:
        """Format fundamentals data for prompt."""
        if not ratios:
            return "No fundamental data available"
        
        lines = []
        for category in ["profitability", "valuation", "solvency"]:
            if category in ratios:
                data = ratios[category]
                if isinstance(data, dict) and data:
                    latest_date = list(data.keys())[0]
                    if latest_date and isinstance(data[latest_date], dict):
                        values = data[latest_date]
                        lines.append(f"\n{category.upper()}:")
                        for key, value in list(values.items())[:3]:
                            if value is not None:
                                lines.append(f"  - {key}: {value}")
        
        return "\n".join(lines) if lines else "Limited fundamental data available"
    
    def _format_technical_indicators(self, technical_indicators: Dict[str, Any]) -> str:
        """Format technical indicators for prompt."""
        if not technical_indicators:
            return "No technical indicator data available"
        
        lines = []
        
        # RSI
        if "rsi" in technical_indicators:
            lines.append("RSI: Available")
        
        # MACD
        if "macd" in technical_indicators or "macd_line" in technical_indicators:
            lines.append("MACD: Available")
        
        # Trend indicators
        if "trend" in technical_indicators:
            lines.append("Trend Indicators: Available")
        
        # Momentum
        if "momentum" in technical_indicators:
            lines.append("Momentum Indicators: Available")
        
        return "\n".join(lines) if lines else "Limited technical data available"
    
    def _format_existing_analysis(self, analysis: Dict[str, Any]) -> str:
        """Format existing analysis for prompt."""
        if not analysis:
            return "No existing analysis available"
        
        lines = []
        
        # Technical signals
        technical_signals = analysis.get("technical_signals", {})
        if technical_signals:
            lines.append(f"Technical Signals: {list(technical_signals.keys())}")
        
        # Health score
        health_score = analysis.get("health_score", {})
        if isinstance(health_score, dict):
            overall = health_score.get("overall", "N/A")
            category = health_score.get("category", "N/A")
            lines.append(f"Health Score: {overall} ({category})")
        
        return "\n".join(lines) if lines else "No existing analysis available"

    def _format_historical_prices(self, historical_prices: Any) -> str:
        """Summarize historical price data for prompt."""
        if not isinstance(historical_prices, list) or len(historical_prices) < 2:
            return "No historical price data available"
        rows = []
        for row in historical_prices:
            if isinstance(row, dict):
                time_key = row.get("time")
                close_value = row.get("close")
                if time_key and isinstance(close_value, (int, float)):
                    rows.append((str(time_key), float(close_value)))
        if len(rows) < 2:
            return "No historical price data available"
        rows.sort(key=lambda r: r[0])
        closes = [r[1] for r in rows]
        latest_close = closes[-1]
        first_close = closes[0]
        change_pct = None
        if first_close > 0:
            change_pct = (latest_close / first_close - 1.0) * 100
        high_52w = max(closes)
        low_52w = min(closes)
        summary = [
            f"- Latest Close: {latest_close:.2f}",
            f"- Range: {low_52w:.2f} - {high_52w:.2f}",
        ]
        if change_pct is not None:
            summary.append(f"- Period Change: {change_pct:.2f}%")
        return "\n".join(summary)
    
    def _calculate_market_score(self, profile: Dict[str, Any]) -> float:
        """Calculate overall market score (0-10).
        
        Args:
            profile: Financial profile from MarketDataService
            
        Returns:
            Market score (0-10)
        """
        score = 5.0  # Default neutral
        
        # Health score contribution
        analysis = profile.get("analysis", {})
        health_score = analysis.get("health_score", {})
        if isinstance(health_score, dict):
            overall = health_score.get("overall", 50)
            if isinstance(overall, (int, float)):
                score = overall / 10.0  # Convert to 0-10 scale
        
        # Technical signals contribution
        technical_signals = analysis.get("technical_signals", {})
        if technical_signals:
            # Positive signals increase score
            if "bullish" in str(technical_signals).lower():
                score += 0.5
            elif "bearish" in str(technical_signals).lower():
                score -= 0.5
        
        # Clamp to 0-10 range
        score = max(0.0, min(10.0, score))
        
        return round(score, 1)
    
    def _categorize_market(self, market_score: float) -> str:
        """Categorize market score."""
        if market_score >= 7:
            return "Bullish"
        elif market_score >= 5:
            return "Neutral-Bullish"
        elif market_score >= 3:
            return "Neutral-Bearish"
        else:
            return "Bearish"
    
    def _extract_fundamentals_summary(self, ratios: Dict[str, Any]) -> Dict[str, Any]:
        """Extract fundamentals summary."""
        summary = {}
        for category in ["profitability", "valuation", "solvency", "liquidity", "efficiency"]:
            if category in ratios:
                summary[category] = "Available"
        return summary
    
    def _extract_technical_summary(self, technical_indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Extract technical indicators summary."""
        summary = {}
        for indicator_type in ["rsi", "macd", "trend", "momentum", "volatility"]:
            if indicator_type in technical_indicators:
                summary[indicator_type] = "Available"
        return summary
