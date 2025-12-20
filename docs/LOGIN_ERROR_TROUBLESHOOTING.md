# 登录错误排查指南

## 常见登录错误

### 1. JWT_SECRET_KEY 未设置

**错误信息**：
```
ValueError: JWT_SECRET_KEY must be set in environment variables or .env file.
```

**原因**：`JWT_SECRET_KEY` 环境变量未设置或为空。

**解决方法**：
在 `.env` 文件中添加：
```bash
JWT_SECRET_KEY=your-secret-key-here
```

生成一个安全的密钥：
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. GOOGLE_CLIENT_ID 未设置

**错误信息**：
```
ValueError: GOOGLE_CLIENT_ID must be set in environment variables or .env file.
```

**原因**：`GOOGLE_CLIENT_ID` 环境变量未设置或为空。

**解决方法**：
1. 在 [Google Cloud Console](https://console.cloud.google.com/apis/credentials) 创建 OAuth 2.0 客户端 ID
2. 在 `.env` 文件中添加：
```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

### 3. Google Token 验证失败

**错误信息**：
```
Authentication failed: Token verification failed: ...
```

**可能原因**：
1. Google Client ID 配置错误
2. Token 已过期
3. Token 的 audience 不匹配
4. 网络问题导致无法验证 token

**解决方法**：
1. 检查 `GOOGLE_CLIENT_ID` 是否正确
2. 确保前端使用的 Client ID 与后端配置一致
3. 检查网络连接（本地开发可能需要代理）

### 4. 数据库连接失败

**错误信息**：
```
Error during user authentication: ...
```

**可能原因**：
1. `DATABASE_URL` 未正确设置
2. 数据库服务未启动
3. 数据库连接配置错误

**解决方法**：
1. 检查 `.env` 文件中的 `DATABASE_URL`
2. 确保数据库容器正在运行：`docker-compose ps`
3. 检查数据库连接字符串格式

### 5. 用户创建失败

**错误信息**：
```
Error during user authentication: ...
```

**可能原因**：
1. 数据库表未创建
2. 数据库迁移未运行
3. 权限问题

**解决方法**：
1. 运行数据库迁移：`docker-compose exec backend alembic upgrade head`
2. 检查数据库表是否存在
3. 查看详细错误日志

## 检查清单

在排查登录问题时，按以下顺序检查：

1. ✅ **环境变量配置**：
   ```bash
   # 检查必需的环境变量
   grep -E "JWT_SECRET_KEY|GOOGLE_CLIENT_ID|GOOGLE_CLIENT_SECRET|DATABASE_URL" .env
   ```

2. ✅ **应用启动日志**：
   ```bash
   docker-compose logs backend | grep -i error
   ```

3. ✅ **数据库连接**：
   ```bash
   docker-compose exec backend python3 -c "from app.core.config import settings; print('DB URL:', settings.database_url[:50])"
   ```

4. ✅ **Google Client ID**：
   ```bash
   docker-compose exec backend python3 -c "from app.core.config import settings; print('Client ID:', settings.google_client_id[:30])"
   ```

5. ✅ **JWT Secret Key**：
   ```bash
   docker-compose exec backend python3 -c "from app.core.config import settings; print('JWT Key set:', bool(settings.jwt_secret_key))"
   ```

## 调试步骤

### 步骤 1：查看完整错误日志

```bash
# 查看后端日志
docker-compose logs backend --tail=100

# 查看特定错误
docker-compose logs backend | grep -A 10 -i "error\|exception\|traceback"
```

### 步骤 2：测试配置加载

```bash
# 进入容器
docker-compose exec backend bash

# 测试配置
python3 -c "
from app.core.config import settings
print('Database URL:', settings.database_url[:50] if settings.database_url else 'NOT SET')
print('Google Client ID:', settings.google_client_id[:30] if settings.google_client_id else 'NOT SET')
print('JWT Secret Key:', 'SET' if settings.jwt_secret_key else 'NOT SET')
"
```

### 步骤 3：测试 Google Token 验证

```bash
# 在容器中测试（需要有效的 token）
docker-compose exec backend python3 -c "
import asyncio
from app.services.auth_service import verify_google_token

# 替换为实际的 token
token = 'your-google-id-token'
try:
    result = asyncio.run(verify_google_token(token))
    print('Success:', result)
except Exception as e:
    print('Error:', e)
"
```

## 常见错误消息对照表

| 错误消息 | 可能原因 | 解决方法 |
|---------|---------|---------|
| `JWT_SECRET_KEY must be set` | 环境变量未设置 | 在 `.env` 文件中添加 `JWT_SECRET_KEY` |
| `GOOGLE_CLIENT_ID must be set` | 环境变量未设置 | 在 `.env` 文件中添加 `GOOGLE_CLIENT_ID` |
| `DATABASE_URL must be set` | 数据库配置未设置 | 检查 `.env` 或 `docker-compose.yml` |
| `Token verification failed` | Google token 无效 | 检查 Client ID 配置和 token 有效性 |
| `Authentication failed` | 用户创建/查询失败 | 检查数据库连接和表结构 |

## 相关文件

- `backend/app/core/config.py` - 配置管理
- `backend/app/core/security.py` - JWT 工具（已添加验证）
- `backend/app/services/auth_service.py` - 认证服务（已添加验证）
- `backend/app/api/endpoints/auth.py` - 认证端点

## 获取帮助

如果问题仍然存在，请提供：
1. 完整的错误堆栈信息
2. `.env` 文件配置（隐藏敏感信息）
3. `docker-compose logs backend` 的输出

