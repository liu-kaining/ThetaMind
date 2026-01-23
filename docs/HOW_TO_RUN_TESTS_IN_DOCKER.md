# 如何在 Docker 中运行测试

**文件**: `tests/api/test_agent_endpoints.py`

---

## 🐳 Docker 环境测试指南

### 方法 1: 进入运行中的容器执行测试

#### 步骤 1: 查看运行中的容器

```bash
# 查看所有运行中的容器
docker ps

# 或者查看 docker-compose 服务
docker-compose ps
```

#### 步骤 2: 进入容器

```bash
# 如果使用 docker-compose
docker-compose exec backend bash

# 或者直接使用容器名称/ID
docker exec -it <container_name_or_id> bash
```

#### 步骤 3: 在容器内运行测试

```bash
# 进入容器后，运行测试
cd /app  # 或容器内的工作目录
pytest tests/api/test_agent_endpoints.py -v
```

---

### 方法 2: 使用 docker-compose exec 直接运行

```bash
# 直接运行测试，不需要进入容器
docker-compose exec backend pytest tests/api/test_agent_endpoints.py -v

# 或者指定完整路径
docker-compose exec backend pytest /app/tests/api/test_agent_endpoints.py -v
```

---

### 方法 3: 使用 docker run 运行一次性测试

```bash
# 从 docker-compose 获取服务名
docker-compose run --rm backend pytest tests/api/test_agent_endpoints.py -v

# 或者使用镜像直接运行
docker run --rm -it \
  --env-file .env \
  <your_image_name> \
  pytest tests/api/test_agent_endpoints.py -v
```

---

## 📋 完整示例

### 示例 1: 使用 docker-compose

```bash
# 1. 确保服务正在运行
docker-compose up -d

# 2. 运行测试
docker-compose exec backend pytest tests/api/test_agent_endpoints.py -v

# 3. 运行特定测试类
docker-compose exec backend pytest tests/api/test_agent_endpoints.py::TestPhase1Endpoints -v

# 4. 运行特定测试函数
docker-compose exec backend pytest tests/api/test_agent_endpoints.py::TestPhase1Endpoints::test_single_agent_mode -v
```

### 示例 2: 进入容器交互式运行

```bash
# 1. 进入容器
docker-compose exec backend bash

# 2. 在容器内运行测试
pytest tests/api/test_agent_endpoints.py -v

# 3. 运行所有 Agent 相关测试
pytest tests/ -k "agent" -v

# 4. 运行并查看覆盖率
pytest tests/api/test_agent_endpoints.py --cov=app.api.endpoints.ai --cov-report=term-missing

# 5. 退出容器
exit
```

---

## 🔧 常用 Docker 测试命令

### 运行所有测试

```bash
docker-compose exec backend pytest tests/ -v
```

### 运行 API 测试

```bash
docker-compose exec backend pytest tests/api/ -v
```

### 运行 Agent 相关测试

```bash
docker-compose exec backend pytest tests/ -k "agent" -v
```

### 运行并显示详细输出

```bash
docker-compose exec backend pytest tests/api/test_agent_endpoints.py -v -s
```

### 运行并生成覆盖率报告

```bash
docker-compose exec backend pytest tests/api/test_agent_endpoints.py --cov=app --cov-report=html
```

### 在第一个失败时停止

```bash
docker-compose exec backend pytest tests/api/test_agent_endpoints.py -x
```

---

## 🐛 常见问题

### 问题 1: 容器未运行

**错误**:
```
Error: No such container
```

**解决方案**:
```bash
# 启动容器
docker-compose up -d

# 或者重新构建并启动
docker-compose up -d --build
```

### 问题 2: 找不到 pytest

**错误**:
```
pytest: command not found
```

**解决方案**:
```bash
# 检查 pytest 是否安装
docker-compose exec backend pip list | grep pytest

# 如果没有，安装它
docker-compose exec backend pip install pytest pytest-asyncio
```

### 问题 3: 路径问题

**错误**:
```
ModuleNotFoundError: No module named 'app'
```

**解决方案**:
```bash
# 确保在正确的工作目录
docker-compose exec backend bash -c "cd /app && pytest tests/api/test_agent_endpoints.py -v"

# 或者设置 PYTHONPATH
docker-compose exec backend bash -c "export PYTHONPATH=/app && pytest tests/api/test_agent_endpoints.py -v"
```

### 问题 4: 权限问题

**错误**:
```
Permission denied
```

**解决方案**:
```bash
# 检查文件权限
docker-compose exec backend ls -la tests/api/test_agent_endpoints.py

# 如果需要，修改权限
docker-compose exec backend chmod +x tests/api/test_agent_endpoints.py
```

---

## 📝 创建测试脚本

### 在容器内创建测试脚本

```bash
# 进入容器
docker-compose exec backend bash

# 创建测试脚本
cat > /app/run_tests.sh << 'EOF'
#!/bin/bash
set -e

echo "Running Agent Framework tests..."
pytest tests/api/test_agent_endpoints.py -v

echo "Running integration tests..."
pytest tests/api/test_agent_integration.py -v

echo "All tests completed!"
EOF

# 添加执行权限
chmod +x /app/run_tests.sh

# 运行脚本
/app/run_tests.sh
```

### 从宿主机运行脚本

```bash
# 在项目根目录创建脚本
cat > run_tests_in_docker.sh << 'EOF'
#!/bin/bash
set -e

echo "Running tests in Docker container..."
docker-compose exec backend pytest tests/api/test_agent_endpoints.py -v
EOF

chmod +x run_tests_in_docker.sh
./run_tests_in_docker.sh
```

---

## 🎯 推荐的测试流程

### 1. 快速测试（单个测试）

```bash
docker-compose exec backend pytest tests/api/test_agent_endpoints.py::TestPhase1Endpoints::test_single_agent_mode -v
```

### 2. 完整测试（所有测试）

```bash
docker-compose exec backend pytest tests/api/test_agent_endpoints.py -v
```

### 3. 带覆盖率的测试

```bash
docker-compose exec backend pytest tests/api/test_agent_endpoints.py \
  --cov=app.api.endpoints.ai \
  --cov=app.services.ai_service \
  --cov-report=term-missing \
  -v
```

### 4. 并行测试（如果安装了 pytest-xdist）

```bash
docker-compose exec backend pip install pytest-xdist
docker-compose exec backend pytest tests/api/test_agent_endpoints.py -n auto -v
```

---

## 🔍 调试技巧

### 查看容器日志

```bash
# 查看所有日志
docker-compose logs backend

# 实时查看日志
docker-compose logs -f backend

# 查看最近的日志
docker-compose logs --tail=100 backend
```

### 检查容器环境

```bash
# 进入容器检查环境
docker-compose exec backend bash

# 检查 Python 版本
python --version

# 检查已安装的包
pip list | grep pytest

# 检查工作目录
pwd

# 检查文件是否存在
ls -la tests/api/test_agent_endpoints.py

# 检查 Python 路径
python -c "import sys; print('\n'.join(sys.path))"
```

### 运行单个测试并查看详细输出

```bash
docker-compose exec backend pytest tests/api/test_agent_endpoints.py::TestPhase1Endpoints::test_single_agent_mode -v -s --tb=long
```

---

## 📊 测试输出示例

### 成功运行示例

```
backend_1  | ============================= test session starts ==============================
backend_1  | platform linux -- Python 3.11.0, pytest-7.4.3, pytest-asyncio-0.21.1
backend_1  | collected 12 items
backend_1  | 
backend_1  | tests/api/test_agent_endpoints.py::TestPhase1Endpoints::test_single_agent_mode PASSED
backend_1  | tests/api/test_agent_endpoints.py::TestPhase1Endpoints::test_multi_agent_mode PASSED
backend_1  | tests/api/test_agent_endpoints.py::TestPhase1Endpoints::test_quota_management PASSED
backend_1  | tests/api/test_agent_endpoints.py::TestPhase1Endpoints::test_quota_insufficient_fallback PASSED
backend_1  | tests/api/test_agent_endpoints.py::TestPhase2Endpoints::test_multi_agent_endpoint PASSED
backend_1  | tests/api/test_agent_endpoints.py::TestPhase2Endpoints::test_options_workflow_endpoint PASSED
backend_1  | tests/api/test_agent_endpoints.py::TestPhase2Endpoints::test_stock_screening_endpoint PASSED
backend_1  | tests/api/test_agent_endpoints.py::TestPhase2Endpoints::test_agent_list_endpoint PASSED
backend_1  | 
backend_1  | ============================== 12 passed in 2.34s ===============================
```

---

## 🚀 快速参考

### 最常用的命令

```bash
# 运行测试（最简单）
docker-compose exec backend pytest tests/api/test_agent_endpoints.py -v

# 进入容器
docker-compose exec backend bash

# 查看日志
docker-compose logs -f backend
```

---

## 💡 提示

1. **使用别名**: 可以创建 shell 别名简化命令
   ```bash
   alias dtest='docker-compose exec backend pytest tests/api/test_agent_endpoints.py -v'
   dtest
   ```

2. **使用 Makefile**: 可以创建 Makefile 简化命令
   ```makefile
   test:
       docker-compose exec backend pytest tests/api/test_agent_endpoints.py -v
   
   test-all:
       docker-compose exec backend pytest tests/ -k "agent" -v
   ```

3. **IDE 集成**: 某些 IDE 支持直接连接到 Docker 容器运行测试

---

## 📚 相关文档

- `docs/HOW_TO_RUN_TEST_AGENT_ENDPOINTS.md` - 本地运行测试指南
- `docs/AGENT_FRAMEWORK_TESTING_GUIDE.md` - 完整测试指南
- `backend/tests/README.md` - 测试目录说明

---

**最后更新**: 2025-01-18  
**版本**: v1.0
