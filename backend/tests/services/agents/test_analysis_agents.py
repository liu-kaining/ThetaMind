"""Tests for Fundamental and Technical Analysis Agents."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.agents.base import AgentContext, AgentType
from app.services.agents.fundamental_analyst import FundamentalAnalyst
from app.services.agents.technical_analyst import TechnicalAnalyst
from app.services.ai.base import BaseAIProvider


class MockAIProvider(BaseAIProvider):
    """Mock AI provider for testing."""
    
    async def generate_report(self, strategy_summary: dict) -> str:
        return "Mock AI Analysis"
    
    async def generate_daily_picks(self, criteria: dict) -> list:
        return []


@pytest.fixture
def mock_ai_provider():
    """Create a mock AI provider."""
    return MockAIProvider()


@pytest.fixture
def mock_market_data_service():
    """Create a mock market data service."""
    service = MagicMock()
    
    # Mock financial profile for fundamental analysis
    service.get_financial_profile.return_value = {
        "ticker": "AAPL",
        "ratios": {
            "profitability": {
                "2024-01-01": {
                    "ROE": 0.25,
                    "ROA": 0.15,
                    "Net Profit Margin": 0.20,
                }
            },
            "valuation": {
                "2024-01-01": {
                    "PE": 30.0,
                    "PB": 5.0,
                }
            },
        },
        "valuation": {
            "dcf": {"value": 150.0},
            "ddm": {"value": 145.0},
        },
        "financial_statements": {
            "income": "Available",
            "balance": "Available",
        },
        "dupont_analysis": {
            "standard": {"ROE": 0.25},
        },
        "technical_indicators": {
            "rsi": {"2024-01-01": {"RSI": 65.0}},
            "macd": {"2024-01-01": {"MACD": 1.5}},
            "sma": {"2024-01-01": {"SMA_20": 150.0}},
            "adx": {"2024-01-01": {"ADX": 25.0}},
        },
        "analysis": {
            "health_score": {"overall": 75, "category": "good"},
            "technical_signals": {
                "rsi": "neutral",
                "macd": "bullish",
            },
        },
    }
    
    # Mock technical chart generation
    service.generate_technical_chart.return_value = "data:image/png;base64,..."
    
    return service


class TestFundamentalAnalyst:
    """Test FundamentalAnalyst agent."""
    
    @pytest.mark.asyncio
    async def test_execute_success(self, mock_ai_provider, mock_market_data_service):
        """Test successful execution."""
        agent = FundamentalAnalyst(
            name="test_fundamental",
            ai_provider=mock_ai_provider,
            dependencies={"market_data_service": mock_market_data_service},
        )
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.FUNDAMENTAL_ANALYSIS,
            input_data={"ticker": "AAPL"},
        )
        
        with patch.object(agent, '_call_ai', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "Fundamental analysis report"
            
            result = await agent.execute(context)
            
            assert result.success is True
            assert result.agent_name == "test_fundamental"
            assert "analysis" in result.data
            assert "health_score" in result.data
            assert "health_category" in result.data
            assert result.data["ticker"] == "AAPL"
            mock_market_data_service.get_financial_profile.assert_called_once_with("AAPL")
    
    @pytest.mark.asyncio
    async def test_execute_no_ticker(self, mock_ai_provider, mock_market_data_service):
        """Test execution with no ticker."""
        agent = FundamentalAnalyst(
            name="test_fundamental",
            ai_provider=mock_ai_provider,
            dependencies={"market_data_service": mock_market_data_service},
        )
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.FUNDAMENTAL_ANALYSIS,
            input_data={},
        )
        
        result = await agent.execute(context)
        
        assert result.success is False
        assert "ticker" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_execute_profile_fetch_failure(self, mock_ai_provider):
        """Test execution when profile fetch fails."""
        service = MagicMock()
        service.get_financial_profile.return_value = None
        
        agent = FundamentalAnalyst(
            name="test_fundamental",
            ai_provider=mock_ai_provider,
            dependencies={"market_data_service": service},
        )
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.FUNDAMENTAL_ANALYSIS,
            input_data={"ticker": "INVALID"},
        )
        
        result = await agent.execute(context)
        
        assert result.success is False
        assert "Failed to fetch" in result.error
    
    def test_format_ratios(self, mock_ai_provider, mock_market_data_service):
        """Test ratio formatting."""
        agent = FundamentalAnalyst(
            name="test",
            ai_provider=mock_ai_provider,
            dependencies={"market_data_service": mock_market_data_service},
        )
        
        ratios = {
            "profitability": {
                "2024-01-01": {"ROE": 0.25, "ROA": 0.15},
            },
        }
        
        formatted = agent._format_ratios(ratios)
        assert "PROFITABILITY" in formatted
        assert "ROE" in formatted
    
    def test_categorize_health(self, mock_ai_provider, mock_market_data_service):
        """Test health categorization."""
        agent = FundamentalAnalyst(
            name="test",
            ai_provider=mock_ai_provider,
            dependencies={"market_data_service": mock_market_data_service},
        )
        
        assert agent._categorize_health(85) == "Excellent"
        assert agent._categorize_health(70) == "Good"
        assert agent._categorize_health(50) == "Fair"
        assert agent._categorize_health(30) == "Poor"


class TestTechnicalAnalyst:
    """Test TechnicalAnalyst agent."""
    
    @pytest.mark.asyncio
    async def test_execute_success(self, mock_ai_provider, mock_market_data_service):
        """Test successful execution."""
        agent = TechnicalAnalyst(
            name="test_technical",
            ai_provider=mock_ai_provider,
            dependencies={"market_data_service": mock_market_data_service},
        )
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.TECHNICAL_ANALYSIS,
            input_data={"ticker": "AAPL"},
        )
        
        with patch.object(agent, '_call_ai', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "Technical analysis report"
            
            result = await agent.execute(context)
            
            assert result.success is True
            assert result.agent_name == "test_technical"
            assert "analysis" in result.data
            assert "technical_score" in result.data
            assert "technical_category" in result.data
            assert result.data["ticker"] == "AAPL"
            mock_market_data_service.get_financial_profile.assert_called_once_with("AAPL")
    
    @pytest.mark.asyncio
    async def test_execute_with_chart(self, mock_ai_provider, mock_market_data_service):
        """Test execution with chart generation."""
        agent = TechnicalAnalyst(
            name="test_technical",
            ai_provider=mock_ai_provider,
            dependencies={"market_data_service": mock_market_data_service},
        )
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.TECHNICAL_ANALYSIS,
            input_data={"ticker": "AAPL"},
        )
        
        with patch.object(agent, '_call_ai', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "Technical analysis report"
            
            result = await agent.execute(context)
            
            assert result.success is True
            assert "chart" in result.data
            mock_market_data_service.generate_technical_chart.assert_called_once_with("AAPL", indicator="rsi")
    
    @pytest.mark.asyncio
    async def test_execute_chart_generation_failure(self, mock_ai_provider, mock_market_data_service):
        """Test execution when chart generation fails."""
        mock_market_data_service.generate_technical_chart.side_effect = Exception("Chart error")
        
        agent = TechnicalAnalyst(
            name="test_technical",
            ai_provider=mock_ai_provider,
            dependencies={"market_data_service": mock_market_data_service},
        )
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.TECHNICAL_ANALYSIS,
            input_data={"ticker": "AAPL"},
        )
        
        with patch.object(agent, '_call_ai', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "Technical analysis report"
            
            result = await agent.execute(context)
            
            # Should still succeed even if chart fails
            assert result.success is True
            assert result.data.get("chart") is None
    
    def test_get_latest_value(self, mock_ai_provider, mock_market_data_service):
        """Test getting latest value from time-series data."""
        agent = TechnicalAnalyst(
            name="test",
            ai_provider=mock_ai_provider,
            dependencies={"market_data_service": mock_market_data_service},
        )
        
        # Test with simple dict
        data = {"2024-01-01": 65.0}
        value = agent._get_latest_value(data)
        assert value == 65.0
        
        # Test with nested dict
        data = {"2024-01-01": {"RSI": 65.0}}
        value = agent._get_latest_value(data)
        assert value == 65.0
        
        # Test with invalid data
        value = agent._get_latest_value({})
        assert value is None
    
    def test_calculate_technical_score(self, mock_ai_provider, mock_market_data_service):
        """Test technical score calculation."""
        agent = TechnicalAnalyst(
            name="test",
            ai_provider=mock_ai_provider,
            dependencies={"market_data_service": mock_market_data_service},
        )
        
        technical_indicators = {
            "rsi": {"2024-01-01": {"RSI": 35.0}},  # Oversold
        }
        analysis = {
            "technical_signals": {"rsi": "oversold"},
        }
        
        score = agent._calculate_technical_score(technical_indicators, analysis)
        
        assert 0 <= score <= 10
        assert isinstance(score, float)
        # Oversold should increase score
        assert score > 5.0
    
    def test_categorize_technical(self, mock_ai_provider, mock_market_data_service):
        """Test technical categorization."""
        agent = TechnicalAnalyst(
            name="test",
            ai_provider=mock_ai_provider,
            dependencies={"market_data_service": mock_market_data_service},
        )
        
        assert agent._categorize_technical(8.0) == "Bullish"
        assert agent._categorize_technical(6.0) == "Neutral-Bullish"
        assert agent._categorize_technical(4.0) == "Neutral-Bearish"
        assert agent._categorize_technical(2.0) == "Bearish"
