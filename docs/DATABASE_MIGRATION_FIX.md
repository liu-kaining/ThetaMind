# 数据库迁移问题修复

## 问题

服务器上报错：`relation "users" does not exist`

这说明数据库表还没有创建，迁移没有执行。

## 根本原因

**`backend/Dockerfile` 中缺少 Alembic 配置文件和迁移文件的复制！**

之前的 Dockerfile 只复制了 `app/` 目录，但没有复制：
- `alembic.ini` - Alembic 配置文件
- `alembic/` - 迁移脚本目录

因此迁移命令 `alembic upgrade head` 无法找到迁移文件，迁移失败。

## 已修复

已更新 `backend/Dockerfile`，添加了：
```dockerfile
# Copy Alembic configuration and migrations
COPY alembic.ini /app/alembic.ini
COPY alembic/ /app/alembic/
```

## 部署步骤

### 1. 重新构建后端镜像

```bash
# 在服务器上
cd /path/to/ThetaMind

# 重新构建后端（不使用缓存，确保最新代码）
docker compose build --no-cache backend

# 重新启动后端
docker compose up -d backend
```

### 2. 验证迁移是否运行

查看后端启动日志，应该看到：
```
Running database migrations...
INFO  [alembic.runtime.migration] Context impl AsyncPGImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001, add_superuser_and_system_configs
...
Migrations completed successfully!
```

### 3. 如果迁移仍未运行，手动执行

```bash
# 进入后端容器
docker compose exec backend bash

# 运行迁移
alembic upgrade head

# 查看当前迁移版本
alembic current

# 退出容器
exit
```

### 4. 验证表是否创建

```bash
# 进入数据库容器
docker compose exec db psql -U thetamind -d thetamind

# 查看所有表
\dt

# 应该看到：
# - users
# - strategies
# - ai_reports
# - payment_events
# - daily_picks
# - system_configs
# - stock_symbols
# - tasks
# - generated_images

# 退出
\q
```

## 验证应用是否正常

迁移成功后，尝试登录：

```bash
# 查看后端日志
docker compose logs backend -f

# 尝试访问健康检查
curl http://localhost:5300/health
```

## 如果问题仍然存在

### 检查迁移文件是否存在

```bash
# 在容器内检查
docker compose exec backend ls -la /app/alembic.ini
docker compose exec backend ls -la /app/alembic/versions/

# 应该看到所有迁移文件
```

### 检查数据库连接

```bash
# 检查 DATABASE_URL
docker compose exec backend env | grep DATABASE_URL

# 应该显示类似：
# DATABASE_URL=postgresql+asyncpg://thetamind:password@db:5432/thetamind
```

### 查看详细的迁移错误

```bash
# 查看完整的启动日志
docker compose logs backend --tail=200 | grep -A 30 -i "migration\|alembic\|error"
```

## 预防措施

确保 `backend/Dockerfile` 中包含：
1. ✅ `COPY alembic.ini /app/alembic.ini`
2. ✅ `COPY alembic/ /app/alembic/`
3. ✅ `COPY ./app /app/app`
4. ✅ `COPY entrypoint.sh /app/entrypoint.sh`

现在这些都已经包含在 Dockerfile 中了。
