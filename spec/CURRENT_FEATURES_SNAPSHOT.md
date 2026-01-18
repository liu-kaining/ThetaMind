# ThetaMind 当前功能快照 (Feature Snapshot)

**创建日期:** 2025-01-XX  
**目的:** 记录当前所有功能，以便后续回退到当前版本  
**Git 状态:** `main` 分支，工作区干净

---

## 📋 目录

1. [后端功能清单](#后端功能清单)
2. [前端功能清单](#前端功能清单)
3. [数据库 Schema](#数据库-schema)
4. [核心服务层](#核心服务层)
5. [API 端点完整列表](#api-端点完整列表)
6. [回退指南](#回退指南)

---

## 后端功能清单

### 1. 认证系统 (Auth)
- ✅ Google OAuth2 登录 (`POST /api/v1/auth/google`)
- ✅ JWT Token 生成和验证
- ✅ 用户信息获取 (`GET /api/v1/auth/me`)
- ✅ 用户模型：`User` (UUID, email, google_sub, is_pro, subscription_type, etc.)

### 2. 市场数据服务 (Market)
- ✅ 期权链数据 (`GET /api/v1/market/chain`)
  - 支持 Pro/Free 用户差异化缓存（Pro: 10分钟，Free: 10分钟）
  - 支持 `force_refresh` 参数（仅 Pro 用户可用）
  - 数据标准化处理（Greeks, IV, 价格等）
- ✅ 股票报价 (`GET /api/v1/market/quote`)
  - 使用价格推断（cost-efficient）
- ✅ 股票搜索 (`GET /api/v1/market/search`)
  - 本地数据库快速搜索（ILIKE）
- ✅ 期权到期日列表 (`GET /api/v1/market/expirations`)
- ✅ 历史K线数据 (`GET /api/v1/market/history`)
  - 支持 period (day/week/month) 和 limit 参数
- ✅ 策略推荐 (`POST /api/v1/market/recommendations`)
  - 基于 Greeks 的算法推荐（非 AI）
- ✅ 市场扫描器 (`POST /api/v1/market/scanner`)
  - 支持 high_iv, top_gainers, most_active, top_losers, high_volume

### 3. AI 功能 (AI)
- ✅ AI 报告生成 (`POST /api/v1/ai/report`)
  - 配额管理（Free: 1/天，Pro Monthly: 10/天，Pro Yearly: 30/天）
  - 自动配额重置（基于 UTC 日期）
  - 支持 `strategy_summary` 和 `strategy_data` 两种格式
- ✅ 每日精选 (`GET /api/v1/ai/daily-picks`)
  - 公开端点（无需认证）
  - 支持日期参数（默认今天 EST）
- ✅ 用户报告列表 (`GET /api/v1/ai/reports`)
  - 分页支持（limit, offset）
- ✅ 删除报告 (`DELETE /api/v1/ai/reports/{report_id}`)
- ✅ AI 图表生成 (`POST /api/v1/ai/chart`)
  - 配额管理（Free: 1/天，Pro Monthly: 10/天，Pro Yearly: 30/天）
  - 异步任务创建
- ✅ 图表信息获取 (`GET /api/v1/ai/chart/info/{image_id}`)
- ✅ 图表下载 (`GET /api/v1/ai/chart/{image_id}/download`)
- ✅ 按 Hash 查询图表 (`GET /api/v1/ai/chart/by-hash/{strategy_hash}`)
  - 支持图表缓存/复用

### 4. 策略管理 (Strategies)
- ✅ 创建策略 (`POST /api/v1/strategies`)
- ✅ 策略列表 (`GET /api/v1/strategies`)
  - 分页支持（limit, offset）
- ✅ 获取策略 (`GET /api/v1/strategies/{strategy_id}`)
- ✅ 更新策略 (`PUT /api/v1/strategies/{strategy_id}`)
- ✅ 删除策略 (`DELETE /api/v1/strategies/{strategy_id}`)

### 5. 支付系统 (Payment)
- ✅ Lemon Squeezy 集成
- ✅ Webhook 验证和审计日志
- ✅ 支付成功回调处理
- ✅ 订阅管理（monthly/yearly）
- ✅ 支付门户 (`GET /api/v1/payment/portal`)

### 6. 任务系统 (Tasks)
- ✅ 异步任务创建和管理
- ✅ 任务状态跟踪（PENDING, PROCESSING, SUCCESS, FAILED）
- ✅ 任务详情查询 (`GET /api/v1/tasks/{task_id}`)
- ✅ 任务列表 (`GET /api/v1/tasks`)
- ✅ 执行历史记录（execution_history）
- ✅ 重试机制（retry_count）

### 7. 管理员功能 (Admin)
- ✅ 系统配置管理 (`GET /api/v1/admin/configs`, `PUT /api/v1/admin/configs/{key}`)
- ✅ 用户管理 (`GET /api/v1/admin/users`)
- ✅ Superuser 权限保护

### 8. 调度器 (Scheduler)
- ✅ 每日精选自动生成（08:30 EST）
- ✅ 配额自动重置（00:00 UTC）
- ✅ 冷启动检查（启动时检查并生成每日精选）

---

## 前端功能清单

### 1. 页面 (Pages)
- ✅ **LandingPage** (`/`) - 落地页，i18n 支持
- ✅ **LoginPage** (`/login`) - Google OAuth 登录
- ✅ **DashboardPage** (`/dashboard`) - 仪表盘
  - 统计卡片
  - 策略列表
  - AI 报告模态框
- ✅ **StrategyLab** (`/strategy-lab`) - 策略实验室
  - 策略构建器（4腿限制）
  - Payoff 图表
  - 期权链表格（分页）
  - 策略模板（24个模板，分页）
  - Smart Price Advisor（Pro 功能，模糊覆盖）
  - Trade Cheat Sheet 模态框
  - AI 分析集成
- ✅ **DailyPicks** (`/daily-picks`) - 每日精选
  - AI 生成的策略卡片展示
- ✅ **Pricing** (`/pricing`) - 定价页面
  - Free vs Pro 对比
  - 结账集成
- ✅ **TaskCenter** (`/dashboard/tasks`) - 任务中心
  - 任务列表和状态
- ✅ **TaskDetailPage** (`/dashboard/tasks/:taskId`) - 任务详情
- ✅ **ReportsPage** (`/reports`) - 报告页面
  - 显示 "Coming Soon" 占位符（后端 API 已存在）
- ✅ **SettingsPage** (`/settings`) - 设置页面
  - 个人资料（只读，来自 Google）
  - 订阅信息（计划、续费日期）
  - 使用配额（AI Daily Usage 进度条）
  - 支付门户按钮
- ✅ **AboutPage** (`/about`) - 关于页面
- ✅ **DemoPage** (`/demo`) - 演示页面
- ✅ **PaymentSuccess** (`/payment/success`) - 支付成功页面
  - 轮询逻辑（每2秒检查一次，最多30次）
  - 自动重定向（3秒后）
- ✅ **AdminSettings** (`/admin/settings`) - 管理员设置
  - 配置管理
  - Prompt 编辑器
- ✅ **AdminUsers** (`/admin/users`) - 管理员用户管理

### 2. 组件 (Components)
- ✅ **MainLayout** - 主布局
  - 侧边栏导航
  - 响应式设计
  - 主题切换（Dark/Light）
  - 用户菜单
- ✅ **Charts**
  - PayoffChart（带导出功能）
  - CandlestickChart（未集成到页面）
- ✅ **Market**
  - OptionChainPriceView
  - OptionChainTable
  - OptionChainVisualization
  - SymbolSearch
- ✅ **Strategy**
  - AIChartTab
  - ScenarioSimulator
  - SmartPriceAdvisor
  - StrategyGreeks
  - StrategyTemplateCard
  - StrategyTemplatesPagination
  - TradeCheatSheet
- ✅ **Tasks**
  - TaskStatusBadge
  - TaskTable
- ✅ **Auth**
  - ProtectedRoute
  - AdminRoute

### 3. 服务层 (Services)
- ✅ API 客户端 (`services/api/`)
  - `auth.ts` - 认证 API
  - `market.ts` - 市场数据 API
  - `ai.ts` - AI API
  - `strategy.ts` - 策略 API
  - `task.ts` - 任务 API
  - `payment.ts` - 支付 API
  - `admin.ts` - 管理员 API
- ✅ React Query 集成（TanStack Query）
- ✅ Zustand 状态管理（全局应用状态）

---

## 数据库 Schema

### 表结构

#### 1. `users`
- `id` (UUID, PK)
- `email` (String, unique, indexed)
- `google_sub` (String, unique, indexed)
- `is_pro` (Boolean, default: false)
- `is_superuser` (Boolean, default: false)
- `subscription_id` (String, nullable)
- `subscription_type` (String, nullable) - "monthly" or "yearly"
- `plan_expiry_date` (DateTime, nullable)
- `daily_ai_usage` (Integer, default: 0)
- `daily_image_usage` (Integer, default: 0)
- `last_quota_reset_date` (DateTime, nullable) - UTC 日期
- `created_at` (DateTime, UTC)

#### 2. `strategies`
- `id` (UUID, PK)
- `user_id` (UUID, FK -> users.id, indexed)
- `name` (String)
- `legs_json` (JSONB)
- `created_at` (DateTime, UTC)

#### 3. `ai_reports`
- `id` (UUID, PK)
- `user_id` (UUID, FK -> users.id, indexed)
- `report_content` (Text)
- `model_used` (String)
- `created_at` (DateTime, UTC)

#### 4. `payment_events`
- `id` (UUID, PK)
- `lemon_squeezy_id` (String, unique, indexed)
- `event_name` (String)
- `payload` (JSONB)
- `processed` (Boolean, default: false)
- `created_at` (DateTime, UTC)

#### 5. `daily_picks`
- `id` (UUID, PK)
- `date` (Date, unique, indexed)
- `content_json` (JSONB)
- `created_at` (DateTime, UTC)

#### 6. `system_configs`
- `id` (UUID, PK)
- `key` (String, unique, indexed)
- `value` (Text)
- `description` (String, nullable)
- `updated_by` (UUID, FK -> users.id, nullable)
- `updated_at` (DateTime, UTC)
- `created_at` (DateTime, UTC)

#### 7. `generated_images`
- `id` (UUID, PK)
- `user_id` (UUID, FK -> users.id, indexed)
- `task_id` (UUID, FK -> tasks.id, nullable, indexed)
- `base64_data` (Text, nullable) - 遗留字段
- `r2_url` (String, nullable, indexed) - Cloudflare R2 URL（首选）
- `strategy_hash` (String, nullable, indexed) - 策略 Hash（用于缓存）
- `created_at` (DateTime, UTC, indexed)
- 索引：`ix_generated_images_user_created`, `ix_generated_images_user_strategy_hash`

#### 8. `stock_symbols`
- `symbol` (String, PK)
- `name` (String)
- `market` (String, default: "US")
- `is_active` (Boolean, default: true)
- `created_at` (DateTime, UTC)
- `updated_at` (DateTime, UTC)
- 索引：`ix_stock_symbols_name`, `ix_stock_symbols_market_active`

#### 9. `tasks`
- `id` (UUID, PK)
- `user_id` (UUID, FK -> users.id, nullable, indexed)
- `task_type` (String, indexed)
- `status` (String, default: "PENDING", indexed) - PENDING, PROCESSING, SUCCESS, FAILED
- `result_ref` (String, nullable)
- `error_message` (Text, nullable)
- `task_metadata` (JSONB, nullable)
- `execution_history` (JSONB, nullable) - 执行时间线
- `prompt_used` (Text, nullable)
- `model_used` (String, nullable)
- `started_at` (DateTime, nullable)
- `retry_count` (Integer, default: 0)
- `created_at` (DateTime, UTC, indexed)
- `updated_at` (DateTime, UTC)
- `completed_at` (DateTime, nullable)
- 索引：`ix_tasks_user_status`, `ix_tasks_created_at`

### 数据库迁移版本

当前最新迁移：`009_add_last_quota_reset_date.py`

迁移历史：
1. `001_add_superuser_and_system_configs.py`
2. `002_add_stock_symbols.py`
3. `003_add_task_execution_history.py`
4. `004_add_generated_images_table.py`
5. `005_allow_system_tasks_null_user.py`
6. `006_add_strategy_hash_to_generated_images.py`
7. `007_add_subscription_type_and_image_usage.py`
8. `008_add_r2_url_to_generated_images.py`
9. `009_add_last_quota_reset_date.py`

---

## 核心服务层

### 1. Tiger Service (`tiger_service.py`)
- ✅ 期权链获取（带缓存）
- ✅ 股票报价
- ✅ 期权到期日列表
- ✅ 历史K线数据
- ✅ 市场扫描器
- ✅ 熔断器（Circuit Breaker）
- ✅ 重试逻辑（Tenacity）
- ✅ Redis 缓存（10分钟 TTL）

### 2. AI Service (`ai_service.py`)
- ✅ Gemini 3.0 Pro 集成
- ✅ 报告生成
- ✅ 每日精选生成
- ✅ 上下文过滤
- ✅ BaseAIProvider 抽象类（支持切换模型）

### 3. Payment Service (`payment_service.py`)
- ✅ Lemon Squeezy Webhook 处理
- ✅ 签名验证
- ✅ 订阅状态更新
- ✅ 审计日志

### 4. Strategy Engine (`strategy_engine.py`)
- ✅ Greeks 计算
- ✅ 策略生成算法
- ✅ 严格验证规则

### 5. Cache Service (`cache.py`)
- ✅ Redis 连接管理
- ✅ 缓存操作（get, set, delete）
- ✅ 降级处理（Redis 不可用时继续运行）

### 6. Config Service (`config_service.py`)
- ✅ Redis 缓存配置
- ✅ 数据库回退
- ✅ 动态配置管理

### 7. Scheduler (`scheduler.py`)
- ✅ APScheduler 集成
- ✅ 每日精选任务（08:30 EST）
- ✅ 配额重置任务（00:00 UTC）

### 8. Storage Service (`storage/r2_service.py`)
- ✅ Cloudflare R2 集成
- ✅ 图片上传和下载
- ✅ URL 生成

---

## API 端点完整列表

### 根端点
- `GET /health` - 健康检查
- `GET /` - API 信息
- `GET /docs` - Swagger UI（非生产环境）
- `GET /redoc` - ReDoc（非生产环境）

### 认证 (`/api/v1/auth`)
- `POST /api/v1/auth/google` - Google OAuth 登录
- `GET /api/v1/auth/me` - 获取当前用户信息

### 市场数据 (`/api/v1/market`)
- `GET /api/v1/market/chain` - 获取期权链
- `GET /api/v1/market/quote` - 获取股票报价
- `GET /api/v1/market/search` - 搜索股票代码
- `GET /api/v1/market/expirations` - 获取期权到期日
- `GET /api/v1/market/history` - 获取历史K线数据
- `GET /api/v1/market/historical` - 历史数据（遗留端点）
- `POST /api/v1/market/recommendations` - 策略推荐
- `POST /api/v1/market/scanner` - 市场扫描器

### AI 功能 (`/api/v1/ai`)
- `POST /api/v1/ai/report` - 生成 AI 报告
- `GET /api/v1/ai/daily-picks` - 获取每日精选
- `GET /api/v1/ai/reports` - 获取用户报告列表
- `DELETE /api/v1/ai/reports/{report_id}` - 删除报告
- `POST /api/v1/ai/chart` - 生成策略图表
- `GET /api/v1/ai/chart/info/{image_id}` - 获取图表信息
- `GET /api/v1/ai/chart/{image_id}` - 获取图表（重定向到 R2）
- `GET /api/v1/ai/chart/{image_id}/download` - 下载图表
- `GET /api/v1/ai/chart/by-hash/{strategy_hash}` - 按 Hash 查询图表

### 策略管理 (`/api/v1/strategies`)
- `POST /api/v1/strategies` - 创建策略
- `GET /api/v1/strategies` - 获取策略列表
- `GET /api/v1/strategies/{strategy_id}` - 获取策略详情
- `PUT /api/v1/strategies/{strategy_id}` - 更新策略
- `DELETE /api/v1/strategies/{strategy_id}` - 删除策略

### 支付 (`/api/v1/payment`)
- `POST /api/v1/payment/webhook` - Lemon Squeezy Webhook
- `GET /api/v1/payment/portal` - 支付门户

### 任务 (`/api/v1/tasks`)
- `GET /api/v1/tasks` - 获取任务列表
- `GET /api/v1/tasks/{task_id}` - 获取任务详情

### 管理员 (`/api/v1/admin`)
- `GET /api/v1/admin/configs` - 获取系统配置
- `PUT /api/v1/admin/configs/{key}` - 更新系统配置
- `GET /api/v1/admin/users` - 获取用户列表

---

## 回退指南

### 方法 1: 使用 Git 标签（推荐）

```bash
# 1. 创建标签保存当前状态
git tag -a v1.0.0-baseline -m "Baseline: Current ThetaMind features before new feature development"

# 2. 推送到远程
git push origin v1.0.0-baseline

# 3. 如果需要回退
git checkout v1.0.0-baseline
# 或者创建新分支
git checkout -b rollback-to-baseline v1.0.0-baseline
```

### 方法 2: 使用 Git 分支

```bash
# 1. 创建基线分支
git checkout -b baseline/current-features
git push origin baseline/current-features

# 2. 如果需要回退
git checkout baseline/current-features
# 或者合并到 main
git checkout main
git merge baseline/current-features
```

### 方法 3: 使用 Git Commit Hash

当前最新提交：`8446ba3` (docs: Add Financial Libraries Integration Plan)

```bash
# 如果需要回退到当前提交
git checkout 8446ba3
# 或者创建新分支
git checkout -b rollback-to-8446ba3 8446ba3
```

### 方法 4: 数据库回退

如果新功能涉及数据库迁移，需要回退迁移：

```bash
# 查看当前迁移版本
alembic current

# 回退到特定版本（例如回退到 009）
alembic downgrade 009_add_last_quota_reset_date

# 或者回退一个版本
alembic downgrade -1
```

**注意：** 数据库回退可能会丢失数据，请确保在回退前备份数据库。

### 方法 5: 功能开关（Feature Flags）

如果使用功能开关，可以通过配置快速禁用新功能：

```bash
# 在 system_configs 表中设置
# key: "new_feature_enabled"
# value: "false"
```

---

## 重要配置

### 环境变量（关键配置）

- `GOOGLE_CLIENT_ID` - Google OAuth Client ID
- `GEMINI_API_KEY` - Gemini API Key
- `TIGER_API_KEY` - Tiger Brokers API Key
- `LEMON_SQUEEZY_WEBHOOK_SECRET` - Lemon Squeezy Webhook Secret
- `DATABASE_URL` - PostgreSQL 连接字符串
- `REDIS_URL` - Redis 连接字符串
- `R2_ACCESS_KEY_ID` - Cloudflare R2 Access Key
- `R2_SECRET_ACCESS_KEY` - Cloudflare R2 Secret Key
- `R2_BUCKET_NAME` - R2 Bucket 名称
- `R2_ENDPOINT_URL` - R2 Endpoint URL

### 配额配置

- **Free 用户:**
  - AI 报告: 1/天
  - AI 图表: 1/天
- **Pro Monthly 用户 ($9.9/月):**
  - AI 报告: 10/天
  - AI 图表: 10/天
- **Pro Yearly 用户 ($599/年):**
  - AI 报告: 30/天
  - AI 图表: 30/天

### 技术栈版本

- **后端:**
  - Python 3.11+
  - FastAPI (Async)
  - SQLAlchemy (Async)
  - Alembic (数据库迁移)
  - PostgreSQL
  - Redis
  - APScheduler
- **前端:**
  - React 18
  - TypeScript
  - Vite
  - Shadcn/UI
  - Tailwind CSS
  - TanStack Query (React Query)
  - Zustand
  - lightweight-charts
  - recharts

### 第三方服务集成

- **Google OAuth2** - 用户认证
- **Gemini 3.0 Pro** - AI 报告生成（默认）
- **ZenMux** - AI 报告生成（可选）
- **Tiger Brokers API** - 期权市场数据
- **Lemon Squeezy** - 支付和订阅管理
- **Cloudflare R2** - 图片存储

---

## 文件结构快照

### 后端关键文件

```
backend/app/
├── main.py                    # FastAPI 应用入口
├── api/
│   ├── admin.py               # 管理员端点
│   ├── deps.py                # 依赖注入（认证等）
│   ├── endpoints/
│   │   ├── ai.py              # AI 功能端点
│   │   ├── auth.py             # 认证端点
│   │   ├── market.py           # 市场数据端点
│   │   ├── payment.py          # 支付端点
│   │   ├── strategy.py         # 策略管理端点
│   │   └── tasks.py            # 任务管理端点
│   └── schemas/                # API 响应模型
├── core/
│   ├── config.py              # 配置管理
│   └── security.py            # 安全工具（JWT）
├── db/
│   ├── models.py              # 数据库模型
│   └── session.py             # 数据库会话
├── services/
│   ├── ai_service.py          # AI 服务主入口
│   ├── ai/
│   │   ├── base.py            # BaseAIProvider 抽象类
│   │   ├── gemini_provider.py  # Gemini 实现
│   │   ├── zenmux_provider.py  # ZenMux 实现
│   │   └── image_provider.py   # AI 图表生成
│   ├── auth_service.py        # 认证服务
│   ├── cache.py               # Redis 缓存服务
│   ├── config_service.py      # 配置服务
│   ├── daily_picks_service.py # 每日精选服务
│   ├── market_scanner.py      # 市场扫描器
│   ├── payment_service.py     # 支付服务
│   ├── scheduler.py           # 调度器
│   ├── strategy_engine.py     # 策略引擎
│   ├── storage/
│   │   └── r2_service.py      # Cloudflare R2 存储
│   └── tiger_service.py       # Tiger API 服务
└── utils/
    └── strategy_hash.py       # 策略 Hash 计算
```

### 前端关键文件

```
frontend/src/
├── App.tsx                    # 主应用组件（路由）
├── pages/                     # 页面组件
│   ├── DashboardPage.tsx
│   ├── StrategyLab.tsx
│   ├── DailyPicks.tsx
│   ├── TaskCenter.tsx
│   ├── TaskDetailPage.tsx
│   ├── ReportsPage.tsx
│   ├── SettingsPage.tsx
│   ├── Pricing.tsx
│   ├── LoginPage.tsx
│   ├── LandingPage.tsx
│   └── admin/                 # 管理员页面
├── components/                # 可复用组件
│   ├── layout/
│   │   └── MainLayout.tsx
│   ├── charts/
│   │   ├── PayoffChart.tsx
│   │   └── CandlestickChart.tsx
│   ├── market/
│   │   ├── OptionChainTable.tsx
│   │   └── SymbolSearch.tsx
│   ├── strategy/
│   │   ├── StrategyGreeks.tsx
│   │   └── SmartPriceAdvisor.tsx
│   └── auth/
│       ├── ProtectedRoute.tsx
│       └── AdminRoute.tsx
├── services/api/              # API 客户端
│   ├── auth.ts
│   ├── market.ts
│   ├── ai.ts
│   ├── strategy.ts
│   ├── task.ts
│   ├── payment.ts
│   └── admin.ts
└── features/
    └── auth/
        └── AuthProvider.tsx
```

---

## API 端点详细补充

### 支付 (`/api/v1/payment`) - 补充

- `POST /api/v1/payment/checkout` - 创建结账链接
  - 请求体: `{ variant_type: "monthly" | "yearly" }`
  - 返回: `{ checkout_url, checkout_id }`
- `GET /api/v1/payment/pricing` - 获取定价信息（公开端点）
  - 返回: `{ monthly_price, yearly_price }`
- `POST /api/v1/payment/webhook` - Lemon Squeezy Webhook（公开端点，签名验证）
- `GET /api/v1/payment/portal` - 获取客户门户 URL

### 任务 (`/api/v1/tasks`) - 补充

- `POST /api/v1/tasks` - 创建任务
  - 请求体: `{ task_type, metadata }`
  - 支持的任务类型: `ai_report`, `generate_strategy_chart`, `daily_picks`
- `DELETE /api/v1/tasks/{task_id}` - 删除任务（同时删除关联的图片和 R2 文件）

### 管理员 (`/api/v1/admin`) - 补充

- `GET /api/v1/admin/configs/{key}` - 获取单个配置项
- `DELETE /api/v1/admin/configs/{key}` - 删除配置项
- `GET /api/v1/admin/users/{user_id}` - 获取用户详情
- `PUT /api/v1/admin/users/{user_id}` - 更新用户（is_pro, is_superuser, plan_expiry_date）
- `DELETE /api/v1/admin/users/{user_id}` - 删除用户（级联删除策略和报告）
- `POST /api/v1/admin/daily-picks/trigger` - 手动触发每日精选生成

---

## 重要业务逻辑

### 配额重置机制

- 基于 UTC 日期自动重置
- 每次检查配额时，如果 `last_quota_reset_date` 与今天不同，自动重置
- 调度器在 00:00 UTC 执行全局重置（双重保障）

### 任务处理流程

1. **创建任务** - 状态: PENDING
2. **后台处理开始** - 状态: PROCESSING
3. **执行历史记录** - 记录所有关键事件
4. **重试机制** - 最多 3 次，指数退避（2s, 4s, 8s）
5. **完成/失败** - 状态: SUCCESS 或 FAILED

### 图片存储策略

- **存储位置**: Cloudflare R2（必需）
- **文件命名**: `strategy_chart/{user_id}/{image_id}.{ext}`
- **策略 Hash**: 用于缓存查询，但不作为文件名（避免覆盖）
- **删除策略**: 删除任务时，同时删除数据库记录和 R2 文件

### 每日精选生成流程

1. **市场扫描** - 使用市场扫描器找到高 IV 股票
2. **策略生成** - 使用 StrategyEngine 生成策略
3. **AI 评论** - 使用 AI 服务为每个策略生成评论
4. **保存到数据库** - 按日期唯一存储（upsert）

---

## 回退检查清单

在开始新功能开发前，请确认：

- [ ] Git 标签已创建（`v1.0.0-baseline`）
- [ ] 基线分支已创建（`baseline/current-features`）
- [ ] 数据库已备份
- [ ] 当前迁移版本已记录（`009_add_last_quota_reset_date.py`）
- [ ] 环境变量配置已记录
- [ ] 第三方服务配置已记录（API Keys, Webhook Secrets）

---

**文档版本:** 1.0  
**最后更新:** 2025-01-XX  
**维护者:** ThetaMind Team