# ThetaMind 配置指南

## ✅ 统一配置管理（只需修改 .env 文件）

**所有配置都在 `.env` 文件中管理，无需修改 `docker-compose.yml`！**

## 配置优先级说明

配置加载优先级（从高到低）：

1. **Docker `environment:` 中的直接设置**（最高优先级，仅用于容器内部配置）
   - `docker-compose.yml` 中 `environment:` 部分直接设置的环境变量
   - **仅用于容器服务名等内部配置**（如 `DB_HOST=db`, `REDIS_URL=redis://redis:6379/0`）
   - **用户配置不应在这里修改**

2. **系统环境变量**
   - 通过 `export VAR=value` 设置的环境变量
   - 在运行 `docker-compose up` 前设置
   - 会覆盖 `.env` 文件

3. **`.env` 文件**（推荐，统一配置源）
   - 项目根目录的 `.env` 文件
   - **所有用户配置都在这里**
   - 适用于开发和生产环境

4. **`config.py` 中的默认值**（最低优先级）
   - `backend/app/core/config.py` 中定义的默认值
   - 仅在以上配置都不存在时使用

## Docker 环境中的配置

`docker-compose.yml` 使用 `env_file: - .env` 自动加载所有 `.env` 文件中的变量。

只有容器内部必需的配置（需要 Docker 服务名）在 `environment:` 中设置：
- `DATABASE_URL` - 需要容器服务名 `db`
- `DB_HOST=db` - Docker 服务名
- `REDIS_URL=redis://redis:6379/0` - Docker 服务名

**所有用户配置（AI_PROVIDER、API keys 等）都在 `.env` 文件中管理。**

## 推荐配置方式

### 开发环境

在项目根目录创建 `.env` 文件：
```bash
# AI Provider Configuration
AI_PROVIDER=zenmux
ZENMUX_API_KEY=your_zenmux_api_key_here
ZENMUX_MODEL=gemini-2.0-flash-exp
ZENMUX_API_BASE=https://api.zenmux.com

# 如果需要使用 Gemini（直接调用）
# AI_PROVIDER=gemini
# GOOGLE_API_KEY=your_google_api_key_here

# 其他配置...
DATABASE_URL=postgresql+asyncpg://...
JWT_SECRET_KEY=your_secret_key
# ...
```

### 生产环境

**推荐方式：使用 .env 文件**
```bash
# 在生产服务器上创建 .env 文件
AI_PROVIDER=zenmux
ZENMUX_API_KEY=your_production_key
ZENMUX_MODEL=gemini-2.0-flash-exp
# ... 其他配置
```

**替代方式：使用系统环境变量**
```bash
export AI_PROVIDER=zenmux
export ZENMUX_API_KEY=your_production_key
export ZENMUX_MODEL=gemini-2.0-flash-exp
docker-compose up -d
```

**重要提示：**
- **不要修改 `docker-compose.yml`** - 所有配置都在 `.env` 文件中
- `.env` 文件不应该提交到版本控制系统（已在 `.gitignore` 中）
- 生产环境可以使用密钥管理服务（如 AWS Secrets Manager）来管理 `.env` 文件

## 完整配置示例

项目根目录有 `.env.example` 文件，包含所有配置项的示例。复制并重命名为 `.env`，然后填入实际值：

```bash
cp .env.example .env
# 编辑 .env 文件，填入你的配置
```

## AI Provider 配置示例

### 使用 ZenMux（默认）

`.env` 文件：
```bash
AI_PROVIDER=zenmux
ZENMUX_API_KEY=your_zenmux_api_key
ZENMUX_MODEL=gemini-2.0-flash-exp
```

### 切换回 Gemini

`.env` 文件：
```bash
AI_PROVIDER=gemini
GOOGLE_API_KEY=your_google_api_key
```

或者在运行时设置：
```bash
export AI_PROVIDER=gemini
export GOOGLE_API_KEY=your_google_api_key
docker-compose restart backend
```

## Cloudflare R2 存储配置（可选）

如果配置了 R2，图片会存储到 R2 而不是数据库：

`.env` 文件：
```bash
CLOUDFLARE_R2_ACCOUNT_ID=your_account_id
CLOUDFLARE_R2_ACCESS_KEY_ID=your_access_key_id
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_secret_access_key
CLOUDFLARE_R2_BUCKET_NAME=thetamind-images
CLOUDFLARE_R2_PUBLIC_URL_BASE=https://pub-xxx.r2.dev
```

**注意**：如果不配置 R2，系统会自动使用数据库存储（向后兼容）。

## 验证配置

启动后端后，查看日志确认使用的 provider：
```
INFO: Using AI provider: zenmux
INFO: ZenMux API configured with model: gemini-2.0-flash-exp
```

如果配置错误，会看到错误信息：
```
ERROR: Failed to initialize provider 'zenmux': ZenMux API key is required
```

## 注意事项

1. **敏感信息**：API keys 等敏感信息不应提交到 Git
2. **.env 文件**：应该添加到 `.gitignore`
3. **优先级**：Docker 环境变量 > 系统环境变量 > .env > config.py 默认值
4. **配置变更**：修改配置后需要重启容器：`docker-compose restart backend`

