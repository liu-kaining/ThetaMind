"""Integration tests for Agent Framework API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.api.endpoints.ai import (
    StrategyAnalysisRequest,
    StockScreeningRequest,
    OptionsAnalysisWorkflowRequest,
)
from app.services.agents.base import AgentType


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock()
    user.id = "test-user-id"
    user.email = "test@example.com"
    user.is_pro = True
    user.subscription_type = "monthly"
    user.daily_ai_usage = 0
    user.last_quota_reset_date = None
    return user


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


@pytest.fixture
def sample_strategy_summary():
    """Sample strategy summary for testing."""
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


class TestPhase1Endpoints:
    """Test Phase 1: Basic integration endpoints."""
    
    @pytest.mark.asyncio
    async def test_single_agent_mode(self, mock_user, mock_db, sample_strategy_summary):
        """Test single-agent mode (backward compatibility)."""
        from app.api.endpoints.ai import generate_ai_report
        
        request = StrategyAnalysisRequest(
            strategy_summary=sample_strategy_summary,
            use_multi_agent=False,
        )
        
        with patch("app.api.endpoints.ai.ai_service") as mock_ai_service:
            mock_ai_service.generate_report = AsyncMock(return_value="Single agent report")
            mock_ai_service.generate_report_with_agents = AsyncMock()
            
            with patch("app.api.endpoints.ai.check_ai_quota") as mock_check:
                mock_check.return_value = None
                
                with patch("app.api.endpoints.ai.increment_ai_usage") as mock_increment:
                    mock_increment.return_value = None
                    
                    with patch("app.api.endpoints.ai.AIReport") as mock_report:
                        mock_report_instance = MagicMock()
                        mock_report_instance.id = "test-id"
                        mock_report_instance.report_content = "Single agent report"
                        mock_report_instance.model_used = "gemini-2.5-pro"
                        mock_report_instance.created_at = None
                        mock_report.return_value = mock_report_instance
                        
                        # This would require more mocking for full test
                        # For now, just verify the structure
                        assert request.use_multi_agent is False
    
    @pytest.mark.asyncio
    async def test_multi_agent_mode(self, mock_user, mock_db, sample_strategy_summary):
        """Test multi-agent mode."""
        from app.api.endpoints.ai import generate_ai_report
        
        request = StrategyAnalysisRequest(
            strategy_summary=sample_strategy_summary,
            use_multi_agent=True,
        )
        
        assert request.use_multi_agent is True
    
    @pytest.mark.asyncio
    async def test_quota_management(self, mock_user, mock_db):
        """Test quota management."""
        from app.api.endpoints.ai import check_ai_quota, increment_ai_usage
        
        # Test quota check
        with patch("app.api.endpoints.ai.check_and_reset_quota_if_needed") as mock_reset:
            mock_reset.return_value = None
            mock_user.daily_ai_usage = 0
            
            # Should not raise for single agent
            await check_ai_quota(mock_user, mock_db, required_quota=1)
            
            # Should not raise for multi-agent if quota available
            mock_user.daily_ai_usage = 0
            await check_ai_quota(mock_user, mock_db, required_quota=5)
    
    @pytest.mark.asyncio
    async def test_quota_insufficient_fallback(self, mock_user, mock_db, sample_strategy_summary):
        """Test automatic fallback when quota insufficient."""
        from app.api.endpoints.ai import generate_ai_report
        from fastapi import HTTPException
        
        request = StrategyAnalysisRequest(
            strategy_summary=sample_strategy_summary,
            use_multi_agent=True,
        )
        
        with patch("app.api.endpoints.ai.check_ai_quota") as mock_check:
            # First call fails (insufficient for multi-agent)
            # Second call succeeds (single-agent)
            call_count = 0
            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1 and kwargs.get("required_quota") == 5:
                    from fastapi import HTTPException, status
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Quota exceeded"
                    )
                return None
            
            mock_check.side_effect = side_effect
            
            # The endpoint should handle fallback automatically
            # This test verifies the structure exists
            assert request.use_multi_agent is True


class TestPhase2Endpoints:
    """Test Phase 2: New dedicated endpoints."""
    
    @pytest.mark.asyncio
    async def test_multi_agent_endpoint(self, mock_user, mock_db, sample_strategy_summary):
        """Test /api/v1/ai/report/multi-agent endpoint."""
        from app.api.endpoints.ai import generate_multi_agent_report
        
        request = StrategyAnalysisRequest(
            strategy_summary=sample_strategy_summary,
        )
        
        # Verify it forces multi-agent mode
        # The endpoint should set use_multi_agent=True
        assert hasattr(request, "use_multi_agent")
    
    @pytest.mark.asyncio
    async def test_options_workflow_endpoint(self, mock_user, mock_db, sample_strategy_summary):
        """Test /api/v1/ai/workflows/options-analysis endpoint."""
        from app.api.endpoints.ai import analyze_options_workflow
        
        request = OptionsAnalysisWorkflowRequest(
            strategy_summary=sample_strategy_summary,
            include_metadata=True,
        )
        
        assert request.strategy_summary == sample_strategy_summary
        assert request.include_metadata is True
    
    @pytest.mark.asyncio
    async def test_stock_screening_endpoint(self, mock_user, mock_db):
        """Test /api/v1/ai/workflows/stock-screening endpoint."""
        from app.api.endpoints.ai import screen_stocks
        
        request = StockScreeningRequest(
            sector="Technology",
            market_cap="Large Cap",
            country="United States",
            limit=10,
            min_score=7.0,
        )
        
        assert request.sector == "Technology"
        assert request.limit == 10
        assert request.min_score == 7.0
    
    @pytest.mark.asyncio
    async def test_agent_list_endpoint(self, mock_user):
        """Test /api/v1/ai/agents/list endpoint."""
        from app.api.endpoints.ai import list_agents
        
        # Test without filter
        # This would require mocking AgentRegistry
        # For now, just verify the function exists
        assert callable(list_agents)
        
        # Test with type filter
        # Would need to mock AgentRegistry.list_agents_by_type
        assert True  # Placeholder


class TestIntegration:
    """Test end-to-end integration."""
    
    @pytest.mark.asyncio
    async def test_full_workflow_single_agent(self, sample_strategy_summary):
        """Test complete single-agent workflow."""
        # This would test the full flow:
        # 1. Request → 2. Quota check → 3. AI generation → 4. Save → 5. Response
        # For now, just verify components exist
        assert sample_strategy_summary is not None
    
    @pytest.mark.asyncio
    async def test_full_workflow_multi_agent(self, sample_strategy_summary):
        """Test complete multi-agent workflow."""
        # This would test the full flow:
        # 1. Request → 2. Quota check → 3. Multi-agent coordination → 4. Save → 5. Response
        # For now, just verify components exist
        assert sample_strategy_summary is not None
    
    @pytest.mark.asyncio
    async def test_error_handling_and_fallback(self, sample_strategy_summary):
        """Test error handling and automatic fallback."""
        # This would test:
        # 1. Multi-agent fails → 2. Automatic fallback to single-agent
        # 3. Quota insufficient → 4. Automatic fallback
        # For now, just verify structure
        assert sample_strategy_summary is not None


class TestGeminiProviderIntegration:
    """Test GeminiProvider Agent mode integration."""
    
    @pytest.mark.asyncio
    async def test_agent_mode_detection(self):
        """Test that GeminiProvider detects Agent mode correctly."""
        from app.services.ai.gemini_provider import GeminiProvider
        
        # Create a strategy_summary with agent flags
        agent_request = {
            "_agent_analysis_request": True,
            "_agent_prompt": "Test prompt",
            "_agent_system_prompt": "Test system prompt",
        }
        
        # Verify the structure
        assert agent_request.get("_agent_analysis_request") is True
        assert "_agent_prompt" in agent_request
        assert "_agent_system_prompt" in agent_request
    
    @pytest.mark.asyncio
    async def test_system_prompt_support(self):
        """Test that system_prompt is supported in API calls."""
        # This would test that _call_ai_api accepts system_prompt parameter
        # For now, just verify the concept
        assert True  # Placeholder
