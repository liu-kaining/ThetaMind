# 快速诊断 Cloud Run 启动失败

## 立即执行的命令

### 1. 查看最新版本的错误日志

```bash
# 替换为你的项目 ID
PROJECT_ID="friendly-vigil-481107-h3"
REVISION_NAME="thetamind-backend-00009-x2g"

# 查看该版本的所有日志
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=thetamind-backend AND resource.labels.revision_name=${REVISION_NAME}" \
  --limit 200 \
  --format="table(timestamp,textPayload)" \
  --project=${PROJECT_ID}
```

### 2. 查看最近的错误

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=thetamind-backend AND severity>=ERROR" \
  --limit 50 \
  --format="table(timestamp,textPayload)" \
  --project=${PROJECT_ID} \
  --freshness=1h
```

### 3. 查找关键信息

```bash
# 查找环境变量检查、数据库连接、启动信息
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=thetamind-backend AND (textPayload:\"Environment variables check\" OR textPayload:\"Starting\" OR textPayload:\"Database\" OR textPayload:\"ERROR\" OR textPayload:\"Constructed\")" \
  --limit 100 \
  --format="table(timestamp,textPayload)" \
  --project=${PROJECT_ID} \
  --freshness=1h
```

## 常见问题检查清单

### ✅ 检查 1：环境变量是否正确

查找日志中的 `Environment variables check:`，应该看到：

```
Environment variables check:
  PORT=8080
  DATABASE_URL present: yes
  CLOUDSQL_CONNECTION_NAME: project-id:region:instance-name
  DB_USER: thetamind
  DB_NAME: thetamind_prod
  DB_PASSWORD: set (hidden)  ← 这个必须显示 "set (hidden)"
  ENVIRONMENT: production
```

**如果 `DB_PASSWORD: not set`：**
- Secret Manager 中的 `DB_PASSWORD` 未正确注入
- 检查 `cloudbuild.yaml` 中的 `--update-secrets`
- 检查 Cloud Run 服务账号权限

### ✅ 检查 2：数据库连接字符串是否构建成功

查找日志中的 `Constructed DATABASE_URL for Cloud Run`，应该看到：

```
Constructed DATABASE_URL for Cloud Run: user=thetamind, db=thetamind_prod, cloudsql=project-id:region:instance-name
```

**如果没有这条日志：**
- `CLOUDSQL_CONNECTION_NAME` 未设置
- 或配置初始化失败

### ✅ 检查 3：应用是否开始启动

查找日志中的 `Starting uvicorn server on 0.0.0.0:8080...`

**如果没有这条日志：**
- 在启动 uvicorn 之前就失败了
- 可能是数据库迁移失败
- 或配置初始化失败

### ✅ 检查 4：数据库初始化是否成功

查找日志中的 `Database initialized` 或 `Database initialization failed`

**如果看到 `Database initialization failed`：**
- 检查具体的错误信息
- 通常是密码错误或连接失败

## 可能的错误模式

### 模式 1：配置初始化失败（在启动脚本之前）

**症状：** 没有看到任何启动脚本的输出

**可能原因：**
- `config.py` 在导入时抛出异常
- 环境变量缺失导致 `ValueError`

**检查：** 查看是否有 Python 异常堆栈

### 模式 2：数据库迁移失败

**症状：** 看到 `Running database migrations...` 但没有后续成功消息

**可能原因：**
- 数据库连接失败
- 迁移脚本错误

**检查：** 查看迁移相关的错误信息

### 模式 3：数据库初始化失败（应用启动时）

**症状：** 看到 `Starting ThetaMind backend...` 但没有 `Database initialized`

**可能原因：**
- 数据库密码错误
- Cloud SQL 连接配置错误
- 网络连接问题

**检查：** 查看 `Database initialization failed` 的详细错误

### 模式 4：应用启动但未监听端口

**症状：** 看到 `Starting uvicorn server` 但 Cloud Run 仍然报超时

**可能原因：**
- uvicorn 启动失败
- 应用崩溃

**检查：** 查看 uvicorn 启动后的错误

## 快速修复命令

### 如果 DB_PASSWORD 未设置

```bash
# 检查 secret 是否存在
gcloud secrets describe DB_PASSWORD --project=${PROJECT_ID}

# 检查 Cloud Run 服务账号权限
PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')
CLOUDRUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member="serviceAccount:${CLOUDRUN_SA}" \
  --role="roles/secretmanager.secretAccessor"
```

## 下一步

1. **运行上面的日志查看命令**，获取具体的错误信息
2. **根据错误信息**，参考相应的文档：
   - 数据库问题 → `docs/CLOUDRUN_DATABASE_FIX.md`
   - 启动失败 → `docs/CLOUDRUN_STARTUP_FAILURE_FIX.md`
   - 配置问题 → `docs/CLOUDRUN_QUICK_SETUP.md`

3. **分享日志输出**，我可以进一步协助诊断

