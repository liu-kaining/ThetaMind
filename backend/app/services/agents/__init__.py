"""Agent Framework - Multi-Agent Execution System for ThetaMind.

This module provides a flexible, extensible framework for building and executing
multi-agent workflows for various financial analysis tasks.

Core Components:
- BaseAgent: Abstract base class for all agents
- AgentRegistry: Central registry for agent registration and discovery
- AgentExecutor: Executes agents (single, parallel, sequential)
- AgentCoordinator: Coordinates complex multi-agent workflows

Usage:
    from app.services.agents import AgentRegistry, AgentExecutor, AgentCoordinator
    from app.services.agents.base import AgentContext, AgentType
    
    # Register agents
    AgentRegistry.register("my_agent", MyAgentClass, AgentType.CUSTOM)
    
    # Execute agent
    executor = AgentExecutor(ai_provider, dependencies)
    result = await executor.execute_single("my_agent", context)
"""

from app.services.agents.base import (
    BaseAgent,
    AgentContext,
    AgentResult,
    AgentType,
)
from app.services.agents.registry import AgentRegistry
from app.services.agents.executor import AgentExecutor
from app.services.agents.coordinator import AgentCoordinator

__all__ = [
    "BaseAgent",
    "AgentContext",
    "AgentResult",
    "AgentType",
    "AgentRegistry",
    "AgentExecutor",
    "AgentCoordinator",
]
