"""Technical Analyst Agent - Analyzes technical indicators and chart patterns."""

import logging
from typing import Any, Dict

from app.services.agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from app.services.ai.base import BaseAIProvider
from app.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)


class TechnicalAnalyst(BaseAgent):
    """Technical Analyst - Analyzes technical indicators and chart patterns.
    
    This agent uses MarketDataService to analyze:
    - Technical indicators (RSI, MACD, Bollinger Bands, etc.)
    - Trend analysis
    - Support and resistance levels
    - Entry/exit signals
    """
    
    def __init__(self, name: str, ai_provider: BaseAIProvider, dependencies: Dict[str, Any]):
        """Initialize Technical Analyst.
        
        Args:
            name: Agent name
            ai_provider: AI provider instance
            dependencies: Dictionary of dependencies (must include market_data_service)
        """
        super().__init__(
            name=name,
            agent_type=AgentType.TECHNICAL_ANALYSIS,
            ai_provider=ai_provider,
            dependencies=dependencies,
        )
        self.market_data_service: MarketDataService = self._get_dependency("market_data_service")
    
    def _get_role_prompt(self) -> str:
        """Get role definition prompt."""
        return """You are a Senior Technical Analyst specializing in chart patterns and technical indicators.

Your expertise includes:
- Technical indicators interpretation (RSI, MACD, Bollinger Bands, SMA, EMA, ADX, ATR, OBV)
- Chart pattern recognition
- Trend analysis (uptrend, downtrend, sideways)
- Support and resistance level identification
- Entry/exit signal generation
- Volume analysis

Your analysis should:
1. Assess current trend (Bullish/Bearish/Neutral)
2. Identify key support and resistance levels
3. Generate entry/exit signals based on technical indicators
4. Assess momentum and trend strength
5. Evaluate risk/reward from a technical perspective
6. Provide actionable trading recommendations

Be objective, data-driven, and focus on practical trading insights."""
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute technical analysis.
        
        Args:
            context: Execution context containing ticker
            
        Returns:
            AgentResult with technical analysis
        """
        try:
            # Get ticker from context
            ticker = context.input_data.get("ticker")
            if not ticker:
                return AgentResult(
                    agent_name=self.name,
                    agent_type=self.agent_type,
                    success=False,
                    data={},
                    error="ticker not provided in context",
                )
            
            # Fetch technical data using MarketDataService
            logger.debug(f"Fetching technical data for {ticker}")
            profile = self.market_data_service.get_financial_profile(ticker)
            
            if not profile:
                return AgentResult(
                    agent_name=self.name,
                    agent_type=self.agent_type,
                    success=False,
                    data={},
                    error=f"Failed to fetch technical data for {ticker}",
                )
            
            # Extract technical indicators
            technical_indicators = profile.get("technical_indicators", {})
            analysis = profile.get("analysis", {})
            
            # Get technical chart (optional)
            chart_base64 = None
            try:
                chart_base64 = self.market_data_service.generate_technical_chart(
                    ticker, indicator="rsi"
                )
            except Exception as e:
                logger.debug(f"Failed to generate technical chart: {e}")
            
            # Build analysis prompt
            prompt = f"""
Analyze the technical indicators for {ticker}:

Momentum Indicators:
{self._format_momentum_indicators(technical_indicators)}

Trend Indicators:
{self._format_trend_indicators(technical_indicators)}

Volatility Indicators:
{self._format_volatility_indicators(technical_indicators)}

Volume Indicators:
{self._format_volume_indicators(technical_indicators)}

Existing Technical Signals:
{self._format_technical_signals(analysis)}

Provide a comprehensive technical analysis covering:
1. Current Trend: Bullish/Bearish/Neutral assessment with strength
2. Key Support and Resistance Levels: Identify important price levels
3. Entry/Exit Signals: Based on technical indicators
4. Momentum Assessment: Is momentum building or weakening?
5. Risk/Reward from Technical Perspective: Entry, stop-loss, target levels
6. Technical Score: Overall technical score (0-10)
7. Recommendations: Actionable technical trading recommendations
"""
            
            # Call AI for analysis
            ai_analysis = await self._call_ai(prompt, system_prompt=self._role_prompt, context=context)
            
            # Calculate technical score
            technical_score = self._calculate_technical_score(technical_indicators, analysis)
            
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                success=True,
                data={
                    "analysis": ai_analysis,
                    "ticker": ticker,
                    "technical_score": technical_score,
                    "technical_category": self._categorize_technical(technical_score),
                    "chart": chart_base64,
                    "indicators_summary": self._extract_indicators_summary(technical_indicators),
                },
            )
            
        except Exception as e:
            logger.error(f"TechnicalAnalyst execution failed: {e}", exc_info=True)
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                success=False,
                data={},
                error=str(e),
            )
    
    def _format_momentum_indicators(self, technical_indicators: Dict[str, Any]) -> str:
        """Format momentum indicators for prompt."""
        lines = []
        
        # RSI
        if "rsi" in technical_indicators:
            rsi_data = technical_indicators["rsi"]
            if isinstance(rsi_data, dict):
                # Get latest RSI value
                latest = self._get_latest_value(rsi_data)
                if latest is not None:
                    lines.append(f"- RSI: {latest:.2f}")
        
        # MACD
        if "macd" in technical_indicators or "macd_line" in technical_indicators:
            lines.append("- MACD: Available")
        
        # Momentum collection
        if "momentum" in technical_indicators:
            lines.append("- Momentum Indicators: Available")
        
        return "\n".join(lines) if lines else "No momentum indicator data available"
    
    def _format_trend_indicators(self, technical_indicators: Dict[str, Any]) -> str:
        """Format trend indicators for prompt."""
        lines = []
        
        # SMA
        if "sma" in technical_indicators:
            lines.append("- SMA: Available")
        
        # EMA
        if "ema" in technical_indicators:
            lines.append("- EMA: Available")
        
        # ADX
        if "adx" in technical_indicators:
            adx_data = technical_indicators["adx"]
            if isinstance(adx_data, dict):
                latest = self._get_latest_value(adx_data)
                if latest is not None:
                    lines.append(f"- ADX: {latest:.2f}")
        
        # Trend collection
        if "trend" in technical_indicators:
            lines.append("- Trend Indicators: Available")
        
        return "\n".join(lines) if lines else "No trend indicator data available"
    
    def _format_volatility_indicators(self, technical_indicators: Dict[str, Any]) -> str:
        """Format volatility indicators for prompt."""
        lines = []
        
        # Bollinger Bands
        if "bollinger_bands" in technical_indicators:
            lines.append("- Bollinger Bands: Available")
        
        # ATR
        if "atr" in technical_indicators:
            lines.append("- ATR: Available")
        
        # Volatility collection
        if "volatility" in technical_indicators:
            lines.append("- Volatility Indicators: Available")
        
        return "\n".join(lines) if lines else "No volatility indicator data available"
    
    def _format_volume_indicators(self, technical_indicators: Dict[str, Any]) -> str:
        """Format volume indicators for prompt."""
        lines = []
        
        # OBV
        if "obv" in technical_indicators:
            lines.append("- OBV: Available")
        
        # Volume collection
        if "volume" in technical_indicators:
            lines.append("- Volume Indicators: Available")
        
        return "\n".join(lines) if lines else "No volume indicator data available"
    
    def _format_technical_signals(self, analysis: Dict[str, Any]) -> str:
        """Format technical signals for prompt."""
        technical_signals = analysis.get("technical_signals", {})
        if not technical_signals:
            return "No technical signals available"
        
        lines = []
        for signal_type, signal_value in technical_signals.items():
            if signal_value:
                lines.append(f"- {signal_type}: {signal_value}")
        
        return "\n".join(lines) if lines else "No technical signals available"
    
    def _get_latest_value(self, data: Dict[str, Any]) -> float:
        """Get latest value from time-series data.
        
        Args:
            data: Dictionary with date keys and values
            
        Returns:
            Latest value or None
        """
        if not isinstance(data, dict):
            return None
        
        # Get first key (assuming sorted by date)
        if data:
            first_key = list(data.keys())[0]
            value = data[first_key]
            
            # Handle nested dictionaries
            if isinstance(value, dict):
                # Get first value from nested dict
                if value:
                    first_nested_key = list(value.keys())[0]
                    value = value[first_nested_key]
            
            try:
                return float(value)
            except (ValueError, TypeError):
                return None
        
        return None
    
    def _calculate_technical_score(self, technical_indicators: Dict[str, Any], analysis: Dict[str, Any]) -> float:
        """Calculate technical score (0-10).
        
        Args:
            technical_indicators: Technical indicators dictionary
            analysis: Analysis dictionary
            
        Returns:
            Technical score (0-10, higher = more bullish)
        """
        score = 5.0  # Default neutral
        
        # RSI contribution
        if "rsi" in technical_indicators:
            rsi_data = technical_indicators["rsi"]
            rsi_value = self._get_latest_value(rsi_data)
            if rsi_value is not None:
                if rsi_value > 70:
                    score -= 1.0  # Overbought
                elif rsi_value < 30:
                    score += 1.0  # Oversold
                elif 40 < rsi_value < 60:
                    score += 0.5  # Neutral-bullish
        
        # Technical signals contribution
        technical_signals = analysis.get("technical_signals", {})
        if technical_signals:
            if "bullish" in str(technical_signals).lower():
                score += 1.0
            elif "bearish" in str(technical_signals).lower():
                score -= 1.0
        
        # Clamp to 0-10 range
        score = max(0.0, min(10.0, score))
        
        return round(score, 1)
    
    def _categorize_technical(self, technical_score: float) -> str:
        """Categorize technical score."""
        if technical_score >= 7:
            return "Bullish"
        elif technical_score >= 5:
            return "Neutral-Bullish"
        elif technical_score >= 3:
            return "Neutral-Bearish"
        else:
            return "Bearish"
    
    def _extract_indicators_summary(self, technical_indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Extract indicators summary."""
        summary = {}
        for indicator_type in ["rsi", "macd", "sma", "ema", "adx", "bollinger_bands", "atr", "obv"]:
            if indicator_type in technical_indicators:
                summary[indicator_type] = "Available"
        return summary
