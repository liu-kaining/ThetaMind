# GCP 部署关键问题修复

本文档记录了根据 Gemini 的建议修复的三个关键问题。

## 🔴 问题 1：数据库连接串拼接失效

### 问题描述

在 `cloudbuild.yaml` 中尝试在环境变量中拼接 `DATABASE_URL` 并使用 `${DB_PASSWORD}` 是**无效的**。Cloud Run 不会在启动时将环境变量中的 `${DB_PASSWORD}` 替换为 Secret 的值，导致数据库连接失败。

### 修复方案

**1. 修改 `backend/app/core/config.py`**：

- 添加了分散的数据库配置字段：
  - `db_user`: 数据库用户
  - `db_name`: 数据库名称
  - `db_password`: 数据库密码（从 Secret Manager 读取）
  - `cloudsql_connection_name`: Cloud SQL 连接名称

- 在 `__init__` 方法中自动构建 `DATABASE_URL`：
  ```python
  if not self.database_url and self.cloudsql_connection_name and self.db_password:
      # Cloud Run: 使用 Unix socket 连接
      self.database_url = (
          f"postgresql+asyncpg://{self.db_user}:{self.db_password}@/{self.db_name}"
          f"?host=/cloudsql/{self.cloudsql_connection_name}"
      )
  ```

**2. 修改 `cloudbuild.yaml`**：

- 移除了 `DATABASE_URL` 的拼接
- 改为传递独立的环境变量：
  ```yaml
  - 'DB_USER=${_DB_USER},DB_NAME=${_DB_NAME},CLOUDSQL_CONNECTION_NAME=${_CLOUDSQL_CONNECTION_NAME},...'
  ```
- `DB_PASSWORD` 通过 `--update-secrets` 从 Secret Manager 注入

### 兼容性

代码同时支持两种方式：
1. **Docker Compose（本地开发）**：使用完整的 `DATABASE_URL` 环境变量
2. **Cloud Run（生产环境）**：使用分散的组件自动构建 `DATABASE_URL`

---

## 🔴 问题 2：Cloud Run 无法直接连接 Redis (Memorystore)

### 问题描述

Google Cloud Memorystore (Redis) 只有**内网 IP**。Cloud Run 是 Serverless 服务，默认在公网，**无法直接连接内网 IP**。配置 `REDIS_URL=redis://${_REDIS_IP}:6379/0` 会导致连接超时。

### 修复方案

**1. 创建 VPC Connector**：

必须在 GCP 控制台创建 Serverless VPC Access Connector：
- **名称**：`thetamind-vpc-connector`
- **区域**：`us-central1`（必须与 Cloud Run 相同）
- **网络**：`default`（或你的 VPC）
- **机器类型**：`f1-micro`（最便宜）
- **最小实例数**：`2`

详细步骤见：[GCP_VPC_CONNECTOR_SETUP.md](./GCP_VPC_CONNECTOR_SETUP.md)

**2. 修改 `cloudbuild.yaml`**：

在 Backend 部署步骤中添加 VPC Connector 配置：
```yaml
- '--vpc-connector'
- 'thetamind-vpc-connector'
```

### 注意事项

- VPC Connector 有额外成本（约 $10-15/月）
- 如果不使用 Redis 缓存，应用会以降级模式运行（无缓存）
- 连接器创建后需要几分钟才能使用

---

## 🔴 问题 3：前端构建时环境变量注入

### 问题描述

Vite/React 应用需要在**构建时**将环境变量打包进 JS 文件。需要确保 Dockerfile 正确接收和传递构建参数。

### 验证结果

**✅ `frontend/Dockerfile` 已正确配置**：

```dockerfile
# 声明 ARG
ARG VITE_GOOGLE_CLIENT_ID
ARG VITE_API_URL

# 转换为 ENV（构建过程中才能读取）
ENV VITE_GOOGLE_CLIENT_ID=${VITE_GOOGLE_CLIENT_ID}
ENV VITE_API_URL=${VITE_API_URL}

# 然后才是构建
RUN npm run build
```

**✅ `cloudbuild.yaml` 已正确传递参数**：

```yaml
--build-arg VITE_API_URL="$$BACKEND_URL" \
--build-arg VITE_GOOGLE_CLIENT_ID="${_VITE_GOOGLE_CLIENT_ID}" \
```

### 说明

- 使用 `VITE_` 前缀（不是 `NEXT_PUBLIC_`），因为项目使用 Vite 而不是 Next.js
- `cloudbuild.yaml` 会从部署后的 Backend URL 获取 `VITE_API_URL`

---

## 📋 部署前检查清单

在部署前，确保：

1. ✅ **VPC Connector 已创建**：
   ```bash
   gcloud compute networks vpc-access connectors describe thetamind-vpc-connector \
     --region=us-central1
   ```
   状态应该是 `READY`

2. ✅ **Cloud Build Trigger 变量已配置**：
   - `_CLOUDSQL_CONNECTION_NAME`
   - `_DB_USER`
   - `_DB_NAME`
   - `_REDIS_IP`
   - `_VITE_GOOGLE_CLIENT_ID`
   - 其他可选变量

3. ✅ **Secret Manager 中已创建所有 Secrets**：
   - `DB_PASSWORD`
   - `GEMINI_API_KEY`
   - `JWT_SECRET_KEY`
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
   - `LEMON_SQUEEZY_API_KEY`
   - `LEMON_SQUEEZY_WEBHOOK_SECRET`
   - `TIGER_PRIVATE_KEY`
   - `TIGER_ID`
   - `TIGER_ACCOUNT`
   - Cloudflare R2 相关的 Secrets

4. ✅ **服务账号权限已配置**：
   - Cloud Build 服务账号：`roles/storage.admin`（Container Registry）
   - Cloud Run 服务账号：`roles/secretmanager.secretAccessor`（Secret Manager）

## 🔄 修改的文件

1. `backend/app/core/config.py` - 数据库连接串自动构建逻辑
2. `cloudbuild.yaml` - 移除 DATABASE_URL 拼接，添加 VPC Connector
3. `docs/GCP_VPC_CONNECTOR_SETUP.md` - VPC Connector 设置指南（新建）

## 📚 相关文档

- [VPC Connector 设置指南](./GCP_VPC_CONNECTOR_SETUP.md)
- [Secret Manager 权限设置](./GCP_SECRET_MANAGER_SETUP.md)
- [Container Registry 修复](./GCP_CONTAINER_REGISTRY_FIX.md)
- [Cloud Run 启动修复](./CLOUDRUN_STARTUP_FIX.md)

