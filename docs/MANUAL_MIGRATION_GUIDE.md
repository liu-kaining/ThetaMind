# 手动运行数据库迁移指南

## 问题

即使修复了 Dockerfile，如果容器是用旧镜像启动的，迁移文件仍然不存在。

## 解决步骤

### 步骤 1：确认是否重新构建了镜像

```bash
# 检查后端镜像的构建时间
docker images | grep thetamind-backend

# 如果镜像很旧，需要重新构建
docker compose build --no-cache backend
docker compose up -d backend
```

### 步骤 2：查看启动日志中的迁移信息

```bash
# 查看完整的启动日志
docker compose logs backend --tail=100

# 查找迁移相关的输出
docker compose logs backend | grep -i "migration\|alembic"
```

如果看到 `WARNING: Database migrations failed` 或没有看到迁移输出，说明迁移没有成功执行。

### 步骤 3：手动运行迁移（推荐）

```bash
# 进入后端容器
docker compose exec backend bash

# 检查迁移文件是否存在
ls -la /app/alembic.ini
ls -la /app/alembic/versions/

# 如果文件存在，运行迁移
alembic upgrade head

# 查看迁移状态
alembic current

# 退出容器
exit
```

### 步骤 4：如果迁移文件不存在

如果容器内没有迁移文件，说明镜像没有重新构建，需要：

```bash
# 1. 停止容器
docker compose down

# 2. 重新构建（不使用缓存）
docker compose build --no-cache backend

# 3. 启动服务
docker compose up -d

# 4. 查看日志确认迁移运行
docker compose logs backend -f
```

### 步骤 5：验证表是否创建

```bash
# 进入数据库容器
docker compose exec db psql -U thetamind -d thetamind

# 查看所有表
\dt

# 应该看到以下表：
# - alembic_version  (Alembic 版本跟踪表)
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

## 快速修复命令（一键执行）

```bash
# 停止并重新构建
docker compose down
docker compose build --no-cache backend

# 启动并查看日志
docker compose up -d backend
docker compose logs backend -f

# 在新的终端窗口中，如果看到迁移失败，手动执行：
docker compose exec backend alembic upgrade head
```

## 如果迁移仍然失败

### 检查迁移错误

```bash
# 查看详细的迁移错误
docker compose exec backend alembic upgrade head -v

# 检查数据库连接
docker compose exec backend env | grep DATABASE_URL
```

### 常见错误及解决方法

1. **`alembic: command not found`**
   - 说明依赖未安装，检查 `requirements.txt` 是否包含 `alembic`

2. **`Can't locate revision identified by 'xxx'`**
   - 数据库中的迁移版本与代码不一致
   - 解决方法：检查 `alembic_version` 表的内容

3. **`relation "alembic_version" does not exist`**
   - 这是正常的，第一次运行迁移时会创建这个表

## 验证迁移成功

迁移成功后，应该能看到：

```bash
# 1. 数据库中有 alembic_version 表
docker compose exec db psql -U thetamind -d thetamind -c "SELECT * FROM alembic_version;"

# 2. 所有表都已创建
docker compose exec db psql -U thetamind -d thetamind -c "\dt"

# 3. 尝试登录不再报错
# 在前端尝试登录，不应该再有 "relation users does not exist" 错误
```

