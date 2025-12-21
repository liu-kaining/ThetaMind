# 如何查看 Cloud Run 日志以诊断启动问题

## 快速查看日志命令

### 1. 查看最近的错误日志

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=thetamind-backend AND severity>=ERROR" \
  --limit 50 \
  --format="table(timestamp,textPayload)" \
  --freshness=1h
```

### 2. 查看所有启动相关日志

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=thetamind-backend AND (textPayload:\"Starting\" OR textPayload:\"ERROR\" OR textPayload:\"Database\" OR textPayload:\"Constructed\" OR textPayload:\"Environment variables check\")" \
  --limit 100 \
  --format="table(timestamp,textPayload)" \
  --freshness=1h
```

### 3. 查看特定版本的日志（使用 revision name）

```bash
REVISION_NAME="thetamind-backend-00009-x2g"  # 从错误信息中获取
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=thetamind-backend AND resource.labels.revision_name=${REVISION_NAME}" \
  --limit 100 \
  --format="table(timestamp,textPayload)"
```

### 4. 查看所有日志（JSON 格式，便于搜索）

```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=thetamind-backend" \
  --limit 100 \
  --format=json \
  --freshness=1h | jq -r '.[] | "\(.timestamp) [\(.severity)] \(.textPayload // .jsonPayload.message // "")"'
```

## 关键信息查找

### 查找环境变量检查输出

查找包含 `Environment variables check:` 的日志行，应该看到：

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

### 查找数据库连接相关信息

查找：
- `Constructed DATABASE_URL for Cloud Run` - 连接字符串构建成功
- `Database initialization failed` - 数据库连接失败
- `password authentication failed` - 密码错误
- `DB_PASSWORD must be set` - Secret Manager 配置问题

### 查找应用启动信息

查找：
- `Starting uvicorn server on 0.0.0.0:8080...` - 端口配置正确
- `Database initialized` - 数据库初始化成功
- `Application startup complete` - 应用启动成功
- `ERROR` 或 `Exception` - 任何错误信息

## 使用 GCP Console 查看日志

1. 访问日志 URL（从错误信息中获取）
2. 或在 GCP Console 中：
   - 导航到 Cloud Run → thetamind-backend
   - 点击 "日志" (Logs) 标签
   - 查看最新的日志条目

## 常见错误模式

### 模式 1：数据库连接失败

```
Database initialization failed: password authentication failed for user "thetamind"
```

**解决：** 检查 `DB_PASSWORD` secret 和 Cloud SQL 密码是否匹配

### 模式 2：配置初始化失败

```
ERROR: DB_PASSWORD is not set in Cloud Run environment!
```

**解决：** 检查 Secret Manager 配置和 `cloudbuild.yaml` 中的 `--update-secrets`

### 模式 3：端口未监听

```
Uvicorn running on http://127.0.0.1:8000
```

**解决：** 确保使用 `--host 0.0.0.0`（已修复）

### 模式 4：启动超时

没有看到 `Starting uvicorn server` 日志，直接超时

**可能原因：**
- 数据库迁移耗时过长
- 配置初始化阻塞
- 其他启动逻辑阻塞

## 下一步

查看日志后，根据具体的错误信息：
1. 如果是数据库连接问题 → 参考 `docs/CLOUDRUN_DATABASE_FIX.md`
2. 如果是配置问题 → 检查环境变量和 Secret Manager
3. 如果是启动超时 → 优化启动逻辑或数据库迁移

