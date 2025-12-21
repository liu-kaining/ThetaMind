# Cloud Run 启动失败修复指南

## 错误信息

```
ERROR: (gcloud.run.deploy) The user-provided container failed to start and listen on the port defined provided by the PORT=8080 environment variable within the allocated timeout.
```

## 常见原因

### 1. VPC Connector 不存在

**错误信息：**
```
VPC connector thetamind-vpc-connector does not exist
```

**原因：** 未创建 VPC 连接器，或区域（Region）不匹配。

**解决方法：**

运行以下命令手动创建 VPC Connector（确保 `--region` 与 Cloud Run 一致）：

```bash
gcloud compute networks vpc-access connectors create thetamind-vpc-connector \
  --region us-central1 \
  --range 10.8.0.0/28 \
  --network default \
  --min-instances 2 \
  --max-instances 3 \
  --machine-type f1-micro
```

**验证：**
```bash
gcloud compute networks vpc-access connectors describe thetamind-vpc-connector \
  --region us-central1
```

**注意：**
- `--region` 必须与 Cloud Run 服务的区域一致（通常是 `us-central1`）
- `--range` 必须是私有 IP 地址范围（不与现有网络冲突）
- 创建 VPC Connector 需要几分钟时间

### 2. 容器监听端口问题

**错误信息：**
```
Container failed to start and listen on the port defined provided by the PORT=8080 environment variable
```

**原因：** 容器启动了，但没有监听 Cloud Run 指定的端口（默认 8080），或者监听了 `127.0.0.1` 而不是 `0.0.0.0`。

**现象：** 日志里可能显示 `Uvicorn running on http://127.0.0.1:8000`，但 Cloud Run 报错超时。

**解决方法：**

我们的 `entrypoint.sh` 已经正确配置：

```bash
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers 1
```

**验证：**
- ✅ 使用 `--host 0.0.0.0`（不是 `127.0.0.1`）
- ✅ 使用 `--port "$PORT"`（使用环境变量，Cloud Run 自动设置）
- ✅ 使用 `exec`（确保 uvicorn 是主进程）

**如果使用 Dockerfile CMD：**
```dockerfile
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
```

**检查日志：**
应该看到：`Starting uvicorn server on 0.0.0.0:8080...`

### 3. 数据库连接失败

**症状：** 应用无法连接到 Cloud SQL 数据库

**检查：**
```bash
# 查看 Cloud Run 日志
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=thetamind-backend" \
  --limit 50 \
  --format="table(timestamp,textPayload)" \
  --freshness=1h
```

**查找错误：**
- `Database initialization failed`
- `password authentication failed`
- `DB_PASSWORD must be set for Cloud Run`
- `DATABASE_URL must be set`

**解决方法：**

1. **检查 `cloudbuild.yaml` 是否正确添加了 `--add-cloudsql-instances`：**
   ```yaml
   - '--add-cloudsql-instances'
   - '${_CLOUDSQL_CONNECTION_NAME}'
   ```
   这告诉 Cloud Run 可以访问指定的 Cloud SQL 实例。

2. **检查 Python 代码是否支持 Cloud SQL Socket 连接：**
   - ✅ `backend/app/core/config.py` 已支持自动构建 Unix socket 连接字符串
   - ✅ 格式：`postgresql+asyncpg://user:password@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE`
   - ✅ 检测到 `CLOUDSQL_CONNECTION_NAME` 后会自动使用 Unix socket 连接

3. **检查 Secret Manager：**
   - `DB_PASSWORD` secret 已创建且值正确
   - `cloudbuild.yaml` 中 `--update-secrets` 包含 `DB_PASSWORD=DB_PASSWORD:latest`
   - Cloud Run 服务账号有 Secret Manager 访问权限（`roles/secretmanager.secretAccessor`）

4. **检查环境变量：**
   - `CLOUDSQL_CONNECTION_NAME` 已设置（格式：`project-id:region:instance-name`）
   - `DB_USER` 已设置且与 Cloud SQL 实例用户名匹配
   - `DB_NAME` 已设置且与 Cloud SQL 实例数据库名匹配

5. **检查 Cloud SQL 实例：**
   - 实例正在运行
   - 连接名称格式正确
   - 用户名和数据库名与配置匹配

### 2. 配置初始化失败

**症状：** `config.py` 初始化时抛出异常

**检查日志中的错误：**
- `ValueError: DB_PASSWORD must be set for Cloud Run`
- `ValueError: DATABASE_URL must be set...`
- `CLOUDSQL_CONNECTION_NAME is not set`

**解决方法：**
1. 确保 Cloud Build Trigger 变量 `_CLOUDSQL_CONNECTION_NAME` 已设置
2. 确保 `cloudbuild.yaml` 中 `--set-env-vars` 包含所有必需的变量

### 3. 启动超时

**症状：** 应用启动时间超过默认超时（60 秒）

**解决方法：**
1. **注意：** Cloud Run 不支持 `--startup-timeout` 参数，启动超时是固定的（约 240 秒）
2. 已启用 `--cpu-boost`（启动时提供更多 CPU，加快启动速度）
3. 检查数据库迁移是否耗时过长，如果迁移时间过长，考虑在 Cloud SQL 实例上直接运行迁移
4. 确保应用启动逻辑高效，避免阻塞操作

### 4. 端口配置错误

**症状：** 应用未监听正确的端口

**检查：**
启动脚本应显示：`Starting uvicorn server on 0.0.0.0:8080...`

**解决方法：**
- `entrypoint.sh` 已配置为使用 `PORT` 环境变量（Cloud Run 自动设置）

## 诊断步骤

### 步骤 1：检查环境变量

查看部署日志中的环境变量检查输出：
```
Environment variables check:
  PORT=8080
  DATABASE_URL present: yes
  CLOUDSQL_CONNECTION_NAME: project-id:region:instance-name
  DB_USER: thetamind
  DB_NAME: thetamind_prod
  DB_PASSWORD: set (hidden)
  ENVIRONMENT: production
```

如果任何必需变量显示 `not set`，检查 Cloud Build Trigger 配置。

### 步骤 2：检查 Secret Manager

```bash
# 列出所有 secrets
gcloud secrets list

# 检查特定 secret 是否存在
gcloud secrets describe DB_PASSWORD

# 检查 Cloud Run 服务账号权限
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CLOUDRUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:${CLOUDRUN_SA}" \
  --format="table(bindings.role)"
```

确保服务账号有 `roles/secretmanager.secretAccessor` 角色。

### 步骤 3：检查数据库连接

```bash
# 检查 Cloud SQL 实例状态
gcloud sql instances describe INSTANCE_NAME

# 检查连接名称格式
# 应该是：project-id:region:instance-name
```

### 步骤 4：查看详细日志

```bash
# 查看最近的错误日志
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=thetamind-backend AND severity>=ERROR" \
  --limit 20 \
  --format="table(timestamp,textPayload)" \
  --freshness=1h

# 查看所有启动相关日志
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=thetamind-backend AND (textPayload:\"Starting\" OR textPayload:\"ERROR\" OR textPayload:\"Database\")" \
  --limit 50 \
  --format="table(timestamp,textPayload)" \
  --freshness=1h
```

## 快速参考：三个最常见问题

根据实际部署经验，以下是三个最常见的问题和快速解决方案：

### Q1: VPC Connector 不存在

**错误：** `VPC connector thetamind-vpc-connector does not exist`

**快速修复：**
```bash
gcloud compute networks vpc-access connectors create thetamind-vpc-connector \
  --region us-central1 \
  --range 10.8.0.0/28 \
  --network default \
  --min-instances 2 \
  --max-instances 3 \
  --machine-type f1-micro
```

### Q2: 容器监听端口问题

**错误：** `Container failed to start and listen on the port defined provided by the PORT=8080`

**快速修复：**
- ✅ 已正确配置：`entrypoint.sh` 使用 `--host 0.0.0.0 --port "$PORT"`
- ✅ 日志应显示：`Starting uvicorn server on 0.0.0.0:8080...`

### Q3: 数据库连接失败

**错误：** `password authentication failed` 或 `Database initialization failed`

**快速修复：**
1. 检查 `cloudbuild.yaml` 中 `--add-cloudsql-instances` 已配置
2. 检查 `DB_PASSWORD` secret 已创建且正确
3. 检查 Python 代码支持 Cloud SQL Socket 连接（已实现）

## 快速修复检查清单

- [ ] Cloud Build Trigger 变量已设置：
  - `_CLOUDSQL_CONNECTION_NAME`
  - `_DB_USER`
  - `_DB_NAME`
  - `_REDIS_IP`
- [ ] Secret Manager 中所有必需的 secrets 已创建
- [ ] Cloud Run 服务账号有 Secret Manager 访问权限
- [ ] `cloudbuild.yaml` 中 `--add-cloudsql-instances` 已配置
- [ ] `cloudbuild.yaml` 中 `--update-secrets` 包含 `DB_PASSWORD`
- [ ] `cloudbuild.yaml` 中 `--set-env-vars` 包含所有必需的变量
- [ ] Cloud SQL 实例正在运行
- [ ] 已启用 `--cpu-boost`（加快启动速度）
- [ ] 注意：Cloud Run 启动超时是固定的（约 240 秒），无法配置

## 常见错误和解决方案

### 错误 1：`DB_PASSWORD must be set for Cloud Run`

**原因：** Secret Manager 中的 `DB_PASSWORD` 未被正确注入

**解决：**
```bash
# 1. 检查 secret 是否存在
gcloud secrets describe DB_PASSWORD

# 2. 检查 cloudbuild.yaml 中的 --update-secrets
# 应该包含：DB_PASSWORD=DB_PASSWORD:latest

# 3. 授予权限
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CLOUDRUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${CLOUDRUN_SA}" \
  --role="roles/secretmanager.secretAccessor"
```

### 错误 2：`password authentication failed for user "thetamind"`

**原因：** 数据库密码不匹配

**解决：**
1. 确认 Secret Manager 中的 `DB_PASSWORD` 与 Cloud SQL 实例的密码匹配
2. 确认 `DB_USER` 环境变量与 Cloud SQL 实例的用户名匹配
3. 确认 `DB_NAME` 环境变量与 Cloud SQL 实例的数据库名匹配

### 错误 3：`could not connect to server`

**原因：** 无法连接到 Cloud SQL 实例

**解决：**
1. 检查 `--add-cloudsql-instances` 参数是否正确
2. 检查 Cloud SQL 实例是否在运行
3. 检查 Cloud Run 服务与 Cloud SQL 是否在同一区域
4. 检查 Cloud SQL 实例的连接名称格式是否正确

### 错误 4：启动超时

**原因：** 应用启动时间超过超时限制

**解决：**
1. **注意：** Cloud Run 不支持 `--startup-timeout` 参数，启动超时是固定的（约 240 秒）
2. 检查数据库迁移是否耗时过长
3. 考虑在 Cloud SQL 实例上运行迁移，而不是在应用启动时运行

## 测试部署

部署后，等待几分钟让服务启动，然后检查：

```bash
# 检查服务状态
gcloud run services describe thetamind-backend --region=us-central1

# 测试健康检查端点
BACKEND_URL=$(gcloud run services describe thetamind-backend --region=us-central1 --format='value(status.url)')
curl $BACKEND_URL/health
```

应该返回：
```json
{"status":"healthy","environment":"production"}
```

## 相关文档

- `docs/CLOUDRUN_DATABASE_FIX.md` - 数据库连接详细指南
- `docs/CLOUDRUN_QUICK_SETUP.md` - 快速配置指南
- `docs/GCP_SECRET_MANAGER_SETUP.md` - Secret Manager 设置

