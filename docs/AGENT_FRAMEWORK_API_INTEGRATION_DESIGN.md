# Agent Framework API 集成设计方案

**版本**: v1.0  
**日期**: 2025-01-18  
**状态**: 📋 设计方案（待实现）

---

## 📋 设计目标

设计 Agent Framework 与现有 API 的集成方案，确保：
1. **无缝集成**：不影响现有 API 功能
2. **向后兼容**：现有 API 调用继续工作（默认单 Agent 模式）
3. **灵活切换**：支持单 Agent 和多 Agent 模式
4. **Gemini 集成**：充分利用 Gemini 3.0 Pro 的能力（用户主要使用 Gemini）
5. **渐进式迁移**：可以逐步启用多 Agent 功能
6. **配额管理**：多 Agent 模式会消耗更多 Gemini API 配额，需要合理管理

---

## 🏗️ 架构概览

### 当前架构

```
API Endpoint
    ↓
AIService.generate_report()
    ↓
GeminiProvider.generate_report()
    ↓
Gemini API
```

### 目标架构（多 Agent 模式）

```
API Endpoint
    ↓
AIService.generate_report_with_agents()
    ↓
AgentCoordinator.coordinate_options_analysis()
    ↓
AgentExecutor (并行/顺序执行)
    ↓
多个 Agent (OptionsGreeksAnalyst, IVEnvironmentAnalyst, ...)
    ↓
每个 Agent 调用 GeminiProvider.generate_report()
    ↓
Gemini API (多次调用)
    ↓
OptionsSynthesisAgent (综合所有结果)
    ↓
Gemini API (最终综合)
    ↓
返回综合报告
```

---

## 🔌 API 集成方案

### 方案 1: 扩展现有端点（推荐）

**设计思路**：
- 在现有 `/api/v1/ai/report` 端点中添加可选参数
- 默认使用单 Agent 模式（保持向后兼容）
- 通过参数启用多 Agent 模式

**API 端点设计**：

```
POST /api/v1/ai/report
```

**请求参数**：

```json
{
  "strategy_summary": {
    "symbol": "AAPL",
    "strategy_name": "Iron Condor",
    "portfolio_greeks": {...},
    "strategy_metrics": {...}
  },
  "use_multi_agent": false,  // 可选，默认 false（向后兼容）
  "agent_config": {          // 可选，多 Agent 模式配置
    "parallel_agents": ["options_greeks_analyst", "iv_environment_analyst", "market_context_analyst"],
    "sequential_agents": ["risk_scenario_analyst", "options_synthesis_agent"],
    "progress_callback_enabled": true
  }
}
```

**响应结构**：

```json
{
  "report": "Markdown 格式的综合报告",
  "metadata": {
    "mode": "multi_agent" | "single_agent",
    "agents_used": ["options_greeks_analyst", "iv_environment_analyst", ...],
    "execution_time_ms": 5000,
    "agent_results": {
      "options_greeks_analyst": {
        "success": true,
        "risk_score": 5.5,
        "risk_category": "Medium"
      },
      ...
    }
  }
}
```

---

### 方案 2: 新增专用端点

**设计思路**：
- 创建新的 `/api/v1/ai/report/multi-agent` 端点
- 保持现有端点不变
- 新端点专门用于多 Agent 分析

**API 端点设计**：

```
POST /api/v1/ai/report/multi-agent
```

**请求参数**：

```json
{
  "strategy_summary": {...},
  "workflow": "options_analysis" | "stock_screening",  // 工作流类型
  "config": {
    "include_agents": ["options_greeks_analyst", "iv_environment_analyst"],
    "exclude_agents": [],
    "timeout_seconds": 60
  }
}
```

**响应结构**：

```json
{
  "report": "综合报告",
  "workflow": "options_analysis",
  "agent_results": {...},
  "execution_summary": {
    "total_agents": 5,
    "successful_agents": 5,
    "failed_agents": [],
    "total_time_ms": 5000
  }
}
```

---

### 方案 3: 混合方案（推荐用于生产）

**设计思路**：
- 方案 1 用于向后兼容
- 方案 2 用于新功能
- 两者共享相同的底层实现

**API 端点**：

1. **现有端点（扩展）**：
   ```
   POST /api/v1/ai/report
   ```
   - 默认：单 Agent 模式（现有行为）
   - 可选：`use_multi_agent=true` 启用多 Agent

2. **新端点（专用）**：
   ```
   POST /api/v1/ai/report/multi-agent
   ```
   - 专门用于多 Agent 分析
   - 支持更多配置选项

3. **工作流端点**：
   ```
   POST /api/v1/ai/workflows/options-analysis
   POST /api/v1/ai/workflows/stock-screening
   ```
   - 预定义的工作流
   - 简化的参数

---

## 🤖 Gemini 集成设计

### 当前 Gemini 使用方式

**GeminiProvider**：
- 使用 Gemini 3.0 Pro 模型
- 通过 `generate_report()` 方法生成报告
- 接收 `strategy_summary` 作为输入

### Agent Framework 中的 Gemini 使用

**设计原则**：
1. **复用现有 Provider**：所有 Agent 使用相同的 `GeminiProvider` 实例
2. **统一接口**：通过 `BaseAgent._call_ai()` 调用
3. **临时方案**：使用 `generate_report()` 作为通用文本生成接口
4. **未来优化**：添加 `generate_text()` 方法到 `BaseAIProvider`

**调用流程**：

```
Agent.execute()
    ↓
Agent._call_ai(prompt, system_prompt)
    ↓
构建 strategy_summary（临时方案）
    ↓
GeminiProvider.generate_report(strategy_summary)
    ↓
Gemini API 调用
    ↓
返回 AI 分析文本
```

**临时方案细节**：

```python
# BaseAgent._call_ai() 当前实现
strategy_summary = {
    "_agent_analysis_request": True,  # 标识这是 Agent 请求
    "_agent_prompt": prompt,          # Agent 的提示
    "_agent_system_prompt": system_prompt,  # 系统提示
    "symbol": symbol,                 # 从 context 提取
    "strategy_name": f"{self.name} Analysis"
}

response = await self.ai_provider.generate_report(
    strategy_summary=strategy_summary
)
```

**GeminiProvider 处理**（需要实现）：

当前 `GeminiProvider.generate_report()` 需要扩展以支持 Agent 请求：

1. **检查标志**：
   - 检查 `strategy_summary` 中是否有 `_agent_analysis_request` 标志
   - 如果有，进入 Agent 模式

2. **Agent 模式**：
   - 提取 `_agent_prompt` 作为用户提示
   - 提取 `_agent_system_prompt` 作为系统提示
   - 直接调用 Gemini API（跳过策略分析模板）

3. **普通模式**（现有逻辑）：
   - 使用策略分析模板
   - 格式化策略摘要
   - 调用 Gemini API

**实现位置**：`backend/app/services/ai/gemini_provider.py` 的 `generate_report()` 方法

---

## 🔄 工作流设计

### 工作流 1: 期权策略分析

**触发条件**：
- API 请求包含 `strategy_summary`
- `use_multi_agent=true` 或使用 `/multi-agent` 端点

**执行流程**：

```
Phase 1 (并行执行):
├─ OptionsGreeksAnalyst → Gemini API 调用 1
├─ IVEnvironmentAnalyst → Gemini API 调用 2
└─ MarketContextAnalyst → Gemini API 调用 3
    ↓
Phase 2 (顺序执行):
└─ RiskScenarioAnalyst → Gemini API 调用 4
    (依赖 Phase 1 结果)
    ↓
Phase 3 (顺序执行):
└─ OptionsSynthesisAgent → Gemini API 调用 5
    (综合所有结果)
    ↓
返回最终报告
```

**Gemini API 调用次数**：
- 总共 5 次调用
- Phase 1: 3 次并行（可同时进行）
- Phase 2: 1 次
- Phase 3: 1 次

**预计执行时间**：
- Phase 1: ~3-5 秒（并行）
- Phase 2: ~2-3 秒
- Phase 3: ~3-5 秒
- **总计**: ~8-13 秒

---

### 工作流 2: 选股推荐

**触发条件**：
- API 请求包含 `criteria`
- 使用 `/workflows/stock-screening` 端点

**执行流程**：

```
Phase 1:
└─ StockScreeningAgent → MarketDataService.search_tickers()
    (无需 Gemini，使用数据库)
    ↓
Phase 2 (并行，对每个候选):
├─ FundamentalAnalyst → Gemini API 调用
└─ TechnicalAnalyst → Gemini API 调用
    (假设 10 个候选 = 20 次并行调用)
    ↓
Phase 3:
└─ StockRankingAgent → Gemini API 调用
    (综合所有分析)
    ↓
返回排序后的股票列表
```

**Gemini API 调用次数**：
- Phase 2: N × 2 次（N = 候选数量）
- Phase 3: 1 次
- **总计**: N × 2 + 1 次

**预计执行时间**：
- Phase 1: ~1 秒（数据库查询）
- Phase 2: ~5-10 秒（10 个候选，并行执行）
- Phase 3: ~3-5 秒
- **总计**: ~9-16 秒（10 个候选）

---

## 📊 数据流设计

### 输入数据流

```
API Request
    ↓
FastAPI Endpoint
    ↓
Request Validation (Pydantic)
    ↓
AIService.generate_report_with_agents()
    ↓
AgentCoordinator.coordinate_*()
    ↓
AgentContext (包含 input_data)
    ↓
各个 Agent.execute()
```

### 输出数据流

```
各个 Agent.execute()
    ↓
AgentResult (包含 data, success, error)
    ↓
AgentCoordinator 收集结果
    ↓
OptionsSynthesisAgent 综合
    ↓
最终 AgentResult
    ↓
AIService._format_agent_report()
    ↓
Markdown 报告 + 元数据
    ↓
API Response
```

---

## 🔧 配置设计

### Agent 配置

**全局配置**（`AIService` 初始化）：
```python
{
    "default_ai_provider": "gemini",  # 使用 Gemini
    "agent_framework_enabled": True,
    "default_workflow": "options_analysis"
}
```

**请求级配置**（API 请求）：
```json
{
    "use_multi_agent": true,
    "agent_config": {
        "timeout_seconds": 60,
        "max_parallel_agents": 5,
        "retry_failed_agents": false,
        "include_metadata": true
    }
}
```

### Gemini 配置

**现有配置**（`.env`）：
```bash
# Gemini API Key (支持两种格式)
# 1. Vertex AI Key (AQ.Ab...): 使用 Vertex AI HTTP 端点
# 2. Generative Language API Key (AIza...): 使用 google.generativeai SDK
GOOGLE_API_KEY=your_key_here

# AI Model (默认使用 Gemini 3.0 Pro)
AI_MODEL_DEFAULT=gemini-3.0-pro

# AI Provider (gemini 或 zenmux)
AI_PROVIDER=gemini
```

**Agent 使用**：
- 所有 Agent 共享同一个 `GeminiProvider` 实例（通过 `AIService._default_provider`）
- 使用相同的 API Key 和模型配置
- 每个 Agent 调用独立计数（用于配额管理）
- 支持 Vertex AI 和 Generative Language API 两种方式

---

## 🚦 错误处理和降级

### 错误处理策略

**1. Agent 执行失败**：
- 单个 Agent 失败不影响其他 Agent
- 失败的 Agent 结果标记为 `None`
- Synthesis Agent 处理部分结果

**2. Gemini API 失败**：
- 重试机制（最多 3 次）
- 如果所有重试失败，Agent 返回错误结果
- Coordinator 继续执行其他 Agent

**3. 超时处理**：
- 每个 Agent 有超时限制（默认 30 秒）
- 超时的 Agent 被标记为失败
- 整体工作流有总超时（默认 60 秒）

### 降级策略

**自动降级**：
1. 如果多 Agent 模式失败，自动降级到单 Agent 模式
2. 如果部分 Agent 失败，使用成功的 Agent 结果
3. 如果所有 Agent 失败，返回错误信息

**手动降级**：
- API 请求可以指定 `fallback_to_single_agent: true`
- 如果多 Agent 失败，自动使用单 Agent 模式

---

## 📈 性能考虑

### Gemini API 调用优化

**1. 并行调用**：
- Phase 1 的 3 个 Agent 并行执行
- 减少总执行时间

**2. 缓存策略**：
- 相同输入的 Agent 结果可以缓存
- 减少重复的 Gemini API 调用

**3. 批处理**（未来优化）：
- 如果 Gemini 支持批处理，可以批量发送请求

### 响应时间优化

**1. 流式响应**（未来）：
- 使用 Server-Sent Events (SSE) 流式返回结果
- 用户可以实时看到分析进度

**2. 异步处理**（未来）：
- 对于长时间运行的分析，使用后台任务
- 返回任务 ID，客户端轮询结果

---

## 🔐 安全和权限

### API 认证

**现有机制**：
- JWT Token 认证
- 用户权限验证（Pro/Free）

**Agent Framework 集成**：
- 使用相同的认证机制
- 不改变现有权限模型

### 配额管理

**Gemini API 配额影响**：
- **单 Agent 模式**：1 次 Gemini API 调用
- **多 Agent 模式（期权分析）**：5 次 Gemini API 调用
  - Phase 1: 3 次并行
  - Phase 2: 1 次
  - Phase 3: 1 次
- **多 Agent 模式（选股）**：N × 2 + 1 次（N = 候选数量）

**配额管理策略**：

1. **用户配额**（现有机制）：
   - Free 用户：1 次/天（单 Agent）
   - Pro Monthly：10 次/天（可支持多 Agent）
   - Pro Yearly：30 次/天（可支持多 Agent）

2. **多 Agent 模式配额**：
   - 建议：多 Agent 模式消耗 5 倍配额（5 次调用 = 5 次配额）
   - 或者：限制多 Agent 模式仅对 Pro 用户开放
   - 或者：多 Agent 模式单独配额（例如：2 次/天）

3. **配额检查时机**：
   - 在 API 端点中检查配额（现有机制）
   - 如果使用多 Agent 模式，检查是否有足够配额（5 次）
   - 如果配额不足，自动降级到单 Agent 模式

---

## 📝 API 文档设计

### 方案 1: 扩展现有端点（推荐）

**端点**：`POST /api/v1/ai/report`

**请求模型扩展**：

```python
class StrategyAnalysisRequest(BaseModel):
    strategy_summary: dict[str, Any] | None = None
    strategy_data: dict[str, Any] | None = None  # Legacy
    option_chain: dict[str, Any] | None = None   # Legacy
    
    # 新增参数
    use_multi_agent: bool = Field(
        False, 
        description="Whether to use multi-agent framework (default: false for backward compatibility)"
    )
    agent_config: dict[str, Any] | None = Field(
        None,
        description="Optional agent configuration (timeout, retry, etc.)"
    )
```

**响应模型扩展**：

```python
class AIReportResponse(BaseModel):
    id: str
    report_content: str
    model_used: str
    created_at: datetime
    
    # 新增字段（可选）
    metadata: dict[str, Any] | None = Field(
        None,
        description="Execution metadata (agent results, execution time, etc.)"
    )
```

---

### 方案 2: 新增专用端点

**端点**：`POST /api/v1/ai/report/multi-agent`

**请求模型**：

```python
class MultiAgentReportRequest(BaseModel):
    strategy_summary: dict[str, Any]
    workflow: str = Field(
        "options_analysis",
        enum=["options_analysis", "stock_screening"]
    )
    config: dict[str, Any] | None = None
```

**响应模型**：

```python
class MultiAgentReportResponse(BaseModel):
    report: str
    workflow: str
    agent_results: dict[str, Any]
    execution_summary: dict[str, Any]
    metadata: dict[str, Any]
```

---

### OpenAPI/Swagger 文档示例

```yaml
/api/v1/ai/report:
  post:
    summary: Generate AI analysis report (single or multi-agent)
    description: |
      Generate AI analysis report for an options strategy.
      
      **Single Agent Mode (default)**:
      - Uses single AI call
      - Fast response (~3-5 seconds)
      - Standard analysis
      
      **Multi-Agent Mode**:
      - Uses 5 specialized agents
      - Comprehensive analysis
      - Slower response (~8-13 seconds)
      - Consumes 5x API quota
    requestBody:
      required: true
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/StrategyAnalysisRequest'
    responses:
      200:
        description: Successfully generated report
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AIReportResponse'
      429:
        description: Quota exceeded
      500:
        description: AI service error
```

---

## 🧪 测试策略

### 单元测试

- 测试每个 Agent 的独立功能
- 测试 Coordinator 的工作流
- Mock Gemini API 调用

### 集成测试

- 测试完整的 API 端点
- 测试多 Agent 工作流
- 测试错误处理和降级

### 端到端测试

- 测试真实 Gemini API 调用（使用测试 Key）
- 验证报告质量
- 性能测试

---

## 🚀 实施计划

### Phase 1: 基础集成（1 周）

1. **GeminiProvider 扩展**（必须先完成）：
   - 在 `GeminiProvider.generate_report()` 中添加 Agent 模式支持
   - 检查 `_agent_analysis_request` 标志
   - 如果是 Agent 请求，使用 `_agent_prompt` 和 `_agent_system_prompt`
   - 直接调用 Gemini API（跳过策略分析模板）

2. **扩展现有端点**：
   - 在 `/api/v1/ai/report` 添加 `use_multi_agent` 参数
   - 修改 `StrategyAnalysisRequest` 模型添加可选参数
   - 在端点中调用 `generate_report_with_agents()`（已实现）
   - 保持向后兼容（默认 `use_multi_agent=false`）

3. **测试和验证**：
   - 测试 Gemini API 调用
   - 测试多 Agent 工作流
   - 测试降级机制

### Phase 2: 新端点（1 周）

1. **新端点实现**：
   - `/api/v1/ai/report/multi-agent`
   - `/api/v1/ai/workflows/options-analysis`
   - `/api/v1/ai/workflows/stock-screening`

2. **配置和文档**：
   - API 文档
   - 使用示例
   - 错误处理文档

### Phase 3: 优化（持续）

1. **性能优化**：
   - 缓存策略
   - 并行优化
   - 超时优化

2. **功能增强**：
   - 流式响应
   - 异步处理
   - 批处理支持

---

## 📋 关键决策点

### 1. API 设计选择

**推荐**：方案 3（混合方案）
- ✅ 向后兼容
- ✅ 灵活性高
- ✅ 渐进式迁移

### 2. Gemini 调用方式

**当前**：临时方案（使用 `generate_report()`）
- ✅ 快速实现
- ⚠️ 需要未来优化

**未来**：添加 `generate_text()` 方法
- ✅ 更清晰的接口
- ✅ 更好的类型安全

### 3. 错误处理策略

**推荐**：优雅降级
- ✅ 部分失败不影响整体
- ✅ 自动降级到单 Agent
- ✅ 用户友好的错误信息

---

## 🎯 成功标准

### 功能完整性

- ✅ 所有 Agent 正常工作
- ✅ 工作流正确执行
- ✅ 报告质量满足要求
- ✅ Gemini API 调用成功
- ✅ 降级机制正常工作

### 性能指标

- ✅ 多 Agent 模式响应时间 < 15 秒
- ✅ 单 Agent 模式响应时间 < 5 秒
- ✅ 错误率 < 1%
- ✅ Gemini API 调用成功率 > 99%

### 用户体验

- ✅ API 易于使用
- ✅ 清晰的错误信息
- ✅ 完整的文档
- ✅ 向后兼容（现有客户端无需修改）

### Gemini 集成

- ✅ 所有 Agent 使用 Gemini 3.0 Pro
- ✅ 支持 Vertex AI 和 Generative Language API
- ✅ 配额管理正确
- ✅ 错误处理和重试机制完善

---

## 🔑 关键实现要点

### 1. GeminiProvider 扩展（必须实现）

**位置**：`backend/app/services/ai/gemini_provider.py`

**设计要点**：

1. **检查 Agent 请求标志**：
   - 在 `generate_report()` 方法开始处检查 `_agent_analysis_request`
   - 如果为 `True`，进入 Agent 模式

2. **Agent 模式处理**：
   - 提取 `_agent_prompt` 作为用户提示
   - 提取 `_agent_system_prompt` 作为系统提示
   - 调用 `_call_ai_api()` 方法（需要支持 `system_prompt` 参数）
   - 跳过策略分析模板格式化

3. **普通模式**（保持现有逻辑）：
   - 使用策略分析模板
   - 格式化策略摘要
   - 调用 Gemini API

4. **`_call_ai_api()` 方法扩展**：
   - 需要支持可选的 `system_prompt` 参数
   - 如果提供 `system_prompt`，在 Gemini API 调用中包含
   - 如果不提供，使用默认行为

### 2. API 端点修改（必须实现）

**位置**：`backend/app/api/endpoints/ai.py`

**需要修改**：

1. **扩展 `StrategyAnalysisRequest` 模型**：
   - 添加 `use_multi_agent: bool = False` 字段（默认 False，向后兼容）
   - 添加 `agent_config: dict[str, Any] | None = None` 字段（可选配置）

2. **修改 `generate_ai_report()` 端点**：
   - 检查 `request.use_multi_agent` 参数
   - 如果为 `True`：
     - 检查配额（多 Agent 模式需要 5 倍配额）
     - 调用 `ai_service.generate_report_with_agents()`
     - 返回报告和元数据
   - 如果为 `False`：
     - 调用 `ai_service.generate_report()`（现有逻辑）
     - 保持现有响应格式

3. **配额管理逻辑**：
   - 多 Agent 模式：消耗 5 次配额
   - 如果配额不足，自动降级到单 Agent 模式
   - 记录日志说明降级原因

### 3. 配额管理（必须实现）

**位置**：`backend/app/api/endpoints/ai.py`

**设计要点**：

1. **配额检查时机**：
   - 在调用 AI Service 之前检查
   - 多 Agent 模式需要 5 次配额
   - 单 Agent 模式需要 1 次配额

2. **配额不足处理**：
   - 如果配额不足，自动降级到单 Agent 模式
   - 记录警告日志
   - 返回响应中包含 `metadata.fallback_reason`

3. **配额消耗**：
   - 单 Agent 模式：消耗 1 次配额（现有逻辑）
   - 多 Agent 模式：消耗 5 次配额（需要修改 `increment_ai_usage()` 逻辑）

4. **配额限制建议**：
   - Free 用户：仅支持单 Agent 模式
   - Pro 用户：支持多 Agent 模式（消耗 5 倍配额）
   - 或者：多 Agent 模式单独配额（例如：2 次/天）

---

## 📄 相关文档

- `docs/AGENT_FRAMEWORK_DESIGN.md` - 框架设计
- `docs/AGENT_FRAMEWORK_IMPLEMENTATION_SUMMARY.md` - 实施总结
- `docs/AGENT_CODE_REVIEW.md` - 代码审查
- `docs/AGENT_BUG_FIXES.md` - Bug 修复
- `docs/AGENT_FRAMEWORK_TEST_SUITE.md` - 测试套件

---

## ⚠️ 重要提醒

### 实施顺序

1. **第一步**：扩展 `GeminiProvider.generate_report()` 支持 Agent 模式
2. **第二步**：扩展 API 端点添加 `use_multi_agent` 参数
3. **第三步**：实现配额管理逻辑
4. **第四步**：测试和验证

### 注意事项

1. **向后兼容**：默认 `use_multi_agent=false`，确保现有客户端不受影响
2. **配额管理**：多 Agent 模式消耗更多配额，需要合理管理
3. **错误处理**：多 Agent 模式失败时自动降级到单 Agent 模式
4. **Gemini 配置**：确保 `GOOGLE_API_KEY` 和 `AI_PROVIDER=gemini` 正确配置

---

**最后更新**: 2025-01-18  
**版本**: v1.0  
**状态**: 📋 设计方案（待实现）
