# Agent Framework 异步处理集成

## 概述

本文档描述了 Agent Framework 与现有 Task 系统的异步处理集成实现。该集成允许长时间运行的 Agent 工作流在后台异步执行，避免 HTTP 请求超时，并提供实时进度更新。

## 实现状态

✅ **已完成** - 所有核心功能已实现并集成到现有 Task 系统

## 核心功能

### 1. 异步任务类型

在 `process_task_async` 中添加了三个新的 task_type：

- **`multi_agent_report`**: 多 Agent 报告生成（异步）
- **`options_analysis_workflow`**: 期权分析工作流（异步）
- **`stock_screening_workflow`**: 股票筛选工作流（异步）

### 2. API 端点异步支持

所有 Agent 相关的 API 端点现在都支持 `async_mode` 参数：

#### `/api/v1/ai/report` (POST)
- **参数**: `async_mode: bool` (默认: `false`)
- **同步模式**: 立即返回 `AIReportResponse`
- **异步模式**: 返回 `TaskResponse`，包含 `task_id` 用于轮询

#### `/api/v1/ai/workflows/options-analysis` (POST)
- **参数**: `async_mode: bool` (默认: `false`)
- **同步模式**: 立即返回 `OptionsAnalysisWorkflowResponse`
- **异步模式**: 返回 `TaskResponse`

#### `/api/v1/ai/workflows/stock-screening` (POST)
- **参数**: `async_mode: bool` (默认: `false`)
- **同步模式**: 立即返回 `StockScreeningResponse`
- **异步模式**: 返回 `TaskResponse`

### 3. 进度回调机制

所有异步任务都实现了进度回调，实时更新 Task 的 `execution_history`：

```python
def progress_callback(progress: int, message: str) -> None:
    """Update task progress in database."""
    # 异步更新 Task execution_history
    # 进度信息存储在 execution_history 中，类型为 "progress"
```

**进度更新示例**:
- `[10%] Phase 1: Parallel analysis (Greeks, IV, Market)...`
- `[60%] Phase 2: Risk scenario analysis...`
- `[80%] Phase 3: Synthesizing final report...`
- `[100%] Options analysis complete`

### 4. 配额管理

异步任务在创建前会检查配额，确保有足够的配额执行任务：

- **multi_agent_report**: 5 配额单位（多 Agent 模式）或 1 配额单位（单 Agent 模式）
- **options_analysis_workflow**: 5 配额单位（固定）
- **stock_screening_workflow**: 动态配额（`min(5, 2 + (limit * 2) // 10)`）

如果配额不足，会自动降级到单 Agent 模式（对于 multi_agent_report）或抛出 429 错误。

## 使用示例

### 1. 异步生成多 Agent 报告

```python
# 请求
POST /api/v1/ai/report
{
    "strategy_summary": {...},
    "use_multi_agent": true,
    "async_mode": true
}

# 响应 (立即返回)
{
    "id": "task-uuid",
    "task_type": "multi_agent_report",
    "status": "PENDING",
    "created_at": "2024-01-01T00:00:00Z",
    ...
}

# 轮询任务状态
GET /api/v1/tasks/{task_id}

# 任务完成后的响应
{
    "id": "task-uuid",
    "status": "SUCCESS",
    "result_ref": "ai-report-uuid",  # 报告 ID
    "execution_history": [
        {"type": "start", "message": "Task processing started", ...},
        {"type": "progress", "message": "[10%] Phase 1: Parallel analysis...", ...},
        {"type": "progress", "message": "[60%] Phase 2: Risk scenario analysis...", ...},
        {"type": "success", "message": "Multi-agent report generated successfully...", ...}
    ],
    ...
}
```

### 2. 异步执行期权分析工作流

```python
# 请求
POST /api/v1/ai/workflows/options-analysis
{
    "strategy_summary": {...},
    "include_metadata": true,
    "async_mode": true
}

# 响应
{
    "id": "task-uuid",
    "task_type": "options_analysis_workflow",
    "status": "PENDING",
    ...
}
```

### 3. 异步执行股票筛选工作流

```python
# 请求
POST /api/v1/ai/workflows/stock-screening
{
    "sector": "Technology",
    "limit": 20,
    "async_mode": true
}

# 响应
{
    "id": "task-uuid",
    "task_type": "stock_screening_workflow",
    "status": "PENDING",
    ...
}

# 任务完成后，结果存储在 task.metadata.candidates 中
```

## 实现细节

### Task 处理流程

1. **任务创建**: API 端点检查配额，创建 Task 记录（状态: `PENDING`）
2. **后台处理**: `create_task_async` 启动后台任务
3. **状态更新**: `process_task_async` 更新状态为 `PROCESSING`
4. **进度更新**: 通过 `progress_callback` 实时更新 `execution_history`
5. **结果保存**: 
   - `multi_agent_report` 和 `options_analysis_workflow`: 保存到 `AIReport` 表，`result_ref` 指向报告 ID
   - `stock_screening_workflow`: 结果存储在 `task.task_metadata.candidates` 中
6. **完成**: 状态更新为 `SUCCESS` 或 `FAILED`

### 错误处理

- **配额不足**: 自动降级（multi_agent_report）或抛出 429 错误
- **Agent 框架不可用**: 抛出 503 错误
- **处理失败**: Task 状态更新为 `FAILED`，错误信息存储在 `error_message`

### 兼容性

- ✅ **向后兼容**: 默认 `async_mode=false`，现有 API 调用不受影响
- ✅ **现有 Task 系统**: 完全兼容现有 Task 逻辑和数据结构
- ✅ **进度追踪**: 使用现有的 `execution_history` 字段，无需额外表结构

## 文件修改清单

### 核心文件

1. **`backend/app/api/endpoints/tasks.py`**
   - 添加了三个新的 task_type 处理逻辑
   - 实现了进度回调更新机制
   - 集成了配额检查和增量

2. **`backend/app/api/endpoints/ai.py`**
   - 为所有 Agent 相关端点添加了 `async_mode` 参数
   - 实现了异步任务创建逻辑
   - 更新了响应类型（支持 `TaskResponse`）

3. **`backend/app/api/schemas/__init__.py`**
   - 更新了请求模型，添加 `async_mode` 字段
   - 更新了响应类型注解（支持联合类型）

4. **`backend/app/db/models.py`**
   - 修复了 Task 模型中重复的 `user_id` 字段定义

## 测试建议

### 单元测试

1. 测试异步任务创建
2. 测试进度回调更新
3. 测试配额检查和降级逻辑
4. 测试错误处理

### 集成测试

1. 端到端异步工作流测试
2. 任务状态轮询测试
3. 进度更新实时性测试

### 手动测试

```bash
# 1. 创建异步任务
curl -X POST http://localhost:8000/api/v1/ai/report \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_summary": {...},
    "use_multi_agent": true,
    "async_mode": true
  }'

# 2. 轮询任务状态
curl http://localhost:8000/api/v1/tasks/{task_id} \
  -H "Authorization: Bearer $TOKEN"

# 3. 获取结果（任务完成后）
curl http://localhost:8000/api/v1/ai/reports/{result_ref} \
  -H "Authorization: Bearer $TOKEN"
```

## 性能考虑

- **并发处理**: 使用 FastAPI 的异步特性，支持高并发任务创建
- **进度更新**: 异步更新，不阻塞主任务执行
- **资源管理**: 每个任务使用独立的数据库会话，避免会话冲突

## 未来优化

1. **WebSocket 支持**: 实时推送进度更新，替代轮询
2. **任务队列**: 使用 Celery 或类似工具处理大量并发任务
3. **结果缓存**: 缓存相同策略的分析结果
4. **批量处理**: 支持批量创建异步任务

## 总结

Agent Framework 异步处理集成已完全实现，与现有 Task 系统无缝集成。所有 Agent 工作流现在都支持异步执行，提供实时进度更新，并完全兼容现有 API 和数据结构。
