# Cloud Run 数据库连接修复

## 问题

Cloud Run 部署后，应用无法连接到 Cloud SQL 数据库，报错：
```
password authentication failed for user "thetamind"
```

或

```
DATABASE_URL must be set...
```

## 原因

Cloud Run 使用 Cloud SQL Unix socket 连接，需要：
1. 通过 `--add-cloudsql-instances` 添加 Cloud SQL 实例
2. 通过环境变量传递 `CLOUDSQL_CONNECTION_NAME`, `DB_USER`, `DB_NAME`
3. 通过 Secret Manager 注入 `DB_PASSWORD`
4. Python 代码自动构建 `DATABASE_URL`

## 解决方案

### 1. 检查 `cloudbuild.yaml` 配置

确保后端部署步骤包含：

```yaml
- name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
  id: 'deploy-backend'
  entrypoint: gcloud
  args:
    - 'run'
    - 'deploy'
    - 'thetamind-backend'
    # ... 其他参数 ...
    - '--add-cloudsql-instances'
    - '${_CLOUDSQL_CONNECTION_NAME}'  # 必需：Cloud SQL 实例连接名
    - '--set-env-vars'
    - 'DB_USER=${_DB_USER},DB_NAME=${_DB_NAME},CLOUDSQL_CONNECTION_NAME=${_CLOUDSQL_CONNECTION_NAME},...'
    - '--update-secrets'
    - 'DB_PASSWORD=DB_PASSWORD:latest,...'  # 必需：从 Secret Manager 注入密码
```

### 2. 检查 Cloud Build Trigger 变量

在 Cloud Build Trigger 中设置以下变量：

**必需变量：**
- `_CLOUDSQL_CONNECTION_NAME`: Cloud SQL 实例连接名（格式：`project-id:region:instance-name`）
- `_DB_USER`: 数据库用户名（默认：`thetamind`）
- `_DB_NAME`: 数据库名（默认：`thetamind_prod`）
- `_REDIS_IP`: Redis IP 地址（Memorystore）
- `_VITE_GOOGLE_CLIENT_ID`: Google OAuth Client ID

**可选变量（有默认值）：**
- `_AI_PROVIDER`: AI 提供商（默认：`gemini`）
- `_TIGER_SANDBOX`: Tiger API 沙箱模式（默认：`true`）
- `_ENABLE_SCHEDULER`: 启用调度器（默认：`false`）

### 3. 检查 Secret Manager

确保以下 secret 已创建并包含正确的值：

```bash
# 必需 secrets
DB_PASSWORD                    # 数据库密码
JWT_SECRET_KEY                 # JWT 密钥
GOOGLE_API_KEY                 # Google API 密钥
GOOGLE_CLIENT_ID              # Google OAuth Client ID
GOOGLE_CLIENT_SECRET          # Google OAuth Client Secret

# 其他 secrets（根据功能需要）
LEMON_SQUEEZY_API_KEY
LEMON_SQUEEZY_WEBHOOK_SECRET
TIGER_PRIVATE_KEY
TIGER_ID
TIGER_ACCOUNT
CLOUDFLARE_R2_ACCESS_KEY_ID
CLOUDFLARE_R2_SECRET_ACCESS_KEY
CLOUDFLARE_R2_BUCKET_NAME
CLOUDFLARE_R2_PUBLIC_URL_BASE
```

### 4. 验证 Cloud Run 服务账号权限

确保 Cloud Run 服务账号有 Secret Manager 访问权限：

```bash
PROJECT_ID="your-project-id"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CLOUDRUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# 授予 Secret Manager 访问权限
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUDRUN_SA}" \
  --role="roles/secretmanager.secretAccessor"
```

### 5. 验证数据库连接字符串构建

应用启动时，`config.py` 会自动构建 `DATABASE_URL`：

**Cloud Run 格式：**
```
postgresql+asyncpg://user:password@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE
```

**检查日志：**
```bash
# 查看 Cloud Run 日志
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=thetamind-backend" \
  --limit 50 \
  --format json
```

查找包含 `Constructed DATABASE_URL for Cloud Run` 的日志，确认连接字符串已正确构建。

### 6. 测试数据库连接

```bash
# 进入 Cloud Run 容器（如果可能）
# 或通过 Cloud Run 的健康检查端点
curl https://your-backend-url/health
```

## 常见问题

### 问题 1：`DB_PASSWORD` 为空

**症状：** 日志显示 `DB_PASSWORD must be set for Cloud Run`

**解决方法：**
1. 检查 Secret Manager 中 `DB_PASSWORD` secret 是否存在
2. 检查 `cloudbuild.yaml` 中 `--update-secrets` 是否包含 `DB_PASSWORD=DB_PASSWORD:latest`
3. 检查 Cloud Run 服务账号是否有 Secret Manager 访问权限

### 问题 2：`CLOUDSQL_CONNECTION_NAME` 未设置

**症状：** 日志显示 `DATABASE_URL must be set...`

**解决方法：**
1. 检查 Cloud Build Trigger 变量中是否设置了 `_CLOUDSQL_CONNECTION_NAME`
2. 检查 `cloudbuild.yaml` 中 `--set-env-vars` 是否包含 `CLOUDSQL_CONNECTION_NAME=${_CLOUDSQL_CONNECTION_NAME}`
3. 确认连接名格式正确：`project-id:region:instance-name`

### 问题 3：数据库密码错误

**症状：** `password authentication failed for user "thetamind"`

**解决方法：**
1. 确认 Secret Manager 中的 `DB_PASSWORD` 与 Cloud SQL 实例的密码匹配
2. 确认 `DB_USER` 环境变量与 Cloud SQL 实例的用户名匹配
3. 确认 `DB_NAME` 环境变量与 Cloud SQL 实例的数据库名匹配

### 问题 4：Cloud SQL 实例未连接

**症状：** `could not connect to server`

**解决方法：**
1. 检查 `--add-cloudsql-instances` 参数是否正确
2. 检查 Cloud SQL 实例是否在运行
3. 检查 Cloud Run 服务是否与 Cloud SQL 实例在同一区域（推荐）

## 验证清单

- [ ] Cloud Build Trigger 变量已设置（`_CLOUDSQL_CONNECTION_NAME`, `_DB_USER`, `_DB_NAME`）
- [ ] Secret Manager 中所有必需的 secrets 已创建
- [ ] Cloud Run 服务账号有 Secret Manager 访问权限
- [ ] `cloudbuild.yaml` 中 `--add-cloudsql-instances` 已配置
- [ ] `cloudbuild.yaml` 中 `--update-secrets` 包含 `DB_PASSWORD`
- [ ] `cloudbuild.yaml` 中 `--set-env-vars` 包含 `CLOUDSQL_CONNECTION_NAME`
- [ ] Cloud SQL 实例正在运行
- [ ] 应用日志显示 `Constructed DATABASE_URL for Cloud Run`

## 相关文件

- `backend/app/core/config.py` - 数据库连接字符串构建逻辑
- `cloudbuild.yaml` - Cloud Build 部署配置
- `docs/GCP_SECRET_MANAGER_SETUP.md` - Secret Manager 设置指南

