# GCP Container Registry 权限修复

## 问题

错误信息：`denied: gcr.io repo does not exist. Creating on push requires the artifactregistry.repositories.createOnPush permission`

这表示 Cloud Build 服务账号没有权限在 Container Registry 中创建仓库。

## 快速修复方案 1：授予 Container Registry 权限

授予 Cloud Build 服务账号必要的权限：

```bash
# 设置变量
PROJECT_ID="your-project-id"  # 替换为你的项目 ID
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CLOUDBUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

# 授予 Storage Admin 角色（Container Registry 使用 Cloud Storage）
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUDBUILD_SA}" \
  --role="roles/storage.admin"
```

## 方案 2：改用 Artifact Registry（推荐，更现代）

Artifact Registry 是 GCP 推荐的容器镜像存储服务，功能更强大且权限管理更清晰。

### 2.1 创建 Artifact Registry 仓库

```bash
PROJECT_ID="your-project-id"
REGION="us-central1"  # 与 Cloud Run 相同区域

# 创建 Docker 仓库
gcloud artifacts repositories create thetamind-docker \
  --repository-format=docker \
  --location=$REGION \
  --description="ThetaMind Docker images" \
  --project=$PROJECT_ID
```

### 2.2 配置认证

```bash
# 配置 Docker 认证
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

### 2.3 更新 cloudbuild.yaml

需要将所有 `gcr.io/$PROJECT_ID` 替换为 `${REGION}-docker.pkg.dev/$PROJECT_ID/thetamind-docker`。

**注意**：这需要修改 `cloudbuild.yaml` 文件中的所有镜像路径。

## 验证

### 检查 Container Registry 权限

```bash
PROJECT_ID="your-project-id"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CLOUDBUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

# 检查权限
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:${CLOUDBUILD_SA}" \
  --format="table(bindings.role)"
```

### 测试推送镜像

```bash
# 构建并推送测试镜像
docker build -t gcr.io/$PROJECT_ID/test-image:latest .
docker push gcr.io/$PROJECT_ID/test-image:latest
```

## 推荐

- **快速修复**：使用方案 1，授予 `roles/storage.admin` 权限
- **长期方案**：使用方案 2，迁移到 Artifact Registry

