"""Fundamental Analyst Agent - Analyzes company fundamentals using MarketDataService."""

import logging
from typing import Any, Dict

from app.services.agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from app.services.ai.base import BaseAIProvider
from app.services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)


class FundamentalAnalyst(BaseAgent):
    """Fundamental Analyst - Analyzes company financials and fundamentals.
    
    This agent uses MarketDataService to fetch comprehensive financial data
    and provides fundamental analysis using AI.
    """
    
    def __init__(self, name: str, ai_provider: BaseAIProvider, dependencies: Dict[str, Any]):
        """Initialize Fundamental Analyst.
        
        Args:
            name: Agent name
            ai_provider: AI provider instance
            dependencies: Dictionary of dependencies (must include market_data_service)
        """
        super().__init__(
            name=name,
            agent_type=AgentType.FUNDAMENTAL_ANALYSIS,
            ai_provider=ai_provider,
            dependencies=dependencies,
        )
        self.market_data_service: MarketDataService = self._get_dependency("market_data_service")
    
    def _get_role_prompt(self) -> str:
        """Get role definition prompt."""
        return """You are a Senior Fundamental Analyst at a top-tier hedge fund.

Your expertise includes:
- Financial statement analysis (Income Statement, Balance Sheet, Cash Flow)
- Valuation models (DCF, DDM, WACC, Enterprise Value)
- Financial ratios (Profitability, Solvency, Liquidity, Efficiency)
- DuPont analysis (Standard and Extended)
- Company financial health assessment

Your analysis should be:
- Data-driven and quantitative
- Focused on intrinsic value
- Critical of red flags and weaknesses
- Objective and professional
- Actionable with clear recommendations

Provide insights on:
1. Financial health score (0-10)
2. Key strengths and competitive advantages
3. Weaknesses and red flags
4. Valuation assessment (overvalued/undervalued/fair)
5. Investment thesis (if applicable)"""
    
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute fundamental analysis.
        
        Args:
            context: Execution context containing ticker
            
        Returns:
            AgentResult with fundamental analysis
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
            
            # Fetch financial profile using MarketDataService
            logger.debug(f"Fetching financial profile for {ticker}")
            profile = self.market_data_service.get_financial_profile(ticker)
            
            if not profile:
                return AgentResult(
                    agent_name=self.name,
                    agent_type=self.agent_type,
                    success=False,
                    data={},
                    error=f"Failed to fetch financial profile for {ticker}",
                )
            
            # Extract key data
            ratios = profile.get("ratios", {})
            valuation = profile.get("valuation", {})
            financial_statements = profile.get("financial_statements", {})
            dupont_analysis = profile.get("dupont_analysis", {})
            analysis = profile.get("analysis", {})
            
            # Build analysis prompt
            prompt = f"""
Analyze the fundamental data for {ticker}:

Financial Ratios:
{self._format_ratios(ratios)}

Valuation Models:
{self._format_valuation(valuation)}

Financial Statements Summary:
{self._format_statements_summary(financial_statements)}

DuPont Analysis:
{self._format_dupont(dupont_analysis)}

Existing Analysis:
{self._format_existing_analysis(analysis)}

Provide a comprehensive fundamental analysis covering:
1. Financial Health Assessment: Overall score and key metrics
2. Profitability Analysis: ROE, ROA, margins, trends
3. Solvency Analysis: Debt ratios, financial stability
4. Liquidity Analysis: Current ratio, quick ratio, cash position
5. Valuation Assessment: DCF, DDM, relative valuation
6. Key Strengths: Competitive advantages, financial strengths
7. Red Flags: Weaknesses, risks, concerns
8. Investment Thesis: Overall assessment and recommendation
"""
            
            # Call AI for analysis
            ai_analysis = await self._call_ai(prompt, system_prompt=self._role_prompt, context=context)
            
            # Extract health score from existing analysis if available
            health_score = analysis.get("health_score", {})
            health_score_value = health_score.get("overall", 50) if isinstance(health_score, dict) else 50
            
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                success=True,
                data={
                    "analysis": ai_analysis,
                    "ticker": ticker,
                    "health_score": health_score_value,
                    "health_category": self._categorize_health(health_score_value),
                    "ratios_summary": self._extract_ratios_summary(ratios),
                    "valuation_summary": self._extract_valuation_summary(valuation),
                },
            )
            
        except Exception as e:
            logger.error(f"FundamentalAnalyst execution failed: {e}", exc_info=True)
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                success=False,
                data={},
                error=str(e),
            )
    
    def _format_ratios(self, ratios: Dict[str, Any]) -> str:
        """Format financial ratios for prompt."""
        if not ratios:
            return "No ratio data available"
        
        lines = []
        for category, data in ratios.items():
            if isinstance(data, dict) and data:
                # Get latest values (first date key)
                latest_date = list(data.keys())[0] if data else None
                if latest_date and isinstance(data[latest_date], dict):
                    values = data[latest_date]
                    lines.append(f"\n{category.upper()}:")
                    for ratio_name, ratio_value in list(values.items())[:5]:  # Limit to 5 per category
                        if ratio_value is not None:
                            lines.append(f"  - {ratio_name}: {ratio_value}")
        
        return "\n".join(lines) if lines else "No ratio data available"
    
    def _format_valuation(self, valuation: Dict[str, Any]) -> str:
        """Format valuation models for prompt."""
        if not valuation:
            return "No valuation data available"
        
        lines = []
        for model_type, data in valuation.items():
            if data:
                lines.append(f"\n{model_type.upper()}:")
                if isinstance(data, dict):
                    for key, value in list(data.items())[:3]:  # Limit to 3 items
                        if value is not None:
                            lines.append(f"  - {key}: {value}")
        
        return "\n".join(lines) if lines else "No valuation data available"
    
    def _format_statements_summary(self, statements: Dict[str, Any]) -> str:
        """Format financial statements summary for prompt."""
        if not statements:
            return "No financial statements available"
        
        summary = []
        for statement_type in ["income", "balance", "cash_flow"]:
            if statement_type in statements:
                summary.append(f"- {statement_type.replace('_', ' ').title()}: Available")
        
        return "\n".join(summary) if summary else "No financial statements available"
    
    def _format_dupont(self, dupont: Dict[str, Any]) -> str:
        """Format DuPont analysis for prompt."""
        if not dupont:
            return "No DuPont analysis available"
        
        lines = []
        for analysis_type, data in dupont.items():
            if data:
                lines.append(f"\n{analysis_type.upper()}:")
                if isinstance(data, dict):
                    for key, value in list(data.items())[:3]:
                        if value is not None:
                            lines.append(f"  - {key}: {value}")
        
        return "\n".join(lines) if lines else "No DuPont analysis available"
    
    def _format_existing_analysis(self, analysis: Dict[str, Any]) -> str:
        """Format existing analysis for prompt."""
        if not analysis:
            return "No existing analysis available"
        
        health_score = analysis.get("health_score", {})
        if isinstance(health_score, dict):
            overall = health_score.get("overall", "N/A")
            category = health_score.get("category", "N/A")
            return f"Health Score: {overall} ({category})"
        
        return "No existing analysis available"
    
    def _extract_ratios_summary(self, ratios: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key ratios summary."""
        summary = {}
        for category, data in ratios.items():
            if isinstance(data, dict) and data:
                latest_date = list(data.keys())[0]
                if latest_date and isinstance(data[latest_date], dict):
                    summary[category] = len(data[latest_date])
        return summary
    
    def _extract_valuation_summary(self, valuation: Dict[str, Any]) -> Dict[str, Any]:
        """Extract valuation summary."""
        summary = {}
        for model_type, data in valuation.items():
            if data:
                summary[model_type] = "Available"
        return summary
    
    def _categorize_health(self, health_score: float) -> str:
        """Categorize health score."""
        if health_score >= 80:
            return "Excellent"
        elif health_score >= 60:
            return "Good"
        elif health_score >= 40:
            return "Fair"
        else:
            return "Poor"
