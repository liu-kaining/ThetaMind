"""Tests for Stock Screening and Ranking Agents."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.agents.base import AgentContext, AgentType
from app.services.agents.stock_screening_agent import StockScreeningAgent
from app.services.agents.stock_ranking_agent import StockRankingAgent
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
    service.search_tickers.return_value = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
    return service


class TestStockScreeningAgent:
    """Test StockScreeningAgent."""
    
    @pytest.mark.asyncio
    async def test_execute_success(self, mock_ai_provider, mock_market_data_service):
        """Test successful execution."""
        agent = StockScreeningAgent(
            name="test_screening",
            ai_provider=mock_ai_provider,
            dependencies={"market_data_service": mock_market_data_service},
        )
        
        criteria = {
            "sector": "Technology",
            "market_cap": "Large Cap",
            "country": "United States",
            "limit": 5,
        }
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.STOCK_SCREENING,
            input_data={"criteria": criteria},
        )
        
        result = await agent.execute(context)
        
        assert result.success is True
        assert "candidates" in result.data
        assert len(result.data["candidates"]) == 5
        assert result.data["candidates"][0]["symbol"] == "AAPL"
        assert "initial_score" in result.data["candidates"][0]
        mock_market_data_service.search_tickers.assert_called_once_with(
            sector="Technology",
            industry=None,
            market_cap="Large Cap",
            country="United States",
        )
    
    @pytest.mark.asyncio
    async def test_execute_with_limit(self, mock_ai_provider, mock_market_data_service):
        """Test execution with limit applied."""
        agent = StockScreeningAgent(
            name="test_screening",
            ai_provider=mock_ai_provider,
            dependencies={"market_data_service": mock_market_data_service},
        )
        
        criteria = {
            "sector": "Technology",
            "limit": 3,
        }
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.STOCK_SCREENING,
            input_data={"criteria": criteria},
        )
        
        result = await agent.execute(context)
        
        assert result.success is True
        assert len(result.data["candidates"]) == 3
    
    @pytest.mark.asyncio
    async def test_execute_no_criteria(self, mock_ai_provider, mock_market_data_service):
        """Test execution with no criteria."""
        agent = StockScreeningAgent(
            name="test_screening",
            ai_provider=mock_ai_provider,
            dependencies={"market_data_service": mock_market_data_service},
        )
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.STOCK_SCREENING,
            input_data={},
        )
        
        result = await agent.execute(context)
        
        assert result.success is False
        assert "criteria" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_execute_no_results(self, mock_ai_provider):
        """Test execution when no stocks are found."""
        service = MagicMock()
        service.search_tickers.return_value = []
        
        agent = StockScreeningAgent(
            name="test_screening",
            ai_provider=mock_ai_provider,
            dependencies={"market_data_service": service},
        )
        
        criteria = {"sector": "Technology"}
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.STOCK_SCREENING,
            input_data={"criteria": criteria},
        )
        
        result = await agent.execute(context)
        
        assert result.success is True
        assert result.data["candidates"] == []
        assert result.data["total_found"] == 0


class TestStockRankingAgent:
    """Test StockRankingAgent."""
    
    @pytest.mark.asyncio
    async def test_execute_success(self, mock_ai_provider):
        """Test successful execution."""
        agent = StockRankingAgent(
            name="test_ranking",
            ai_provider=mock_ai_provider,
            dependencies={},
        )
        
        analysis_results = [
            {
                "candidate": {"symbol": "AAPL"},
                "analysis": {
                    "fundamental_analyst": {
                        "health_score": 80,
                    },
                    "technical_analyst": {
                        "technical_score": 7.5,
                    },
                },
            },
            {
                "candidate": {"symbol": "MSFT"},
                "analysis": {
                    "fundamental_analyst": {
                        "health_score": 70,
                    },
                    "technical_analyst": {
                        "technical_score": 6.5,
                    },
                },
            },
        ]
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.RECOMMENDATION,
            input_data={"analysis_results": analysis_results},
        )
        
        with patch.object(agent, '_call_ai', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "Ranking analysis report"
            
            result = await agent.execute(context)
            
            assert result.success is True
            assert "ranked_stocks" in result.data
            assert "top_recommendations" in result.data
            assert len(result.data["ranked_stocks"]) == 2
            # AAPL should rank higher (higher scores)
            assert result.data["ranked_stocks"][0]["symbol"] == "AAPL"
            assert result.data["ranked_stocks"][0]["rank"] == 1
            assert result.data["ranked_stocks"][1]["symbol"] == "MSFT"
            assert result.data["ranked_stocks"][1]["rank"] == 2
    
    @pytest.mark.asyncio
    async def test_execute_no_analysis_results(self, mock_ai_provider):
        """Test execution with no analysis results."""
        agent = StockRankingAgent(
            name="test_ranking",
            ai_provider=mock_ai_provider,
            dependencies={},
        )
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.RECOMMENDATION,
            input_data={},
        )
        
        result = await agent.execute(context)
        
        assert result.success is False
        assert "analysis_results" in result.error.lower()
    
    def test_calculate_composite_scores(self, mock_ai_provider):
        """Test composite score calculation."""
        agent = StockRankingAgent(
            name="test",
            ai_provider=mock_ai_provider,
            dependencies={},
        )
        
        analysis_results = [
            {
                "candidate": {"symbol": "AAPL"},
                "analysis": {
                    "fundamental_analyst": {"health_score": 80},
                    "technical_analyst": {"technical_score": 7.5},
                },
            },
            {
                "candidate": {"symbol": "MSFT"},
                "analysis": {
                    "fundamental_analyst": {"health_score": 70},
                    "technical_analyst": {"technical_score": 6.5},
                },
            },
        ]
        
        ranked = agent._calculate_composite_scores(analysis_results)
        
        assert len(ranked) == 2
        assert ranked[0]["symbol"] == "AAPL"
        assert ranked[0]["composite_score"] > ranked[1]["composite_score"]
        assert ranked[0]["rank"] == 1
        assert ranked[1]["rank"] == 2
    
    def test_calculate_composite_scores_missing_data(self, mock_ai_provider):
        """Test composite score calculation with missing data."""
        agent = StockRankingAgent(
            name="test",
            ai_provider=mock_ai_provider,
            dependencies={},
        )
        
        analysis_results = [
            {
                "candidate": {"symbol": "AAPL"},
                "analysis": {
                    # Missing scores
                },
            },
        ]
        
        ranked = agent._calculate_composite_scores(analysis_results)
        
        assert len(ranked) == 1
        assert ranked[0]["composite_score"] == 5.0  # Default neutral score
        assert ranked[0]["rank"] == 1
