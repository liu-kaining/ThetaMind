# ThetaMind 系统架构技术白皮书

**版本**: 2.0  
**日期**: 2026-02-06  
**状态**: 完整文档（已上线生产环境）

---

## 📋 目录

1. [系统概述](#系统概述)
2. [整体架构](#整体架构)
3. [前端架构](#前端架构)
4. [后端架构](#后端架构)
5. [数据库架构](#数据库架构)
6. [服务层架构](#服务层架构)
7. [外部服务集成](#外部服务集成)
8. [数据流](#数据流)
9. [部署架构](#部署架构)
10. [依赖关系](#依赖关系)

---

## 系统概述

ThetaMind 是一个专业的美国股票期权策略分析平台，采用前后端分离的架构设计。系统专注于期权策略的风险分析、P&L 计算和 AI 驱动的深度分析，**不执行实际交易**。

### 核心特性

- **实时期权链数据**: 通过 Tiger Brokers API 获取，包含完整 Greeks，智能缓存策略确保数据新鲜度
- **实时股票报价**: 直接调用 FMP API `/stable/quote` 端点，确保获取当天实时价格而非延迟数据
- **股票市场数据**: 通过 FMP API 获取，支持历史数据、技术指标、基本面分析
- **策略推荐引擎**: 基于数学逻辑的算法推荐（非 AI）
- **多 Agent AI 分析**: 5 个专业 Agent 协作生成深度分析报告
- **异步任务系统**: 支持长时间运行的 AI 分析任务，防止重复运行机制
- **用户配额管理**: Free/Pro 差异化功能和服务
- **智能缓存策略**: 历史数据缓存自动检测过期，确保用户看到最新交易日数据

### 技术栈总览

- **前端**: React 18 + TypeScript + Vite + Tailwind CSS
- **后端**: FastAPI (Python 3.10+) + SQLAlchemy (Async) + Alembic
- **数据库**: PostgreSQL 15
- **缓存**: Redis 7
- **AI**: Google Gemini 3.0 Pro (Vertex AI)
- **支付**: Lemon Squeezy
- **存储**: Cloudflare R2 (S3-compatible)

---

## 整体架构

### 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Strategy │  │  Market  │  │   AI     │  │  Admin   │   │
│  │   Lab    │  │   Data   │  │ Reports  │  │ Settings │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS (REST API)
                       │ JWT Bearer Token
┌──────────────────────▼──────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              API Layer (Endpoints)                    │   │
│  │  /auth  /market  /strategies  /ai  /payment  /tasks  │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Service Layer                           │   │
│  │  MarketDataService  TigerService  AIService          │   │
│  │  StrategyEngine  AgentCoordinator  PaymentService    │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Data Layer                              │   │
│  │  SQLAlchemy (Async)  Redis Cache  Alembic Migrations│   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌────▼────┐ ┌──────▼──────┐
│  PostgreSQL  │ │  Redis   │ │  Cloudflare │
│   Database   │ │  Cache   │ │     R2      │
└──────────────┘ └──────────┘ └─────────────┘
        │
        │
┌───────▼──────────────────────────────────────┐
│         External Services                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Tiger  │  │   FMP    │  │ Gemini  │    │
│  │  API    │  │   API    │  │   AI    │    │
│  └──────────┘  └──────────┘  └──────────┘    │
│  ┌──────────┐  ┌──────────┐                  │
│  │ Lemon    │  │Finance   │                  │
│  │ Squeezy  │  │Toolkit   │                  │
│  └──────────┘  └──────────┘                  │
└───────────────────────────────────────────────┘
```

---

## 前端架构

### 技术栈

- **框架**: React 18.2.0
- **构建工具**: Vite 5.0.8
- **语言**: TypeScript 5.2.2
- **UI 库**: 
  - Shadcn/UI (基于 Radix UI)
  - Tailwind CSS 3.3.6
- **状态管理**: 
  - React Query (TanStack Query) 5.12.2 - 服务器状态
  - Zustand 4.4.7 - 全局应用状态
- **路由**: React Router DOM 6.20.0
- **图表库**:
  - Lightweight Charts 4.1.3 - K 线图
  - Recharts 2.10.3 - P&L 图表、面积图
- **认证**: @react-oauth/google 0.11.0
- **Markdown**: react-markdown 9.0.1 + remark-gfm 4.0.1
- **PDF 导出**: jspdf 3.0.4 + html2canvas 1.4.1
- **时区处理**: date-fns 2.30.0 + date-fns-tz 2.0.0

### 项目结构

```
frontend/
├── src/
│   ├── components/          # React 组件
│   │   ├── auth/           # 认证组件
│   │   ├── charts/         # 图表组件
│   │   ├── common/         # 通用组件
│   │   ├── layout/         # 布局组件
│   │   ├── market/         # 市场数据组件
│   │   ├── strategy/       # 策略相关组件
│   │   ├── tasks/          # 任务管理组件
│   │   └── ui/             # Shadcn/UI 基础组件
│   ├── contexts/           # React Context
│   │   └── LanguageContext.tsx
│   ├── features/           # 功能模块
│   │   └── auth/
│   │       └── AuthProvider.tsx
│   ├── lib/                # 工具库
│   │   ├── constants/      # 常量定义
│   │   ├── strategyTemplates.ts
│   │   └── utils.ts
│   ├── pages/              # 页面组件
│   │   ├── admin/          # 管理员页面
│   │   ├── payment/        # 支付页面
│   │   ├── show/           # 静态页面
│   │   ├── AboutPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── DailyPicks.tsx
│   │   ├── LandingPage.tsx
│   │   ├── LoginPage.tsx
│   │   ├── Pricing.tsx
│   │   ├── ReportsPage.tsx
│   │   ├── ReportDetailPage.tsx
│   │   ├── SettingsPage.tsx
│   │   ├── StrategyLab.tsx
│   │   ├── TaskCenter.tsx
│   │   └── TaskDetailPage.tsx
│   ├── services/           # API 服务层
│   │   └── api/
│   │       ├── admin.ts
│   │       ├── ai.ts
│   │       ├── auth.ts
│   │       ├── client.ts    # Axios 客户端配置
│   │       ├── market.ts
│   │       ├── payment.ts
│   │       ├── strategy.ts
│   │       └── task.ts
│   ├── utils/               # 工具函数
│   │   └── strategyHash.ts
│   ├── App.tsx              # 根组件
│   ├── main.tsx             # 入口文件
│   └── index.css            # 全局样式
├── package.json
└── vite.config.ts
```

### 核心页面

1. **LandingPage**: 首页/登录页
2. **DashboardPage**: 用户仪表板（策略列表、报告列表）
3. **StrategyLab**: 策略构建器（核心功能）
   - 期权链可视化
   - 策略构建（多腿）
   - P&L 图表
   - AI 分析
4. **DailyPicks**: 每日 AI 精选策略
5. **ReportsPage**: AI 报告列表
6. **ReportDetailPage**: 报告详情（Markdown 渲染、PDF 导出）
7. **TaskCenter**: 异步任务中心
8. **Pricing**: 订阅定价页面
9. **SettingsPage**: 用户设置
10. **AdminSettings**: 管理员配置（Superuser）
11. **AdminUsers**: 用户管理（Superuser）

### 状态管理

#### React Query (服务器状态)

- **用途**: 管理所有 API 数据
- **特性**:
  - 自动缓存
  - 后台刷新
  - 乐观更新
  - Pro 用户实时轮询（5 秒间隔）

#### Zustand (全局状态)

- **用途**: 用户认证状态、UI 状态
- **存储**:
  - 当前用户信息
  - 认证 Token
  - UI 偏好设置

### API 客户端

**位置**: `frontend/src/services/api/client.ts`

- 基于 Axios
- 自动添加 JWT Token
- 统一错误处理
- 请求/响应拦截器

---

## 后端架构

### 技术栈

- **框架**: FastAPI 0.104.1
- **ASGI 服务器**: Uvicorn 0.24.0
- **语言**: Python 3.10+
- **数据库 ORM**: SQLAlchemy 2.0.23 (Async)
- **数据库迁移**: Alembic 1.12.1
- **缓存**: Redis 5.0.1 (hiredis)
- **调度器**: APScheduler 3.10.4
- **HTTP 客户端**: httpx 0.25.2
- **数据验证**: Pydantic 2.5.0
- **认证**: python-jose 3.3.0
- **金融计算**: 
  - FinanceToolkit >= 2.0.0
  - FinanceDatabase >= 2.0.0
  - pandas >= 2.0.0
  - numpy 1.26.2
  - scipy 1.11.4

### 项目结构

```
backend/
├── app/
│   ├── api/                 # API 层
│   │   ├── endpoints/       # 路由端点
│   │   │   ├── ai.py
│   │   │   ├── auth.py
│   │   │   ├── market.py
│   │   │   ├── payment.py
│   │   │   ├── strategy.py
│   │   │   └── tasks.py
│   │   ├── admin.py         # 管理员 API
│   │   ├── deps.py          # 依赖注入（认证、数据库）
│   │   └── schemas.py       # Pydantic 模型
│   ├── core/                # 核心配置
│   │   ├── config.py        # 环境变量配置
│   │   ├── constants.py     # 常量定义
│   │   └── security.py      # JWT 认证
│   ├── db/                  # 数据库层
│   │   ├── models.py        # SQLAlchemy 模型
│   │   └── session.py       # 数据库会话
│   ├── services/            # 服务层
│   │   ├── agents/          # 多 Agent 框架
│   │   │   ├── base.py
│   │   │   ├── coordinator.py
│   │   │   ├── executor.py
│   │   │   ├── registry.py
│   │   │   ├── options_greeks_analyst.py
│   │   │   ├── iv_environment_analyst.py
│   │   │   ├── market_context_analyst.py
│   │   │   ├── risk_scenario_analyst.py
│   │   │   └── options_synthesis_agent.py
│   │   ├── ai/              # AI 服务
│   │   │   ├── base.py      # BaseAIProvider 抽象类
│   │   │   ├── gemini_provider.py
│   │   │   ├── zenmux_provider.py
│   │   │   └── registry.py
│   │   ├── ai_service.py    # AI 服务适配器
│   │   ├── auth_service.py  # 认证服务
│   │   ├── cache.py         # Redis 缓存服务
│   │   ├── config_service.py # 配置服务
│   │   ├── market_data_service.py # 市场数据服务
│   │   ├── payment_service.py # 支付服务
│   │   ├── scheduler.py     # 任务调度器
│   │   ├── strategy_engine.py # 策略推荐引擎
│   │   └── tiger_service.py # Tiger API 服务
│   └── main.py              # FastAPI 应用入口
├── alembic/                 # 数据库迁移
│   └── versions/
├── requirements.txt
└── Dockerfile
```

### API 路由结构

```
/api/v1/
├── /auth
│   ├── POST /google         # Google OAuth 登录
│   └── GET  /me             # 获取当前用户信息
├── /market
│   ├── GET  /chain          # 期权链
│   ├── GET  /quote           # 股票报价
│   ├── GET  /quotes/batch    # 批量报价
│   ├── GET  /historical/{interval} # 历史数据
│   ├── GET  /technical/{indicator} # 技术指标
│   ├── GET  /market/*        # 市场表现数据
│   ├── GET  /analyst/*       # 分析师数据
│   ├── GET  /financial/*     # TTM 财务数据
│   ├── GET  /search          # 股票搜索
│   ├── POST /recommendations # 策略推荐
│   └── POST /scanner         # 市场扫描器
├── /strategies
│   ├── POST   /              # 创建策略
│   ├── GET    /              # 列表策略
│   ├── GET    /{id}          # 获取策略
│   ├── PUT    /{id}          # 更新策略
│   └── DELETE /{id}          # 删除策略
├── /ai
│   ├── POST /report          # 生成 AI 报告
│   ├── POST /report/multi-agent # 多 Agent 报告
│   ├── GET  /daily-picks     # 每日精选
│   ├── GET  /reports         # 报告列表
│   ├── GET  /reports/{id}    # 报告详情
│   ├── DELETE /reports/{id}  # 删除报告
│   ├── POST /chart           # 生成图表
│   ├── GET  /chart/{id}      # 获取图表
│   ├── POST /workflows/options-analysis # 期权分析工作流
│   └── POST /workflows/stock-screening # 股票筛选工作流
├── /payment
│   ├── POST /checkout        # 创建结账链接
│   ├── POST /webhook         # Lemon Squeezy Webhook
│   ├── GET  /pricing         # 获取价格
│   └── GET  /portal          # 客户门户
├── /tasks
│   ├── POST   /              # 创建任务
│   ├── GET    /              # 任务列表
│   ├── GET    /{id}          # 任务详情
│   └── DELETE /{id}          # 删除任务
└── /admin
    ├── GET    /configs       # 配置列表
    ├── GET    /configs/{key} # 获取配置
    ├── PUT    /configs/{key} # 更新配置
    ├── DELETE /configs/{key} # 删除配置
    ├── GET    /users         # 用户列表
    ├── GET    /users/{id}    # 用户详情
    ├── PUT    /users/{id}    # 更新用户
    ├── DELETE /users/{id}    # 删除用户
    └── POST   /daily-picks/trigger # 触发每日精选
```

### 服务层架构

#### 1. MarketDataService

**职责**: 市场数据聚合服务

**数据源**:
- FMP API (主要) - 股票数据、历史数据、技术指标
- FinanceToolkit - 财务分析、技术指标计算
- FinanceDatabase - 股票发现、筛选
- Tiger API (回退) - 价格推断

**核心方法**:
- `get_stock_quote()` - 股票报价
- `get_batch_quotes()` - 批量报价
- `get_historical_price()` - 多间隔历史数据
- `get_technical_indicator()` - 技术指标
- `get_financial_profile()` - 财务概况
- `get_sector_performance()` - 板块表现
- `get_analyst_estimates()` - 分析师预测
- `get_key_metrics_ttm()` - TTM 关键指标

---

#### 2. TigerService

**职责**: Tiger Brokers API 集成

**特性**:
- Circuit Breaker (5 次失败后熔断 60 秒)
- Retry 逻辑 (指数退避)
- 异步包装 (run_in_threadpool)
- 智能缓存策略

**核心方法**:
- `get_option_chain()` - 期权链（含 Greeks）
- `get_option_expirations()` - 到期日列表
- `get_kline_data()` - K 线数据
- `get_market_scanner()` - 市场扫描器
- `ping()` - 连通性检查

---

#### 3. StrategyEngine

**职责**: 策略推荐引擎（数学逻辑，非 AI）

**算法**:
- Iron Condor (中性策略)
- Long Straddle (波动率策略)
- Bull Call Spread (看涨策略)

**验证规则**:
- 流动性检查 (Spread < 10%)
- Delta 中性检查
- 信用/借记检查
- POP (Probability of Profit) 计算

**Greeks 计算**:
- 优先使用 Tiger API 返回的 Greeks
- 缺失时使用 FinanceToolkit 计算（备用）

---

#### 4. AIService

**职责**: AI 服务适配器

**Provider 支持**:
- GeminiProvider (默认) - Google Gemini 3.0 Pro
- ZenMuxProvider - OpenAI 兼容 API

**功能**:
- 单 Agent 报告生成
- 多 Agent 报告生成（5 个专业 Agent）
- 每日精选生成
- Provider 自动切换和回退

---

#### 5. AgentCoordinator

**职责**: 多 Agent 工作流协调

**工作流**:
1. **Phase 1 (并行)**:
   - OptionsGreeksAnalyst
   - IVEnvironmentAnalyst
   - MarketContextAnalyst
2. **Phase 2 (顺序)**:
   - RiskScenarioAnalyst (依赖 Phase 1)
3. **Phase 3 (顺序)**:
   - OptionsSynthesisAgent (综合所有结果)

**特性**:
- 并行执行优化
- 进度回调支持
- 错误处理和回退

---

#### 6. CacheService

**职责**: Redis 缓存管理

**缓存策略**:
- Pro 用户: 5 秒 TTL（实时数据）
- Free 用户: 15 分钟 TTL（节省配额）
- 期权链: 10 分钟 TTL（所有用户）
- 历史数据: 24 小时 TTL，但**智能过期检测**：自动检查缓存数据的最新日期，如果不是今天（US/Eastern），强制刷新
- 股票报价: 优先直接调用 FMP API `/stable/quote`，确保实时数据；失败时回退到 FinanceToolkit 或历史数据

**键格式**:
- `option_chain:{symbol}:{expiration_date}`
- `stock_quote:{symbol}:{user_type}`
- `historical:{symbol}:{interval}:{limit}`

---

#### 7. PaymentService

**职责**: Lemon Squeezy 支付集成

**功能**:
- 创建结账链接
- Webhook 签名验证 (HMAC SHA256)
- 订阅状态管理
- 客户门户 URL 生成

---

#### 8. ConfigService

**职责**: 动态配置管理

**存储**: PostgreSQL (system_configs 表)
**缓存**: Redis (5 分钟 TTL)

**用途**:
- AI Prompt 模板管理
- 系统参数配置
- 动态功能开关

---

### 任务调度器

**框架**: APScheduler

**定时任务**:
1. **每日配额重置** (00:00 UTC)
   - 重置所有用户的 `daily_ai_usage` 和 `daily_image_usage`
2. **每日精选生成** (08:30 EST)
   - 生成当天的 AI 精选策略
   - 存储到 `daily_picks` 表

---

### 异步任务系统

**实现**: FastAPI `asyncio.create_task()` (非 Celery)

**任务类型**:
- `ai_report` - 单 Agent AI 报告
- `multi_agent_report` - 多 Agent AI 报告
- `options_analysis_workflow` - 期权分析工作流
- `stock_screening_workflow` - 股票筛选工作流
- `generate_strategy_chart` - 策略图表生成
- `daily_picks` - 每日精选生成

**任务状态**:
- `PENDING` - 待处理
- `PROCESSING` - 处理中
- `SUCCESS` - 成功
- `FAILED` - 失败

**进度跟踪**:
- `execution_history` - 执行历史（JSONB）
- 实时进度更新（进度百分比 + 消息）

---

## 数据库架构

### 数据库: PostgreSQL 15

### 表结构

#### 1. users

**用途**: 用户账户信息

**字段**:
- `id` (UUID, PK)
- `email` (String, Unique, Indexed)
- `google_sub` (String, Unique, Indexed)
- `is_pro` (Boolean)
- `is_superuser` (Boolean)
- `subscription_id` (String, Nullable)
- `subscription_type` (String, Nullable) - "monthly" or "yearly"
- `plan_expiry_date` (DateTime, Nullable)
- `daily_ai_usage` (Integer)
- `daily_image_usage` (Integer)
- `last_quota_reset_date` (DateTime, Nullable)
- `created_at` (DateTime)

**关系**:
- `strategies` (One-to-Many)
- `ai_reports` (One-to-Many)
- `tasks` (One-to-Many, Cascade Delete)

---

#### 2. strategies

**用途**: 用户保存的策略

**字段**:
- `id` (UUID, PK)
- `user_id` (UUID, FK → users.id, Indexed)
- `name` (String)
- `legs_json` (JSONB) - 策略腿数据
- `created_at` (DateTime)

**关系**:
- `user` (Many-to-One)

---

#### 3. ai_reports

**用途**: AI 生成的策略分析报告

**字段**:
- `id` (UUID, PK)
- `user_id` (UUID, FK → users.id, Indexed)
- `report_content` (Text) - Markdown 格式
- `model_used` (String) - AI 模型名称
- `created_at` (DateTime)

**关系**:
- `user` (Many-to-One)

---

#### 4. payment_events

**用途**: Lemon Squeezy Webhook 事件审计

**字段**:
- `id` (UUID, PK)
- `lemon_squeezy_id` (String, Unique, Indexed)
- `event_name` (String)
- `payload` (JSONB) - 完整 Webhook 载荷
- `processed` (Boolean) - 是否已处理
- `created_at` (DateTime)

**说明**:
- 所有 Webhook 事件都记录（审计追踪）
- 幂等性检查（通过 `lemon_squeezy_id`）

---

#### 5. daily_picks

**用途**: 每日 AI 精选策略（Cold Start 解决方案）

**字段**:
- `id` (UUID, PK)
- `date` (Date, Unique, Indexed) - EST 日期
- `content_json` (JSONB) - 精选策略列表
- `created_at` (DateTime)

**说明**:
- 每天生成一次（08:30 EST）
- 启动时检查，缺失则后台生成

---

#### 6. system_configs

**用途**: 系统动态配置

**字段**:
- `id` (UUID, PK)
- `key` (String, Unique, Indexed)
- `value` (Text)
- `description` (String, Nullable)
- `updated_by` (UUID, FK → users.id, Nullable)
- `updated_at` (DateTime)
- `created_at` (DateTime)

**用途**:
- AI Prompt 模板
- 系统参数
- 功能开关

---

#### 7. generated_images

**用途**: AI 生成的策略图表图像

**字段**:
- `id` (UUID, PK)
- `user_id` (UUID, FK → users.id, Indexed)
- `task_id` (UUID, FK → tasks.id, Nullable, Indexed)
- `base64_data` (Text, Nullable) - 遗留字段
- `r2_url` (String, Nullable, Indexed) - Cloudflare R2 URL（首选）
- `strategy_hash` (String, Nullable, Indexed) - 策略哈希（用于缓存）
- `created_at` (DateTime, Indexed)

**索引**:
- `ix_generated_images_user_created` (user_id, created_at)
- `ix_generated_images_user_strategy_hash` (user_id, strategy_hash)

---

#### 8. stock_symbols

**用途**: 股票代码仓库（快速搜索）

**字段**:
- `symbol` (String, PK)
- `name` (String)
- `market` (String, Default: "US")
- `is_active` (Boolean, Default: True)
- `created_at` (DateTime)
- `updated_at` (DateTime)

**索引**:
- `ix_stock_symbols_name` (name)
- `ix_stock_symbols_market_active` (market, is_active)

---

#### 9. tasks

**用途**: 后台任务跟踪

**字段**:
- `id` (UUID, PK)
- `user_id` (UUID, FK → users.id, Nullable, Indexed)
- `task_type` (String, Indexed)
- `status` (String, Indexed) - PENDING, PROCESSING, SUCCESS, FAILED
- `result_ref` (String, Nullable) - 结果引用（如报告 ID）
- `error_message` (Text, Nullable)
- `task_metadata` (JSONB, Nullable)
- `execution_history` (JSONB, Nullable) - 执行历史时间线
- `prompt_used` (Text, Nullable) - 完整 Prompt
- `model_used` (String, Nullable) - AI 模型
- `started_at` (DateTime, Nullable)
- `retry_count` (Integer)
- `created_at` (DateTime, Indexed)
- `updated_at` (DateTime)
- `completed_at` (DateTime, Nullable)

**索引**:
- `ix_tasks_user_status` (user_id, status)
- `ix_tasks_created_at` (created_at)

---

### 数据库连接

**连接池配置**:
- `pool_size`: 20
- `max_overflow`: 10
- `pool_timeout`: 30 秒
- `pool_recycle`: 3600 秒

**时区**:
- 所有时间戳使用 UTC
- 应用层负责时区转换（显示时使用 US/Eastern）

---

## 服务层架构

### 依赖关系图

```
┌─────────────────────────────────────────────────────────┐
│                    API Endpoints                        │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│                    Service Layer                        │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Market     │  │    Tiger     │  │     AI       │ │
│  │   Data       │  │   Service    │  │   Service    │ │
│  │   Service    │  │              │  │              │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                  │                  │         │
│         │                  │                  │         │
│  ┌──────▼──────────────────▼──────────────────▼───────┐ │
│  │            StrategyEngine                          │ │
│  │  (Uses MarketDataService for FinanceToolkit)        │ │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
│  ┌────────────────────────────────────────────────────┐ │
│  │         AgentCoordinator                           │ │
│  │  (Uses AIService, MarketDataService)                │ │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │    Cache     │  │   Payment    │  │   Config     │ │
│  │   Service    │  │   Service    │  │   Service    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────┐
│              Database & External Services                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │PostgreSQL│  │  Redis   │  │  Tiger   │  │   FMP    │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │Gemini AI │  │  Lemon   │  │Finance   │              │
│  │          │  │ Squeezy  │  │Toolkit   │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────┘
```

---

## 外部服务集成

### 1. Tiger Brokers API

**用途**: 期权链数据（主要数据源）

**权限要求**:
- `usOptionQuote` - 期权报价
- `usQuoteBasic` - 股票报价（回退）

**特性**:
- Circuit Breaker 保护
- Retry 机制
- 异步包装
- 智能缓存

**限制**:
- 单客户端限制（生产/开发环境需分离）
- 免费配额有限

---

### 2. FMP (Financial Modeling Prep) API

**用途**: 股票市场数据（主要数据源）

**定价计划**: Premium ($29/月)

**功能**:
- 实时报价
- 批量报价
- 多间隔历史数据（1min-1day）
- 技术指标（10+ 种）
- 市场表现数据
- 分析师数据
- TTM 财务数据

**优势**:
- 多客户端支持（共享 API Key）
- 高配额限制
- 完整的数据覆盖

---

### 3. Google Gemini AI

**用途**: AI 分析报告生成

**模型**: Gemini 3.0 Pro (Vertex AI)

**功能**:
- 策略分析报告
- 多 Agent 协作分析
- 每日精选生成

**配额管理**:
- 基于用户订阅类型
- 自动降级机制

---

### 4. FinanceToolkit

**用途**: 专业金融计算库

**功能**:
- 150+ 财务比率
- 30+ 技术指标
- 风险指标（VaR, CVaR, 最大回撤等）
- 性能指标（Sharpe, Sortino, Alpha 等）
- 财务报表分析
- **期权 Greeks 计算**（备用方案）

**数据源**:
- FMP API (主要)
- Yahoo Finance (回退)

---

### 5. FinanceDatabase

**用途**: 股票发现和筛选

**功能**:
- 30 万+ 金融工具数据库
- 按板块、行业、市值筛选
- 公司名称搜索

**优势**:
- 本地数据库，无需 API 调用
- 快速搜索

---

### 6. Lemon Squeezy

**用途**: 订阅支付处理

**功能**:
- 结账链接生成
- Webhook 事件处理
- 订阅状态管理
- 客户门户

**安全**:
- HMAC SHA256 签名验证
- 速率限制（10 请求/分钟/IP）

---

### 7. Cloudflare R2

**用途**: 策略图表图像存储

**特性**:
- S3-compatible API
- 使用 boto3 客户端
- 直接 URL 访问（无需后端代理）

---

## 数据流

### 1. 期权链数据流

```
用户请求
  ↓
GET /api/v1/market/chain
  ↓
TigerService.get_option_chain()
  ↓
检查 Redis 缓存
  ├─ 缓存命中 → 返回缓存数据
  └─ 缓存未命中
      ↓
    调用 Tiger API
      ↓
    解析响应（Greeks, 价格等）
      ↓
    写入 Redis 缓存
      ↓
    返回数据
```

---

### 2. AI 报告生成流程

#### 同步模式

```
用户请求
  ↓
POST /api/v1/ai/report
  ↓
检查配额
  ├─ 配额不足 → 429 错误
  └─ 配额充足
      ↓
    AIService.generate_report()
      ├─ 单 Agent 模式
      │   └─ GeminiProvider.generate_report()
      └─ 多 Agent 模式
          └─ AgentCoordinator.coordinate_options_analysis()
              ├─ Phase 1 (并行): 3 个 Agent
              ├─ Phase 2 (顺序): Risk Analyst
              └─ Phase 3 (顺序): Synthesis Agent
      ↓
    保存报告到数据库
      ↓
    更新用户配额
      ↓
    返回报告
```

#### 异步模式

```
用户请求 (async_mode=true)
  ↓
POST /api/v1/ai/report
  ↓
检查配额
  ↓
创建 Task (status=PENDING)
  ↓
返回 Task ID
  ↓
后台处理 (asyncio.create_task)
  ↓
更新 Task 状态 (PROCESSING)
  ↓
执行 AI 分析（带进度回调）
  ↓
保存报告
  ↓
更新 Task (status=SUCCESS, result_ref=report_id)
```

---

### 3. 策略推荐流程

```
用户请求
  ↓
POST /api/v1/market/recommendations
  ↓
TigerService.get_option_chain() (获取期权链)
  ↓
StrategyEngine.generate_strategies()
  ├─ 根据 outlook 选择算法
  ├─ 查找目标 Delta 的期权
  ├─ 创建 OptionLeg 对象
  ├─ 验证流动性
  ├─ 计算 Net Greeks
  ├─ 验证规则（Delta 中性、信用检查等）
  └─ 返回通过验证的策略
  ↓
返回策略列表
```

---

### 4. 支付 Webhook 流程

```
Lemon Squeezy Webhook
  ↓
POST /api/v1/payment/webhook
  ↓
速率限制检查
  ├─ 超限 → 返回 200（防止重试）
  └─ 通过
      ↓
    HMAC 签名验证
      ├─ 验证失败 → 返回 200（防止重试）
      └─ 验证成功
          ↓
        检查幂等性 (lemon_squeezy_id)
          ├─ 已处理 → 跳过
          └─ 未处理
              ↓
            保存到 payment_events 表
              ↓
            处理业务逻辑
              ├─ subscription_created → 设置 is_pro=true
              ├─ subscription_updated → 更新订阅信息
              ├─ subscription_expired → 设置 is_pro=false
              └─ subscription_cancelled → 设置 is_pro=false
              ↓
            标记为已处理 (processed=true)
              ↓
            返回 200
```

---

## 部署架构

### 开发环境

```
┌─────────────┐
│   Frontend  │  (Vite Dev Server, Port 5173)
│   (React)   │
└──────┬──────┘
       │
       │ HTTP
       │
┌──────▼──────┐
│   Backend   │  (Uvicorn, Port 5300)
│  (FastAPI)  │
└──────┬──────┘
       │
       ├──► PostgreSQL (localhost:5432)
       ├──► Redis (localhost:6379)
       └──► External APIs
```

---

### 生产环境 (Docker Compose)

```
┌─────────────────────────────────────────────┐
│              Nginx (Gateway)                │
│  - Reverse Proxy                            │
│  - SSL Termination                          │
│  - Static File Serving                      │
└──────┬──────────────────────┬───────────────┘
       │                      │
       │                      │
┌──────▼──────┐      ┌────────▼────────┐
│   Frontend  │      │    Backend      │
│  (React)    │      │   (FastAPI)     │
│  Port 80    │      │   Port 8000     │
└─────────────┘      └────────┬────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
        ┌───────▼────┐ ┌─────▼────┐ ┌─────▼────┐
        │ PostgreSQL │ │  Redis   │ │External  │
        │  Port 5432 │ │ Port 6379│ │  APIs     │
        └────────────┘ └───────────┘ └───────────┘
```

---

### 容器化

**Frontend**:
- 基于 Node.js 镜像
- Vite 构建
- Nginx 服务静态文件

**Backend**:
- 基于 Python 3.10 镜像
- Uvicorn ASGI 服务器
- 环境变量配置

**数据库**:
- PostgreSQL 15 官方镜像
- 数据持久化卷

**缓存**:
- Redis 7 官方镜像
- 持久化配置

---

## 依赖关系

### 后端依赖 (requirements.txt)

#### 核心框架
- `fastapi==0.104.1` - Web 框架
- `uvicorn[standard]==0.24.0` - ASGI 服务器
- `python-multipart==0.0.6` - 文件上传支持

#### 数据库
- `sqlalchemy[asyncio]==2.0.23` - ORM
- `alembic==1.12.1` - 数据库迁移
- `asyncpg==0.29.0` - PostgreSQL 异步驱动

#### 缓存
- `redis[hiredis]==5.0.1` - Redis 客户端

#### 弹性模式
- `tenacity==8.2.3` - Retry 逻辑
- `pybreaker==1.0.1` - Circuit Breaker

#### 外部 API
- `tigeropen==3.4.9` - Tiger Brokers SDK
- `google-genai>=0.2.0` - Google AI SDK (新)
- `google-generativeai==0.3.2` - Google AI SDK (遗留)
- `google-cloud-aiplatform>=1.38.0` - Vertex AI SDK
- `httpx==0.25.2` - 异步 HTTP 客户端
- `openai>=1.0.0` - OpenAI 兼容 API (ZenMux)

#### 认证
- `python-jose[cryptography]==3.3.0` - JWT 处理
- `passlib[bcrypt]==1.7.4` - 密码哈希

#### 数据验证
- `pydantic[email]==2.5.0` - 数据验证
- `pydantic-settings==2.1.0` - 配置管理

#### 金融计算
- `financetoolkit>=2.0.0` - 金融分析工具包
- `financedatabase>=2.0.0` - 金融数据库
- `pandas>=2.0.0` - 数据处理
- `numpy==1.26.2` - 数值计算
- `scipy==1.11.4` - 科学计算

#### 工具
- `pytz==2023.3` - 时区处理
- `python-dotenv==1.0.0` - 环境变量
- `apscheduler==3.10.4` - 任务调度
- `boto3==1.34.0` - AWS S3/R2 客户端

---

### 前端依赖 (package.json)

#### 核心框架
- `react@^18.2.0` - UI 框架
- `react-dom@^18.2.0` - DOM 渲染
- `react-router-dom@^6.20.0` - 路由

#### 构建工具
- `vite@^5.0.8` - 构建工具
- `typescript@^5.2.2` - 类型系统
- `@vitejs/plugin-react@^4.2.1` - React 插件

#### UI 库
- `@radix-ui/*` - 无样式 UI 组件
- `tailwindcss@^3.3.6` - CSS 框架
- `tailwindcss-animate@^1.0.7` - 动画
- `lucide-react@^0.294.0` - 图标库

#### 状态管理
- `@tanstack/react-query@^5.12.2` - 服务器状态
- `zustand@^4.4.7` - 全局状态

#### 图表
- `lightweight-charts@^4.1.3` - K 线图
- `recharts@^2.10.3` - 通用图表

#### 工具库
- `axios@^1.6.2` - HTTP 客户端
- `date-fns@^2.30.0` - 日期处理
- `date-fns-tz@^2.0.0` - 时区处理
- `react-markdown@^9.0.1` - Markdown 渲染
- `remark-gfm@^4.0.1` - GitHub Flavored Markdown
- `jspdf@^3.0.4` - PDF 生成
- `html2canvas@^1.4.1` - HTML 转 Canvas
- `@react-oauth/google@^0.11.0` - Google OAuth
- `sonner@^1.3.1` - Toast 通知

---

## 安全架构

### 认证与授权

1. **JWT Token**:
   - 算法: HS256
   - 有效期: 可配置（默认 7 天）
   - 存储: 前端内存（不持久化）

2. **用户角色**:
   - Free User
   - Pro User (Monthly/Yearly)
   - Superuser (管理员)

3. **权限控制**:
   - API 端点级别权限检查
   - 资源级别所有权验证

---

### 数据安全

1. **敏感数据**:
   - API Keys: 环境变量存储
   - 用户密码: 不存储（使用 Google OAuth）
   - 支付信息: 不存储（Lemon Squeezy 处理）

2. **Webhook 安全**:
   - HMAC SHA256 签名验证
   - 速率限制
   - 幂等性检查

3. **CORS**:
   - 生产环境限制允许的来源
   - 开发环境允许 localhost

---

### 错误处理

1. **异常传播**:
   - 不静默吞掉异常
   - 详细日志记录（`exc_info=True`）

2. **Circuit Breaker**:
   - Tiger API: 5 次失败后熔断 60 秒
   - 防止级联故障

3. **Retry 逻辑**:
   - 指数退避策略
   - 最大重试次数限制

---

## 性能优化

### 缓存策略

1. **Redis 缓存**:
   - 市场数据: 根据用户类型差异化 TTL
   - 配置数据: 5 分钟 TTL
   - 期权链: 10 分钟 TTL

2. **前端缓存**:
   - React Query 自动缓存
   - Pro 用户实时轮询（5 秒）

---

### 数据库优化

1. **索引**:
   - 所有外键字段索引
   - 常用查询字段索引
   - 复合索引（user_id + status）

2. **连接池**:
   - 连接池大小: 20
   - 最大溢出: 10

3. **查询优化**:
   - 使用 `selectinload` 预加载关系
   - 分页查询限制

---

### 异步处理

1. **异步任务**:
   - 长时间运行的 AI 分析使用异步任务
   - 避免 HTTP 请求超时

2. **并行执行**:
   - 多 Agent 工作流的 Phase 1 并行执行
   - 减少总执行时间

---

## 监控与日志

### 日志级别

- **INFO**: 正常业务流程
- **WARNING**: 非关键错误（如 API 回退）
- **ERROR**: 严重错误（带堆栈跟踪）
- **DEBUG**: 调试信息（开发环境）

### 关键日志点

1. **API 调用**:
   - 请求参数
   - 响应状态
   - 执行时间

2. **外部服务**:
   - Tiger API 调用
   - FMP API 调用
   - Gemini API 调用

3. **业务事件**:
   - 用户注册/登录
   - 订阅状态变更
   - 配额使用

---

## 扩展性设计

### 水平扩展

1. **无状态后端**:
   - FastAPI 应用无状态
   - 可部署多个实例

2. **共享状态**:
   - Redis 缓存（分布式）
   - PostgreSQL 数据库（共享）

3. **负载均衡**:
   - Nginx 反向代理
   - 多实例负载均衡

---

### 垂直扩展

1. **数据库**:
   - 连接池调优
   - 查询优化
   - 读写分离（未来）

2. **缓存**:
   - Redis 集群（未来）
   - 缓存预热

---

## 未来架构规划

### 短期 (3-6 个月)

1. **消息队列**:
   - 引入 Celery + RabbitMQ/Redis
   - 更可靠的任务处理

2. **CDN**:
   - 静态资源 CDN 加速
   - 图像资源 CDN

3. **监控系统**:
   - Prometheus + Grafana
   - 应用性能监控 (APM)

---

### 中期 (6-12 个月)

1. **微服务化**:
   - 市场数据服务独立
   - AI 服务独立
   - 支付服务独立

2. **事件驱动**:
   - 事件总线
   - 异步事件处理

3. **数据仓库**:
   - 历史数据分析
   - 用户行为分析

---

### 长期 (12+ 个月)

1. **机器学习**:
   - 策略推荐模型训练
   - 用户行为预测

2. **实时流处理**:
   - 实时市场数据流
   - WebSocket 支持

3. **多区域部署**:
   - 全球 CDN
   - 区域数据库副本

---

## 总结

ThetaMind 采用现代化的前后端分离架构，具有以下特点：

1. **模块化设计**: 清晰的服务层分离
2. **弹性架构**: Circuit Breaker + Retry + 缓存
3. **异步处理**: 支持长时间运行的任务
4. **可扩展性**: 无状态设计，易于水平扩展
5. **安全性**: JWT 认证 + Webhook 签名验证
6. **专业性**: 使用专业金融工具库（FinanceToolkit）

系统设计遵循最佳实践，为未来的功能扩展和性能优化奠定了坚实基础。

---

**文档维护**: 本文档应随系统架构变更及时更新。  
**最后更新**: 2026-02-06

---

## 最新更新（2026-02-06）

### 数据实时性优化

1. **股票报价实时化**
   - 直接调用 FMP API `/stable/quote` 端点，确保获取当天实时价格
   - 完整的 fallback 机制：FMP → FinanceToolkit → Historical Data
   - 解决了用户反馈的"数据延迟一天"问题

2. **历史数据智能缓存**
   - 缓存数据自动检查最新日期（US/Eastern 时区）
   - 如果缓存数据不是今天，自动强制刷新
   - 前端缓存时间从 24 小时优化到 5 分钟，窗口焦点时自动刷新

### 用户体验优化

1. **防止重复运行机制**
   - 前端实时检查运行中的任务（每 5 秒轮询）
   - 有任务运行时，按钮自动禁用并显示"Analyzing..."
   - 防止免费用户无限运行报告

2. **DOM 操作安全性**
   - 所有 `removeChild` 操作添加父节点检查
   - 防止组件卸载时的 DOM 错误
   - 提升页面稳定性

### AI 服务优化

1. **图像生成 429 重试**
   - 自动重试机制（最多 5 次，指数退避）
   - 改进的错误提示，包含官方文档链接
   - 提升用户体验和成功率
