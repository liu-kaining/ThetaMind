# ThetaMind 通用 Agent 执行框架设计方案

**版本**: v1.0  
**日期**: 2025-01-18  
**状态**: 📋 设计方案（待实现）

---

## 📋 项目现状分析

### 现有系统能力评估

#### ✅ 已具备的核心能力

1. **AI Service 基础设施** ⭐⭐⭐⭐⭐
   - ✅ `BaseAIProvider` 抽象基类（策略模式）
   - ✅ `ProviderRegistry` 注册机制（可扩展）
   - ✅ `GeminiProvider` / `ZenMuxProvider` 实现
   - ✅ 进度回调机制（`progress_callback`）
   - ✅ 错误处理和降级机制

2. **MarketDataService (FMP)** ⭐⭐⭐⭐⭐
   - ✅ 完整的财务分析能力（200+ 数据点）
   - ✅ 技术指标（30+ 指标）
   - ✅ 财务报表（Income, Balance Sheet, Cash Flow）
   - ✅ 估值模型（DCF, DDM, WACC）
   - ✅ 数据清洗和标准化
   - ✅ 图表生成能力

3. **Tiger Service** ⭐⭐⭐⭐
   - ✅ 期权链数据获取
   - ✅ 实时行情数据
   - ✅ 缓存机制（Pro/Free 差异化）
   - ✅ 历史数据

4. **Strategy Engine** ⭐⭐⭐⭐
   - ✅ 策略计算逻辑
   - ✅ Greeks 分析
   - ✅ 策略生成

5. **Daily Picks Service** ⭐⭐⭐
   - ✅ 每日精选生成流程
   - ✅ 市场扫描
   - ✅ 策略评分

#### ⚠️ 缺失的能力

1. **多智能体协调机制** - 无
2. **任务类型抽象** - 无
3. **Agent 生命周期管理** - 无
4. **工作流编排** - 无（虽然有 `generate_deep_research_report`，但不够通用）

---

## 🎯 设计目标

### 核心需求

1. **通用性**：支持多种任务类型
   - 期权策略分析
   - 基本面分析
   - 技术面分析
   - 选股推荐
   - 每日精选生成

2. **可扩展性**：易于添加新的 Agent 和任务类型

3. **高性能**：支持并行执行、缓存、降级

4. **可观测性**：进度跟踪、日志、错误处理

---

## 🏗️ 架构设计

### 1. 核心架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Framework Layer                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ Agent        │    │ Agent        │    │ Agent        │  │
│  │ Registry     │    │ Executor     │    │ Coordinator  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                   │           │
│         └───────────────────┴───────────────────┘           │
│                            │                                 │
│                    ┌───────▼────────┐                        │
│                    │  Task Router   │                        │
│                    └───────┬────────┘                        │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌────────▼────────┐  ┌──────▼────────┐
│  Base Agent    │  │  Task Context   │  │  Agent Result │
│  (Abstract)    │  │  (Input/Output) │  │  (Structured) │
└────────────────┘  └─────────────────┘  └───────────────┘
        │
        ├── OptionsAnalysisAgent
        ├── FundamentalAnalysisAgent
        ├── TechnicalAnalysisAgent
        ├── StockScreeningAgent
        └── RecommendationAgent
```

### 2. 核心组件设计

#### 2.1 BaseAgent（抽象基类）

```python
# backend/app/services/agents/base.py

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timezone

class AgentType(str, Enum):
    """Agent 类型枚举"""
    OPTIONS_ANALYSIS = "options_analysis"
    FUNDAMENTAL_ANALYSIS = "fundamental_analysis"
    TECHNICAL_ANALYSIS = "technical_analysis"
    STOCK_SCREENING = "stock_screening"
    RECOMMENDATION = "recommendation"
    CUSTOM = "custom"

@dataclass
class AgentContext:
    """Agent 执行上下文"""
    task_id: str
    task_type: AgentType
    input_data: Dict[str, Any]
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class AgentResult:
    """Agent 执行结果"""
    agent_name: str
    agent_type: AgentType
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

class BaseAgent(ABC):
    """Agent 基类 - 所有 Agent 的抽象接口"""
    
    def __init__(
        self,
        name: str,
        agent_type: AgentType,
        ai_provider: BaseAIProvider,
        dependencies: Optional[Dict[str, Any]] = None
    ):
        """
        Args:
            name: Agent 名称（唯一标识）
            agent_type: Agent 类型
            ai_provider: AI Provider 实例
            dependencies: 依赖的服务（如 MarketDataService, TigerService）
        """
        self.name = name
        self.agent_type = agent_type
        self.ai_provider = ai_provider
        self.dependencies = dependencies or {}
        self._role_prompt = self._get_role_prompt()
    
    @abstractmethod
    def _get_role_prompt(self) -> str:
        """返回该 Agent 的角色定义提示词"""
        pass
    
    @abstractmethod
    async def execute(self, context: AgentContext) -> AgentResult:
        """
        执行 Agent 的核心逻辑
        
        Args:
            context: 执行上下文
            
        Returns:
            AgentResult: 执行结果
        """
        pass
    
    def _get_dependency(self, name: str) -> Any:
        """获取依赖的服务"""
        if name not in self.dependencies:
            raise ValueError(f"Dependency '{name}' not found. Available: {list(self.dependencies.keys())}")
        return self.dependencies[name]
    
    async def _call_ai(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """调用 AI Provider（统一接口）"""
        # 使用现有的 AI Service 机制
        # 这里可以扩展支持不同的调用方式
        pass
```

#### 2.2 Agent Registry（注册中心）

```python
# backend/app/services/agents/registry.py

from typing import Dict, Type, List, Optional
from app.services.agents.base import BaseAgent, AgentType

class AgentRegistry:
    """Agent 注册中心 - 管理所有 Agent 的注册和获取"""
    
    _agents: Dict[str, Type[BaseAgent]] = {}
    _agents_by_type: Dict[AgentType, List[str]] = {}
    
    @classmethod
    def register(
        cls,
        agent_name: str,
        agent_class: Type[BaseAgent],
        agent_type: AgentType
    ):
        """注册 Agent"""
        if agent_name in cls._agents:
            raise ValueError(f"Agent '{agent_name}' already registered")
        
        cls._agents[agent_name] = agent_class
        if agent_type not in cls._agents_by_type:
            cls._agents_by_type[agent_type] = []
        cls._agents_by_type[agent_type].append(agent_name)
    
    @classmethod
    def get_agent_class(cls, agent_name: str) -> Type[BaseAgent]:
        """获取 Agent 类"""
        if agent_name not in cls._agents:
            raise ValueError(f"Agent '{agent_name}' not found. Available: {list(cls._agents.keys())}")
        return cls._agents[agent_name]
    
    @classmethod
    def list_agents_by_type(cls, agent_type: AgentType) -> List[str]:
        """按类型列出 Agent"""
        return cls._agents_by_type.get(agent_type, [])
    
    @classmethod
    def list_all_agents(cls) -> List[str]:
        """列出所有注册的 Agent"""
        return list(cls._agents.keys())
```

#### 2.3 Agent Executor（执行器）

```python
# backend/app/services/agents/executor.py

import asyncio
import time
from typing import List, Dict, Any, Optional, Callable
from app.services.agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from app.services.agents.registry import AgentRegistry

class AgentExecutor:
    """Agent 执行器 - 负责执行单个或多个 Agent"""
    
    def __init__(self, ai_provider, dependencies: Dict[str, Any]):
        """
        Args:
            ai_provider: AI Provider 实例
            dependencies: 依赖的服务字典
        """
        self.ai_provider = ai_provider
        self.dependencies = dependencies
    
    async def execute_single(
        self,
        agent_name: str,
        context: AgentContext,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> AgentResult:
        """执行单个 Agent"""
        start_time = time.time()
        
        try:
            # 1. 获取 Agent 类
            agent_class = AgentRegistry.get_agent_class(agent_name)
            
            # 2. 实例化 Agent
            agent = agent_class(
                name=agent_name,
                agent_type=context.task_type,
                ai_provider=self.ai_provider,
                dependencies=self.dependencies
            )
            
            # 3. 执行 Agent
            if progress_callback:
                progress_callback(50, f"Executing {agent_name}...")
            
            result = await agent.execute(context)
            
            # 4. 计算执行时间
            execution_time_ms = int((time.time() - start_time) * 1000)
            result.execution_time_ms = execution_time_ms
            
            if progress_callback:
                progress_callback(100, f"{agent_name} completed")
            
            return result
            
        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return AgentResult(
                agent_name=agent_name,
                agent_type=context.task_type,
                success=False,
                data={},
                error=str(e),
                execution_time_ms=execution_time_ms
            )
    
    async def execute_parallel(
        self,
        agent_names: List[str],
        context: AgentContext,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, AgentResult]:
        """并行执行多个 Agent"""
        tasks = []
        for agent_name in agent_names:
            task = self.execute_single(agent_name, context, None)  # 不传递 progress_callback 到单个任务
            tasks.append((agent_name, task))
        
        # 并行执行
        results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
        
        # 组装结果
        result_dict = {}
        for (agent_name, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                result_dict[agent_name] = AgentResult(
                    agent_name=agent_name,
                    agent_type=context.task_type,
                    success=False,
                    data={},
                    error=str(result)
                )
            else:
                result_dict[agent_name] = result
        
        if progress_callback:
            progress_callback(100, f"All {len(agent_names)} agents completed")
        
        return result_dict
    
    async def execute_sequential(
        self,
        agent_names: List[str],
        context: AgentContext,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> List[AgentResult]:
        """顺序执行多个 Agent（前一个的结果可以作为后一个的输入）"""
        results = []
        total = len(agent_names)
        
        for i, agent_name in enumerate(agent_names):
            if progress_callback:
                progress = int((i / total) * 100)
                progress_callback(progress, f"Executing {agent_name} ({i+1}/{total})...")
            
            result = await self.execute_single(agent_name, context)
            results.append(result)
            
            # 如果失败，可以选择是否继续
            if not result.success:
                # 可以选择继续或中断
                # 这里选择继续，但记录错误
                pass
            
            # 将结果添加到 context 中，供下一个 Agent 使用
            if result.success:
                context.input_data[f"_agent_result_{agent_name}"] = result.data
        
        if progress_callback:
            progress_callback(100, "All agents completed")
        
        return results
```

#### 2.4 Agent Coordinator（协调器）

```python
# backend/app/services/agents/coordinator.py

from typing import Dict, List, Any, Optional, Callable
from app.services.agents.base import AgentContext, AgentResult, AgentType
from app.services.agents.executor import AgentExecutor
from app.services.agents.registry import AgentRegistry

class AgentCoordinator:
    """Agent 协调器 - 管理复杂的工作流"""
    
    def __init__(self, executor: AgentExecutor):
        self.executor = executor
    
    async def coordinate_options_analysis(
        self,
        strategy_summary: Dict[str, Any],
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        协调期权策略分析工作流
        
        工作流：
        1. 并行执行：Greeks 分析、IV 分析、市场环境分析
        2. 顺序执行：风险分析（依赖前面的结果）
        3. 综合：生成最终报告
        """
        context = AgentContext(
            task_id=f"options_analysis_{strategy_summary.get('symbol', 'unknown')}",
            task_type=AgentType.OPTIONS_ANALYSIS,
            input_data={"strategy_summary": strategy_summary}
        )
        
        # Phase 1: 并行分析
        if progress_callback:
            progress_callback(10, "Phase 1: Parallel analysis...")
        
        parallel_results = await self.executor.execute_parallel(
            agent_names=[
                "options_greeks_analyst",
                "iv_environment_analyst",
                "market_context_analyst"
            ],
            context=context
        )
        
        # Phase 2: 风险分析（依赖前面的结果）
        if progress_callback:
            progress_callback(60, "Phase 2: Risk analysis...")
        
        # 将并行结果添加到 context
        for agent_name, result in parallel_results.items():
            if result.success:
                context.input_data[f"_result_{agent_name}"] = result.data
        
        risk_result = await self.executor.execute_single(
            "risk_scenario_analyst",
            context
        )
        
        # Phase 3: 综合报告
        if progress_callback:
            progress_callback(80, "Phase 3: Synthesizing report...")
        
        # 将所有结果传递给综合 Agent
        context.input_data["_all_results"] = {
            **parallel_results,
            "risk_scenario_analyst": risk_result
        }
        
        synthesis_result = await self.executor.execute_single(
            "options_synthesis_agent",
            context
        )
        
        if progress_callback:
            progress_callback(100, "Analysis complete")
        
        return {
            "parallel_analysis": parallel_results,
            "risk_analysis": risk_result.data if risk_result.success else None,
            "synthesis": synthesis_result.data if synthesis_result.success else None,
            "all_results": {
                **{k: v.data for k, v in parallel_results.items() if v.success},
                "risk_scenario_analyst": risk_result.data if risk_result.success else None,
                "options_synthesis_agent": synthesis_result.data if synthesis_result.success else None
            }
        }
    
    async def coordinate_stock_screening(
        self,
        criteria: Dict[str, Any],
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        协调选股工作流
        
        工作流：
        1. 使用 MarketDataService 筛选股票
        2. 对每个候选股票进行基本面分析
        3. 对每个候选股票进行技术面分析
        4. 综合评分和排序
        """
        context = AgentContext(
            task_id=f"stock_screening_{criteria.get('sector', 'all')}",
            task_type=AgentType.STOCK_SCREENING,
            input_data={"criteria": criteria}
        )
        
        # Phase 1: 初步筛选
        if progress_callback:
            progress_callback(20, "Phase 1: Initial screening...")
        
        screening_result = await self.executor.execute_single(
            "stock_screening_agent",
            context
        )
        
        if not screening_result.success:
            return []
        
        candidates = screening_result.data.get("candidates", [])
        
        # Phase 2: 对每个候选进行深度分析（并行）
        if progress_callback:
            progress_callback(40, f"Phase 2: Analyzing {len(candidates)} candidates...")
        
        analysis_results = []
        for i, candidate in enumerate(candidates):
            candidate_context = AgentContext(
                task_id=f"{context.task_id}_candidate_{i}",
                task_type=AgentType.FUNDAMENTAL_ANALYSIS,
                input_data={"ticker": candidate["symbol"]}
            )
            
            # 并行执行基本面和技术面分析
            results = await self.executor.execute_parallel(
                agent_names=["fundamental_analyst", "technical_analyst"],
                context=candidate_context
            )
            
            analysis_results.append({
                "candidate": candidate,
                "analysis": results
            })
            
            if progress_callback:
                progress = 40 + int((i + 1) / len(candidates) * 40)
                progress_callback(progress, f"Analyzed {i+1}/{len(candidates)} candidates")
        
        # Phase 3: 综合评分
        if progress_callback:
            progress_callback(90, "Phase 3: Ranking candidates...")
        
        ranking_result = await self.executor.execute_single(
            "stock_ranking_agent",
            AgentContext(
                task_id=f"{context.task_id}_ranking",
                task_type=AgentType.RECOMMENDATION,
                input_data={"analysis_results": analysis_results}
            )
        )
        
        if progress_callback:
            progress_callback(100, "Screening complete")
        
        return ranking_result.data.get("ranked_stocks", []) if ranking_result.success else []
```

---

## 🔧 具体 Agent 实现示例

### 1. OptionsGreeksAnalyst（期权 Greeks 分析师）

```python
# backend/app/services/agents/options_greeks_analyst.py

from app.services.agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from app.services.ai.base import BaseAIProvider

class OptionsGreeksAnalyst(BaseAgent):
    """期权 Greeks 分析师 - 分析策略的 Greeks 风险"""
    
    def __init__(self, name: str, ai_provider: BaseAIProvider, dependencies: dict):
        super().__init__(
            name=name,
            agent_type=AgentType.OPTIONS_ANALYSIS,
            ai_provider=ai_provider,
            dependencies=dependencies
        )
    
    def _get_role_prompt(self) -> str:
        return """You are a Senior Options Strategist specializing in Greeks analysis.
Your expertise includes:
- Delta: Directional risk assessment
- Gamma: Acceleration risk (pin risk)
- Theta: Time decay analysis
- Vega: Volatility sensitivity

Analyze the Greeks exposure and provide:
1. Risk assessment for each Greek
2. Key risk factors
3. Recommendations for risk management"""
    
    async def execute(self, context: AgentContext) -> AgentResult:
        strategy_summary = context.input_data.get("strategy_summary", {})
        greeks = strategy_summary.get("portfolio_greeks", {})
        
        # 构建分析提示词
        prompt = f"""
Analyze the Greeks exposure for this options strategy:

Net Greeks:
- Delta: {greeks.get('delta', 0)}
- Gamma: {greeks.get('gamma', 0)}
- Theta: {greeks.get('theta', 0)}
- Vega: {greeks.get('vega', 0)}

Strategy Structure:
{strategy_summary.get('strategy_name', 'Unknown')}

Provide a comprehensive Greeks risk analysis.
"""
        
        analysis = await self._call_ai(prompt, system_prompt=self._role_prompt)
        
        return AgentResult(
            agent_name=self.name,
            agent_type=self.agent_type,
            success=True,
            data={
                "analysis": analysis,
                "greeks": greeks,
                "risk_score": self._calculate_risk_score(greeks)
            }
        )
    
    def _calculate_risk_score(self, greeks: dict) -> float:
        # 简单的风险评分逻辑
        # 可以根据实际需求扩展
        score = 50.0  # 默认中等风险
        # ... 计算逻辑
        return score
```

### 2. FundamentalAnalyst（基本面分析师）

```python
# backend/app/services/agents/fundamental_analyst.py

from app.services.agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from app.services.market_data_service import MarketDataService

class FundamentalAnalyst(BaseAgent):
    """基本面分析师 - 使用 MarketDataService 进行财务分析"""
    
    def __init__(self, name: str, ai_provider: BaseAIProvider, dependencies: dict):
        super().__init__(
            name=name,
            agent_type=AgentType.FUNDAMENTAL_ANALYSIS,
            ai_provider=ai_provider,
            dependencies=dependencies
        )
        self.market_data_service = self._get_dependency("market_data_service")
    
    def _get_role_prompt(self) -> str:
        return """You are a Senior Fundamental Analyst.
Analyze company financials, valuation, and financial health.
Provide objective, data-driven insights."""
    
    async def execute(self, context: AgentContext) -> AgentResult:
        ticker = context.input_data.get("ticker")
        if not ticker:
            return AgentResult(
                agent_name=self.name,
                agent_type=self.agent_type,
                success=False,
                data={},
                error="Ticker not provided"
            )
        
        # 使用 MarketDataService 获取数据
        profile = self.market_data_service.get_financial_profile(ticker)
        
        # 构建分析提示词
        prompt = f"""
Analyze the fundamental data for {ticker}:

Financial Ratios:
{self._format_ratios(profile.get("ratios", {}))}

Valuation Models:
{self._format_valuation(profile.get("valuation", {}))}

Financial Statements:
{self._format_statements(profile.get("financial_statements", {}))}

Provide a comprehensive fundamental analysis.
"""
        
        analysis = await self._call_ai(prompt, system_prompt=self._role_prompt)
        
        return AgentResult(
            agent_name=self.name,
            agent_type=self.agent_type,
            success=True,
            data={
                "analysis": analysis,
                "profile": profile,
                "health_score": profile.get("analysis", {}).get("health_score", {})
            }
        )
    
    def _format_ratios(self, ratios: dict) -> str:
        # 格式化财务比率数据
        pass
    
    def _format_valuation(self, valuation: dict) -> str:
        # 格式化估值数据
        pass
    
    def _format_statements(self, statements: dict) -> str:
        # 格式化财务报表数据
        pass
```

### 3. StockScreeningAgent（选股 Agent）

```python
# backend/app/services/agents/stock_screening_agent.py

from app.services.agents.base import BaseAgent, AgentContext, AgentResult, AgentType
from app.services.market_data_service import MarketDataService

class StockScreeningAgent(BaseAgent):
    """选股 Agent - 使用 MarketDataService 进行股票筛选"""
    
    def __init__(self, name: str, ai_provider: BaseAIProvider, dependencies: dict):
        super().__init__(
            name=name,
            agent_type=AgentType.STOCK_SCREENING,
            ai_provider=ai_provider,
            dependencies=dependencies
        )
        self.market_data_service = self._get_dependency("market_data_service")
    
    def _get_role_prompt(self) -> str:
        return """You are a Stock Screening Specialist.
Filter stocks based on criteria and return candidate list."""
    
    async def execute(self, context: AgentContext) -> AgentResult:
        criteria = context.input_data.get("criteria", {})
        
        # 使用 MarketDataService 筛选股票
        tickers = self.market_data_service.search_tickers(
            sector=criteria.get("sector"),
            industry=criteria.get("industry"),
            market_cap=criteria.get("market_cap", "Large Cap"),
            country=criteria.get("country", "United States")
        )
        
        # 可以进一步使用 AI 进行筛选
        if criteria.get("use_ai_filtering", False):
            # 使用 AI 对候选股票进行初步评估
            filtered_tickers = await self._ai_filter(tickers, criteria)
        else:
            filtered_tickers = tickers[:criteria.get("limit", 20)]
        
        return AgentResult(
            agent_name=self.name,
            agent_type=self.agent_type,
            success=True,
            data={
                "candidates": [
                    {"symbol": ticker, "initial_score": 0.5}
                    for ticker in filtered_tickers
                ],
                "total_found": len(tickers),
                "filtered_count": len(filtered_tickers)
            }
        )
    
    async def _ai_filter(self, tickers: list, criteria: dict) -> list:
        # 使用 AI 进行智能筛选
        pass
```

---

## 🚀 集成到现有系统

### 1. 修改 AIService

```python
# backend/app/services/ai_service.py (扩展)

from app.services.agents.coordinator import AgentCoordinator
from app.services.agents.executor import AgentExecutor
from app.services.agents.registry import AgentRegistry

class AIService:
    def __init__(self):
        # ... 现有初始化代码
        
        # 初始化 Agent 框架
        self._init_agent_framework()
    
    def _init_agent_framework(self):
        """初始化 Agent 框架"""
        from app.services.market_data_service import MarketDataService
        from app.services.tiger_service import tiger_service
        
        # 准备依赖
        dependencies = {
            "market_data_service": MarketDataService(),
            "tiger_service": tiger_service,
            # 可以添加更多依赖
        }
        
        # 创建执行器
        executor = AgentExecutor(
            ai_provider=self._default_provider,
            dependencies=dependencies
        )
        
        # 创建协调器
        self._agent_coordinator = AgentCoordinator(executor)
        
        # 注册所有 Agent
        self._register_agents()
    
    def _register_agents(self):
        """注册所有 Agent"""
        from app.services.agents.options_greeks_analyst import OptionsGreeksAnalyst
        from app.services.agents.fundamental_analyst import FundamentalAnalyst
        # ... 注册其他 Agent
        
        AgentRegistry.register("options_greeks_analyst", OptionsGreeksAnalyst, AgentType.OPTIONS_ANALYSIS)
        AgentRegistry.register("fundamental_analyst", FundamentalAnalyst, AgentType.FUNDAMENTAL_ANALYSIS)
        # ... 注册其他 Agent
    
    async def generate_report_with_agents(
        self,
        strategy_summary: dict[str, Any],
        use_multi_agent: bool = True,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> str:
        """使用多智能体系统生成报告"""
        if use_multi_agent:
            result = await self._agent_coordinator.coordinate_options_analysis(
                strategy_summary,
                progress_callback
            )
            return self._format_agent_report(result)
        else:
            # 回退到原有单一 AI 分析
            return await self.generate_report(strategy_summary=strategy_summary)
    
    async def screen_stocks(
        self,
        criteria: dict[str, Any],
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> list[dict[str, Any]]:
        """使用 Agent 框架进行选股"""
        return await self._agent_coordinator.coordinate_stock_screening(
            criteria,
            progress_callback
        )
```

### 2. 创建 API 端点

```python
# backend/app/api/endpoints/agents.py (新建)

from fastapi import APIRouter, Depends, HTTPException
from app.services.ai_service import ai_service

router = APIRouter(prefix="/agents", tags=["agents"])

@router.post("/analyze-options")
async def analyze_options_with_agents(
    strategy_summary: dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """使用多智能体分析期权策略"""
    report = await ai_service.generate_report_with_agents(
        strategy_summary,
        use_multi_agent=True
    )
    return {"report": report}

@router.post("/screen-stocks")
async def screen_stocks(
    criteria: dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """使用 Agent 框架进行选股"""
    stocks = await ai_service.screen_stocks(criteria)
    return {"stocks": stocks}
```

---

## 📊 实施计划

### Phase 1: 基础框架（1-2 周）

1. ✅ 实现 `BaseAgent` 抽象基类
2. ✅ 实现 `AgentRegistry` 注册中心
3. ✅ 实现 `AgentExecutor` 执行器
4. ✅ 实现 `AgentCoordinator` 协调器
5. ✅ 实现 2-3 个示例 Agent（OptionsGreeksAnalyst, FundamentalAnalyst）

### Phase 2: 核心 Agent（2-3 周）

1. ⚠️ 实现所有期权分析 Agent
2. ⚠️ 实现基本面分析 Agent
3. ⚠️ 实现技术面分析 Agent
4. ⚠️ 实现选股 Agent

### Phase 3: 集成和优化（1-2 周）

1. ⚠️ 集成到现有 AIService
2. ⚠️ 创建 API 端点
3. ⚠️ 性能优化（缓存、并行）
4. ⚠️ 错误处理和降级

### Phase 4: 扩展功能（持续）

1. ⚠️ 添加更多 Agent 类型
2. ⚠️ 工作流可视化
3. ⚠️ Agent 性能监控
4. ⚠️ 自定义工作流配置

---

## ✅ 可行性评估

### 快速实现能力：⭐⭐⭐⭐⭐

**优势**：
1. ✅ 现有 AI Service 基础设施完善
2. ✅ MarketDataService 提供丰富数据
3. ✅ Tiger Service 提供期权数据
4. ✅ 架构设计清晰，易于实现

**挑战**：
1. ⚠️ 需要设计好 Agent 接口
2. ⚠️ 需要管理 Agent 之间的依赖
3. ⚠️ 需要处理并行执行的复杂性

### 扩展性：⭐⭐⭐⭐⭐

**优势**：
1. ✅ 基于抽象基类，易于扩展
2. ✅ 注册机制支持动态添加
3. ✅ 依赖注入支持灵活配置

### 性能：⭐⭐⭐⭐

**优势**：
1. ✅ 支持并行执行
2. ✅ 可以复用现有缓存机制
3. ✅ 可以降级到单一 AI 分析

**挑战**：
1. ⚠️ 多 Agent 会增加 API 调用次数
2. ⚠️ 需要优化并行执行的效率

---

## 🎯 总结

### 核心结论

**完全有能力快速实现通用的 Agent 执行框架！**

### 关键成功因素

1. ✅ **复用现有基础设施**：AI Service, MarketDataService, Tiger Service
2. ✅ **清晰的架构设计**：BaseAgent → Registry → Executor → Coordinator
3. ✅ **渐进式实施**：先实现框架，再逐步添加 Agent
4. ✅ **灵活的扩展机制**：支持多种任务类型

### 下一步行动

1. **立即开始 Phase 1**：实现基础框架
2. **快速验证**：实现 2-3 个示例 Agent
3. **迭代优化**：根据实际使用情况调整架构

---

**最后更新**: 2025-01-18  
**版本**: v1.0  
**状态**: 📋 设计方案完成，准备实施
