# Docker 测试问题修复

**问题**: `pytest: executable file not found in $PATH`

**原因**: Docker 容器内没有安装 pytest（它是开发依赖，不在 requirements.txt 中）

---

## 🔧 解决方案

### 方案 1: 临时安装（快速解决）

在容器内临时安装 pytest：

```bash
# 进入容器
docker-compose exec backend bash

# 安装 pytest
pip install pytest pytest-asyncio

# 运行测试
pytest tests/api/test_agent_endpoints.py -v

# 退出容器
exit
```

或者一行命令：

```bash
docker-compose exec backend pip install pytest pytest-asyncio && \
docker-compose exec backend pytest tests/api/test_agent_endpoints.py -v
```

### 方案 2: 修改 Dockerfile（永久解决）✅

我已经修改了 `backend/Dockerfile`，添加了 pytest 安装。

**需要重新构建镜像**：

```bash
# 重新构建并启动
docker-compose up -d --build backend

# 然后运行测试
docker-compose exec backend pytest tests/api/test_agent_endpoints.py -v
```

### 方案 3: 使用 python -m pytest

如果 pytest 已安装但不在 PATH 中：

```bash
docker-compose exec backend python -m pytest tests/api/test_agent_endpoints.py -v
```

---

## 🚀 推荐操作步骤

### 立即运行测试（临时方案）

```bash
# 1. 在容器内安装 pytest
docker-compose exec backend pip install pytest pytest-asyncio

# 2. 运行测试
docker-compose exec backend pytest tests/api/test_agent_endpoints.py -v
```

### 永久解决（推荐）

```bash
# 1. 重新构建镜像（已修改 Dockerfile）
docker-compose build backend

# 2. 重启容器
docker-compose up -d backend

# 3. 运行测试
docker-compose exec backend pytest tests/api/test_agent_endpoints.py -v
```

---

## ✅ 验证

运行以下命令验证 pytest 已安装：

```bash
# 检查 pytest 是否安装
docker-compose exec backend pytest --version

# 或者
docker-compose exec backend python -m pytest --version
```

---

**最后更新**: 2025-01-18
