"""Agent Executor - Executes agents (single, parallel, sequential)."""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from app.services.agents.base import AgentContext, AgentResult, AgentType
from app.services.agents.registry import AgentRegistry

logger = logging.getLogger(__name__)


class AgentExecutor:
    """Agent executor for running agents.
    
    Supports three execution modes:
    1. Single: Execute one agent
    2. Parallel: Execute multiple agents concurrently
    3. Sequential: Execute agents one after another (results can be chained)
    
    Example:
        executor = AgentExecutor(ai_provider, dependencies)
        
        # Single execution
        result = await executor.execute_single("my_agent", context)
        
        # Parallel execution
        results = await executor.execute_parallel(["agent1", "agent2"], context)
        
        # Sequential execution
        results = await executor.execute_sequential(["agent1", "agent2"], context)
    """
    
    def __init__(self, ai_provider: Any, dependencies: Dict[str, Any]):
        """Initialize executor.
        
        Args:
            ai_provider: AI provider instance (BaseAIProvider)
            dependencies: Dictionary of dependency services
                (e.g., {"market_data_service": MarketDataService()})
        """
        self.ai_provider = ai_provider
        self.dependencies = dependencies
        logger.debug(f"Initialized AgentExecutor with dependencies: {list(dependencies.keys())}")
    
    async def execute_single(
        self,
        agent_name: str,
        context: AgentContext,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> AgentResult:
        """Execute a single agent.
        
        Args:
            agent_name: Name of the agent to execute
            context: Execution context
            progress_callback: Optional callback(progress_percent, message)
            
        Returns:
            AgentResult with execution results
        """
        start_time = time.time()
        
        try:
            if progress_callback:
                progress_callback(10, f"Initializing {agent_name}...")
            
            # 1. Get agent class from registry
            agent_class = AgentRegistry.get_agent_class(agent_name)
            
            # 2. Instantiate agent
            agent = agent_class(
                name=agent_name,
                ai_provider=self.ai_provider,
                dependencies=self.dependencies,
            )
            
            if progress_callback:
                progress_callback(30, f"Executing {agent_name}...")
            
            # 3. Execute agent
            result = await agent.execute(context)
            
            # 4. Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)
            result.execution_time_ms = execution_time_ms
            
            if progress_callback:
                progress_callback(100, f"{agent_name} completed in {execution_time_ms}ms")
            
            logger.info(
                f"Agent '{agent_name}' executed successfully in {execution_time_ms}ms"
            )
            return result
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"Agent '{agent_name}' execution failed after {execution_time_ms}ms: {e}",
                exc_info=True,
            )
            
            if progress_callback:
                progress_callback(100, f"{agent_name} failed: {str(e)}")
            
            return AgentResult(
                agent_name=agent_name,
                agent_type=context.task_type,
                success=False,
                data={},
                error=str(e),
                execution_time_ms=execution_time_ms,
            )
    
    async def execute_parallel(
        self,
        agent_names: List[str],
        context: AgentContext,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Dict[str, AgentResult]:
        """Execute multiple agents in parallel.
        
        All agents receive the same context and execute concurrently.
        This is useful when agents are independent of each other.
        
        Args:
            agent_names: List of agent names to execute
            context: Execution context (shared by all agents)
            progress_callback: Optional callback(progress_percent, message)
            
        Returns:
            Dictionary mapping agent names to their results
        """
        if not agent_names:
            return {}
        
        if progress_callback:
            progress_callback(0, f"Starting parallel execution of {len(agent_names)} agents...")
        
        # Create tasks for parallel execution
        tasks = []
        for agent_name in agent_names:
            async def run_agent(name: str) -> AgentResult:
                # Create a nested progress callback for this specific agent
                def agent_progress_callback(progress: int, message: str) -> None:
                    if progress_callback:
                        # Map agent progress (0-100) to overall parallel execution range (30-70)
                        overall_progress = 30 + int(progress * 0.4)  # 30-70 range
                        progress_callback(overall_progress, f"Agent {name}: {message}")
                
                if progress_callback:
                    progress_callback(30, f"Agent {name} started")
                result = await self.execute_single(name, context, agent_progress_callback if progress_callback else None)
                if progress_callback:
                    status = "succeeded" if result.success else "failed"
                    progress_callback(70, f"Agent {name} {status}")
                return result

            task = run_agent(agent_name)
            tasks.append((agent_name, task))
        
        # Execute all tasks in parallel
        if progress_callback:
            progress_callback(20, "Executing agents in parallel...")
        
        results = await asyncio.gather(
            *[task for _, task in tasks],
            return_exceptions=True,
        )
        
        # Assemble results
        result_dict: Dict[str, AgentResult] = {}
        for (agent_name, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                logger.error(f"Agent '{agent_name}' raised exception: {result}", exc_info=True)
                result_dict[agent_name] = AgentResult(
                    agent_name=agent_name,
                    agent_type=context.task_type,
                    success=False,
                    data={},
                    error=str(result),
                )
            else:
                result_dict[agent_name] = result
        
        # Calculate overall success rate
        successful = sum(1 for r in result_dict.values() if r.success)
        total = len(result_dict)
        
        if progress_callback:
            progress_callback(
                100,
                f"Parallel execution complete: {successful}/{total} agents succeeded",
            )
        
        logger.info(
            f"Parallel execution completed: {successful}/{total} agents succeeded"
        )
        
        return result_dict
    
    async def execute_sequential(
        self,
        agent_names: List[str],
        context: AgentContext,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        stop_on_error: bool = False,
    ) -> List[AgentResult]:
        """Execute multiple agents sequentially.
        
        Agents execute one after another. Each agent's result can be added
        to the context for the next agent to use.
        
        Args:
            agent_names: List of agent names to execute (in order)
            context: Execution context (will be modified with results)
            progress_callback: Optional callback(progress_percent, message)
            stop_on_error: If True, stop execution on first error
            
        Returns:
            List of results in execution order
        """
        if not agent_names:
            return []
        
        results: List[AgentResult] = []
        total = len(agent_names)
        
        for i, agent_name in enumerate(agent_names):
            if progress_callback:
                progress = int((i / total) * 100)
                progress_callback(
                    progress,
                    f"Executing {agent_name} ({i+1}/{total})...",
                )
            
            # Create a nested progress callback for this specific agent
            def make_agent_callback(base_progress: int, agent_name: str) -> Callable[[int, str], None] | None:
                if not progress_callback:
                    return None
                def agent_progress_callback(agent_progress: int, message: str) -> None:
                    # Map agent progress (0-100) to this agent's range in sequential execution
                    # Each agent gets roughly (100/total) percent of the overall progress
                    agent_range = 100 / total
                    agent_start = base_progress
                    agent_end = base_progress + agent_range
                    overall_progress = int(agent_start + (agent_progress / 100) * agent_range)
                    progress_callback(overall_progress, f"Agent {agent_name}: {message}")
                return agent_progress_callback
            
            agent_callback = make_agent_callback(progress, agent_name)
            
            if progress_callback:
                progress_callback(progress, f"Agent {agent_name} started")
            result = await self.execute_single(agent_name, context, agent_callback)
            if progress_callback:
                status = "succeeded" if result.success else "failed"
                progress_callback(progress + 5, f"Agent {agent_name} {status}")
            results.append(result)
            
            # Handle errors
            if not result.success:
                logger.warning(
                    f"Agent '{agent_name}' failed: {result.error}. "
                    f"stop_on_error={stop_on_error}"
                )
                if stop_on_error:
                    break
            
            # Add result to context for next agent (if successful)
            if result.success:
                context.input_data[f"_agent_result_{agent_name}"] = result.data
                logger.debug(
                    f"Added result from '{agent_name}' to context for next agents"
                )
        
        if progress_callback:
            progress_callback(100, f"Sequential execution complete: {len(results)} agents executed")
        
        successful = sum(1 for r in results if r.success)
        logger.info(
            f"Sequential execution completed: {successful}/{len(results)} agents succeeded"
        )
        
        return results
