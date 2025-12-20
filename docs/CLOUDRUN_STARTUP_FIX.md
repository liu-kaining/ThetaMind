# Cloud Run 启动问题完整修复

## 问题

容器无法在 Cloud Run 启动，错误信息：
```
The user-provided container failed to start and listen on the port defined provided by the PORT=8080 environment variable within the allocated timeout.
```

## 根本原因

1. **端口配置**：应用硬编码监听 8000，但 Cloud Run 使用动态 PORT（通常是 8080）
2. **启动阻塞**：启动时的某些操作（Redis 连接、Tiger API ping、数据库迁移等）可能失败或超时，导致应用无法启动

## 修复方案

### 1. 端口配置修复 (`backend/entrypoint.sh`)

**问题**：Dockerfile CMD 硬编码端口 8000

**修复**：使用 Cloud Run 的 PORT 环境变量
```bash
PORT=${PORT:-8000}
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers 1
```

### 2. 数据库迁移容错 (`backend/entrypoint.sh`)

**问题**：迁移失败会阻止应用启动

**修复**：迁移失败记录警告但不阻止启动
```bash
set +e
alembic upgrade head
MIGRATION_EXIT_CODE=$?
set -e
if [ $MIGRATION_EXIT_CODE -ne 0 ]; then
  echo "WARNING: Database migrations failed, but continuing startup..."
fi
```

### 3. Cloud SQL Unix Socket 检测 (`backend/entrypoint.sh`)

**问题**：`pg_isready` 无法用于 Unix socket 连接

**修复**：检测 Cloud SQL 连接并跳过 `pg_isready`
```bash
if [ -n "$DATABASE_URL" ] && echo "$DATABASE_URL" | grep -q "/cloudsql/"; then
  echo "Detected Cloud SQL Unix socket connection - skipping pg_isready check"
else
  # Use pg_isready for TCP connections
fi
```

### 4. 启动流程容错 (`backend/app/main.py`)

**问题**：Redis、Tiger API、Daily Picks、Scheduler 等非关键服务失败会阻止启动

**修复**：添加全面的错误处理，只让数据库初始化失败阻止启动

```python
# 数据库（关键）- 失败则阻止启动
try:
    await init_db()
except Exception as e:
    logger.error(f"Database initialization failed: {e}")
    raise  # Fail fast for critical services

# Redis（非关键）- 失败则继续
try:
    await cache_service.connect()
except Exception as e:
    logger.warning(f"Redis connection failed (continuing anyway): {e}")

# Tiger API（非关键）- 失败则继续
try:
    tiger_available = await tiger_service.ping()
except Exception as e:
    logger.warning(f"Tiger API ping failed (continuing anyway): {e}")

# Daily Picks（非关键）- 失败则继续
try:
    await check_and_generate_daily_picks()
except Exception as e:
    logger.warning(f"Daily picks check failed (continuing anyway): {e}")

# Scheduler（非关键）- 失败则继续
try:
    setup_scheduler()
    start_scheduler()
except Exception as e:
    logger.warning(f"Scheduler setup failed (continuing anyway): {e}")
```

### 5. Redis 连接超时 (`backend/app/services/cache.py`)

**问题**：Redis 连接可能阻塞很长时间

**修复**：添加 5 秒超时
```python
self._redis = await asyncio.wait_for(
    aioredis.from_url(
        settings.redis_url,
        socket_connect_timeout=5,
    ),
    timeout=5.0,
)
```

### 6. CPU Boost (`cloudbuild.yaml`)

**问题**：启动时 CPU 不足，导致启动缓慢

**修复**：启用 CPU boost 加快启动
```yaml
- '--cpu-boost'  # Enable CPU boost during startup
```

## 关键原则

1. **数据库是关键服务**：失败则阻止启动（fail fast）
2. **其他服务是非关键的**：失败则降级运行（degraded mode）
3. **所有连接都有超时**：防止无限阻塞
4. **详细日志**：便于排查问题

## 验证

部署后，检查日志应该看到：

1. ✅ 端口正确使用：
   ```
   Using port: 8080
   ```

2. ✅ 数据库连接检测跳过：
   ```
   Detected Cloud SQL Unix socket connection - skipping pg_isready check
   ```

3. ✅ 启动成功：
   ```
   ThetaMind backend startup completed successfully!
   INFO:     Uvicorn running on http://0.0.0.0:8080
   ```

## 相关文件

- `backend/entrypoint.sh` - 启动脚本
- `backend/app/main.py` - FastAPI 应用启动流程
- `backend/app/services/cache.py` - Redis 连接（带超时）
- `cloudbuild.yaml` - Cloud Build 配置（CPU boost）

## 注意事项

- Cloud Run 会自动设置 `PORT` 环境变量（通常是 8080）
- 本地开发时，如果没有设置 `PORT`，默认使用 8000
- 生产环境应该监控日志，确保所有服务正常启动
- 如果 Redis 不可用，应用会以降级模式运行（无缓存）

