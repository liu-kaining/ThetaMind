# 如何运行 test_agent_endpoints.py

**文件位置**: `backend/tests/api/test_agent_endpoints.py`

---

## 📋 前置条件

### 1. 安装依赖

```bash
cd backend

# 安装项目依赖
pip install -r requirements.txt

# 安装测试依赖（如果还没有）
pip install pytest pytest-asyncio
```

### 2. 检查依赖

测试需要以下 Python 包：
- `pytest` - 测试框架
- `pytest-asyncio` - 异步测试支持
- `unittest.mock` - Mock 工具（Python 标准库）

---

## 🚀 运行测试

### 方法 1: 运行整个测试文件

```bash
cd backend
pytest tests/api/test_agent_endpoints.py -v
```

**参数说明**:
- `-v` 或 `--verbose`: 显示详细输出
- `-s`: 显示 print 输出（如果需要）
- `--tb=short`: 简短的错误追踪

### 方法 2: 运行特定的测试类

```bash
# 运行 Phase 1 测试
pytest tests/api/test_agent_endpoints.py::TestPhase1Endpoints -v

# 运行 Phase 2 测试
pytest tests/api/test_agent_endpoints.py::TestPhase2Endpoints -v

# 运行集成测试
pytest tests/api/test_agent_endpoints.py::TestIntegration -v
```

### 方法 3: 运行特定的测试函数

```bash
# 测试单 Agent 模式
pytest tests/api/test_agent_endpoints.py::TestPhase1Endpoints::test_single_agent_mode -v

# 测试多 Agent 模式
pytest tests/api/test_agent_endpoints.py::TestPhase1Endpoints::test_multi_agent_mode -v

# 测试配额管理
pytest tests/api/test_agent_endpoints.py::TestPhase1Endpoints::test_quota_management -v

# 测试多 Agent 端点
pytest tests/api/test_agent_endpoints.py::TestPhase2Endpoints::test_multi_agent_endpoint -v
```

### 方法 4: 运行所有相关测试

```bash
# 运行所有 Agent 相关测试
pytest tests/ -k "agent" -v

# 运行所有 API 端点测试
pytest tests/api/ -v
```

---

## 📊 测试输出示例

### 成功运行示例

```
============================= test session starts ==============================
platform darwin -- Python 3.11.0, pytest-7.4.3, pytest-asyncio-0.21.1
collected 12 items

tests/api/test_agent_endpoints.py::TestPhase1Endpoints::test_single_agent_mode PASSED
tests/api/test_agent_endpoints.py::TestPhase1Endpoints::test_multi_agent_mode PASSED
tests/api/test_agent_endpoints.py::TestPhase1Endpoints::test_quota_management PASSED
tests/api/test_agent_endpoints.py::TestPhase1Endpoints::test_quota_insufficient_fallback PASSED
tests/api/test_agent_endpoints.py::TestPhase2Endpoints::test_multi_agent_endpoint PASSED
tests/api/test_agent_endpoints.py::TestPhase2Endpoints::test_options_workflow_endpoint PASSED
tests/api/test_agent_endpoints.py::TestPhase2Endpoints::test_stock_screening_endpoint PASSED
tests/api/test_agent_endpoints::TestPhase2Endpoints::test_agent_list_endpoint PASSED
tests/api/test_agent_endpoints.py::TestIntegration::test_full_workflow_single_agent PASSED
tests/api/test_agent_endpoints.py::TestIntegration::test_full_workflow_multi_agent PASSED
tests/api/test_agent_endpoints.py::TestIntegration::test_error_handling_and_fallback PASSED
tests/api/test_agent_endpoints.py::TestGeminiProviderIntegration::test_agent_mode_detection PASSED

============================== 12 passed in 2.34s ===============================
```

---

## 🔧 常用 pytest 选项

### 显示详细输出

```bash
pytest tests/api/test_agent_endpoints.py -v -s
```

### 只运行失败的测试

```bash
pytest tests/api/test_agent_endpoints.py --lf
```

### 在第一个失败时停止

```bash
pytest tests/api/test_agent_endpoints.py -x
```

### 显示覆盖率

```bash
pytest tests/api/test_agent_endpoints.py --cov=app.api.endpoints.ai --cov-report=html
```

### 并行运行（需要 pytest-xdist）

```bash
pip install pytest-xdist
pytest tests/api/test_agent_endpoints.py -n auto
```

---

## 🐛 常见问题

### 问题 1: ModuleNotFoundError

**错误**:
```
ModuleNotFoundError: No module named 'pytest'
```

**解决方案**:
```bash
pip install pytest pytest-asyncio
```

### 问题 2: 导入错误

**错误**:
```
ImportError: cannot import name 'StrategyAnalysisRequest' from 'app.api.endpoints.ai'
```

**解决方案**:
确保在 `backend` 目录下运行，并且 Python 路径正确：
```bash
cd backend
export PYTHONPATH=$PWD:$PYTHONPATH
pytest tests/api/test_agent_endpoints.py -v
```

### 问题 3: 异步测试错误

**错误**:
```
RuntimeError: Event loop is closed
```

**解决方案**:
确保安装了 `pytest-asyncio`:
```bash
pip install pytest-asyncio
```

### 问题 4: 环境变量缺失

**错误**:
```
pydantic_core._pydantic_core.ValidationError: Field required
```

**解决方案**:
测试使用 Mock，不需要真实环境变量。如果遇到此错误，可能需要设置测试环境变量或使用 `.env.test` 文件。

---

## 📝 测试结构

### 测试类

1. **TestPhase1Endpoints**: Phase 1 基础集成测试
   - `test_single_agent_mode`: 单 Agent 模式
   - `test_multi_agent_mode`: 多 Agent 模式
   - `test_quota_management`: 配额管理
   - `test_quota_insufficient_fallback`: 配额不足降级

2. **TestPhase2Endpoints**: Phase 2 新端点测试
   - `test_multi_agent_endpoint`: Multi-agent 端点
   - `test_options_workflow_endpoint`: 期权工作流端点
   - `test_stock_screening_endpoint`: 选股端点
   - `test_agent_list_endpoint`: Agent 列表端点

3. **TestIntegration**: 集成测试
   - `test_full_workflow_single_agent`: 完整单 Agent 工作流
   - `test_full_workflow_multi_agent`: 完整多 Agent 工作流
   - `test_error_handling_and_fallback`: 错误处理和降级

4. **TestGeminiProviderIntegration**: GeminiProvider 集成测试
   - `test_agent_mode_detection`: Agent 模式检测
   - `test_system_prompt_support`: System prompt 支持

---

## 🎯 快速开始

### 最简单的运行方式

```bash
cd backend
pytest tests/api/test_agent_endpoints.py -v
```

### 查看测试帮助

```bash
pytest --help
```

### 查看测试列表（不运行）

```bash
pytest tests/api/test_agent_endpoints.py --collect-only
```

---

## 💡 提示

1. **使用虚拟环境**: 建议在虚拟环境中运行测试
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   venv\Scripts\activate  # Windows
   pip install -r requirements.txt pytest pytest-asyncio
   ```

2. **IDE 集成**: 大多数 IDE（如 PyCharm、VSCode）都支持直接运行 pytest 测试

3. **持续集成**: 可以将测试添加到 CI/CD 流程中

---

## 📚 相关文档

- `docs/AGENT_FRAMEWORK_TESTING_GUIDE.md` - 完整测试指南
- `docs/AGENT_FRAMEWORK_TESTING_SUMMARY.md` - 测试总结
- `backend/tests/README.md` - 测试目录说明

---

**最后更新**: 2025-01-18  
**版本**: v1.0
