"""Base Agent Framework - Core abstractions for all agents."""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from app.services.ai.base import BaseAIProvider

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Agent type enumeration.
    
    Defines the different types of agents in the system.
    Each agent type corresponds to a specific analysis domain.
    """
    OPTIONS_ANALYSIS = "options_analysis"
    FUNDAMENTAL_ANALYSIS = "fundamental_analysis"
    TECHNICAL_ANALYSIS = "technical_analysis"
    STOCK_SCREENING = "stock_screening"
    RECOMMENDATION = "recommendation"
    CUSTOM = "custom"


@dataclass
class AgentContext:
    """Agent execution context.
    
    Contains all information needed for an agent to execute its task.
    
    Attributes:
        task_id: Unique identifier for this task
        task_type: Type of task (AgentType enum)
        input_data: Input data dictionary for the agent
        user_id: Optional user ID (for user-specific operations)
        metadata: Additional metadata dictionary
    """
    task_id: str
    task_type: AgentType
    input_data: Dict[str, Any]
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Agent execution result.
    
    Standardized result structure for all agents.
    
    Attributes:
        agent_name: Name of the agent that produced this result
        agent_type: Type of agent
        success: Whether the execution was successful
        data: Result data dictionary
        error: Error message if execution failed
        execution_time_ms: Execution time in milliseconds
        timestamp: When the result was generated
    """
    agent_name: str
    agent_type: AgentType
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BaseAgent(ABC):
    """Abstract base class for all agents.
    
    All agents must inherit from this class and implement:
    - _get_role_prompt(): Return the role definition prompt
    - execute(): Execute the agent's core logic
    
    Agents receive:
    - AI provider for LLM calls
    - Dependencies (services like MarketDataService, TigerService)
    
    Example:
        class MyAgent(BaseAgent):
            def _get_role_prompt(self) -> str:
                return "You are a financial analyst..."
            
            async def execute(self, context: AgentContext) -> AgentResult:
                # Agent logic here
                return AgentResult(...)
    """
    
    def __init__(
        self,
        name: str,
        agent_type: AgentType,
        ai_provider: BaseAIProvider,
        dependencies: Optional[Dict[str, Any]] = None,
    ):
        """Initialize agent.
        
        Args:
            name: Agent name (unique identifier)
            agent_type: Type of agent (AgentType enum)
            ai_provider: AI provider instance for LLM calls
            dependencies: Dictionary of dependency services
                (e.g., {"market_data_service": MarketDataService()})
        """
        self.name = name
        self.agent_type = agent_type
        self.ai_provider = ai_provider
        self.dependencies = dependencies or {}
        self._role_prompt = self._get_role_prompt()
        
        logger.debug(f"Initialized agent: {name} (type: {agent_type})")
    
    @abstractmethod
    def _get_role_prompt(self) -> str:
        """Get the role definition prompt for this agent.
        
        This prompt defines the agent's role, expertise, and behavior.
        It will be used as the system prompt for all AI calls.
        
        Returns:
            Role definition prompt string
        """
        pass
    
    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """Execute the agent's core logic.
        
        This is the main entry point for agent execution.
        Subclasses must implement this method.
        
        Args:
            context: Execution context containing input data and metadata
            
        Returns:
            AgentResult with execution results
        """
        pass
    
    def _get_dependency(self, name: str) -> Any:
        """Get a dependency service by name.
        
        Args:
            name: Name of the dependency
            
        Returns:
            Dependency service instance
            
        Raises:
            ValueError: If dependency not found
        """
        if name not in self.dependencies:
            available = list(self.dependencies.keys())
            raise ValueError(
                f"Dependency '{name}' not found for agent '{self.name}'. "
                f"Available dependencies: {available}"
            )
        return self.dependencies[name]
    
    async def _call_ai(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[AgentContext] = None,
        **kwargs: Any,
    ) -> str:
        """Call AI provider with prompt.
        
        This is a convenience method for agents to make AI calls.
        Uses the agent's role prompt as the system prompt by default.
        
        Note: This is a temporary implementation that uses generate_report as a workaround.
        In the future, BaseAIProvider should have a generic generate_text() method.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt (defaults to agent's role prompt)
            context: Optional execution context (for extracting ticker/symbol)
            **kwargs: Additional arguments for AI provider (currently unused)
            
        Returns:
            AI response string
            
        Raises:
            Exception: If AI call fails
        """
        # Use agent's role prompt as system prompt if not provided
        effective_system_prompt = system_prompt or self._role_prompt
        
        # Temporary workaround: Use generate_report with a minimal strategy_summary
        # The prompt will be embedded in the strategy_summary and the AI provider
        # will process it. This is not ideal but works until we add a generic
        # generate_text() method to BaseAIProvider.
        try:
            # Extract symbol from context if available
            symbol = "UNKNOWN"
            if context:
                symbol = context.input_data.get("ticker") or context.input_data.get("symbol", "UNKNOWN")
            elif hasattr(self, '_current_context'):
                symbol = self._current_context.input_data.get("ticker") or self._current_context.input_data.get("symbol", "UNKNOWN")
            
            # Create a minimal strategy_summary structure
            # The AI provider will extract the prompt from this structure
            strategy_summary = {
                "_agent_analysis_request": True,
                "_agent_prompt": prompt,
                "_agent_system_prompt": effective_system_prompt,
                # Add minimal required fields to avoid validation errors
                "symbol": symbol,
                "strategy_name": f"{self.name} Analysis",
            }
            
            # Call AI provider
            # Note: This requires the AI provider to handle the _agent_analysis_request flag
            # For now, GeminiProvider will process this as a regular report request
            response = await self.ai_provider.generate_report(
                strategy_summary=strategy_summary,
            )
            
            return response
            
        except Exception as e:
            logger.error(
                f"AI call failed for agent {self.name}: {e}",
                exc_info=True,
            )
            raise
    
    def __repr__(self) -> str:
        """String representation of agent."""
        return f"<{self.__class__.__name__}(name='{self.name}', type={self.agent_type})>"
