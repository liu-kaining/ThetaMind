# Nginx 配置修复说明

## 修复的问题

### 1. ❌ API 路径 rewrite 错误（已修复）

**原配置**：
```nginx
location /api/ {
    rewrite ^/api/(.*) /$1 break;  # ❌ 错误：会把 /api/v1/auth 变成 /v1/auth
    proxy_pass http://backend;
}
```

**问题**：后端的 FastAPI 路由已经是 `/api/v1/...`，这个 rewrite 会把 `/api/v1/auth/google` 变成 `/v1/auth/google`，导致 404。

**修复后**：
```nginx
location /api/ {
    proxy_pass http://backend;  # ✅ 直接转发，保留完整路径
    # ... 其他配置
}
```

### 2. ❌ Webhook 路径错误（已移除）

**原配置**：
```nginx
location /webhook {
    proxy_pass http://backend/webhook;  # ❌ 错误：实际路径是 /api/v1/payment/webhook
}
```

**问题**：Lemon Squeezy webhook 的实际路径是 `/api/v1/payment/webhook`，不是 `/webhook`。

**修复**：已移除单独的 `/webhook` location，webhook 请求会通过 `/api/` location 正常转发。

### 3. ✅ X-Forwarded-Proto 修正

**原配置**：
```nginx
proxy_set_header X-Forwarded-Proto $http_x_forwarded_proto;
```

**问题**：变量名错误，应该是 `$scheme`（nginx 内置变量）或检查 `$http_x_forwarded_proto`（如果 Cloudflare 设置）。

**修复后**：
```nginx
proxy_set_header X-Forwarded-Proto $scheme;  # ✅ 使用 nginx 内置变量
```

**注意**：如果使用 Cloudflare，Cloudflare 会设置 `CF-Visitor` header，后端可以从那里获取协议信息。`$scheme` 是更标准的做法。

### 4. ✅ 健康检查路径修正

**原配置**：
```nginx
location /health {
    access_log off;
    return 200 "healthy\n";  # ❌ 错误：返回固定字符串，不是真实后端状态
    add_header Content-Type text/plain;
}
```

**问题**：返回固定字符串，无法反映后端实际健康状态。

**修复后**：
```nginx
location /health {
    proxy_pass http://backend/health;  # ✅ 转发到后端真实健康检查
    proxy_set_header Host $host;
    access_log off;
}
```

### 5. ✅ 添加 Redoc 支持

添加了 `/redoc` location，支持 FastAPI 的 ReDoc 文档（如果启用）。

### 6. ✅ WebSocket 连接头修正

**原配置**：
```nginx
proxy_set_header Connection $connection_upgrade;  # ❌ 变量未定义
```

**修复后**：
```nginx
proxy_set_header Connection $http_connection;  # ✅ 使用标准 HTTP 变量
```

## 当前配置结构

```
/                    → frontend (React SPA)
/api/                → backend (FastAPI, 保留完整路径)
/docs                → backend (Swagger UI)
/openapi.json        → backend (OpenAPI schema)
/redoc               → backend (ReDoc)
/health              → backend (健康检查)
```

## 验证

配置修复后，应该验证：

1. **API 请求**：
   ```bash
   curl http://localhost/api/v1/auth/me
   # 应该能正常访问后端 API
   ```

2. **Webhook**：
   ```bash
   curl -X POST http://localhost/api/v1/payment/webhook
   # 应该转发到后端 webhook 端点
   ```

3. **前端 SPA**：
   ```bash
   curl http://localhost/dashboard
   # 应该返回前端页面（前端 nginx 会处理 SPA 路由）
   ```

4. **健康检查**：
   ```bash
   curl http://localhost/health
   # 应该返回后端真实的健康状态
   ```

## 注意事项

1. **Cloudflare 集成**：
   - 如果使用 Cloudflare，建议使用 `$scheme` 或从 `CF-Visitor` header 获取协议
   - Cloudflare 会自动处理 SSL 终止，后端收到的 `X-Forwarded-Proto` 应该是 `https`

2. **前端 SPA 路由**：
   - 前端 Dockerfile 中的 nginx 配置已经处理了 SPA 路由（`try_files $uri $uri/ /index.html;`）
   - 主 nginx 只需要代理到前端即可

3. **超时设置**：
   - AI 相关接口的超时设置为 300s（5分钟），这对 Gemini 分析可能较长的情况是合适的

4. **流式传输**：
   - 已启用 `proxy_buffering off` 和 `chunked_transfer_encoding on`，支持 Server-Sent Events 和流式响应

