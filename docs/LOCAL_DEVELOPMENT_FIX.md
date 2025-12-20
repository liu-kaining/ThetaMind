# 本地开发环境修复

## 问题

修改了 `config.py` 以支持 Cloud Run 的数据库连接方式后，本地开发环境可能无法启动。

## 原因

`database_url` 字段现在有默认值 `""`，如果环境变量 `DATABASE_URL` 没有正确设置，会导致启动失败。

## 解决方案

### 1. 确保 `.env` 文件存在并包含 `DATABASE_URL`

```bash
# 在项目根目录创建或检查 .env 文件
DATABASE_URL=postgresql+asyncpg://thetamind:your_password@localhost:5432/thetamind
```

### 2. 确保 `docker-compose.yml` 正确设置环境变量

`docker-compose.yml` 中已经设置了 `DATABASE_URL`：
```yaml
environment:
  - DATABASE_URL=postgresql+asyncpg://${DB_USER:-thetamind}:${DB_PASSWORD}@db:5432/${DB_NAME:-thetamind}
```

确保 `.env` 文件中包含：
```bash
DB_USER=thetamind
DB_PASSWORD=your_password
DB_NAME=thetamind
```

### 3. 验证配置

运行以下命令验证配置：
```bash
# 检查环境变量
docker-compose config | grep DATABASE_URL

# 查看容器日志
docker-compose logs backend
```

## 配置逻辑说明

`config.py` 的 `__init__` 方法按以下优先级处理 `DATABASE_URL`：

1. **如果 `DATABASE_URL` 已设置**（从环境变量或 .env 文件）：
   - 直接使用，不进行任何构建

2. **如果 `CLOUDSQL_CONNECTION_NAME` 和 `DB_PASSWORD` 都设置了**（Cloud Run 环境）：
   - 自动构建 Cloud SQL Unix socket 连接串

3. **否则**：
   - 尝试从 `os.getenv("DATABASE_URL")` 读取
   - 如果仍然为空，抛出错误

## 故障排查

### 错误：`DATABASE_URL must be set...`

**原因**：环境变量 `DATABASE_URL` 没有被正确设置。

**解决方法**：
1. 检查 `.env` 文件是否存在
2. 检查 `docker-compose.yml` 中的环境变量设置
3. 确保 Docker Compose 正确读取了 `.env` 文件

### 错误：数据库连接失败

**原因**：`DATABASE_URL` 格式不正确或数据库服务未启动。

**解决方法**：
1. 确保 PostgreSQL 容器正在运行：`docker-compose ps`
2. 检查 `DATABASE_URL` 格式是否正确
3. 验证数据库用户名、密码和数据库名称

## 本地开发 vs Cloud Run

| 环境 | DATABASE_URL 来源 | 配置方式 |
|------|------------------|----------|
| 本地开发 | `.env` 文件或 `docker-compose.yml` | 完整的连接串 |
| Cloud Run | 自动构建 | 从 `DB_USER`, `DB_NAME`, `DB_PASSWORD`, `CLOUDSQL_CONNECTION_NAME` 构建 |

## 相关文件

- `backend/app/core/config.py` - 配置类
- `docker-compose.yml` - 本地开发环境配置
- `.env` - 环境变量文件（需要创建）

