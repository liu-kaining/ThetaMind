# ThetaMind API 端点技术白皮书

**版本**: 1.0  
**日期**: 2025-01-24  
**状态**: 完整文档

---

## 📋 目录

1. [概述](#概述)
2. [认证与授权](#认证与授权)
3. [市场数据 API](#市场数据-api)
4. [策略管理 API](#策略管理-api)
5. [AI 分析 API](#ai-分析-api)
6. [支付系统 API](#支付系统-api)
7. [任务管理 API](#任务管理-api)
8. [管理员 API](#管理员-api)
9. [系统端点](#系统端点)

---

## 概述

ThetaMind API 采用 RESTful 架构，所有端点均以 `/api/v1` 为前缀。系统使用 JWT Bearer Token 进行身份认证，大部分端点需要认证，部分公开端点（如健康检查、每日精选）无需认证。

### 基础信息

- **Base URL**: `https://api.thetamind.com/api/v1` (生产环境)
- **Base URL**: `http://localhost:5300/api/v1` (开发环境)
- **认证方式**: JWT Bearer Token
- **内容类型**: `application/json`
- **时区**: 后端存储使用 UTC，前端显示使用 US/Eastern

### 响应格式

所有成功响应返回 JSON 格式。错误响应遵循以下格式：

```json
{
  "detail": "Error message description"
}
```

### HTTP 状态码

- `200 OK`: 请求成功
- `201 Created`: 资源创建成功
- `204 No Content`: 删除成功，无响应体
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未认证或 Token 无效
- `403 Forbidden`: 权限不足（如 Free 用户尝试使用 Pro 功能）
- `404 Not Found`: 资源不存在
- `429 Too Many Requests`: 配额超限
- `500 Internal Server Error`: 服务器内部错误
- `503 Service Unavailable`: 服务暂时不可用（Circuit Breaker 触发）

---

## 认证与授权

### `POST /api/v1/auth/google`

**功能**: Google OAuth2 登录认证

**认证**: 无需认证（公开端点）

**请求体**:
```json
{
  "token": "google-id-token"
}
```

**响应**:
```json
{
  "access_token": "jwt-token-string",
  "token_type": "bearer"
}
```

**说明**:
- 验证 Google ID Token
- 自动创建或更新用户记录
- 返回 JWT Access Token，用于后续 API 调用
- Token 有效期由 `JWT_EXPIRATION_MINUTES` 配置决定

---

### `GET /api/v1/auth/me`

**功能**: 获取当前用户信息

**认证**: 需要认证

**响应**:
```json
{
  "id": "user-uuid",
  "email": "user@example.com",
  "is_pro": true,
  "is_superuser": false,
  "subscription_id": "sub_xxx",
  "subscription_type": "monthly",
  "plan_expiry_date": "2025-02-24T00:00:00Z",
  "daily_ai_usage": 5,
  "daily_ai_quota": 10,
  "daily_image_usage": 2,
  "daily_image_quota": 10,
  "created_at": "2024-01-01T00:00:00Z"
}
```

**说明**:
- 返回当前认证用户的详细信息
- 包含订阅状态、配额使用情况
- 配额根据订阅类型自动计算（Free: 1, Pro Monthly: 10, Pro Yearly: 30）

---

## 市场数据 API

### 期权数据

#### `GET /api/v1/market/chain`

**功能**: 获取期权链数据

**认证**: 需要认证

**查询参数**:
- `symbol` (required): 股票代码，如 "AAPL"
- `expiration_date` (required): 到期日，格式 YYYY-MM-DD
- `force_refresh` (optional, default: false): 强制刷新，绕过缓存（仅 Pro 用户）

**响应**:
```json
{
  "symbol": "AAPL",
  "expiration_date": "2024-06-21",
  "calls": [
    {
      "strike": 150.0,
      "bid": 2.50,
      "ask": 2.60,
      "volume": 1000,
      "open_interest": 5000,
      "delta": 0.65,
      "gamma": 0.02,
      "theta": -0.05,
      "vega": 0.15,
      "rho": 0.01,
      "implied_volatility": 0.25,
      "greeks": {
        "delta": 0.65,
        "gamma": 0.02,
        "theta": -0.05,
        "vega": 0.15,
        "rho": 0.01
      }
    }
  ],
  "puts": [...],
  "spot_price": 150.25,
  "_source": "cache"
}
```

**说明**:
- 数据来源：Tiger Brokers API
- 缓存策略：所有用户 10 分钟 TTL
- Pro 用户可使用 `force_refresh=true` 获取实时数据
- Free 用户尝试使用 `force_refresh` 将返回 403 错误
- 包含完整的 Greeks 数据（Delta, Gamma, Theta, Vega, Rho）

---

#### `GET /api/v1/market/expirations`

**功能**: 获取股票的期权到期日列表

**认证**: 需要认证

**查询参数**:
- `symbol` (required): 股票代码

**响应**:
```json
["2024-06-21", "2024-06-28", "2024-07-19", ...]
```

**说明**:
- 返回所有可用的期权到期日
- 日期格式：YYYY-MM-DD
- 按时间顺序排序

---

### 股票数据

#### `GET /api/v1/market/quote`

**功能**: 获取股票实时报价

**认证**: 需要认证

**查询参数**:
- `symbol` (required): 股票代码

**响应**:
```json
{
  "symbol": "AAPL",
  "data": {
    "price": 150.25,
    "change": 2.50,
    "change_percent": 1.69,
    "volume": 50000000
  },
  "is_pro": true,
  "price_source": "fmp"
}
```

**说明**:
- 数据来源：优先使用 FMP API（通过 FinanceToolkit），失败时回退到 Tiger API 价格推断
- `price_source`: "fmp"（完整数据）、"inferred"（仅价格）、"unavailable"（不可用）

---

#### `GET /api/v1/market/quotes/batch`

**功能**: 批量获取多个股票的实时报价（P0 功能）

**认证**: 需要认证

**查询参数**:
- `symbols` (required): 逗号分隔的股票代码，如 "AAPL,MSFT,GOOGL"

**响应**:
```json
{
  "AAPL": {
    "price": 150.25,
    "change": 2.50,
    "change_percent": 1.69
  },
  "MSFT": {...},
  "GOOGL": {...}
}
```

**说明**:
- 直接调用 FMP API 批量报价接口
- 适用于同时监控多个持仓的场景

---

#### `GET /api/v1/market/profile`

**功能**: 获取股票财务概况（基本面 + 技术指标）

**认证**: 需要认证

**查询参数**:
- `symbol` (required): 股票代码

**响应**:
```json
{
  "ticker": "AAPL",
  "profile": {...},
  "ratios": {...},
  "technical_indicators": {...}
}
```

**说明**:
- 使用 MarketDataService（FMP + Yahoo 回退）
- 包含财务比率、技术指标等综合数据

---

### 历史数据

#### `GET /api/v1/market/historical/{interval}`

**功能**: 获取多时间间隔历史价格数据（P0 功能）

**认证**: 需要认证

**路径参数**:
- `interval`: 时间间隔（1min, 5min, 15min, 30min, 1hour, 4hour, 1day）

**查询参数**:
- `symbol` (required): 股票代码
- `limit` (optional, default: None): 最大数据点数（1-10000）

**响应**:
```json
{
  "symbol": "AAPL",
  "interval": "1day",
  "data": [
    {
      "date": "2024-01-01",
      "open": 150.0,
      "high": 152.0,
      "low": 149.0,
      "close": 151.0,
      "volume": 50000000
    }
  ]
}
```

**说明**:
- 直接调用 FMP API 多间隔历史数据接口
- 支持日内（1min-4hour）和日线（1day）数据
- 用于技术分析和策略回测

---

#### `GET /api/v1/market/history`

**功能**: 获取历史 K 线数据（使用 Tiger API）

**认证**: 需要认证

**查询参数**:
- `symbol` (required): 股票代码
- `period` (optional, default: "day"): 周期类型（day, week, month）
- `limit` (optional, default: 100): 返回的 K 线数量（1-500）

**响应**:
```json
{
  "symbol": "AAPL",
  "data": [
    {
      "time": "2024-01-01T00:00:00Z",
      "open": 150.0,
      "high": 152.0,
      "low": 149.0,
      "close": 151.0,
      "volume": 50000000
    }
  ],
  "_source": "tiger_bars"
}
```

**说明**:
- 优先使用 Tiger API 的 `get_bars` 方法（免费配额）
- 失败时回退到 FMP API
- 缓存 1 小时

---

#### `GET /api/v1/market/historical`

**功能**: 历史数据（遗留端点，向后兼容）

**认证**: 需要认证

**查询参数**:
- `symbol` (required): 股票代码
- `days` (optional, default: 30): 历史天数（1-365）

**说明**:
- 映射到 `/market/history` 端点
- 保持向后兼容性

---

### 技术指标

#### `GET /api/v1/market/technical/{indicator}`

**功能**: 获取技术指标数据（P0 功能）

**认证**: 需要认证

**路径参数**:
- `indicator`: 技术指标名称（sma, ema, rsi, adx, macd, bollinger_bands, williams, standarddeviation, wma, dema, tema）

**查询参数**:
- `symbol` (required): 股票代码
- `period_length` (optional, default: 10): 计算周期长度（1-200）
- `timeframe` (optional, default: "1day"): 时间框架（1min, 5min, 15min, 30min, 1hour, 1day）

**响应**:
```json
{
  "symbol": "AAPL",
  "indicator": "rsi",
  "period_length": 14,
  "timeframe": "1day",
  "data": {
    "2024-01-01": 65.5,
    "2024-01-02": 67.2
  }
}
```

**说明**:
- 直接调用 FMP API 技术指标接口
- 支持 10+ 种常用技术指标
- 用于策略信号生成

---

### 市场表现数据（P1）

#### `GET /api/v1/market/market/sector-performance`

**功能**: 获取板块表现快照

**认证**: 需要认证

**查询参数**:
- `date` (optional): 日期，格式 YYYY-MM-DD（默认：最新）

**响应**:
```json
{
  "date": "2024-01-24",
  "sectors": [
    {
      "sector": "Technology",
      "change_percent": 1.5
    }
  ]
}
```

---

#### `GET /api/v1/market/market/industry-performance`

**功能**: 获取行业表现快照

**认证**: 需要认证

**查询参数**:
- `date` (optional): 日期，格式 YYYY-MM-DD

---

#### `GET /api/v1/market/market/biggest-gainers`

**功能**: 获取涨幅最大的股票

**认证**: 需要认证

**响应**:
```json
[
  {
    "symbol": "AAPL",
    "change_percent": 5.2,
    "price": 155.0
  }
]
```

---

#### `GET /api/v1/market/market/biggest-losers`

**功能**: 获取跌幅最大的股票

**认证**: 需要认证

---

#### `GET /api/v1/market/market/most-actives`

**功能**: 获取交易最活跃的股票

**认证**: 需要认证

---

### 分析师数据（P1）

#### `GET /api/v1/market/analyst/estimates`

**功能**: 获取分析师财务预测

**认证**: 需要认证

**查询参数**:
- `symbol` (required): 股票代码
- `period` (optional, default: "annual"): 周期（annual, quarter）
- `limit` (optional, default: 10): 最大预测数量（1-100）

**响应**:
```json
{
  "symbol": "AAPL",
  "estimates": [
    {
      "date": "2024-12-31",
      "estimatedEps": 6.5,
      "estimatedRevenue": 400000000000
    }
  ]
}
```

---

#### `GET /api/v1/market/analyst/price-target`

**功能**: 获取价格目标摘要

**认证**: 需要认证

**查询参数**:
- `symbol` (required): 股票代码

---

#### `GET /api/v1/market/analyst/price-target-consensus`

**功能**: 获取价格目标共识（高、低、中位数、共识）

**认证**: 需要认证

**查询参数**:
- `symbol` (required): 股票代码

---

#### `GET /api/v1/market/analyst/grades`

**功能**: 获取股票评级/等级

**认证**: 需要认证

**查询参数**:
- `symbol` (required): 股票代码

---

#### `GET /api/v1/market/analyst/ratings`

**功能**: 获取评级快照

**认证**: 需要认证

**查询参数**:
- `symbol` (required): 股票代码

---

### TTM 财务数据（P1）

#### `GET /api/v1/market/financial/key-metrics-ttm`

**功能**: 获取过去 12 个月（TTM）关键财务指标

**认证**: 需要认证

**查询参数**:
- `symbol` (required): 股票代码

---

#### `GET /api/v1/market/financial/ratios-ttm`

**功能**: 获取过去 12 个月（TTM）财务比率

**认证**: 需要认证

**查询参数**:
- `symbol` (required): 股票代码

---

### 股票搜索

#### `GET /api/v1/market/search`

**功能**: 搜索股票代码（按代码或公司名称）

**认证**: 需要认证

**查询参数**:
- `q` (required): 搜索关键词
- `limit` (optional, default: 10): 最大结果数（1-50）

**响应**:
```json
[
  {
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "market": "US"
  }
]
```

**说明**:
- 使用本地数据库快速搜索（ILIKE 查询）
- 支持代码和公司名称匹配

---

### 策略推荐

#### `POST /api/v1/market/recommendations`

**功能**: 生成算法策略推荐（基于数学逻辑，非 AI）

**认证**: 需要认证

**请求体**:
```json
{
  "symbol": "AAPL",
  "outlook": "NEUTRAL",
  "risk_profile": "CONSERVATIVE",
  "capital": 10000.0,
  "expiration_date": "2024-06-21"
}
```

**响应**:
```json
[
  {
    "name": "High Theta Iron Condor",
    "description": "Neutral strategy collecting premium...",
    "legs": [...],
    "metrics": {
      "max_profit": 500.0,
      "max_loss": 4500.0,
      "risk_reward_ratio": 0.11,
      "pop": 0.75,
      "breakeven_points": [155.0, 145.0],
      "net_greeks": {
        "delta": 0.05,
        "gamma": -0.01,
        "theta": 2.5,
        "vega": -0.3,
        "rho": 0.02
      },
      "theta_decay_per_day": 250.0,
      "liquidity_score": 85.5
    }
  }
]
```

**说明**:
- 使用 StrategyEngine 进行数学计算
- 基于 Greeks 分析和严格验证规则
- 不调用 AI 模型，快速且确定性
- 支持策略类型：Iron Condor, Long Straddle, Bull Call Spread

---

### 市场扫描器

#### `POST /api/v1/market/scanner`

**功能**: 市场扫描器（发现功能）

**认证**: 需要认证

**查询参数**:
- `criteria` (required): 扫描条件（high_iv, top_gainers, most_active, top_losers, high_volume）
- `market_value_min` (optional): 最小市值过滤
- `volume_min` (optional): 最小成交量过滤
- `limit` (optional, default: 100): 最大结果数（1-500）

**响应**:
```json
{
  "criteria": "high_iv",
  "count": 50,
  "stocks": [
    {
      "symbol": "AAPL",
      "price": 150.25,
      "change_percent": 1.5,
      "volume": 50000000
    }
  ]
}
```

**说明**:
- 使用 Tiger Market Scanner API
- 支持多种扫描条件
- 用于发现高波动率、活跃股票等

---

## 策略管理 API

### `POST /api/v1/strategies`

**功能**: 创建新策略

**认证**: 需要认证

**请求体**:
```json
{
  "name": "My Iron Condor",
  "legs_json": {
    "legs": [
      {
        "symbol": "AAPL",
        "strike": 150.0,
        "type": "CALL",
        "action": "sell",
        "quantity": 1,
        "expiration_date": "2024-06-21"
      }
    ]
  }
}
```

**响应**:
```json
{
  "id": "strategy-uuid",
  "name": "My Iron Condor",
  "legs_json": {...},
  "created_at": "2024-01-24T00:00:00Z"
}
```

---

### `GET /api/v1/strategies`

**功能**: 获取用户策略列表（分页）

**认证**: 需要认证

**查询参数**:
- `limit` (optional, default: 10): 每页数量（1-100）
- `offset` (optional, default: 0): 偏移量

**响应**:
```json
[
  {
    "id": "strategy-uuid",
    "name": "My Iron Condor",
    "legs_json": {...},
    "created_at": "2024-01-24T00:00:00Z"
  }
]
```

---

### `GET /api/v1/strategies/{strategy_id}`

**功能**: 获取单个策略详情

**认证**: 需要认证

**路径参数**:
- `strategy_id`: 策略 UUID

**响应**: 同创建策略响应

---

### `PUT /api/v1/strategies/{strategy_id}`

**功能**: 更新策略

**认证**: 需要认证

**路径参数**:
- `strategy_id`: 策略 UUID

**请求体**: 同创建策略请求体

**响应**: 同创建策略响应

---

### `DELETE /api/v1/strategies/{strategy_id}`

**功能**: 删除策略

**认证**: 需要认证

**路径参数**:
- `strategy_id`: 策略 UUID

**响应**: 204 No Content

---

## AI 分析 API

### `POST /api/v1/ai/report`

**功能**: 生成 AI 分析报告

**认证**: 需要认证

**请求体**:
```json
{
  "strategy_summary": {
    "symbol": "AAPL",
    "strategy_name": "Iron Condor",
    "legs": [...],
    "portfolio_greeks": {...},
    "metrics": {...}
  },
  "option_chain": {...},
  "use_multi_agent": false,
  "async_mode": false
}
```

**响应** (同步模式):
```json
{
  "id": "report-uuid",
  "report_content": "# Strategy Analysis\n\n...",
  "model_used": "gemini-2.5-pro",
  "created_at": "2024-01-24T00:00:00Z",
  "metadata": {
    "mode": "single-agent",
    "quota_used": 1
  }
}
```

**响应** (异步模式):
```json
{
  "id": "task-uuid",
  "task_type": "ai_report",
  "status": "PENDING",
  "result_ref": null,
  "metadata": {...}
}
```

**说明**:
- 配额要求：单 Agent 模式 1 单位，多 Agent 模式 5 单位
- 支持同步和异步模式
- 异步模式返回 Task ID，可通过 `/api/v1/tasks/{task_id}` 查询进度
- 配额不足时自动降级到单 Agent 模式

---

### `POST /api/v1/ai/report/multi-agent`

**功能**: 生成多 Agent 分析报告（专用端点）

**认证**: 需要认证

**请求体**: 同 `/ai/report`，但强制使用多 Agent 模式

**说明**:
- 始终使用多 Agent 模式（5 个专业 Agent）
- 等价于 `use_multi_agent=true`

---

### `GET /api/v1/ai/daily-picks`

**功能**: 获取每日 AI 精选策略

**认证**: 无需认证（公开端点）

**查询参数**:
- `date` (optional): 日期，格式 YYYY-MM-DD（默认：今天 EST）

**响应**:
```json
{
  "date": "2024-01-24",
  "content_json": [
    {
      "symbol": "AAPL",
      "strategy_name": "Iron Condor",
      "description": "...",
      "legs": [...]
    }
  ],
  "created_at": "2024-01-24T00:00:00Z"
}
```

---

### `GET /api/v1/ai/reports`

**功能**: 获取用户的 AI 报告列表（分页）

**认证**: 需要认证

**查询参数**:
- `limit` (optional, default: 10): 每页数量（1-100）
- `offset` (optional, default: 0): 偏移量

**响应**:
```json
[
  {
    "id": "report-uuid",
    "report_content": "...",
    "model_used": "gemini-2.5-pro",
    "created_at": "2024-01-24T00:00:00Z"
  }
]
```

---

### `GET /api/v1/ai/reports/{report_id}`

**功能**: 获取单个 AI 报告详情

**认证**: 需要认证

**路径参数**:
- `report_id`: 报告 UUID

---

### `DELETE /api/v1/ai/reports/{report_id}`

**功能**: 删除 AI 报告

**认证**: 需要认证

**路径参数**:
- `report_id`: 报告 UUID

**响应**: 204 No Content

---

### AI 工作流端点

#### `POST /api/v1/ai/workflows/options-analysis`

**功能**: 期权分析工作流（多 Agent，详细结果）

**认证**: 需要认证

**请求体**:
```json
{
  "strategy_summary": {...},
  "option_chain": {...},
  "include_metadata": true,
  "async_mode": false
}
```

**响应** (同步模式):
```json
{
  "report": "# Comprehensive Analysis\n\n...",
  "parallel_analysis": {
    "options_greeks_analyst": {...},
    "iv_environment_analyst": {...},
    "market_context_analyst": {...}
  },
  "risk_analysis": {...},
  "synthesis": {...},
  "execution_time_ms": 8500,
  "metadata": {
    "mode": "multi-agent",
    "quota_used": 5,
    "total_agents": 5,
    "successful_agents": 5
  }
}
```

**说明**:
- 返回详细的中间 Agent 输出
- 适用于需要深度分析的场景
- 配额：5 单位

---

#### `POST /api/v1/ai/workflows/stock-screening`

**功能**: 股票筛选工作流（多 Agent）

**认证**: 需要认证

**请求体**:
```json
{
  "sector": "Technology",
  "industry": null,
  "market_cap": "Large Cap",
  "country": "United States",
  "limit": 10,
  "min_score": 7.0,
  "async_mode": false
}
```

**响应**:
```json
{
  "candidates": [
    {
      "symbol": "AAPL",
      "composite_score": 8.5,
      "analysis": {...}
    }
  ],
  "total_found": 50,
  "filtered_count": 10,
  "execution_time_ms": 12000,
  "metadata": {...}
}
```

**说明**:
- 使用多 Agent 进行基本面和技术面分析
- 配额：根据候选数量估算（最多 5 单位）

---

### AI 图表生成

#### `POST /api/v1/ai/chart`

**功能**: 生成策略图表图像

**认证**: 需要认证

**请求体**: 同 `/ai/report` 请求体

**响应**:
```json
{
  "task_id": "task-uuid",
  "image_id": null,
  "cached": false
}
```

**说明**:
- 创建异步任务生成图表
- 配额：图像生成配额（Free: 1, Pro Monthly: 10, Pro Yearly: 30）
- 通过 Task ID 查询生成进度

---

#### `GET /api/v1/ai/chart/{image_id}`

**功能**: 获取生成的图表图像

**认证**: 需要认证

**路径参数**:
- `image_id`: 图像 UUID

**响应**: 302 Redirect 到 Cloudflare R2 URL

---

#### `GET /api/v1/ai/chart/info/{image_id}`

**功能**: 获取图表图像信息（包括 R2 URL）

**认证**: 需要认证

**响应**:
```json
{
  "r2_url": "https://r2-url.com/image.png",
  "image_id": "image-uuid"
}
```

---

#### `GET /api/v1/ai/chart/by-hash/{strategy_hash}`

**功能**: 通过策略哈希查找已生成的图表

**认证**: 需要认证

**路径参数**:
- `strategy_hash`: 策略 SHA256 哈希（64 字符十六进制）

**响应**:
```json
{
  "image_id": "image-uuid",
  "r2_url": "https://r2-url.com/image.png"
}
```

**说明**:
- 用于图表缓存/重用
- 如果未找到，返回 `{"image_id": null}`

---

#### `GET /api/v1/ai/chart/{image_id}/download`

**功能**: 下载图表图像（PDF 导出）

**认证**: 需要认证

**响应**: PDF 文件下载

---

### Agent 管理

#### `GET /api/v1/ai/agents/list`

**功能**: 列出所有可用的 Agent

**认证**: 需要认证

**查询参数**:
- `agent_type` (optional): 按类型过滤

**响应**:
```json
{
  "agents": [
    {
      "name": "options_greeks_analyst",
      "type": "options_analysis",
      "description": "Analyzes option Greeks..."
    }
  ],
  "total_count": 5
}
```

---

## 支付系统 API

### `POST /api/v1/payment/checkout`

**功能**: 创建 Lemon Squeezy 结账链接

**认证**: 需要认证

**请求体**:
```json
{
  "variant_type": "monthly"
}
```

**响应**:
```json
{
  "checkout_url": "https://checkout.lemonsqueezy.com/...",
  "checkout_id": "checkout_xxx"
}
```

**说明**:
- `variant_type`: "monthly" 或 "yearly"
- 返回结账链接，用户完成支付后通过 Webhook 更新订阅状态

---

### `POST /api/v1/payment/webhook`

**功能**: Lemon Squeezy Webhook 端点

**认证**: 无需认证（通过 HMAC 签名验证）

**请求头**:
- `X-Signature`: HMAC SHA256 签名

**说明**:
- 处理订阅创建、更新、过期、取消等事件
- 自动更新用户 `is_pro` 状态
- 始终返回 200（防止重试和信息泄露）
- 速率限制：10 请求/分钟/IP

---

### `GET /api/v1/payment/pricing`

**功能**: 获取订阅价格信息

**认证**: 无需认证（公开端点）

**响应**:
```json
{
  "monthly_price": 9.9,
  "yearly_price": 599.0
}
```

---

### `GET /api/v1/payment/portal`

**功能**: 获取客户门户 URL（管理订阅）

**认证**: 需要认证

**响应**:
```json
{
  "portal_url": "https://portal.lemonsqueezy.com/..."
}
```

**说明**:
- 仅限有活跃订阅的用户

---

## 任务管理 API

### `POST /api/v1/tasks`

**功能**: 创建异步任务

**认证**: 需要认证

**请求体**:
```json
{
  "task_type": "ai_report",
  "metadata": {...}
}
```

**响应**:
```json
{
  "id": "task-uuid",
  "task_type": "ai_report",
  "status": "PENDING",
  "result_ref": null,
  "error_message": null,
  "metadata": {...},
  "execution_history": [],
  "created_at": "2024-01-24T00:00:00Z"
}
```

**支持的任务类型**:
- `ai_report`: AI 报告生成（单 Agent）
- `multi_agent_report`: AI 报告生成（多 Agent）
- `options_analysis_workflow`: 期权分析工作流
- `stock_screening_workflow`: 股票筛选工作流
- `generate_strategy_chart`: 策略图表生成

---

### `GET /api/v1/tasks`

**功能**: 获取用户任务列表（分页）

**认证**: 需要认证

**查询参数**:
- `limit` (optional, default: 10): 每页数量
- `offset` (optional, default: 0): 偏移量
- `status` (optional): 按状态过滤（PENDING, PROCESSING, SUCCESS, FAILED）
- `task_type` (optional): 按任务类型过滤

**响应**:
```json
[
  {
    "id": "task-uuid",
    "task_type": "ai_report",
    "status": "SUCCESS",
    "result_ref": "report-uuid",
    "execution_history": [
      {
        "timestamp": "2024-01-24T00:00:00Z",
        "event": "progress",
        "message": "Phase 1: Parallel analysis...",
        "progress": 10
      }
    ],
    "created_at": "2024-01-24T00:00:00Z",
    "completed_at": "2024-01-24T00:00:10Z"
  }
]
```

---

### `GET /api/v1/tasks/{task_id}`

**功能**: 获取单个任务详情

**认证**: 需要认证

**路径参数**:
- `task_id`: 任务 UUID

**响应**: 同任务列表中的单个任务对象

---

### `DELETE /api/v1/tasks/{task_id}`

**功能**: 删除任务

**认证**: 需要认证

**路径参数**:
- `task_id`: 任务 UUID

**响应**: 204 No Content

---

## 管理员 API

### `GET /api/v1/admin/configs`

**功能**: 获取所有系统配置

**认证**: 需要认证 + Superuser 权限

**响应**:
```json
[
  {
    "key": "ai_prompt_template",
    "value": "...",
    "description": "AI prompt template",
    "updated_at": "2024-01-24T00:00:00Z"
  }
]
```

---

### `GET /api/v1/admin/configs/{key}`

**功能**: 获取特定系统配置

**认证**: 需要认证 + Superuser 权限

**路径参数**:
- `key`: 配置键名

---

### `PUT /api/v1/admin/configs/{key}`

**功能**: 更新系统配置

**认证**: 需要认证 + Superuser 权限

**路径参数**:
- `key`: 配置键名

**请求体**:
```json
{
  "value": "new value",
  "description": "updated description"
}
```

---

### `DELETE /api/v1/admin/configs/{key}`

**功能**: 删除系统配置

**认证**: 需要认证 + Superuser 权限

**路径参数**:
- `key`: 配置键名

**响应**: 204 No Content

---

## 系统端点

### `GET /health`

**功能**: 健康检查

**认证**: 无需认证

**响应**:
```json
{
  "status": "healthy",
  "environment": "production"
}
```

---

### `GET /`

**功能**: 根端点

**认证**: 无需认证

**响应**:
```json
{
  "message": "ThetaMind API",
  "version": "0.1.0",
  "docs": "/docs"
}
```

---

## 配额系统

### 配额类型

1. **AI 报告配额**:
   - Free: 1 次/天
   - Pro Monthly: 10 次/天
   - Pro Yearly: 30 次/天
   - 多 Agent 模式消耗 5 单位配额

2. **图像生成配额**:
   - Free: 1 次/天
   - Pro Monthly: 10 次/天
   - Pro Yearly: 30 次/天

3. **配额重置**:
   - 每日 UTC 00:00 自动重置
   - 或通过调度器在日期变更时重置

### 配额检查

- 所有 AI 相关端点都会检查配额
- 配额不足时返回 `429 Too Many Requests`
- 多 Agent 模式配额不足时自动降级到单 Agent 模式

---

## 缓存策略

### 市场数据缓存

- **期权链**: 所有用户 10 分钟 TTL
- **股票报价**: Pro 用户 5 秒，Free 用户 15 分钟
- **历史数据**: 1 小时 TTL
- **技术指标**: 根据数据频率动态调整

### 缓存键格式

- 期权链: `option_chain:{symbol}:{expiration_date}`
- 股票报价: `stock_quote:{symbol}:{user_type}`
- 历史数据: `historical:{symbol}:{interval}:{limit}`

---

## 错误处理

### 常见错误码

- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: Token 无效或过期
- `403 Forbidden`: Free 用户尝试使用 Pro 功能
- `404 Not Found`: 资源不存在
- `429 Too Many Requests`: 配额超限
- `500 Internal Server Error`: 服务器错误
- `503 Service Unavailable`: 服务不可用（Circuit Breaker）

### 错误响应格式

```json
{
  "detail": "Error message description"
}
```

---

## 速率限制

### 当前限制

- **Webhook**: 10 请求/分钟/IP
- **API 调用**: 无全局限制（依赖外部 API 配额）

### 未来计划

- 基于用户类型的速率限制
- Redis 分布式速率限制

---

## 版本控制

- 当前版本: `v1`
- API 版本通过路径前缀 `/api/v1` 标识
- 未来版本将使用 `/api/v2` 等

---

## 安全考虑

1. **认证**: JWT Bearer Token
2. **授权**: 基于用户角色（Free/Pro/Superuser）
3. **Webhook 安全**: HMAC SHA256 签名验证
4. **CORS**: 生产环境限制允许的来源
5. **数据验证**: Pydantic 模型验证所有输入

---

**文档维护**: 本文档应随 API 变更及时更新。  
**最后更新**: 2025-01-24
