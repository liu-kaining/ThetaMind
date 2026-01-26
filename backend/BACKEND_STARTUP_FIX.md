# Backend 启动错误修复

## 🔴 错误分析

从日志中看到两个问题：

### 1. ✅ 已修复：FastAPI 路由定义错误（致命）

**错误**：
```
AssertionError: Cannot use `Query` for path param 'indicator'
```

**位置**：`/app/app/api/endpoints/market.py` 第 474 行

**原因**：路由定义为 `/technical/{indicator}`，但参数使用了 `Query` 而不是 `Path`

**修复**：已修改为使用 `Path` 参数

---

### 2. ⚠️ Tiger API 私钥格式错误（非致命，但会产生警告）

**错误**：
```
Could not deserialize key data. The data may be in an incorrect format...
Failed to initialize TigerService
```

**原因**：Tiger API 私钥格式不正确或已损坏

**影响**：Tiger API 功能将不可用，但不会阻止 backend 启动

**解决方案**：

#### 选项 A: 修复私钥（如果使用 Tiger API）

1. **检查 .env 文件中的 `TIGER_PRIVATE_KEY`**：
   ```bash
   # 私钥应该是完整的 PEM 格式，包括：
   # -----BEGIN RSA PRIVATE KEY-----
   # ...
   # -----END RSA PRIVATE KEY-----
   ```

2. **确保私钥格式正确**：
   - 私钥应该是完整的 PEM 格式
   - 如果是从文件读取，确保包含换行符
   - 如果存储在环境变量中，可能需要使用 `\n` 转义

3. **验证私钥**：
   ```bash
   # 测试私钥格式
   openssl rsa -in your_private_key.pem -check
   ```

#### 选项 B: 禁用 Tiger API（如果不使用）

如果不需要 Tiger API，可以：

1. **在 .env 中留空或删除 Tiger 相关配置**：
   ```env
   TIGER_API_KEY=
   TIGER_API_SECRET=
   TIGER_PRIVATE_KEY=
   ```

2. **Tiger Service 会自动处理缺失配置**，不会阻止启动

---

## ✅ 修复步骤

### Step 1: 重新构建并启动 backend

```bash
# 从项目根目录
docker-compose down backend
docker-compose up -d --build backend

# 查看日志确认修复
docker-compose logs -f backend
```

---

### Step 2: 验证启动成功

启动后应该看到：

```
Starting uvicorn server on 0.0.0.0:8000...
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**不应该再看到**：
- ❌ `AssertionError: Cannot use Query for path param`
- ⚠️ `Failed to initialize TigerService`（如果修复了私钥）

---

### Step 3: 测试 API

```bash
# 健康检查
curl http://localhost:5300/health

# 应该返回：
# {"status":"healthy","environment":"development"}
```

---

## 🔍 如果 Tiger API 错误仍然存在

### 临时解决方案：忽略 Tiger API 错误

Tiger API 错误已经被捕获，不会阻止启动。但如果你想消除警告：

1. **检查 .env 中的 Tiger 配置**：
   ```bash
   grep TIGER .env
   ```

2. **如果不需要 Tiger API**，可以留空：
   ```env
   TIGER_API_KEY=
   TIGER_API_SECRET=
   TIGER_PRIVATE_KEY=
   TIGER_ID=
   TIGER_ACCOUNT=
   ```

3. **如果需要 Tiger API**，修复私钥格式（见上面的选项 A）

---

## 📝 修复总结

✅ **已修复**：
- FastAPI 路由定义错误（`Query` → `Path`）

⚠️ **需要处理**（可选）：
- Tiger API 私钥格式（如果不使用 Tiger API，可以忽略）

---

## 🚀 验证

修复后运行：

```bash
docker-compose logs backend | tail -20
```

应该看到：
- ✅ 没有 `AssertionError`
- ✅ Server 启动成功
- ⚠️ 可能还有 Tiger API 警告（如果私钥未修复，但不影响使用）

访问 http://localhost:5300/docs 应该能看到 Swagger UI。
