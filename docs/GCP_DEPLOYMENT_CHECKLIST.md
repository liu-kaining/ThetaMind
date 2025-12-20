# GCP 部署检查清单

## ✅ 部署前准备清单

### 1. GCP 项目设置

- [ ] 创建或选择 GCP 项目
- [ ] 启用必需的 API：
  - [ ] Cloud Run API
  - [ ] Cloud SQL Admin API
  - [ ] Cloud Build API
  - [ ] Secret Manager API
  - [ ] Memorystore for Redis API
- [ ] 设置计费账户（如果使用付费服务）

### 2. Cloud SQL 数据库

- [ ] 创建 PostgreSQL 15 实例
- [ ] 记录 **Connection Name**（格式：`project-id:region:instance-name`）
- [ ] 创建数据库：`thetamind_prod`
- [ ] 创建用户：`thetamind`
- [ ] 设置数据库密码（保存到 Secret Manager）

### 3. Memorystore Redis

- [ ] 创建 Redis 实例（Basic Tier, 1GB）
- [ ] 记录 **IP 地址**（例如：`10.0.0.3`）
- [ ] 确保与 Cloud Run 在同一区域或 VPC 可访问

### 4. Secret Manager

创建以下 Secrets（所有敏感信息）：

- [ ] `DB_PASSWORD` - 数据库密码
- [ ] `JWT_SECRET_KEY` - JWT 签名密钥（生成随机字符串）
- [ ] `GOOGLE_API_KEY` - Google API Key（如果使用）
- [ ] `GEMINI_API_KEY` - Gemini API Key
- [ ] `GOOGLE_CLIENT_ID` - Google OAuth Client ID
- [ ] `GOOGLE_CLIENT_SECRET` - Google OAuth Client Secret
- [ ] `LEMON_SQUEEZY_API_KEY` - Lemon Squeezy API Key
- [ ] `LEMON_SQUEEZY_WEBHOOK_SECRET` - Webhook 签名密钥
- [ ] `TIGER_PRIVATE_KEY` - Tiger API 私钥
- [ ] `TIGER_ID` - Tiger ID
- [ ] `TIGER_ACCOUNT` - Tiger 账户

### 5. IAM 权限配置

#### Cloud Build 服务账号

```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CLOUDBUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

# Secret Manager 访问权限
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUDBUILD_SA}" \
  --role="roles/secretmanager.secretAccessor"
```

- [ ] Cloud Build 服务账号有 `roles/secretmanager.secretAccessor` 权限

#### Cloud Run 服务账号

```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CLOUDRUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Cloud SQL 访问权限
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUDRUN_SA}" \
  --role="roles/cloudsql.client"

# Secret Manager 访问权限
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUDRUN_SA}" \
  --role="roles/secretmanager.secretAccessor"
```

- [ ] Cloud Run 服务账号有 `roles/cloudsql.client` 权限
- [ ] Cloud Run 服务账号有 `roles/secretmanager.secretAccessor` 权限

### 6. Cloud Build Trigger 配置

- [ ] 连接 GitHub 仓库
- [ ] 设置触发分支：`main`（或你的主分支）
- [ ] 配置文件路径：`/cloudbuild.yaml`
- [ ] 设置 Substitution variables：

  **必须配置（REQUIRED）：**
  
  | 变量名 | 说明 | 示例 |
  |--------|------|------|
  | `_CLOUDSQL_CONNECTION_NAME` | Cloud SQL 连接名称 | `my-project:us-central1:thetamind-db` |
  | `_REDIS_IP` | Redis IP 地址 | `10.0.0.3` |
  | `_VITE_GOOGLE_CLIENT_ID` | Google OAuth Client ID | `xxx.apps.googleusercontent.com` |

  **可选配置（有默认值，可不配置）：**

  | 变量名 | 说明 | 默认值 | 示例 |
  |--------|------|--------|------|
  | `_DB_USER` | 数据库用户 | `thetamind` | `thetamind` |
  | `_DB_NAME` | 数据库名称 | `thetamind_prod` | `thetamind_prod` |
  | `_AI_PROVIDER` | AI 提供商 | `gemini` | `gemini` |
  | `_TIGER_SANDBOX` | Tiger 沙盒模式 | `true` | `true` |
  | `_ENABLE_SCHEDULER` | 启用调度器 | `false` | `false` |

## 🚀 部署流程

### 首次部署

1. **提交代码**：
   ```bash
   git add cloudbuild.yaml
   git commit -m "Add GCP deployment configuration"
   git push origin main
   ```

2. **监控构建**：
   - 进入 Cloud Build → History
   - 查看构建日志
   - 确认所有步骤成功

3. **验证服务**：
   ```bash
   # 获取服务 URL
   gcloud run services list --region=us-central1
   
   # 测试 Backend
   curl https://thetamind-backend-xxxxx.run.app/health
   
   # 测试 Frontend
   curl https://thetamind-frontend-xxxxx.run.app
   ```

### 验证清单

部署成功后，验证以下功能：

- [ ] Backend 健康检查：`/health` 返回 200
- [ ] 数据库连接：创建测试用户/策略
- [ ] Redis 缓存：检查缓存是否工作
- [ ] Google OAuth 登录
- [ ] API 调用：前端能调用 Backend API
- [ ] AI 功能：生成报告、图片
- [ ] 任务系统：后台任务正常执行
- [ ] 支付功能：Lemon Squeezy webhook

## 🔍 故障排查

### 常见错误

1. **数据库连接失败**
   - 检查 Connection Name 格式是否正确
   - 确认 Cloud SQL 连接配置正确
   - 检查服务账号权限

2. **Secret Manager 访问失败**
   - 确认 Secret 名称正确
   - 检查服务账号权限
   - 确认 Secret 版本（使用 `:latest`）

3. **前端 API 调用失败（CORS）**
   - 检查 Backend CORS 配置
   - 确认 `VITE_API_URL` 正确

4. **Redis 连接失败**
   - 检查 Redis IP 地址
   - 确认网络连通性
   - 检查防火墙规则

## 📝 环境变量参考

### Backend 环境变量

| 变量名 | 来源 | 说明 |
|--------|------|------|
| `DATABASE_URL` | 自动构建 | `postgresql+asyncpg://user:${DB_PASSWORD}@/dbname?host=/cloudsql/...` |
| `REDIS_URL` | Substitution | `redis://10.0.0.3:6379/0` |
| `DB_PASSWORD` | Secret Manager | 数据库密码 |
| `JWT_SECRET_KEY` | Secret Manager | JWT 密钥 |
| `GOOGLE_API_KEY` | Secret Manager | Google API Key |
| `GEMINI_API_KEY` | Secret Manager | Gemini API Key |
| `GOOGLE_CLIENT_ID` | Secret Manager | OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | Secret Manager | OAuth Client Secret |
| `LEMON_SQUEEZY_API_KEY` | Secret Manager | Lemon Squeezy API Key |
| `LEMON_SQUEEZY_WEBHOOK_SECRET` | Secret Manager | Webhook 密钥 |
| `TIGER_PRIVATE_KEY` | Secret Manager | Tiger 私钥 |
| `TIGER_ID` | Secret Manager | Tiger ID |
| `TIGER_ACCOUNT` | Secret Manager | Tiger 账户 |

### Frontend 构建参数

| 参数名 | 来源 | 说明 |
|--------|------|------|
| `VITE_API_URL` | 自动获取 | Backend Cloud Run URL |
| `VITE_GOOGLE_CLIENT_ID` | Substitution | Google OAuth Client ID |

## 💡 提示

- 首次部署建议在非高峰时段进行
- 保留 Cloud Build 日志以便故障排查
- 定期备份数据库（Cloud SQL 自动备份）
- 监控 Cloud Run 的使用量和成本

## 📚 相关文档

- [完整部署指南](./GCP_DEPLOYMENT_GUIDE.md)
- [部署方案 Review](./GCP_DEPLOYMENT_REVIEW.md)
- [cloudbuild.yaml](../cloudbuild.yaml)

