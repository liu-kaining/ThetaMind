"""Agent Registry - Central registry for agent registration and discovery."""

import logging
from typing import Dict, List, Optional, Type

from app.services.agents.base import BaseAgent, AgentType

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Central registry for managing agent registration and discovery.
    
    This class provides a singleton-like registry for all agents in the system.
    Agents must be registered before they can be used.
    
    Usage:
        # Register an agent
        AgentRegistry.register("my_agent", MyAgentClass, AgentType.CUSTOM)
        
        # Get agent class
        agent_class = AgentRegistry.get_agent_class("my_agent")
        
        # List agents by type
        agents = AgentRegistry.list_agents_by_type(AgentType.OPTIONS_ANALYSIS)
    """
    
    _agents: Dict[str, Type[BaseAgent]] = {}
    _agents_by_type: Dict[AgentType, List[str]] = {}
    
    @classmethod
    def register(
        cls,
        agent_name: str,
        agent_class: Type[BaseAgent],
        agent_type: AgentType,
    ) -> None:
        """Register an agent class.
        
        Args:
            agent_name: Unique name for the agent
            agent_class: Agent class (must inherit from BaseAgent)
            agent_type: Type of agent
            
        Raises:
            ValueError: If agent name already registered or invalid
        """
        if not issubclass(agent_class, BaseAgent):
            raise ValueError(
                f"Agent class {agent_class.__name__} must inherit from BaseAgent"
            )
        
        if agent_name in cls._agents:
            logger.warning(
                f"Agent '{agent_name}' already registered. Overwriting with {agent_class.__name__}"
            )
        
        cls._agents[agent_name] = agent_class
        
        if agent_type not in cls._agents_by_type:
            cls._agents_by_type[agent_type] = []
        
        if agent_name not in cls._agents_by_type[agent_type]:
            cls._agents_by_type[agent_type].append(agent_name)
        
        logger.info(f"Registered agent: {agent_name} ({agent_class.__name__}, type: {agent_type})")
    
    @classmethod
    def get_agent_class(cls, agent_name: str) -> Type[BaseAgent]:
        """Get agent class by name.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent class
            
        Raises:
            ValueError: If agent not found
        """
        if agent_name not in cls._agents:
            available = list(cls._agents.keys())
            raise ValueError(
                f"Agent '{agent_name}' not found. Available agents: {available}"
            )
        return cls._agents[agent_name]
    
    @classmethod
    def list_agents_by_type(cls, agent_type: AgentType) -> List[str]:
        """List all agent names of a specific type.
        
        Args:
            agent_type: Type of agents to list
            
        Returns:
            List of agent names
        """
        return cls._agents_by_type.get(agent_type, []).copy()
    
    @classmethod
    def list_all_agents(cls) -> List[str]:
        """List all registered agent names.
        
        Returns:
            List of all agent names
        """
        return list(cls._agents.keys())
    
    @classmethod
    def is_registered(cls, agent_name: str) -> bool:
        """Check if an agent is registered.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            True if registered, False otherwise
        """
        return agent_name in cls._agents
    
    @classmethod
    def unregister(cls, agent_name: str) -> None:
        """Unregister an agent.
        
        Args:
            agent_name: Name of the agent to unregister
        """
        if agent_name in cls._agents:
            agent_type = None
            for atype, names in cls._agents_by_type.items():
                if agent_name in names:
                    agent_type = atype
                    names.remove(agent_name)
                    break
            
            del cls._agents[agent_name]
            logger.info(f"Unregistered agent: {agent_name} (type: {agent_type})")
        else:
            logger.warning(f"Attempted to unregister non-existent agent: {agent_name}")
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered agents (mainly for testing)."""
        cls._agents.clear()
        cls._agents_by_type.clear()
        logger.info("Cleared all registered agents")
