# Cloud Run 快速配置指南

## 核心要点

Cloud Run 的数据库连接与本地不同，需要特殊配置。

### 本地 vs Cloud Run

| 配置项 | 本地开发 | Cloud Run |
|--------|---------|-----------|
| 数据库连接 | TCP 连接 (`db:5432`) | Unix Socket (`/cloudsql/...`) |
| 连接字符串 | 完整 `DATABASE_URL` | 由组件自动构建 |
| 密码来源 | `.env` 文件 | Secret Manager |

## 必需配置步骤

### 1. Cloud Build Trigger 变量

在 Cloud Build Trigger 中设置以下**必需变量**：

```
_CLOUDSQL_CONNECTION_NAME=project-id:region:instance-name
_DB_USER=thetamind
_DB_NAME=thetamind_prod
_REDIS_IP=10.x.x.x  # Memorystore 内部 IP
_VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

### 2. Secret Manager

确保以下 secrets 已创建：

```bash
# 数据库密码（必需）
DB_PASSWORD

# 其他必需 secrets
JWT_SECRET_KEY
GOOGLE_API_KEY
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
```

### 3. Cloud Run 服务账号权限

```bash
PROJECT_ID="your-project-id"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CLOUDRUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# 授予 Secret Manager 访问权限
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUDRUN_SA}" \
  --role="roles/secretmanager.secretAccessor"
```

### 4. 验证配置

部署后，检查 Cloud Run 日志：

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=thetamind-backend" \
  --limit 20 \
  --format="table(timestamp,textPayload)"
```

查找：
- ✅ `Constructed DATABASE_URL for Cloud Run` - 连接字符串已构建
- ❌ `DB_PASSWORD must be set` - Secret Manager 配置问题
- ❌ `password authentication failed` - 密码不匹配

## 工作原理

### 自动构建 DATABASE_URL

`backend/app/core/config.py` 会自动检测环境并构建连接字符串：

1. **本地开发**：使用 `DATABASE_URL` 环境变量（完整 URL）
2. **Cloud Run**：检测到 `CLOUDSQL_CONNECTION_NAME` 后，自动构建：
   ```
   postgresql+asyncpg://user:password@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE
   ```

### 环境变量映射

Pydantic 自动将环境变量映射到字段：
- `DB_PASSWORD` → `db_password`
- `DB_USER` → `db_user`
- `DB_NAME` → `db_name`
- `CLOUDSQL_CONNECTION_NAME` → `cloudsql_connection_name`

## 故障排查

### 问题 1：密码验证失败

**检查：**
1. Secret Manager 中的 `DB_PASSWORD` 是否与 Cloud SQL 密码匹配
2. `DB_USER` 环境变量是否与 Cloud SQL 用户名匹配
3. Cloud Run 服务账号是否有 Secret Manager 访问权限

### 问题 2：连接字符串未构建

**检查：**
1. `CLOUDSQL_CONNECTION_NAME` 环境变量是否设置
2. `cloudbuild.yaml` 中 `--set-env-vars` 是否包含 `CLOUDSQL_CONNECTION_NAME`
3. Cloud Build Trigger 变量 `_CLOUDSQL_CONNECTION_NAME` 是否设置

### 问题 3：无法连接到 Cloud SQL

**检查：**
1. `--add-cloudsql-instances` 参数是否正确
2. Cloud SQL 实例是否在运行
3. Cloud Run 服务与 Cloud SQL 是否在同一区域

## 相关文档

- `docs/CLOUDRUN_DATABASE_FIX.md` - 详细故障排查指南
- `docs/GCP_SECRET_MANAGER_SETUP.md` - Secret Manager 设置
- `cloudbuild.yaml` - 部署配置

