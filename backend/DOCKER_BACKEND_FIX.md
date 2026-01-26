# Docker Backend 容器未启动 - 修复指南

## 🔴 问题

从 `docker ps` 输出可以看到：
- ✅ `thetamind-frontend` - 运行中
- ✅ `thetamind-db` - 运行中
- ✅ `thetamind-redis` - 运行中
- ❌ **`thetamind-backend` - 缺失！**

---

## 🔍 诊断步骤

### Step 1: 检查 backend 容器状态

```bash
# 查看所有容器（包括已停止的）
docker ps -a | grep thetamind-backend

# 查看 backend 日志
docker logs thetamind-backend

# 或者使用 docker-compose
docker-compose logs backend
```

---

### Step 2: 检查 backend 容器是否在运行

```bash
# 查看 docker-compose 服务状态
docker-compose ps

# 如果 backend 显示为 "Exited" 或 "Restarting"，查看日志
docker-compose logs --tail=50 backend
```

---

## ✅ 常见原因和解决方案

### 原因 1: Backend 容器启动失败（最常见）

**可能原因**：
- 数据库迁移失败
- 环境变量配置错误
- 依赖安装失败

**解决方案**：

```bash
# 1. 查看详细日志
docker-compose logs backend

# 2. 重新构建并启动
docker-compose up -d --build backend

# 3. 如果还是失败，查看实时日志
docker-compose up backend
```

---

### 原因 2: Backend 容器未启动

**可能原因**：
- 只启动了部分服务
- Backend 服务被手动停止

**解决方案**：

```bash
# 启动所有服务
docker-compose up -d

# 或者只启动 backend
docker-compose up -d backend
```

---

### 原因 3: 数据库连接失败

**可能原因**：
- DATABASE_URL 配置错误
- 数据库密码不匹配
- 数据库未就绪

**解决方案**：

1. **检查 .env 文件中的 DATABASE_URL**：
   ```bash
   # 应该类似这样（Docker 内部使用服务名 'db'）
   DATABASE_URL=postgresql+asyncpg://thetamind:password@db:5432/thetamind
   ```

2. **检查数据库容器是否健康**：
   ```bash
   docker ps | grep thetamind-db
   # 应该显示 (healthy)
   ```

3. **测试数据库连接**：
   ```bash
   docker exec -it thetamind-db psql -U thetamind -d thetamind -c "SELECT 1;"
   ```

---

### 原因 4: 环境变量缺失

**可能原因**：
- .env 文件不存在或配置不完整
- 必需的配置项缺失

**解决方案**：

1. **检查 .env 文件**：
   ```bash
   # 从项目根目录
   ls -la .env
   
   # 如果不存在，复制示例文件
   cp .env.example .env
   ```

2. **检查必需的环境变量**：
   ```bash
   # 至少需要这些：
   # - DATABASE_URL (或 DB_USER, DB_PASSWORD, DB_NAME)
   # - REDIS_URL
   # - JWT_SECRET_KEY
   ```

---

### 原因 5: 数据库迁移失败

**可能原因**：
- 迁移脚本错误
- 数据库 schema 不一致

**解决方案**：

```bash
# 1. 进入 backend 容器
docker exec -it thetamind-backend bash

# 2. 手动运行迁移
alembic upgrade head

# 3. 如果迁移失败，查看错误信息
alembic current
alembic history
```

---

## 🚀 快速修复（推荐）

### 方法 1: 重新启动所有服务

```bash
# 从项目根目录
docker-compose down
docker-compose up -d --build
```

这会：
- 停止所有容器
- 重新构建 backend 镜像
- 启动所有服务

---

### 方法 2: 只重新构建 backend

```bash
# 停止 backend
docker-compose stop backend

# 重新构建并启动
docker-compose up -d --build backend

# 查看日志
docker-compose logs -f backend
```

---

### 方法 3: 手动启动 backend 并查看实时日志

```bash
# 启动 backend（前台运行，可以看到实时日志）
docker-compose up backend
```

这会显示所有启动日志，方便诊断问题。

---

## 🔍 详细诊断命令

```bash
# 1. 查看所有容器状态
docker-compose ps

# 2. 查看 backend 日志（最后 50 行）
docker-compose logs --tail=50 backend

# 3. 查看 backend 实时日志
docker-compose logs -f backend

# 4. 进入 backend 容器（如果容器在运行）
docker exec -it thetamind-backend bash

# 5. 检查 backend 健康状态
curl http://localhost:5300/health
# 或者
curl http://localhost:8000/health
```

---

## ✅ 验证修复成功

修复后，应该看到：

```bash
$ docker ps | grep thetamind
fcb9d9719588   thetamind-frontend   ...   Up   0.0.0.0:3000->80/tcp
abb26c52e87d   postgres:15-alpine   ...   Up   0.0.0.0:5432->5432/tcp
4fe565b293b7   redis:7-alpine       ...   Up   0.0.0.0:6379->6379/tcp
[新的容器ID]   thetamind-backend    ...   Up   0.0.0.0:5300->8000/tcp  ✅
```

访问：
- **健康检查**: http://localhost:5300/health
- **API 文档**: http://localhost:5300/docs

---

## 📝 常见错误日志

### 错误 1: "Database is unavailable"

```
Waiting for database to be ready...
Database is unavailable - sleeping
```

**解决**：检查数据库容器是否健康，等待数据库就绪。

---

### 错误 2: "Migration failed"

```
WARNING: Database migrations failed (exit code: 1)
```

**解决**：查看迁移日志，可能需要手动修复数据库 schema。

---

### 错误 3: "ModuleNotFoundError"

```
ModuleNotFoundError: No module named 'fastapi'
```

**解决**：重新构建 Docker 镜像（`docker-compose build backend`）。

---

### 错误 4: "Port already in use"

```
Error: bind: address already in use
```

**解决**：检查端口 5300 是否被占用，或修改 `BACKEND_PORT` 环境变量。

---

## 💡 预防措施

1. **使用健康检查**：确保数据库和 Redis 健康后再启动 backend
2. **查看日志**：启动后立即查看日志确认成功
3. **使用 docker-compose**：不要手动启动单个容器

---

## 🆘 如果还是不行

1. **提供完整日志**：
   ```bash
   docker-compose logs backend > backend_error.log
   ```

2. **检查配置**：
   - .env 文件是否存在且配置正确
   - DATABASE_URL 格式是否正确
   - 所有必需的环境变量是否设置

3. **尝试本地启动**：
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
   如果本地可以启动，问题可能在 Docker 配置。
