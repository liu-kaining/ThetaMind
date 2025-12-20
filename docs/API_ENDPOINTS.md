# ThetaMind Backend API 端点列表

所有 API 端点都有 `/api/v1` 前缀。

基础 URL: `https://your-backend-url.com` (生产环境) 或 `http://localhost:5300` (本地开发)

## 📋 目录

- [健康检查](#健康检查)
- [认证 (Auth)](#认证-auth)
- [市场数据 (Market)](#市场数据-market)
- [策略 (Strategies)](#策略-strategies)
- [AI 功能 (AI)](#ai-功能-ai)
- [支付 (Payment)](#支付-payment)
- [任务 (Tasks)](#任务-tasks)
- [管理员 (Admin)](#管理员-admin)

---

## 健康检查

### `GET /health`
健康检查端点（无需认证）

**响应**:
```json
{
  "status": "healthy",
  "environment": "production"
}
```

### `GET /`
根端点（无需认证）

**响应**:
```json
{
  "message": "ThetaMind API",
  "version": "0.1.0",
  "docs": "/docs"
}
```

---

## 认证 (Auth)

**基础路径**: `/api/v1/auth`

### `POST /api/v1/auth/google`
Google OAuth 登录（无需认证）

**请求体**:
```json
{
  "token": "google-id-token"
}
```

**响应**:
```json
{
  "access_token": "jwt-token",
  "token_type": "bearer"
}
```

### `GET /api/v1/auth/me`
获取当前用户信息（需要认证）

**响应**:
```json
{
  "id": "user-uuid",
  "email": "user@example.com",
  "google_sub": "google-sub-id",
  "is_pro": true,
  "subscription_type": "pro_monthly",
  "daily_ai_usage": 5,
  "daily_image_usage": 3,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

---

## 市场数据 (Market)

**基础路径**: `/api/v1/market`

### `GET /api/v1/market/chain`
获取期权链数据（需要认证）

**查询参数**:
- `symbol` (required): 股票代码，如 "AAPL"
- `expiration_date` (required): 到期日，格式 YYYY-MM-DD

**响应**: `OptionChainResponse`

### `GET /api/v1/market/quote`
获取股票报价（需要认证）

**查询参数**:
- `symbol` (required): 股票代码

### `GET /api/v1/market/search`
搜索股票代码（需要认证）

**查询参数**:
- `query` (required): 搜索关键词

**响应**: `list[SymbolSearchResponse]`

### `GET /api/v1/market/expirations`
获取股票的期权到期日列表（需要认证）

**查询参数**:
- `symbol` (required): 股票代码

**响应**: `list[str]` (日期字符串列表，格式 YYYY-MM-DD)

### `GET /api/v1/market/history`
获取历史价格数据（需要认证）

**查询参数**:
- `symbol` (required): 股票代码
- `period`: 时间周期（可选）

### `GET /api/v1/market/historical`
获取历史K线数据（需要认证）

**查询参数**:
- `symbol` (required): 股票代码
- `start_date`: 开始日期
- `end_date`: 结束日期

### `POST /api/v1/market/recommendations`
获取策略推荐（需要认证）

**请求体**: `StrategyRecommendationRequest`

**响应**: `list[CalculatedStrategy]`

### `POST /api/v1/market/scanner`
股票扫描器（需要认证）

**请求体**: 扫描条件

---

## 策略 (Strategies)

**基础路径**: `/api/v1/strategies`

### `POST /api/v1/strategies`
创建策略（需要认证）

**请求体**: 策略数据

**响应**: `StrategyResponse`

### `GET /api/v1/strategies`
获取策略列表（需要认证）

**查询参数**:
- `skip`: 分页偏移（默认 0）
- `limit`: 每页数量（默认 100）

**响应**: `list[StrategyResponse]`

### `GET /api/v1/strategies/{strategy_id}`
获取单个策略详情（需要认证）

**路径参数**:
- `strategy_id`: 策略 UUID

**响应**: `StrategyResponse`

### `PUT /api/v1/strategies/{strategy_id}`
更新策略（需要认证）

**路径参数**:
- `strategy_id`: 策略 UUID

**请求体**: 更新的策略数据

**响应**: `StrategyResponse`

### `DELETE /api/v1/strategies/{strategy_id}`
删除策略（需要认证）

**路径参数**:
- `strategy_id`: 策略 UUID

**状态码**: 204 No Content

---

## AI 功能 (AI)

**基础路径**: `/api/v1/ai`

### `POST /api/v1/ai/report`
生成 AI 分析报告（需要认证）

**请求体**: 
```json
{
  "strategy_data": {...},
  "metrics": {...}
}
```

**响应**: `AIReportResponse`

### `GET /api/v1/ai/reports`
获取 AI 报告列表（需要认证）

**查询参数**:
- `skip`: 分页偏移（默认 0）
- `limit`: 每页数量（默认 100）

**响应**: `list[AIReportResponse]`

### `DELETE /api/v1/ai/reports/{report_id}`
删除 AI 报告（需要认证）

**路径参数**:
- `report_id`: 报告 UUID

**状态码**: 204 No Content

### `GET /api/v1/ai/daily-picks`
获取每日精选（无需认证）

**响应**: `DailyPickResponse`

### `POST /api/v1/ai/chart`
生成策略图表（需要认证）

**请求体**: 策略数据和指标

**响应**: 包含 `task_id` 的响应

### `GET /api/v1/ai/chart/info/{image_id}`
获取图表信息（需要认证）

**路径参数**:
- `image_id`: 图片 UUID

### `GET /api/v1/ai/chart/by-hash/{strategy_hash}`
根据策略哈希获取图表（需要认证）

**路径参数**:
- `strategy_hash`: 策略哈希值

### `GET /api/v1/ai/chart/{image_id}`
获取图表图片（需要认证）

**路径参数**:
- `image_id`: 图片 UUID

**响应**: 图片文件（重定向到 R2 URL）

---

## 支付 (Payment)

**基础路径**: `/api/v1/payment`

### `POST /api/v1/payment/checkout`
创建支付结账链接（需要认证）

**请求体**:
```json
{
  "variant_id": "monthly-variant-id"  // 或 yearly variant ID
}
```

**响应**: `CheckoutResponse`
```json
{
  "checkout_url": "https://..."
}
```

### `POST /api/v1/payment/webhook`
Lemon Squeezy Webhook 端点（无需认证，需要签名验证）

**请求体**: Lemon Squeezy webhook payload

**状态码**: 200 OK

### `GET /api/v1/payment/pricing`
获取订阅价格（无需认证）

**响应**:
```json
{
  "monthly_price": 9.9,
  "yearly_price": 99.0
}
```

### `GET /api/v1/payment/portal`
获取客户门户链接（需要认证）

**响应**: `CustomerPortalResponse`
```json
{
  "portal_url": "https://..."
}
```

---

## 任务 (Tasks)

**基础路径**: `/api/v1/tasks`

### `POST /api/v1/tasks`
创建后台任务（需要认证）

**请求体**: `TaskCreateRequest`

**响应**: `TaskResponse`

### `GET /api/v1/tasks`
获取任务列表（需要认证）

**查询参数**:
- `skip`: 分页偏移（默认 0）
- `limit`: 每页数量（默认 100）
- `status`: 过滤状态（可选）

**响应**: `list[TaskResponse]`

### `GET /api/v1/tasks/{task_id}`
获取任务详情（需要认证）

**路径参数**:
- `task_id`: 任务 UUID

**响应**: `TaskResponse`

### `DELETE /api/v1/tasks/{task_id}`
删除任务（需要认证）

**路径参数**:
- `task_id`: 任务 UUID

**状态码**: 204 No Content

---

## 管理员 (Admin)

**基础路径**: `/api/v1/admin`（需要超级用户权限）

### `GET /api/v1/admin/configs`
获取所有系统配置（需要超级用户）

**响应**: `list[ConfigItem]`

### `GET /api/v1/admin/configs/{key}`
获取单个配置项（需要超级用户）

**路径参数**:
- `key`: 配置键名

**响应**: `ConfigItem`

### `PUT /api/v1/admin/configs/{key}`
更新配置项（需要超级用户）

**路径参数**:
- `key`: 配置键名

**请求体**: 配置值

**响应**: `ConfigItem`

### `DELETE /api/v1/admin/configs/{key}`
删除配置项（需要超级用户）

**路径参数**:
- `key`: 配置键名

**状态码**: 204 No Content

### `GET /api/v1/admin/users`
获取用户列表（需要超级用户）

**查询参数**:
- `skip`: 分页偏移（默认 0）
- `limit`: 每页数量（默认 100）

**响应**: `list[UserResponse]`

### `GET /api/v1/admin/users/{user_id}`
获取用户详情（需要超级用户）

**路径参数**:
- `user_id`: 用户 UUID

**响应**: `UserResponse`

### `PUT /api/v1/admin/users/{user_id}`
更新用户信息（需要超级用户）

**路径参数**:
- `user_id`: 用户 UUID

**请求体**: 更新的用户数据

**响应**: `UserResponse`

### `DELETE /api/v1/admin/users/{user_id}`
删除用户（需要超级用户）

**路径参数**:
- `user_id`: 用户 UUID

**状态码**: 204 No Content

### `POST /api/v1/admin/daily-picks/trigger`
手动触发每日精选生成（需要超级用户）

**响应**: `DailyPicksTriggerResponse`

---

## 认证说明

大部分端点需要 JWT Bearer Token 认证。

**请求头**:
```
Authorization: Bearer <access_token>
```

**获取 Token**: 使用 `POST /api/v1/auth/google` 端点进行 Google OAuth 登录。

---

## 文档

- **Swagger UI**: `/docs` (仅开发环境)
- **ReDoc**: `/redoc` (仅开发环境)
- **OpenAPI JSON**: `/openapi.json` (仅开发环境)

---

## 注意事项

1. 所有时间使用 UTC 存储，前端显示时转换为 US/Eastern 时区
2. 分页参数 `skip` 和 `limit` 用于控制返回结果数量
3. UUID 格式用于所有资源 ID
4. 生产环境禁用 API 文档端点以增强安全性

