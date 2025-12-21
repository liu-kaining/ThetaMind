# 管理员用户指南

## 查看当前用户和管理员状态

### 方法 1：通过数据库查询（推荐）

```bash
# 进入数据库
docker compose exec db psql -U thetamind -d thetamind

# 查看所有用户及其管理员状态
SELECT email, is_superuser, is_pro, created_at FROM users ORDER BY created_at;

# 或者更详细的查询
SELECT 
    email, 
    is_superuser, 
    is_pro,
    subscription_type,
    daily_ai_usage,
    daily_image_usage,
    created_at 
FROM users 
ORDER BY created_at;

# 只查看管理员用户
SELECT email, is_superuser, created_at FROM users WHERE is_superuser = true;

# 退出
\q
```

### 方法 2：使用 Python 脚本查看（会列出所有用户）

```bash
# 进入后端容器
docker compose exec backend bash

# 运行脚本（不传参数会列出所有用户）
cd /app
python scripts/set_superuser.py

# 或者直接运行（会显示用法）
python scripts/set_superuser.py "" 2>&1 | head -20
```

## 创建/设置管理员用户

### 方法 1：使用脚本（推荐）

```bash
# 在服务器上
cd /path/to/ThetaMind

# 进入后端容器
docker compose exec backend bash

# 运行脚本设置管理员（替换为你的邮箱）
python scripts/set_superuser.py your-email@example.com

# 退出容器
exit
```

**注意**：用户必须已经存在（已经通过 Google 登录过一次），脚本才能找到并设置为管理员。

### 方法 2：直接通过数据库 SQL

```bash
# 进入数据库
docker compose exec db psql -U thetamind -d thetamind

# 查看所有用户
SELECT email FROM users;

# 设置指定用户为管理员（替换为实际邮箱）
UPDATE users SET is_superuser = true WHERE email = 'your-email@example.com';

# 验证设置
SELECT email, is_superuser FROM users WHERE email = 'your-email@example.com';

# 退出
\q
```

## 完整流程示例

### 1. 首次登录创建用户

1. 使用 Google 账号在前端登录
2. 系统会自动创建用户（`is_superuser=False`）

### 2. 设置为管理员

```bash
# 方法 A：使用脚本
docker compose exec backend python scripts/set_superuser.py your-email@example.com

# 方法 B：直接 SQL
docker compose exec db psql -U thetamind -d thetamind -c "UPDATE users SET is_superuser = true WHERE email = 'your-email@example.com';"
```

### 3. 验证管理员权限

1. 重新登录（刷新 token）
2. 访问 `/admin/users` 端点（应该能访问）
3. 或者查看前端的管理员页面

## 检查当前登录用户是否是管理员

### 通过 API

```bash
# 获取当前用户信息（需要登录 token）
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:5300/api/v1/auth/me

# 响应中会包含 is_superuser 字段
```

### 通过数据库

```bash
docker compose exec db psql -U thetamind -d thetamind -c "SELECT email, is_superuser FROM users;"
```

## 快速检查命令

```bash
# 一键查看所有用户和管理员状态
docker compose exec db psql -U thetamind -d thetamind -c "SELECT email, is_superuser, is_pro, created_at FROM users ORDER BY created_at;"
```

## 注意事项

1. **用户必须已存在**：只有已经通过 Google 登录过的用户才能设置为管理员
2. **需要重新登录**：设置管理员后，用户需要重新登录才能获得管理员权限
3. **管理员权限**：管理员可以访问 `/api/v1/admin/*` 端点和前端的管理员页面

## 常见问题

### Q: 如何撤销管理员权限？

```bash
docker compose exec db psql -U thetamind -d thetamind -c "UPDATE users SET is_superuser = false WHERE email = 'user@example.com';"
```

### Q: 如何查看管理员用户列表？

```bash
docker compose exec db psql -U thetamind -d thetamind -c "SELECT email, created_at FROM users WHERE is_superuser = true;"
```

### Q: 用户不存在怎么办？

脚本会显示所有可用用户的列表，确保使用正确的邮箱地址。

