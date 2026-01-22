"""Tests for BaseAgent and core framework components."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.agents.base import (
    AgentContext,
    AgentResult,
    AgentType,
    BaseAgent,
)
from app.services.ai.base import BaseAIProvider


class MockAIProvider(BaseAIProvider):
    """Mock AI provider for testing."""
    
    async def generate_report(self, strategy_summary: dict) -> str:
        """Mock report generation."""
        return "Mock AI Analysis Report"
    
    async def generate_daily_picks(self, criteria: dict) -> list:
        """Mock daily picks generation."""
        return []


class TestAgent(BaseAgent):
    """Test agent implementation."""
    
    def _get_role_prompt(self) -> str:
        return "You are a test agent."
    
    async def execute(self, context: AgentContext) -> AgentResult:
        return AgentResult(
            agent_name=self.name,
            agent_type=self.agent_type,
            success=True,
            data={"test": "data"},
        )


@pytest.fixture
def mock_ai_provider():
    """Create a mock AI provider."""
    return MockAIProvider()


@pytest.fixture
def test_agent(mock_ai_provider):
    """Create a test agent instance."""
    return TestAgent(
        name="test_agent",
        agent_type=AgentType.CUSTOM,
        ai_provider=mock_ai_provider,
        dependencies={},
    )


@pytest.fixture
def agent_context():
    """Create a test agent context."""
    return AgentContext(
        task_id="test_task_1",
        task_type=AgentType.CUSTOM,
        input_data={"test": "input"},
    )


class TestBaseAgent:
    """Test BaseAgent functionality."""
    
    def test_agent_initialization(self, mock_ai_provider):
        """Test agent initialization."""
        agent = TestAgent(
            name="test",
            agent_type=AgentType.CUSTOM,
            ai_provider=mock_ai_provider,
            dependencies={"service": "mock"},
        )
        
        assert agent.name == "test"
        assert agent.agent_type == AgentType.CUSTOM
        assert agent.ai_provider == mock_ai_provider
        assert agent.dependencies == {"service": "mock"}
        assert agent._role_prompt == "You are a test agent."
    
    def test_get_dependency_success(self, test_agent):
        """Test getting a dependency that exists."""
        test_agent.dependencies = {"service": "mock_service"}
        service = test_agent._get_dependency("service")
        assert service == "mock_service"
    
    def test_get_dependency_not_found(self, test_agent):
        """Test getting a dependency that doesn't exist."""
        test_agent.dependencies = {}
        with pytest.raises(ValueError, match="Dependency 'service' not found"):
            test_agent._get_dependency("service")
    
    @pytest.mark.asyncio
    async def test_execute(self, test_agent, agent_context):
        """Test agent execution."""
        result = await test_agent.execute(agent_context)
        
        assert result.success is True
        assert result.agent_name == "test_agent"
        assert result.data == {"test": "data"}
    
    @pytest.mark.asyncio
    async def test_call_ai(self, test_agent, agent_context):
        """Test AI call functionality."""
        with patch.object(test_agent.ai_provider, 'generate_report', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "AI Response"
            
            response = await test_agent._call_ai(
                prompt="Test prompt",
                context=agent_context,
            )
            
            assert response == "AI Response"
            mock_generate.assert_called_once()
            call_args = mock_generate.call_args[1]
            strategy_summary = call_args["strategy_summary"]
            assert strategy_summary["_agent_analysis_request"] is True
            assert strategy_summary["_agent_prompt"] == "Test prompt"
    
    @pytest.mark.asyncio
    async def test_call_ai_with_system_prompt(self, test_agent, agent_context):
        """Test AI call with custom system prompt."""
        with patch.object(test_agent.ai_provider, 'generate_report', new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = "AI Response"
            
            response = await test_agent._call_ai(
                prompt="Test prompt",
                system_prompt="Custom system prompt",
                context=agent_context,
            )
            
            assert response == "AI Response"
            call_args = mock_generate.call_args[1]
            strategy_summary = call_args["strategy_summary"]
            assert strategy_summary["_agent_system_prompt"] == "Custom system prompt"


class TestAgentContext:
    """Test AgentContext dataclass."""
    
    def test_context_creation(self):
        """Test creating an agent context."""
        context = AgentContext(
            task_id="task_1",
            task_type=AgentType.OPTIONS_ANALYSIS,
            input_data={"symbol": "AAPL"},
        )
        
        assert context.task_id == "task_1"
        assert context.task_type == AgentType.OPTIONS_ANALYSIS
        assert context.input_data == {"symbol": "AAPL"}
        assert context.user_id is None
        assert context.metadata == {}
    
    def test_context_with_metadata(self):
        """Test context with metadata."""
        context = AgentContext(
            task_id="task_1",
            task_type=AgentType.OPTIONS_ANALYSIS,
            input_data={},
            user_id="user_123",
            metadata={"key": "value"},
        )
        
        assert context.user_id == "user_123"
        assert context.metadata == {"key": "value"}


class TestAgentResult:
    """Test AgentResult dataclass."""
    
    def test_result_creation_success(self):
        """Test creating a successful result."""
        result = AgentResult(
            agent_name="test_agent",
            agent_type=AgentType.CUSTOM,
            success=True,
            data={"key": "value"},
        )
        
        assert result.agent_name == "test_agent"
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
    
    def test_result_creation_failure(self):
        """Test creating a failed result."""
        result = AgentResult(
            agent_name="test_agent",
            agent_type=AgentType.CUSTOM,
            success=False,
            data={},
            error="Test error",
        )
        
        assert result.success is False
        assert result.error == "Test error"
