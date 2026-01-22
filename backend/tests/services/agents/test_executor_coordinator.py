"""Tests for AgentExecutor and AgentCoordinator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.agents.base import AgentContext, AgentResult, AgentType
from app.services.agents.executor import AgentExecutor
from app.services.agents.coordinator import AgentCoordinator
from app.services.agents.registry import AgentRegistry
from app.services.ai.base import BaseAIProvider


class MockAIProvider(BaseAIProvider):
    """Mock AI provider for testing."""
    
    async def generate_report(self, strategy_summary: dict) -> str:
        return "Mock AI Analysis"
    
    async def generate_daily_picks(self, criteria: dict) -> list:
        return []


class MockAgent:
    """Mock agent for testing."""
    
    def __init__(self, name, agent_type, ai_provider, dependencies):
        self.name = name
        self.agent_type = agent_type
        self.ai_provider = ai_provider
        self.dependencies = dependencies
        self._role_prompt = "Mock role prompt"
    
    async def execute(self, context):
        return AgentResult(
            agent_name=self.name,
            agent_type=self.agent_type,
            success=True,
            data={"result": f"Result from {self.name}"},
        )


@pytest.fixture
def mock_ai_provider():
    """Create a mock AI provider."""
    return MockAIProvider()


@pytest.fixture
def executor(mock_ai_provider):
    """Create an executor instance."""
    return AgentExecutor(
        ai_provider=mock_ai_provider,
        dependencies={},
    )


@pytest.fixture
def coordinator(executor):
    """Create a coordinator instance."""
    return AgentCoordinator(executor)


@pytest.fixture
def registered_agent(mock_ai_provider):
    """Register a mock agent for testing."""
    AgentRegistry.register("mock_agent", MockAgent, AgentType.CUSTOM)
    yield
    # Cleanup
    if "mock_agent" in AgentRegistry._agents:
        del AgentRegistry._agents["mock_agent"]


class TestAgentExecutor:
    """Test AgentExecutor functionality."""
    
    @pytest.mark.asyncio
    async def test_execute_single_success(self, executor, registered_agent):
        """Test single agent execution."""
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.CUSTOM,
            input_data={"test": "data"},
        )
        
        result = await executor.execute_single("mock_agent", context)
        
        assert result.success is True
        assert result.agent_name == "mock_agent"
        assert "result" in result.data
        assert result.execution_time_ms is not None
    
    @pytest.mark.asyncio
    async def test_execute_single_with_progress_callback(self, executor, registered_agent):
        """Test single execution with progress callback."""
        progress_calls = []
        
        def progress_callback(percent, message):
            progress_calls.append((percent, message))
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.CUSTOM,
            input_data={},
        )
        
        result = await executor.execute_single(
            "mock_agent",
            context,
            progress_callback=progress_callback,
        )
        
        assert result.success is True
        assert len(progress_calls) > 0
        # Check that progress reached 100%
        assert any(p[0] == 100 for p in progress_calls)
    
    @pytest.mark.asyncio
    async def test_execute_single_agent_not_found(self, executor):
        """Test execution with non-existent agent."""
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.CUSTOM,
            input_data={},
        )
        
        with pytest.raises(Exception):  # Should raise KeyError or similar
            await executor.execute_single("non_existent_agent", context)
    
    @pytest.mark.asyncio
    async def test_execute_parallel(self, executor, registered_agent):
        """Test parallel agent execution."""
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.CUSTOM,
            input_data={},
        )
        
        # Register multiple agents
        AgentRegistry.register("mock_agent_2", MockAgent, AgentType.CUSTOM)
        
        try:
            results = await executor.execute_parallel(
                ["mock_agent", "mock_agent_2"],
                context,
            )
            
            assert len(results) == 2
            assert "mock_agent" in results
            assert "mock_agent_2" in results
            assert results["mock_agent"].success is True
            assert results["mock_agent_2"].success is True
        finally:
            if "mock_agent_2" in AgentRegistry._agents:
                del AgentRegistry._agents["mock_agent_2"]
    
    @pytest.mark.asyncio
    async def test_execute_parallel_with_progress(self, executor, registered_agent):
        """Test parallel execution with progress callback."""
        progress_calls = []
        
        def progress_callback(percent, message):
            progress_calls.append((percent, message))
        
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.CUSTOM,
            input_data={},
        )
        
        results = await executor.execute_parallel(
            ["mock_agent"],
            context,
            progress_callback=progress_callback,
        )
        
        assert len(results) == 1
        assert len(progress_calls) > 0
    
    @pytest.mark.asyncio
    async def test_execute_sequential(self, executor, registered_agent):
        """Test sequential agent execution."""
        context = AgentContext(
            task_id="test_1",
            task_type=AgentType.CUSTOM,
            input_data={},
        )
        
        results = await executor.execute_sequential(
            ["mock_agent", "mock_agent"],
            context,
        )
        
        assert len(results) == 2
        assert all(r.success for r in results)
        # Check that results are added to context
        assert "_agent_result_mock_agent" in context.input_data
    
    @pytest.mark.asyncio
    async def test_execute_sequential_stop_on_error(self, executor, registered_agent):
        """Test sequential execution with stop_on_error."""
        # Create a failing agent
        class FailingAgent(MockAgent):
            async def execute(self, context):
                return AgentResult(
                    agent_name=self.name,
                    agent_type=self.agent_type,
                    success=False,
                    data={},
                    error="Test error",
                )
        
        AgentRegistry.register("failing_agent", FailingAgent, AgentType.CUSTOM)
        
        try:
            context = AgentContext(
                task_id="test_1",
                task_type=AgentType.CUSTOM,
                input_data={},
            )
            
            results = await executor.execute_sequential(
                ["mock_agent", "failing_agent", "mock_agent"],
                context,
                stop_on_error=True,
            )
            
            # Should stop after first failure
            assert len(results) == 2
            assert results[0].success is True
            assert results[1].success is False
        finally:
            if "failing_agent" in AgentRegistry._agents:
                del AgentRegistry._agents["failing_agent"]


class TestAgentCoordinator:
    """Test AgentCoordinator functionality."""
    
    @pytest.mark.asyncio
    async def test_coordinate_options_analysis(self, coordinator, mock_ai_provider):
        """Test options analysis coordination."""
        # Mock the agents
        with patch.object(coordinator.executor, 'execute_parallel') as mock_parallel, \
             patch.object(coordinator.executor, 'execute_single') as mock_single:
            
            # Setup mocks
            mock_parallel.return_value = {
                "options_greeks_analyst": AgentResult(
                    agent_name="options_greeks_analyst",
                    agent_type=AgentType.OPTIONS_ANALYSIS,
                    success=True,
                    data={"analysis": "Greeks analysis"},
                ),
                "iv_environment_analyst": AgentResult(
                    agent_name="iv_environment_analyst",
                    agent_type=AgentType.OPTIONS_ANALYSIS,
                    success=True,
                    data={"analysis": "IV analysis"},
                ),
                "market_context_analyst": AgentResult(
                    agent_name="market_context_analyst",
                    agent_type=AgentType.OPTIONS_ANALYSIS,
                    success=True,
                    data={"analysis": "Market analysis"},
                ),
            }
            
            mock_single.side_effect = [
                AgentResult(
                    agent_name="risk_scenario_analyst",
                    agent_type=AgentType.OPTIONS_ANALYSIS,
                    success=True,
                    data={"analysis": "Risk analysis"},
                ),
                AgentResult(
                    agent_name="options_synthesis_agent",
                    agent_type=AgentType.OPTIONS_ANALYSIS,
                    success=True,
                    data={"analysis": "Synthesis report"},
                ),
            ]
            
            strategy_summary = {
                "symbol": "AAPL",
                "strategy_name": "Iron Condor",
                "portfolio_greeks": {"delta": 0.05},
                "strategy_metrics": {"max_profit": 500},
            }
            
            result = await coordinator.coordinate_options_analysis(strategy_summary)
            
            assert "parallel_analysis" in result
            assert "risk_analysis" in result
            assert "synthesis" in result
            assert "all_results" in result
            assert "metadata" in result
            
            # Verify execution flow
            assert mock_parallel.call_count == 1
            assert mock_single.call_count == 2
    
    @pytest.mark.asyncio
    async def test_coordinate_stock_screening(self, coordinator):
        """Test stock screening coordination."""
        # Mock the agents
        with patch.object(coordinator.executor, 'execute_single') as mock_single, \
             patch.object(coordinator.executor, 'execute_parallel') as mock_parallel:
            
            # Phase 1: Screening
            mock_single.side_effect = [
                AgentResult(
                    agent_name="stock_screening_agent",
                    agent_type=AgentType.STOCK_SCREENING,
                    success=True,
                    data={
                        "candidates": [
                            {"symbol": "AAPL"},
                            {"symbol": "MSFT"},
                        ],
                    },
                ),
                # Phase 3: Ranking
                AgentResult(
                    agent_name="stock_ranking_agent",
                    agent_type=AgentType.RECOMMENDATION,
                    success=True,
                    data={
                        "ranked_stocks": [
                            {"symbol": "AAPL", "rank": 1, "composite_score": 8.5},
                            {"symbol": "MSFT", "rank": 2, "composite_score": 7.5},
                        ],
                    },
                ),
            ]
            
            # Phase 2: Parallel analysis (for each candidate)
            mock_parallel.return_value = {
                "fundamental_analyst": AgentResult(
                    agent_name="fundamental_analyst",
                    agent_type=AgentType.FUNDAMENTAL_ANALYSIS,
                    success=True,
                    data={"health_score": 75},
                ),
                "technical_analyst": AgentResult(
                    agent_name="technical_analyst",
                    agent_type=AgentType.TECHNICAL_ANALYSIS,
                    success=True,
                    data={"technical_score": 7.0},
                ),
            }
            
            criteria = {
                "sector": "Technology",
                "market_cap": "Large Cap",
                "country": "United States",
                "limit": 10,
            }
            
            result = await coordinator.coordinate_stock_screening(criteria)
            
            assert len(result) == 2
            assert result[0]["symbol"] == "AAPL"
            assert result[0]["rank"] == 1
            assert result[1]["symbol"] == "MSFT"
            assert result[1]["rank"] == 2
    
    @pytest.mark.asyncio
    async def test_coordinate_stock_screening_no_candidates(self, coordinator):
        """Test stock screening with no candidates."""
        with patch.object(coordinator.executor, 'execute_single') as mock_single:
            mock_single.return_value = AgentResult(
                agent_name="stock_screening_agent",
                agent_type=AgentType.STOCK_SCREENING,
                success=True,
                data={"candidates": []},
            )
            
            criteria = {"sector": "Technology"}
            result = await coordinator.coordinate_stock_screening(criteria)
            
            assert result == []
    
    @pytest.mark.asyncio
    async def test_coordinate_stock_screening_failure(self, coordinator):
        """Test stock screening when screening fails."""
        with patch.object(coordinator.executor, 'execute_single') as mock_single:
            mock_single.return_value = AgentResult(
                agent_name="stock_screening_agent",
                agent_type=AgentType.STOCK_SCREENING,
                success=False,
                data={},
                error="Screening failed",
            )
            
            criteria = {"sector": "Technology"}
            result = await coordinator.coordinate_stock_screening(criteria)
            
            assert result == []
