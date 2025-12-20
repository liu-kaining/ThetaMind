# GCP Secret Manager 权限设置指南

## 问题

Cloud Run 部署时可能遇到权限错误：
```
Permission denied on secret: projects/xxx/secrets/XXX/versions/latest for Revision service account
The service account used must be granted the 'Secret Manager Secret Accessor' role
```

## 解决方案

### 方法 1：项目级别权限（推荐）

授予 Cloud Run 服务账号访问所有 Secret Manager secrets 的权限：

```bash
# 设置变量
PROJECT_ID="your-project-id"  # 替换为你的项目 ID
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CLOUDRUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# 授予 Secret Manager Secret Accessor 角色（项目级别）
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUDRUN_SA}" \
  --role="roles/secretmanager.secretAccessor"
```

### 方法 2：单个 Secret 级别权限

如果只想授予特定 secret 的访问权限：

```bash
PROJECT_ID="your-project-id"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CLOUDRUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# 为每个 secret 授予权限
SECRETS=(
  "DB_PASSWORD"
  "JWT_SECRET_KEY"
  "GOOGLE_API_KEY"
  "GOOGLE_CLIENT_SECRET"
  "GEMINI_API_KEY"
  "LEMON_SQUEEZY_API_KEY"
  "LEMON_SQUEEZY_WEBHOOK_SECRET"
  "TIGER_PRIVATE_KEY"
  "TIGER_ID"
  "TIGER_ACCOUNT"
  "CLOUDFLARE_R2_ACCESS_KEY_ID"
  "CLOUDFLARE_R2_SECRET_ACCESS_KEY"
  "CLOUDFLARE_R2_BUCKET_NAME"
  "CLOUDFLARE_R2_PUBLIC_URL_BASE"
)

for SECRET in "${SECRETS[@]}"; do
  echo "Granting access to secret: $SECRET"
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:${CLOUDRUN_SA}" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID
done
```

### 方法 3：一键设置脚本

```bash
#!/bin/bash

# 设置项目 ID
PROJECT_ID="your-project-id"  # 替换为你的项目 ID

# 获取项目编号
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CLOUDRUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Project ID: $PROJECT_ID"
echo "Project Number: $PROJECT_NUMBER"
echo "Cloud Run Service Account: $CLOUDRUN_SA"
echo ""

# 方法 1：项目级别权限（最简单）
echo "Granting project-level Secret Manager access..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUDRUN_SA}" \
  --role="roles/secretmanager.secretAccessor"

echo "✅ Permission granted successfully!"
```

## 验证权限

### 检查服务账号权限

```bash
PROJECT_ID="your-project-id"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CLOUDRUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# 检查项目级别权限
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:${CLOUDRUN_SA}" \
  --format="table(bindings.role)"
```

### 检查特定 Secret 权限

```bash
PROJECT_ID="your-project-id"
SECRET_NAME="DB_PASSWORD"

gcloud secrets get-iam-policy $SECRET_NAME --project=$PROJECT_ID
```

## 完整的 Secret 列表

确保以下所有 secrets 都在 Secret Manager 中创建，并且 Cloud Run 服务账号有访问权限：

### 数据库和认证
- `DB_PASSWORD` - PostgreSQL 数据库密码
- `JWT_SECRET_KEY` - JWT 签名密钥

### Google 服务
- `GOOGLE_API_KEY` - Google API Key（可选）
- `GOOGLE_CLIENT_ID` - Google OAuth Client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth Client Secret
- `GEMINI_API_KEY` - Gemini API Key（如果使用 Gemini）

### 支付（Lemon Squeezy）
- `LEMON_SQUEEZY_API_KEY` - Lemon Squeezy API Key
- `LEMON_SQUEEZY_WEBHOOK_SECRET` - Webhook 签名密钥

### 券商（Tiger Brokers）
- `TIGER_PRIVATE_KEY` - Tiger 私钥
- `TIGER_ID` - Tiger ID
- `TIGER_ACCOUNT` - Tiger 账户

### 存储（Cloudflare R2）
- `CLOUDFLARE_R2_ACCESS_KEY_ID` - R2 Access Key ID
- `CLOUDFLARE_R2_SECRET_ACCESS_KEY` - R2 Secret Access Key
- `CLOUDFLARE_R2_BUCKET_NAME` - R2 Bucket 名称
- `CLOUDFLARE_R2_PUBLIC_URL_BASE` - R2 公共 URL 基础路径

## 创建 Secrets

如果 secrets 还没有创建，可以使用以下命令创建：

```bash
PROJECT_ID="your-project-id"

# 示例：创建 DB_PASSWORD secret
echo -n "your-db-password" | gcloud secrets create DB_PASSWORD \
  --data-file=- \
  --replication-policy="automatic" \
  --project=$PROJECT_ID

# 或者从文件创建
gcloud secrets create JWT_SECRET_KEY \
  --data-file=./jwt-secret.txt \
  --replication-policy="automatic" \
  --project=$PROJECT_ID

# 更新现有 secret
echo -n "new-value" | gcloud secrets versions add DB_PASSWORD \
  --data-file=- \
  --project=$PROJECT_ID
```

## 注意事项

1. **项目级别权限 vs Secret 级别权限**：
   - 项目级别权限：一次性授予，适用于所有 secrets（推荐）
   - Secret 级别权限：需要为每个 secret 单独授予

2. **权限生效时间**：
   - 权限更改可能需要几秒钟才能生效
   - 如果仍然报错，等待 1-2 分钟后重试

3. **权限检查**：
   - 使用 `gcloud projects get-iam-policy` 检查项目级别权限
   - 使用 `gcloud secrets get-iam-policy` 检查单个 secret 权限

4. **Secret 版本**：
   - Cloud Run 使用 `:latest` 标签，确保 secret 有版本
   - 每次更新 secret 都会创建新版本，`:latest` 自动指向最新版本

## 故障排查

### 问题：权限设置后仍然报错

1. **检查服务账号名称**：
   ```bash
   # 确认服务账号格式正确
   PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
   echo "${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
   ```

2. **检查 Secret 是否存在**：
   ```bash
   gcloud secrets list --project=$PROJECT_ID
   ```

3. **检查 Secret 是否有版本**：
   ```bash
   gcloud secrets versions list SECRET_NAME --project=$PROJECT_ID
   ```

4. **等待权限生效**：
   - 权限更改可能需要 1-2 分钟才能生效
   - 重新部署 Cloud Run 服务

### 问题：Secret 名称不匹配

确保 `cloudbuild.yaml` 中的 secret 名称与 Secret Manager 中的名称完全一致（区分大小写）。

