# 数据库密码验证失败修复

## 问题

错误信息：
```
asyncpg.exceptions.InvalidPasswordError: password authentication failed for user "thetamind"
```

## 原因

数据库密码不匹配。可能的原因：

1. `.env` 文件中 `DB_PASSWORD` 未设置，导致 `DATABASE_URL` 中的密码为空
2. `.env` 文件中的 `DB_PASSWORD` 与数据库容器的密码不匹配
3. 数据库名不匹配（`thetamind_prod` vs `thetamind`）

## 解决方法

### 方法 1：确保 `.env` 文件配置正确

在项目根目录的 `.env` 文件中设置：

```bash
# 数据库配置（必须与 docker-compose.yml 中的默认值匹配）
# ⚠️ 警告：请使用强密码，不要在生产环境使用默认密码！
DB_USER=thetamind
DB_PASSWORD=your_secure_password_here  # ⚠️ 请替换为强密码
DB_NAME=thetamind
```

**重要**：`DB_PASSWORD` 必须与 `docker-compose.yml` 中数据库容器的 `POSTGRES_PASSWORD` 匹配。

### 方法 2：检查数据库容器配置

`docker-compose.yml` 中的默认值：
```yaml
POSTGRES_USER: ${DB_USER:-thetamind}
POSTGRES_PASSWORD: ${DB_PASSWORD:-thetamind_dev_password}
POSTGRES_DB: ${DB_NAME:-thetamind}
```

如果 `.env` 文件中没有设置这些变量，数据库容器会使用默认值：
- 用户：`thetamind`
- 密码：`thetamind_dev_password` ⚠️ **仅用于开发环境，生产环境必须设置强密码！**
- 数据库：`thetamind`

### 方法 3：重置数据库（如果密码已更改）

如果之前修改过密码，但数据库容器已经创建，需要重置：

```bash
# 停止并删除数据库容器和卷
docker-compose down -v

# 重新创建数据库容器（使用新的密码）
docker-compose up -d db

# 等待数据库启动
docker-compose logs -f db

# 然后启动后端
docker-compose up -d backend
```

## 验证配置

### 检查环境变量

```bash
# 在容器中检查 DATABASE_URL
docker-compose exec backend env | grep DATABASE_URL

# 应该看到类似：
# DATABASE_URL=postgresql+asyncpg://thetamind:your_secure_password@db:5432/thetamind
```

### 测试数据库连接

```bash
# 进入数据库容器
docker-compose exec db psql -U thetamind -d thetamind

# 如果连接成功，说明密码正确
```

### 检查数据库是否存在

```bash
# 列出所有数据库
docker-compose exec db psql -U thetamind -c "\l"

# 应该看到 thetamind 数据库
```

## 常见问题

### 问题 1：`.env` 文件不存在

**解决方法**：
```bash
# 创建 .env 文件
cp .env.example .env

# 编辑 .env 文件，设置正确的密码
```

### 问题 2：密码包含特殊字符

如果密码包含特殊字符（如 `@`, `#`, `$` 等），需要在 URL 中编码：

```bash
# 例如，密码是 "pass@word"
# 在 DATABASE_URL 中应该是 "pass%40word"
```

### 问题 3：数据库名不匹配

**错误**：尝试连接 `thetamind_prod`，但数据库是 `thetamind`

**解决方法**：
1. 在 `.env` 文件中设置 `DB_NAME=thetamind`
2. 或者创建 `thetamind_prod` 数据库：
   ```bash
   docker-compose exec db psql -U thetamind -c "CREATE DATABASE thetamind_prod;"
   ```

## 快速修复命令

```bash
# 1. 确保 .env 文件存在并包含：
cat > .env << EOF
DB_USER=thetamind
DB_PASSWORD=your_secure_password_here  # ⚠️ 请替换为强密码
DB_NAME=thetamind
EOF

# 2. 重启服务
docker-compose down
docker-compose up -d

# 3. 检查日志
docker-compose logs backend | tail -20
```

## 相关文件

- `docker-compose.yml` - 数据库容器配置
- `.env` - 环境变量配置（需要创建）
- `backend/app/core/config.py` - 应用配置（已修复默认值）

