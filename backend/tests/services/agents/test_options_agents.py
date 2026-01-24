"""Tests for Options Analysis Agents."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.agents.base import AgentContext, AgentResult, AgentType
from app.services.agents.options_greeks_analyst import OptionsGreeksAnalyst
from app.services.agents.iv_environment_analyst import IVEnvironmentAnalyst
from app.services.agents.market_context_analyst import MarketContextAnalyst
from app.services.agents.risk_scenario_analyst import RiskScenarioAnalyst
from app.services.agents.options_synthesis_agent import OptionsSynthesisAgent
from app.services.ai.base import BaseAIProvider


class MockAIProvider(BaseAIProvider):
    """Mock AI provider for testing."""
    
    async def generate_report(self, strategy_summary: dict) -> str:
        return "Mock AI Analysis"
    
    async def generate_daily_picks(self, criteria: dict) -> list:
        return []

    def filter_option_chain(self, chain_data: dict, spot_price: float) -> dict:
        return chain_data


@pytest.fixture
def mock_ai_provider():
    """Create a mock AI provider."""
    return MockAIProvider()


@pytest.fixture
def strategy_summary():
    """Create a sample strategy summary."""
    return {
        "symbol": "AAPL",
        "strategy_name": "Iron Condor",
        "portfolio_greeks": {
            "delta": 0.05,
            "gamma": 0.02,
            "theta": -15.5,
            "vega": -25.3,
        },
        "strategy_metrics": {
            "max_profit": 500,
            "max_loss": -1000,
            "pop": 65.0,
        },
    }


class TestOptionsGreeksAnalyst:
    """Test OptionsGreeksAnalyst agent."""
    
    @pytest.mark.asyncio
    async def test_execute_success(self, mock_ai_provider, strategy_summary):
        """Test successful execution."""
        agent = OptionsGreeksAnalyst(
            name="test_greeks",
            ai_provider=mock_ai_provider,
            dependencies={},
        )
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.OPTIONS_ANALYSIS,
            input_data={"strategy_summary": strategy_summary},
        )
        
        with patch.object(agent, '_call_ai', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "Greeks analysis report"
            
            result = await agent.execute(context)
            
            assert result.success is True
            assert result.agent_name == "test_greeks"
            assert "analysis" in result.data
            assert "risk_score" in result.data
            assert "risk_category" in result.data
            assert result.data["symbol"] == "AAPL"
    
    @pytest.mark.asyncio
    async def test_execute_missing_strategy_summary(self, mock_ai_provider):
        """Test execution with missing strategy summary."""
        agent = OptionsGreeksAnalyst(
            name="test_greeks",
            ai_provider=mock_ai_provider,
            dependencies={},
        )
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.OPTIONS_ANALYSIS,
            input_data={},
        )
        
        result = await agent.execute(context)
        
        assert result.success is False
        assert "strategy_summary" in result.error.lower()
    
    def test_calculate_risk_score(self, mock_ai_provider):
        """Test risk score calculation."""
        agent = OptionsGreeksAnalyst(
            name="test",
            ai_provider=mock_ai_provider,
            dependencies={},
        )
        
        greeks = {"delta": 0.6, "gamma": 0.15, "theta": -20, "vega": 120}
        metrics = {"max_profit": 100, "max_loss": -500}
        
        score = agent._calculate_risk_score(greeks, metrics)
        
        assert 0 <= score <= 10
        assert isinstance(score, float)
    
    def test_categorize_risk(self, mock_ai_provider):
        """Test risk categorization."""
        agent = OptionsGreeksAnalyst(
            name="test",
            ai_provider=mock_ai_provider,
            dependencies={},
        )
        
        assert agent._categorize_risk(2.0) == "Low"
        assert agent._categorize_risk(5.0) == "Medium"
        assert agent._categorize_risk(7.0) == "High"
        assert agent._categorize_risk(9.0) == "Very High"


class TestIVEnvironmentAnalyst:
    """Test IVEnvironmentAnalyst agent."""
    
    @pytest.mark.asyncio
    async def test_execute_success(self, mock_ai_provider, strategy_summary):
        """Test successful execution."""
        strategy_summary["legs"] = [
            {"implied_volatility": 0.25},
            {"implied_volatility": 0.30},
        ]
        strategy_summary["metadata"] = {
            "iv_rank": 75.0,
            "iv_percentile": 80.0,
            "historical_volatility": 0.20,
        }
        
        agent = IVEnvironmentAnalyst(
            name="test_iv",
            ai_provider=mock_ai_provider,
            dependencies={},
        )
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.OPTIONS_ANALYSIS,
            input_data={"strategy_summary": strategy_summary},
        )
        
        with patch.object(agent, '_call_ai', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "IV analysis report"
            
            result = await agent.execute(context)
            
            assert result.success is True
            assert "iv_score" in result.data
            assert "iv_category" in result.data
            assert "iv_data" in result.data
    
    @pytest.mark.asyncio
    async def test_execute_no_iv_data(self, mock_ai_provider):
        """Test execution with no IV data."""
        agent = IVEnvironmentAnalyst(
            name="test_iv",
            ai_provider=mock_ai_provider,
            dependencies={},
        )
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.OPTIONS_ANALYSIS,
            input_data={"strategy_summary": {}},
        )
        
        result = await agent.execute(context)
        
        assert result.success is False
        assert "IV data" in result.error

    @pytest.mark.asyncio
    async def test_execute_success_with_option_chain(self, mock_ai_provider):
        """Test execution using IV data from option chain."""
        agent = IVEnvironmentAnalyst(
            name="test_iv",
            ai_provider=mock_ai_provider,
            dependencies={},
        )

        option_chain = {
            "symbol": "AAPL",
            "calls": [{"implied_volatility": 0.25}, {"implied_volatility": 0.30}],
            "puts": [{"implied_volatility": 0.28}, {"implied_volatility": 0.27}],
        }

        context = AgentContext(
            task_id="test_chain",
            task_type=AgentType.OPTIONS_ANALYSIS,
            input_data={"strategy_summary": {}, "option_chain": option_chain},
        )

        with patch.object(agent, "_call_ai", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "IV analysis report"

            result = await agent.execute(context)

            assert result.success is True
            assert result.data.get("symbol") == "AAPL"
            assert "iv_data" in result.data
    
    def test_extract_iv_data_from_legs(self, mock_ai_provider):
        """Test IV data extraction from legs."""
        agent = IVEnvironmentAnalyst(
            name="test",
            ai_provider=mock_ai_provider,
            dependencies={},
        )
        
        strategy_summary = {
            "legs": [
                {"implied_volatility": 0.25},
                {"implied_volatility": 0.30},
            ],
        }
        
        iv_data = agent._extract_iv_data(strategy_summary, {})
        
        assert "current_iv" in iv_data
        assert iv_data["current_iv"] == 0.275  # Average of 0.25 and 0.30
        assert "iv_range" in iv_data
    
    def test_calculate_iv_score(self, mock_ai_provider):
        """Test IV score calculation."""
        agent = IVEnvironmentAnalyst(
            name="test",
            ai_provider=mock_ai_provider,
            dependencies={},
        )
        
        iv_data = {
            "iv_rank": 75.0,
            "current_iv": 0.30,
            "historical_volatility": 0.20,
        }
        
        score = agent._calculate_iv_score(iv_data)
        
        assert 0 <= score <= 10
        assert isinstance(score, float)


class TestMarketContextAnalyst:
    """Test MarketContextAnalyst agent."""
    
    @pytest.fixture
    def mock_market_data_service(self):
        """Create a mock market data service."""
        service = MagicMock()
        service.get_financial_profile.return_value = {
            "ratios": {
                "profitability": {"2024-01-01": {"ROE": 0.25}},
                "valuation": {"2024-01-01": {"PE": 30.0}},
            },
            "technical_indicators": {
                "rsi": {"2024-01-01": {"RSI": 65.0}},
            },
            "analysis": {
                "health_score": {"overall": 75, "category": "good"},
                "technical_signals": {"rsi": "neutral"},
            },
        }
        return service
    
    @pytest.mark.asyncio
    async def test_execute_success(self, mock_ai_provider, mock_market_data_service, strategy_summary):
        """Test successful execution."""
        agent = MarketContextAnalyst(
            name="test_market",
            ai_provider=mock_ai_provider,
            dependencies={"market_data_service": mock_market_data_service},
        )
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.OPTIONS_ANALYSIS,
            input_data={"strategy_summary": strategy_summary},
        )
        
        with patch.object(agent, '_call_ai', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "Market context analysis"
            
            result = await agent.execute(context)
            
            assert result.success is True
            assert "market_score" in result.data
            assert "market_category" in result.data
            mock_market_data_service.get_financial_profile.assert_called_once_with("AAPL")
    
    @pytest.mark.asyncio
    async def test_execute_no_ticker(self, mock_ai_provider, mock_market_data_service):
        """Test execution with no ticker."""
        agent = MarketContextAnalyst(
            name="test_market",
            ai_provider=mock_ai_provider,
            dependencies={"market_data_service": mock_market_data_service},
        )
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.OPTIONS_ANALYSIS,
            input_data={},
        )
        
        result = await agent.execute(context)
        
        assert result.success is False
        assert "ticker" in result.error.lower()


class TestRiskScenarioAnalyst:
    """Test RiskScenarioAnalyst agent."""
    
    @pytest.mark.asyncio
    async def test_execute_success(self, mock_ai_provider, strategy_summary):
        """Test successful execution."""
        agent = RiskScenarioAnalyst(
            name="test_risk",
            ai_provider=mock_ai_provider,
            dependencies={},
        )
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.OPTIONS_ANALYSIS,
            input_data={"strategy_summary": strategy_summary},
        )
        
        with patch.object(agent, '_call_ai', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "Risk scenario analysis"
            
            result = await agent.execute(context)
            
            assert result.success is True
            assert "risk_score" in result.data
            assert "risk_category" in result.data
            assert "max_loss" in result.data
            assert "max_profit" in result.data


class TestOptionsSynthesisAgent:
    """Test OptionsSynthesisAgent."""
    
    @pytest.mark.asyncio
    async def test_execute_success(self, mock_ai_provider, strategy_summary):
        """Test successful synthesis."""
        agent = OptionsSynthesisAgent(
            name="test_synthesis",
            ai_provider=mock_ai_provider,
            dependencies={},
        )
        
        all_results = {
            "options_greeks_analyst": {
                "analysis": "Greeks analysis",
                "risk_score": 5.0,
                "risk_category": "Medium",
            },
            "iv_environment_analyst": {
                "analysis": "IV analysis",
                "iv_score": 7.0,
                "iv_category": "Expensive",
            },
            "market_context_analyst": {
                "analysis": "Market analysis",
                "market_score": 6.0,
                "market_category": "Neutral-Bullish",
            },
            "risk_scenario_analyst": {
                "analysis": "Risk analysis",
                "risk_score": 4.0,
                "risk_category": "Medium Risk",
            },
        }
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.OPTIONS_ANALYSIS,
            input_data={
                "_all_results": all_results,
                "strategy_summary": strategy_summary,
            },
        )
        
        with patch.object(agent, '_call_ai', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "Synthesis report"
            
            result = await agent.execute(context)
            
            assert result.success is True
            assert "overall_score" in result.data
            assert "recommendation" in result.data
            assert "synthesis_metadata" in result.data
    
    @pytest.mark.asyncio
    async def test_execute_no_results(self, mock_ai_provider, strategy_summary):
        """Test execution with no previous results."""
        agent = OptionsSynthesisAgent(
            name="test_synthesis",
            ai_provider=mock_ai_provider,
            dependencies={},
        )
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.OPTIONS_ANALYSIS,
            input_data={"strategy_summary": strategy_summary},
        )
        
        result = await agent.execute(context)
        
        assert result.success is False
        assert "No previous analysis results" in result.error
    
    def test_extract_analysis_text(self, mock_ai_provider):
        """Test analysis text extraction."""
        agent = OptionsSynthesisAgent(
            name="test",
            ai_provider=mock_ai_provider,
            dependencies={},
        )
        
        # Test with valid analysis
        data = {"analysis": "Test analysis text"}
        text = agent._extract_analysis_text(data)
        assert text == "Test analysis text"
        
        # Test with long analysis (truncation)
        long_text = "x" * 1500
        data = {"analysis": long_text}
        text = agent._extract_analysis_text(data)
        assert len(text) <= 1000 + len("... (truncated)")
        assert text.endswith("... (truncated)")
        
        # Test with no analysis
        text = agent._extract_analysis_text({})
        assert text == "Analysis not available"
    
    def test_calculate_overall_score(self, mock_ai_provider):
        """Test overall score calculation."""
        agent = OptionsSynthesisAgent(
            name="test",
            ai_provider=mock_ai_provider,
            dependencies={},
        )
        
        all_results = {
            "options_greeks_analyst": {"risk_score": 5.0},
            "iv_environment_analyst": {"iv_score": 7.0},
            "market_context_analyst": {"market_score": 6.0},
            "risk_scenario_analyst": {"risk_score": 4.0},
        }
        
        score = agent._calculate_overall_score(all_results)
        
        assert 0 <= score <= 10
        assert isinstance(score, float)
