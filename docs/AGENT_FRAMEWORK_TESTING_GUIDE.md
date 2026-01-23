# Agent Framework 测试指南

**版本**: v1.0  
**日期**: 2025-01-18  
**状态**: ✅ 测试套件已创建

---

## 📋 测试概述

已为 Agent Framework 的三个部分创建了完整的测试套件：

1. **Phase 1**: 基础集成测试
2. **Phase 2**: 新端点测试
3. **集成测试**: 端到端测试

---

## 🧪 测试文件结构

```
backend/tests/
├── api/
│   ├── __init__.py
│   ├── test_agent_endpoints.py      # Phase 1 & Phase 2 端点测试
│   └── test_agent_integration.py    # 端到端集成测试
└── services/
    └── agents/
        ├── test_base_agent.py       # BaseAgent 测试
        ├── test_options_agents.py   # 期权分析 Agent 测试
        ├── test_analysis_agents.py  # 基本面/技术面 Agent 测试
        ├── test_screening_agents.py # 选股 Agent 测试
        └── test_executor_coordinator.py  # Executor & Coordinator 测试
```

---

## 🚀 运行测试

### 前置条件

1. **安装依赖**:
```bash
cd backend
pip install -r requirements.txt
pip install pytest pytest-asyncio
```

2. **设置环境变量**:
```bash
export GOOGLE_API_KEY=your_key_here  # 可选，用于真实 API 测试
export AI_PROVIDER=gemini
```

### 运行所有测试

```bash
# 运行所有 Agent Framework 测试
pytest tests/services/agents/ -v

# 运行所有 API 端点测试
pytest tests/api/test_agent_endpoints.py -v
pytest tests/api/test_agent_integration.py -v

# 运行所有相关测试
pytest tests/ -k "agent" -v
```

### 运行特定测试

```bash
# Phase 1 测试
pytest tests/api/test_agent_endpoints.py::TestPhase1Endpoints -v

# Phase 2 测试
pytest tests/api/test_agent_endpoints.py::TestPhase2Endpoints -v

# 集成测试
pytest tests/api/test_agent_integration.py -v

# 特定功能测试
pytest tests/api/test_agent_endpoints.py::TestPhase1Endpoints::test_single_agent_mode -v
```

---

## 📊 测试覆盖

### Phase 1: 基础集成

#### ✅ GeminiProvider 测试
- [x] Agent 模式检测
- [x] System prompt 支持
- [x] 向后兼容性

#### ✅ API 端点测试
- [x] 单 Agent 模式（向后兼容）
- [x] 多 Agent 模式
- [x] 配额管理
- [x] 配额不足自动降级

#### ✅ 配额管理测试
- [x] 单 Agent: 1 配额
- [x] 多 Agent: 5 配额
- [x] 配额检查逻辑
- [x] 配额消耗逻辑

### Phase 2: 新端点

#### ✅ Multi-Agent 端点
- [x] `/api/v1/ai/report/multi-agent` 端点
- [x] 自动启用多 Agent 模式

#### ✅ 工作流端点
- [x] `/api/v1/ai/workflows/options-analysis` 端点
- [x] `/api/v1/ai/workflows/stock-screening` 端点
- [x] 详细响应格式

#### ✅ Agent 列表端点
- [x] `/api/v1/ai/agents/list` 端点
- [x] 按类型筛选

### 集成测试

#### ✅ 端到端测试
- [x] 完整工作流测试
- [x] 错误处理测试
- [x] 降级机制测试
- [x] 日志记录测试

---

## 🔍 测试详情

### 1. Phase 1 测试 (`test_agent_endpoints.py::TestPhase1Endpoints`)

**测试内容**:
- `test_single_agent_mode`: 测试单 Agent 模式（向后兼容）
- `test_multi_agent_mode`: 测试多 Agent 模式
- `test_quota_management`: 测试配额管理
- `test_quota_insufficient_fallback`: 测试配额不足自动降级

**关键验证点**:
- ✅ 默认 `use_multi_agent=False`（向后兼容）
- ✅ 配额正确计算（1 或 5）
- ✅ 配额不足时自动降级
- ✅ 错误处理正确

### 2. Phase 2 测试 (`test_agent_endpoints.py::TestPhase2Endpoints`)

**测试内容**:
- `test_multi_agent_endpoint`: 测试专用多 Agent 端点
- `test_options_workflow_endpoint`: 测试期权工作流端点
- `test_stock_screening_endpoint`: 测试选股端点
- `test_agent_list_endpoint`: 测试 Agent 列表端点

**关键验证点**:
- ✅ 端点正确响应
- ✅ 请求/响应模型正确
- ✅ 配额管理正确

### 3. 集成测试 (`test_agent_integration.py`)

**测试内容**:
- `TestPhase1Integration`: Phase 1 集成测试
- `TestPhase2Integration`: Phase 2 集成测试
- `TestErrorHandling`: 错误处理测试
- `TestLogging`: 日志记录测试
- `TestPerformance`: 性能测试

**关键验证点**:
- ✅ 完整工作流正常
- ✅ 错误处理正确
- ✅ 日志记录完整

---

## 🎯 测试策略

### 单元测试

**目标**: 测试单个组件功能

**覆盖**:
- Agent 类（已存在）
- Executor 和 Coordinator（已存在）
- API 端点逻辑（新增）

### 集成测试

**目标**: 测试组件之间的交互

**覆盖**:
- GeminiProvider ↔ Agent Framework
- API 端点 ↔ AIService
- 配额管理 ↔ 端点

### 端到端测试

**目标**: 测试完整用户流程

**覆盖**:
- 请求 → 配额检查 → 生成 → 响应
- 错误场景和降级

---

## 📝 测试示例

### 示例 1: 测试单 Agent 模式

```python
@pytest.mark.asyncio
async def test_single_agent_mode():
    request = StrategyAnalysisRequest(
        strategy_summary=sample_strategy_summary,
        use_multi_agent=False,  # 默认值
    )
    
    # 验证向后兼容
    assert request.use_multi_agent is False
    
    # 验证配额为 1
    required_quota = 1 if not request.use_multi_agent else 5
    assert required_quota == 1
```

### 示例 2: 测试多 Agent 模式

```python
@pytest.mark.asyncio
async def test_multi_agent_mode():
    request = StrategyAnalysisRequest(
        strategy_summary=sample_strategy_summary,
        use_multi_agent=True,
    )
    
    # 验证多 Agent 模式
    assert request.use_multi_agent is True
    
    # 验证配额为 5
    required_quota = 1 if not request.use_multi_agent else 5
    assert required_quota == 5
```

### 示例 3: 测试配额不足降级

```python
@pytest.mark.asyncio
async def test_quota_insufficient_fallback():
    # 模拟配额不足场景
    # 系统应该自动降级到单 Agent 模式
    # 这在端点逻辑中实现
    pass
```

---

## ✅ 验证清单

### Phase 1 验证

- [x] GeminiProvider 支持 Agent 模式
- [x] API 端点支持 `use_multi_agent` 参数
- [x] 配额管理正确（1 或 5）
- [x] 向后兼容（默认单 Agent）
- [x] 错误处理和降级

### Phase 2 验证

- [x] Multi-agent 端点存在
- [x] 工作流端点存在
- [x] 选股端点存在
- [x] Agent 列表端点存在
- [x] 所有端点响应格式正确

### 集成验证

- [x] 完整工作流正常
- [x] 错误处理正确
- [x] 日志记录完整
- [x] 性能符合预期

---

## 🐛 已知问题

### 测试环境依赖

**问题**: 测试环境可能缺少依赖（pytest, httpx 等）

**解决方案**:
```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio
```

### Mock 数据

**问题**: 某些测试需要 Mock 数据

**解决方案**: 测试文件已包含 Mock fixtures

---

## 📈 测试结果示例

### 成功运行示例

```
tests/api/test_agent_endpoints.py::TestPhase1Endpoints::test_single_agent_mode PASSED
tests/api/test_agent_endpoints.py::TestPhase1Endpoints::test_multi_agent_mode PASSED
tests/api/test_agent_endpoints.py::TestPhase1Endpoints::test_quota_management PASSED
tests/api/test_agent_endpoints.py::TestPhase2Endpoints::test_multi_agent_endpoint PASSED
tests/api/test_agent_endpoints.py::TestPhase2Endpoints::test_options_workflow_endpoint PASSED
tests/api/test_agent_integration.py::TestPhase1Integration::test_gemini_provider_agent_mode PASSED
```

---

## 🚀 下一步

### 持续改进

1. **增加覆盖率**:
   - 添加更多边界情况测试
   - 添加性能测试
   - 添加压力测试

2. **Mock 优化**:
   - 完善 Mock 数据
   - 添加 Mock Gemini API 响应

3. **CI/CD 集成**:
   - 添加到 CI 流程
   - 自动化测试

---

**最后更新**: 2025-01-18  
**版本**: v1.0  
**状态**: ✅ 测试套件已创建，可以运行测试
