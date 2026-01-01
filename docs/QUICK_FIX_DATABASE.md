# 快速修复数据库密码问题

## 问题

```
asyncpg.exceptions.InvalidPasswordError: password authentication failed for user "thetamind"
```

## 立即修复

### 步骤 1：检查/创建 `.env` 文件

在项目根目录创建或编辑 `.env` 文件：

```bash
# 数据库配置（必须与 docker-compose.yml 匹配）
# ⚠️ 警告：请使用强密码，不要在生产环境使用默认密码！
DB_USER=thetamind
DB_PASSWORD=your_secure_password_here  # ⚠️ 请替换为强密码
DB_NAME=thetamind

# 其他必需配置
JWT_SECRET_KEY=your-jwt-secret-key-here
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### 步骤 2：重置数据库（如果之前密码错误）

```bash
# 停止并删除数据库容器和卷
docker-compose down -v

# 重新创建所有服务
docker-compose up -d

# 等待几秒钟让服务启动
sleep 5

# 检查后端日志
docker-compose logs backend | tail -30
```

### 步骤 3：验证

```bash
# 测试后端健康检查
curl http://localhost:5300/health

# 应该返回：{"status":"healthy","environment":"development"}
```

## 如果问题仍然存在

检查 `DATABASE_URL` 是否正确：

```bash
# 进入后端容器
docker-compose exec backend bash

# 检查环境变量
echo $DATABASE_URL

# 应该看到类似：
# postgresql+asyncpg://thetamind:your_secure_password@db:5432/thetamind
```

如果 `DATABASE_URL` 中的密码部分为空（`thetamind:@db`），说明 `.env` 文件中的 `DB_PASSWORD` 没有正确设置。

