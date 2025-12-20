# ThetaMind Google Cloud Platform 部署指南

## 📋 概述

本文档详细说明如何将 ThetaMind 部署到 Google Cloud Platform (GCP) 的生产环境。

## 🏗️ 架构图

```
用户请求
   ↓ (HTTPS)
Cloud Load Balancing
   ↓
Cloud Run (Frontend)  →  Cloud Run (Backend)
                           ↓
                    Cloud SQL (PostgreSQL)
                    Memorystore (Redis)
                    Secret Manager (API Keys)
```

## 📝 前置准备

### 1. GCP 项目设置

1. 登录 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目或选择现有项目
3. 启用以下 API：
   - Cloud Run API
   - Cloud SQL Admin API
   - Cloud Build API
   - Secret Manager API
   - Memorystore for Redis API
   - Cloud Resource Manager API

```bash
# 使用 gcloud CLI 启用 API（推荐）
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable redis.googleapis.com
```

### 2. 创建 Cloud SQL PostgreSQL 实例

```bash
# 创建 PostgreSQL 实例
gcloud sql instances create thetamind-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=YOUR_SECURE_PASSWORD

# 获取连接名称（格式：project-id:region:instance-name）
gcloud sql instances describe thetamind-db --format='value(connectionName)'
```

**手动步骤（如果使用 Console）：**
1. 进入 Cloud SQL → 创建实例
2. 选择 PostgreSQL 15
3. 选择区域（建议：us-central1）
4. 选择机器类型（最低：db-f1-micro，生产建议：db-n1-standard-1）
5. 设置 root 密码
6. **重要**：记录 **Connection Name**（例如：`your-project-id:us-central1:thetamind-db`）

**创建数据库和用户：**
```sql
-- 连接到数据库（使用 Cloud SQL Proxy 或 Console SQL 编辑器）
CREATE DATABASE thetamind_prod;
CREATE USER thetamind WITH PASSWORD 'YOUR_SECURE_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE thetamind_prod TO thetamind;
```

### 3. 创建 Memorystore Redis 实例

```bash
# 创建 Redis 实例
gcloud redis instances create thetamind-redis \
  --size=1 \
  --region=us-central1 \
  --tier=basic

# 获取 Redis IP 地址
gcloud redis instances describe thetamind-redis --region=us-central1 --format='value(host)'
```

**手动步骤（如果使用 Console）：**
1. 进入 Memorystore → Redis → 创建实例
2. 选择区域（必须与 Cloud Run 在同一区域或 VPC 连通）
3. 选择 Tier：Basic（最便宜）
4. 选择容量：1 GB（最小）
5. **重要**：记录 **IP 地址**（例如：`10.0.0.3`）

**注意**：Memorystore 较贵（约 $30-40/月）。如果预算有限，可以使用 Compute Engine 安装 Redis（详见省钱方案）。

### 4. 配置 Secret Manager

生产环境**绝对不能**在代码中硬编码 API Key 或密码。使用 Secret Manager 存储所有敏感信息。

```bash
# 创建所有必需的 Secrets
gcloud secrets create DB_PASSWORD --data-file=- <<< "your-database-password"
gcloud secrets create JWT_SECRET_KEY --data-file=- <<< "your-jwt-secret-key"
gcloud secrets create GOOGLE_API_KEY --data-file=- <<< "your-google-api-key"
gcloud secrets create GEMINI_API_KEY --data-file=- <<< "your-gemini-api-key"
gcloud secrets create GOOGLE_CLIENT_ID --data-file=- <<< "your-google-oauth-client-id"
gcloud secrets create GOOGLE_CLIENT_SECRET --data-file=- <<< "your-google-oauth-client-secret"
gcloud secrets create LEMON_SQUEEZY_API_KEY --data-file=- <<< "your-lemon-squeezy-api-key"
gcloud secrets create LEMON_SQUEEZY_WEBHOOK_SECRET --data-file=- <<< "your-lemon-squeezy-webhook-secret"
gcloud secrets create TIGER_PRIVATE_KEY --data-file=- <<< "your-tiger-private-key"
gcloud secrets create TIGER_ID --data-file=- <<< "your-tiger-id"
gcloud secrets create TIGER_ACCOUNT --data-file=- <<< "your-tiger-account"
```

**手动步骤（如果使用 Console）：**
1. 进入 Security → Secret Manager → 创建密钥
2. 为每个敏感变量创建独立的 Secret：
   - `DB_PASSWORD`
   - `JWT_SECRET_KEY`
   - `GOOGLE_API_KEY`
   - `GEMINI_API_KEY`
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `LEMON_SQUEEZY_API_KEY`
   - `LEMON_SQUEEZY_WEBHOOK_SECRET`
   - `TIGER_PRIVATE_KEY`
   - `TIGER_ID`
   - `TIGER_ACCOUNT`

**重要**：确保 Cloud Build 服务账号有访问 Secret Manager 的权限：
```bash
# 获取 Cloud Build 服务账号
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CLOUDBUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

# 授予 Secret Manager Secret Accessor 角色
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUDBUILD_SA}" \
  --role="roles/secretmanager.secretAccessor"
```

### 5. 配置 Cloud Build Trigger

1. 进入 Cloud Build → Triggers → 创建触发器
2. 配置触发器：
   - **名称**：`thetamind-deploy`
   - **事件**：推送到分支
   - **分支**：`^main$`（或你的主分支）
   - **配置**：Cloud Build 配置文件（yaml/json）
   - **位置**：`/cloudbuild.yaml`
3. **重要**：设置替换变量（Substitution variables）：

   **必须配置的（REQUIRED）：**
   ```
   _CLOUDSQL_CONNECTION_NAME: your-project-id:us-central1:thetamind-db
   _REDIS_IP: 10.0.0.3
   _VITE_GOOGLE_CLIENT_ID: your-google-oauth-client-id.apps.googleusercontent.com
   ```

   **可选配置的（有默认值，如果不配置将使用默认值）：**
   ```
   _DB_USER: thetamind              # 默认值：thetamind
   _DB_NAME: thetamind_prod         # 默认值：thetamind_prod
   _AI_PROVIDER: gemini             # 默认值：gemini
   _TIGER_SANDBOX: true             # 默认值：true
   _ENABLE_SCHEDULER: false         # 默认值：false
   ```

   > **注意**：如果使用默认值，可以不配置可选变量。但建议明确配置以便于管理和维护。

### 6. 授予 Cloud Run 访问权限

```bash
# 获取 Cloud Run 服务账号
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CLOUDRUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# 授予 Cloud SQL Client 权限
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUDRUN_SA}" \
  --role="roles/cloudsql.client"

# 授予 Secret Manager Secret Accessor 权限
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUDRUN_SA}" \
  --role="roles/secretmanager.secretAccessor"
```

## 🚀 部署流程

### 自动部署（推荐）

1. **提交代码到主分支**：
   ```bash
   git add .
   git commit -m "Deploy to production"
   git push origin main
   ```

2. **Cloud Build 自动触发**：
   - 进入 Cloud Build → History 查看构建进度
   - 构建成功后，Backend 和 Frontend 会自动部署到 Cloud Run

3. **验证部署**：
   ```bash
   # 获取服务 URL
   gcloud run services list --region=us-central1
   
   # 测试 Backend
   curl https://thetamind-backend-xxxxx.run.app/health
   
   # 测试 Frontend
   curl https://thetamind-frontend-xxxxx.run.app
   ```

### 手动部署（测试）

如果需要手动测试部署：

```bash
# 构建 Backend 镜像
gcloud builds submit --tag gcr.io/$PROJECT_ID/thetamind-backend:test ./backend

# 部署 Backend
gcloud run deploy thetamind-backend \
  --image gcr.io/$PROJECT_ID/thetamind-backend:test \
  --region us-central1 \
  --add-cloudsql-instances YOUR_CONNECTION_NAME \
  --set-env-vars "DATABASE_URL=postgresql+asyncpg://user:pass@/db?host=/cloudsql/YOUR_CONNECTION_NAME" \
  --update-secrets "DB_PASSWORD=DB_PASSWORD:latest"
```

## 🔧 配置说明

### 数据库连接

**本地开发**：
```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/thetamind
```

**生产环境（Cloud Run + Cloud SQL）**：
```
DATABASE_URL=postgresql+asyncpg://user:${DB_PASSWORD}@/thetamind_prod?host=/cloudsql/PROJECT:REGION:INSTANCE
```

Cloud Run 使用 Unix socket (`/cloudsql/...`) 连接 Cloud SQL，这是 GCP 推荐的方式。

### Redis 连接

**本地开发**：
```env
REDIS_URL=redis://localhost:6379/0
```

**生产环境（Memorystore）**：
```env
REDIS_URL=redis://10.0.0.3:6379/0  # Memorystore IP 地址
```

### 前端 API URL

前端需要知道 Backend 的 URL。在 `cloudbuild.yaml` 中，我们会在部署 Backend 后获取 URL，然后在构建 Frontend 时注入。

**本地开发**：
```env
VITE_API_URL=http://localhost:5300
```

**生产环境**：
```
VITE_API_URL=https://thetamind-backend-xxxxx.run.app
```

## 💰 成本优化建议

### 1. 数据库优化

- **开发/测试**：使用 `db-f1-micro`（免费额度内）
- **生产**：至少 `db-n1-standard-1`（约 $50/月）
- **省钱技巧**：使用 Cloud SQL 的自动备份和快照功能，避免数据丢失

### 2. Redis 优化

**方案 A：Memorystore（推荐，省心）**
- 成本：约 $30-40/月（Basic Tier, 1GB）
- 优点：托管服务，自动备份，高可用

**方案 B：Compute Engine + Redis（省钱）**
- 成本：约 $7-10/月（e2-micro + Redis）
- 步骤：
  1. 创建 e2-micro 实例（免费额度内）
  2. 安装 Redis：`sudo apt install redis-server`
  3. 配置防火墙规则，允许 Cloud Run 访问
  4. 更新 `REDIS_IP` 为 Compute Engine 的内网 IP

### 3. Cloud Run 优化

- **最小实例数**：0（空闲时自动缩容到 0，节省成本）
- **最大实例数**：根据流量设置（默认 10）
- **内存**：Backend 2GB，Frontend 512MB（可根据实际使用调整）
- **CPU**：Backend 2 vCPU，Frontend 1 vCPU

### 4. 域名和 SSL

Cloud Run 支持自定义域名和自动 SSL 证书：

1. 进入 Cloud Run → 选择服务 → 管理自定义域名
2. 添加域名（例如：`app.thetamind.ai`）
3. GCP 会自动申请和续期 SSL 证书
4. **完全免费**

## 🔒 安全最佳实践

1. **永远不要**在代码中硬编码敏感信息
2. **使用 Secret Manager**存储所有 API Key 和密码
3. **最小权限原则**：只授予必要的 IAM 角色
4. **启用审计日志**：监控所有 API 访问
5. **使用 VPC**：将 Redis 和数据库放在私有网络中
6. **定期轮换密钥**：定期更新 Secret Manager 中的密钥

## 📊 监控和日志

### 查看日志

```bash
# Backend 日志
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=thetamind-backend" --limit 50

# Frontend 日志
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=thetamind-frontend" --limit 50
```

### 监控指标

进入 Cloud Run → 选择服务 → 指标，查看：
- 请求数量
- 延迟
- 错误率
- CPU 和内存使用率

## 🐛 故障排查

### 常见问题

1. **数据库连接失败**
   - 检查 Cloud SQL 连接名称是否正确
   - 确认 Cloud Run 服务账号有 `cloudsql.client` 权限
   - 检查数据库用户和密码是否正确

2. **Redis 连接失败**
   - 检查 Redis IP 地址是否正确
   - 确认 Cloud Run 和 Redis 在同一 VPC 或可访问
   - 检查防火墙规则

3. **Secret Manager 访问失败**
   - 确认 Cloud Run 服务账号有 `secretmanager.secretAccessor` 权限
   - 检查 Secret 名称是否正确

4. **前端 API 调用失败（CORS）**
   - 检查 `VITE_API_URL` 是否正确
   - 确认 Backend CORS 配置允许前端域名

### 查看构建日志

```bash
# 查看最近的构建
gcloud builds list --limit=5

# 查看构建日志
gcloud builds log BUILD_ID
```

## 📝 环境变量清单

### Backend 必需的环境变量

| 变量名 | 来源 | 说明 |
|--------|------|------|
| `DATABASE_URL` | 自动构建 | Cloud SQL 连接字符串 |
| `REDIS_URL` | Substitution | Memorystore Redis IP |
| `DB_PASSWORD` | Secret Manager | 数据库密码 |
| `JWT_SECRET_KEY` | Secret Manager | JWT 签名密钥 |
| `GOOGLE_API_KEY` | Secret Manager | Google API Key |
| `GOOGLE_CLIENT_ID` | Secret Manager | OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | Secret Manager | OAuth Client Secret |
| `LEMON_SQUEEZY_API_KEY` | Secret Manager | Lemon Squeezy API Key |
| `LEMON_SQUEEZY_WEBHOOK_SECRET` | Secret Manager | Webhook 签名密钥 |
| `TIGER_PRIVATE_KEY` | Secret Manager | Tiger API 私钥 |
| `TIGER_ID` | Secret Manager | Tiger ID |
| `TIGER_ACCOUNT` | Secret Manager | Tiger 账户 |

### Frontend 必需的构建参数

| 参数名 | 来源 | 说明 |
|--------|------|------|
| `VITE_API_URL` | 自动获取 | Backend Cloud Run URL |
| `VITE_GOOGLE_CLIENT_ID` | Substitution | Google OAuth Client ID |

## 🎯 下一步

1. ✅ 完成所有前置准备
2. ✅ 创建并测试 Cloud Build Trigger
3. ✅ 首次部署到生产环境
4. ✅ 配置自定义域名
5. ✅ 设置监控和告警
6. ✅ 配置自动备份（数据库和 Redis）

## 📚 参考资源

- [Cloud Run 文档](https://cloud.google.com/run/docs)
- [Cloud SQL 文档](https://cloud.google.com/sql/docs)
- [Secret Manager 文档](https://cloud.google.com/secret-manager/docs)
- [Cloud Build 文档](https://cloud.google.com/build/docs)
- [Memorystore 文档](https://cloud.google.com/memorystore/docs/redis)

