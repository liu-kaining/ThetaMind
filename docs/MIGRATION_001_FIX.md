# 迁移文件 001 修复说明

## 问题

第一个迁移文件 `001_add_superuser_and_system_configs.py` 假设 `users` 表已经存在，但实际上这是第一次迁移，表还不存在，导致错误：

```
sqlalchemy.exc.NoSuchTableError: users
```

## 修复

已修复迁移文件，现在它会：

1. **首先检查 `users` 表是否存在**
   - 如果不存在 → 创建完整的 `users` 表（包含所有字段）
   - 如果存在 → 只添加 `is_superuser` 列（如果还没有）

2. **然后创建 `system_configs` 表**（如果不存在）

## 使用方法

### 1. 重新构建后端镜像（包含修复的迁移文件）

```bash
# 在服务器上
cd /path/to/ThetaMind

# 重新构建后端
docker compose build --no-cache backend

# 重新启动
docker compose up -d backend
```

### 2. 如果迁移已经部分执行，可能需要重置

如果迁移已经部分执行（创建了 `alembic_version` 表），需要：

```bash
# 进入数据库
docker compose exec db psql -U thetamind -d thetamind

# 删除 alembic_version 表（如果存在）
DROP TABLE IF EXISTS alembic_version;

# 退出
\q

# 然后重新运行迁移
docker compose exec backend alembic upgrade head
```

### 3. 或者直接运行迁移

```bash
# 运行迁移
docker compose exec backend alembic upgrade head
```

## 验证

迁移成功后，检查表是否创建：

```bash
# 查看所有表
docker compose exec db psql -U thetamind -d thetamind -c "\dt"

# 应该看到：
# - alembic_version
# - users
# - system_configs
# 以及其他表（如果后续迁移也成功执行）
```

## 注意事项

- `users` 表现在会在第一次迁移时完整创建
- 如果 `users` 表已经存在但缺少 `is_superuser` 列，迁移会自动添加
- 所有字段都包含了适当的默认值和约束

