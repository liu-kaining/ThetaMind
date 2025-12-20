# Cloud Run 部署问题修复

## 问题描述

Cloud Run 部署时遇到错误：
```
The user-provided container failed to start and listen on the port defined provided by the PORT=8000 environment variable within the allocated timeout.
```

## 问题原因

1. **端口配置问题**：容器硬编码监听端口 8000，但 Cloud Run 通过 `PORT` 环境变量动态指定端口
2. **数据库连接检查问题**：`entrypoint.sh` 使用 `pg_isready` 检查数据库连接，但 Cloud Run 使用 Cloud SQL Unix socket 连接，`pg_isready` 无法工作

## 修复方案

### 1. 修复端口配置

修改 `backend/entrypoint.sh`，使其读取 `PORT` 环境变量：

```bash
# Use PORT environment variable (Cloud Run sets this) or default to 8000
PORT=${PORT:-8000}
echo "Using port: $PORT"

if [ "$1" = "uvicorn" ]; then
  exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers 4
fi
```

### 2. 修复数据库连接检查

修改 `backend/entrypoint.sh`，检测 Cloud SQL Unix socket 连接并跳过 `pg_isready` 检查：

```bash
# Check if using Cloud SQL Unix socket (Cloud Run)
if [ -n "$DATABASE_URL" ] && echo "$DATABASE_URL" | grep -q "/cloudsql/"; then
  echo "Detected Cloud SQL Unix socket connection - skipping pg_isready check"
else
  # Wait for database (TCP connections only)
  ...
fi
```

## Cloud SQL 连接格式

在 Cloud Run 中，`DATABASE_URL` 格式为：
```
postgresql+asyncpg://user:password@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE
```

这个格式使用 Unix socket 连接，不是 TCP 连接，所以 `pg_isready` 无法工作。

## 验证

部署后，检查日志确认：

1. 端口正确使用：
   ```
   Using port: 8080  # Cloud Run 设置的端口
   ```

2. 数据库连接检查被跳过：
   ```
   Detected Cloud SQL Unix socket connection - skipping pg_isready check
   ```

3. 应用正常启动：
   ```
   Starting application...
   INFO:     Uvicorn running on http://0.0.0.0:8080
   ```

## 注意事项

- Cloud Run 会自动设置 `PORT` 环境变量，应用必须监听这个端口
- 本地开发时，如果没有设置 `PORT`，默认使用 8000
- `pg_isready` 仅适用于 TCP 连接（如 Docker Compose），不适用于 Unix socket

## 相关文件

- `backend/entrypoint.sh` - 启动脚本
- `backend/Dockerfile` - Docker 配置
- `cloudbuild.yaml` - Cloud Build 配置

