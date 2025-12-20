# ERR_CONNECTION_REFUSED 错误修复

## 问题描述

前端无法连接到后端，错误信息：
```
POST http://localhost:5300/api/v1/auth/google net::ERR_CONNECTION_REFUSED
```

## 原因

后端服务没有运行或没有监听正确的端口。

## 解决方法

### 1. 检查后端服务状态

```bash
# 查看所有容器状态
docker-compose ps

# 应该看到 thetamind-backend 容器状态为 "Up"
```

### 2. 启动后端服务

如果后端没有运行，启动它：

```bash
# 启动所有服务
docker-compose up -d

# 或者只启动后端
docker-compose up -d backend
```

### 3. 查看后端日志

```bash
# 查看后端启动日志
docker-compose logs backend

# 实时查看日志
docker-compose logs -f backend
```

### 4. 检查端口映射

确认端口映射正确：
- 容器内端口：`8000`（后端应用监听）
- 主机端口：`5300`（前端访问）

在 `docker-compose.yml` 中：
```yaml
ports:
  - "${BACKEND_PORT:-5300}:8000"
```

### 5. 验证后端健康检查

```bash
# 测试后端是否响应
curl http://localhost:5300/health

# 应该返回：
# {"status":"healthy","environment":"development"}
```

### 6. 常见问题

#### 问题 1：容器启动失败

**检查日志**：
```bash
docker-compose logs backend | tail -50
```

**可能原因**：
- 环境变量未设置（`JWT_SECRET_KEY`, `GOOGLE_CLIENT_ID`, `DATABASE_URL`）
- 数据库连接失败
- 端口被占用

#### 问题 2：端口被占用

**检查端口占用**：
```bash
# macOS/Linux
lsof -i :5300

# 或者
netstat -an | grep 5300
```

**解决方法**：
- 停止占用端口的进程
- 或者修改 `BACKEND_PORT` 环境变量使用其他端口

#### 问题 3：数据库未启动

**检查数据库**：
```bash
docker-compose ps db
```

**启动数据库**：
```bash
docker-compose up -d db
```

## 快速诊断命令

```bash
# 1. 检查所有服务状态
docker-compose ps

# 2. 检查后端日志
docker-compose logs backend --tail=50

# 3. 测试后端连接
curl http://localhost:5300/health

# 4. 检查端口
lsof -i :5300

# 5. 重启后端
docker-compose restart backend
```

## 端口配置说明

| 服务 | 容器内端口 | 主机端口 | 环境变量 |
|------|-----------|---------|---------|
| Backend | 8000 | 5300 | `BACKEND_PORT` |
| Frontend | 80 | 3000 | `FRONTEND_PORT` |
| Database | 5432 | 5432 | `DB_PORT` |
| Redis | 6379 | 6379 | `REDIS_PORT` |

## 相关文件

- `docker-compose.yml` - 服务配置
- `backend/entrypoint.sh` - 后端启动脚本
- `.env` - 环境变量配置

