# ThetaMind 技术白皮书

**文档版本**: 2.0  
**适用版本**: ThetaMind v2.0.0（生产版）  
**用途**: 技术架构说明、技术融资、技术尽调材料  
**最后更新**: 2026-02-06  
**状态**: 已上线生产环境

---

## 摘要

本白皮书描述 ThetaMind 的**整体技术架构、核心数据流、突破性技术难点与核心技术价值**。ThetaMind 将**真实期权链（Tiger）与基本面（FMP）**、**五专家多智能体编排**与**带实时检索的 Deep Research** 整合为一条可审计的流水线，在**不执行交易**的前提下，为美股期权策略提供「研究台级别」的一键分析能力。技术亮点包括：多智能体依赖编排与上下文传递、大模型上下文过滤与成本控制、外部 API 熔断与缓存降级、支付与 AI 配额的审计与幂等设计、以及可替换的 AI Provider 架构。

---

## 一、整体技术架构

### 1.1 系统边界与部署形态

- **前端**：React 18 + Vite + TypeScript，Shadcn/UI + Tailwind；构建为静态资源，由 Nginx 或对象存储托管。  
- **网关**：Nginx，反向代理 `/api` 至后端，`/` 至前端静态。  
- **后端**：FastAPI（异步），单应用内聚 Auth、Market、Strategy、AI、Payment、Tasks、Admin 等模块。  
- **数据层**：PostgreSQL（主数据）、Redis（缓存与限流）。  
- **外部依赖**：Tiger Brokers OpenAPI、FMP（含 FinanceToolkit）、Google Gemini API、Google OAuth2、Lemon Squeezy、Cloudflare R2。  
- **部署**：Docker Compose 一键拉起 db、redis、backend、frontend、nginx；生产可拆分为 GCP/Cloud Run + Cloud SQL + Memorystore 等。

### 1.2 高层架构图

<img width="1024" height="1024" alt="image" src="https://github.com/user-attachments/assets/a1746d0b-c883-4f34-802f-10d83dfa907e" />



```
                    ┌─────────────────────────────────────────────────────────┐
                    │                     User (Browser)                        │
                    └────────────────────────────┬──────────────────────────────┘
                                                 │ HTTPS
                    ┌────────────────────────────▼──────────────────────────────┐
                    │                     Nginx Gateway                           │
                    │              /api → Backend   / → Frontend Static            │
                    └────────────────────────────┬──────────────────────────────┘
                                                 │
    ┌────────────────────────────────────────────▼────────────────────────────────────────────┐
    │                              FastAPI Backend (Async)                                       │
    │  ┌──────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐   │
    │  │  Auth    │ │ Market Data  │ │  Strategy    │ │  AI Service   │ │  Payment         │   │
    │  │ (Google  │ │ (Tiger+FMP   │ │  Engine      │ │ (Gemini +    │ │ (Lemon Squeezy   │   │
    │  │  OAuth2) │ │ +Redis+CB)   │ │  + CRUD      │ │  Multi-Agent │ │  Webhook+Audit)  │   │
    │  └────┬─────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └────────┬─────────┘   │
    │       │              │                │                │                  │             │
    │       │              │                │                │                  │             │
    │  ┌────▼──────────────▼────────────────▼────────────────▼──────────────────▼─────────┐   │
    │  │                         Tasks Pipeline (Async Worker)                            │   │
    │  │   Data Enrichment → Phase A (5 Agents) → Phase A+ (Rec) → Phase B (Deep Research) │   │
    │  └──────────────────────────────────────────────────────────────────────────────────┘   │
    │  ┌──────────────┐  ┌──────────────┐                                                     │
    │  │  Scheduler   │  │  Config      │  (APScheduler: Daily Picks 08:30 EST, Quota 00:00 UTC) │
    │  └──────────────┘  └──────────────┘                                                     │
    └────────────┬─────────────────────┬─────────────────────┬─────────────────────┬────────────┘
                 │                     │                     │                     │
    ┌────────────▼────────┐  ┌─────────▼────────┐  ┌────────▼────────┐  ┌────────▼────────────┐
    │   PostgreSQL        │  │   Redis           │  │  Tiger / FMP     │  │  Gemini / Lemon / R2 │
    │   (users, strategies│  │   (cache,        │  │  (market data)   │  │  (AI, payment,       │
    │   tasks, reports,   │  │   rate limit)     │  │                  │  │   image storage)    │
    │   payment_events)   │  │                  │  │                  │  │                     │
    └─────────────────────┘  └───────────────────┘  └──────────────────┘  └─────────────────────┘
```

### 1.3 技术栈一览

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 前端 | React 18, Vite, TypeScript | SPA，严格类型 |
| 前端 UI | Shadcn/UI, Tailwind CSS | 一致性与可维护性 |
| 前端状态 | TanStack Query, Zustand | 服务端状态 + 全局客户端状态 |
| 前端图表 | lightweight-charts, recharts | K 线、Payoff、面积图 |
| 后端 | FastAPI (async) | 异步 I/O，OpenAPI 文档 |
| ORM / 迁移 | SQLAlchemy (async), Alembic | 异步连接池，版本化 Schema |
| 缓存 | Redis (redis-py async) | 期权链、报价、配置、限流 |
| 弹性 | pybreaker (Circuit Breaker), tenacity (Retry) | Tiger/Gemini 熔断与重试 |
| 调度 | APScheduler | 每日精选、配额重置 |
| AI | Google Gemini 3.0 Pro, BaseAIProvider 抽象 | 可切换 DeepSeek/Qwen |
| 支付 | Lemon Squeezy | Checkout + Webhook，先落库再处理 |
| 存储 | Cloudflare R2 | AI 生成图片 |
| 时区 | 后端 UTC，前端 US/Eastern | 金融时间一致性 |

---

## 二、核心数据流与关键设计

### 2.1 市场数据流（期权链与报价）

- **入口**：`GET /market/chain?symbol=&expiration_date=&force_refresh=`，带 JWT，区分 Pro/Free。
- **逻辑**：  
  1. **Pro + force_refresh**：可跳过缓存，直接请求 Tiger。  
  2. **否则**：先查 Redis 键（如 `market:chain:{symbol}:{date}`），命中则返回；未命中则调 Tiger，写入 Redis（当前 TTL 10 分钟），再返回。  
  3. **Tiger 调用**：通过 `TigerService`，所有对外 Tiger 调用经 `@tiger_circuit_breaker` + tenacity 重试；熔断打开时立即返回 503 与 Retry-After，避免雪崩。  
  4. **股票报价**：**直接调用 FMP API `/stable/quote` 端点**，确保实时数据；失败时回退 FinanceToolkit 或 Tiger 价格推断。  
  5. **历史 K 线**：优先 Tiger get_bars，失败则 FMP 历史数据；**智能缓存过期检测**：检查缓存数据的最新日期，如果不是今天（US/Eastern），强制刷新，确保用户看到最新交易日数据。

**设计要点**：缓存降低 Tiger 调用量、熔断保护后端、多源回退保证「有数据可展示」而非整站不可用。

### 2.2 AI 报告流水线（Deep Research 全流程）

- **入口**：用户在 Strategy Lab 点击 Deep Research → 前端调 `POST /api/v1/ai/report`（或先创建任务再轮询任务状态）；请求体含 `strategy_summary`、`option_chain`，`use_multi_agent=true`，配额按 5 单位检查与扣减。
- **服务端**：  
  1. **配额校验**：按用户 plan 取每日上限（Free 5 / 月付 40 / 年付 100），`daily_ai_usage + 5` 不超限则扣减并创建任务。  
  2. **任务执行（异步）**：  
     - **Data Enrichment**：拉取 FMP 基本面、财报日历、分析师数据等，写入 `strategy_summary` 或上下文，供后续 Agent 与 Deep Research 使用。  
     - **Phase A**：Coordinator 调度五专家 Agent（Greeks、IV、Market 并行 → Risk 顺序 → Synthesis 顺序），各 Agent 通过 `AgentContext.input_data` 读取上游结果，输出写入 `_result_*` / `_all_results`。  
     - **Phase A+**：可选，基于期权链与 Agent 结论生成 1～2 条推荐策略（名称、腿、行权价、逻辑）。  
     - **Phase B**：Gemini Provider 的 `generate_deep_research_report`：规划 4 个研究问题 → 调用 Gemini（开启 `google_search_retrieval`）多轮检索与合成 → 产出长文；进度通过 callback 回写任务 `execution_history` 与子阶段状态。  
  3. **持久化**：最终报告写入 `ai_reports`，任务状态更新为 SUCCESS，`task_metadata` / `execution_history` / `prompt_used` 保存完整审计信息。
- **降级**：若 Deep Research 超时或失败，可降级为单 Agent 简单报告，仍计 5 单位，保证用户至少得到一份分析。

**设计要点**：一条流水线从「策略输入」到「可审计报告」；Phase 间通过结构化上下文传递，避免重复拉数；Deep Research 使用实时检索，增强时效性与可信度。

### 2.3 多智能体编排与上下文传递

- **角色**：  
  - **Executor**：单 Agent 执行、并行执行、顺序执行；统一进度回调与异常包装。  
  - **Coordinator**：定义 Phase 1（并行）→ Phase 2（Risk，依赖 Phase 1）→ Phase 3（Synthesis，依赖全部）；将各 Agent 输出写入 `AgentContext.input_data`（如 `_result_options_greeks_analyst`），供下游只读。  
- **数据契约**：每个 Agent 实现 `BaseAgent`，输入来自 `context.input_data`（含 `strategy_summary`、`option_chain`、上游 `_result_*`），输出为 `AgentResult.data`（结构化文本/字典），由 Coordinator 写入 context，供下一阶段使用。  
- **难点与突破**：依赖关系明确、并行与顺序混合、单点失败不拖垮整链（可记录失败 Agent 并继续或降级），实现了**可扩展的多步推理流水线**而非单一大 Prompt。

### 2.4 上下文过滤与 Token 控制

- **问题**：完整期权链行数多，直接喂给大模型会导致 Token 爆炸、延迟高、噪音大。  
- **做法**：  
  - **报告与单 Agent**：`GeminiProvider.filter_option_chain(chain, spot)`，仅保留行权价在 **spot ±15%** 内的合约；再组 Prompt。  
  - **推荐策略生成**：使用 `_filter_option_chain_for_recommendation(chain, spot, 0.25)`，保留 ±25% 以兼顾更多行权档位。  
- **效果**：在保证 ATM 附近分析质量的前提下，显著降低 Token 消耗与延迟，并减少无关合约带来的幻觉。

### 2.5 支付与 Webhook 审计

- **流程**：Lemon Squeezy 发送 Webhook → 后端验证签名 → **先插入 `payment_events`（lemon_squeezy_id, event_name, payload, processed=false）** → 若已存在则幂等返回 → 再在事务内更新 `users`（is_pro、plan_expiry_date、subscription_type 等）并标记 `processed=true`。  
- **价值**：每一笔支付/订阅变更都有持久化事件，可对账、排查与审计；重复推送不会重复生效。

### 2.6 配额与重置

- **存储**：`users.daily_ai_usage`、`users.daily_image_usage`、`users.last_quota_reset_date`（UTC 日期）。  
- **规则**：每次使用前检查 `last_quota_reset_date` 是否为「今天 UTC」；若不是则先重置再扣减。另由 Scheduler 在每日 00:00 UTC 执行全局重置，双保险。  
- **单位**：1 次 Deep Research = 5 单位；简单报告也按 5 单位计（与前端「一次报告」心智一致）。

---

## 三、突破的技术难点

### 3.1 多智能体依赖编排与可观测性

- **难点**：五专家 Agent 之间存在依赖（如 Risk 依赖 Greeks/IV/Market；Synthesis 依赖全部），需要并行与顺序混合执行，且结果要在内存与任务持久化中一致传递。  
- **突破**：  
  - 引入 **Coordinator + Executor** 分层：Coordinator 只定义 DAG 与数据键约定，Executor 负责调用 BaseAgent、写入 context。  
  - 各阶段结果写入 `execution_history` 与 `task_metadata`，前端可展示「Phase A 各 Agent → Phase B 各子阶段」，实现**全链路可观测与可重放**。

### 3.2 外部数据源高可用（熔断 + 缓存 + 多源回退）

- **难点**：Tiger、FMP、Gemini 任一不可用或抖动时，若直接透传失败，会导致整站或核心功能不可用。  
- **突破**：  
  - **Tiger**：所有调用经 `pybreaker`（如 5 次失败即熔断 60s），熔断期内直接 503，避免长时间阻塞；Tenacity 对连接/超时类异常重试。  
  - **Redis 缓存**：期权链、报价等按 key TTL 缓存，熔断或超时时可返回过期缓存并在响应中标注，前端可提示「数据可能非实时」。  
  - **报价/K 线**：FMP 为主、Tiger 为回退（或反之），保证「至少一个源可用」时用户仍能获得数据。

### 3.3 大模型长上下文与成本控制

- **难点**：期权链 + 多 Agent 中间结果 + Deep Research 多轮检索，若全量送入模型，Token 与延迟不可控。  
- **突破**：  
  - **链上过滤**：±15% spot 过滤期权链；推荐阶段 ±25%。  
  - **Agent 输出摘要**：Deep Research 的输入使用各 Agent 的**摘要**（如每 Agent 最多 1800 字符），而非原始长文，在保留信息量的前提下控制 Token。  
  - **超时与降级**：Deep Research 设总超时（如 30 分钟）；超时或异常时降级为单 Agent 报告，仍计 5 单位，保证产品可用性。

### 3.4 实时检索与长文合成（Deep Research）

- **难点**：将「多 Agent 结论」与「实时网络信息」结合成一份连贯、可引用的长报告，需规划问题、多轮检索、去重与合成。  
- **突破**：  
  - 使用 Gemini 的 **Google Search grounding**（`google_search_retrieval`），在单次或多次调用中完成规划 → 检索 → 合成。  
  - Phase B 子阶段（Planning / Research / Synthesis）与进度回调写入任务，便于前端展示「Deep Research 进行中」与事后审计。

### 3.5 支付与订阅的审计与幂等

- **难点**：Webhook 可能重复、乱序；若直接改用户状态，难以对账与排查。  
- **突破**：**先写 payment_events，再改 users**；对 `lemon_squeezy_id`（或事件 id）做唯一约束或查重，重复事件不二次处理，实现幂等与完整审计轨迹。

---

## 四、核心技术价值总结

1. **研究台级分析流水线**：从「策略 + 真实链 + 基本面」到「五专家 + Deep Research」的一体化、可审计流水线，输出一份长报告与可选推荐策略，**一键替代多工具拼接与手工整理**。  
2. **真实数据融合**：Tiger 期权链与 FMP 基本面在同一上下文中被多智能体与 Deep Research 使用，分析结论与券商可见数据一致，**无模拟数据、无黑箱数据源**。  
3. **可追溯与合规友好**：每份报告对应任务、每任务含阶段输出与 Prompt；**无黑箱**，适合风控、合规与机构合作。  
4. **高可用与弹性**：熔断、缓存、多源回退与配额降级，保证在外部 API 故障时**系统仍可读、可降级服务**，而非全站挂掉。  
5. **可扩展的 AI 与数据层**：BaseAIProvider 可挂接 Gemini/DeepSeek/Qwen；数据层可增加更多数据源与缓存策略，为后续「更多市场、更多资产类别」预留扩展点。  
6. **清晰的业务边界**：**分析仅用于研究与教育，不执行交易、不托管资金**，技术实现与产品定位一致，便于合规与对外表述。

---

## 五、安全与合规要点

- **认证**：Google OAuth2 + JWT；不存储密码，不记录 API Key 与用户 PII 到日志。  
- **支付**：Lemon Squeezy Webhook 签名校验；敏感字段不落日志。  
- **时区与数据**：后端全量 UTC；前端展示 US/Eastern；期权到期等与交易所时间一致。  
- **免责**：全站显著位置声明「分析研究工具、非交易平台、非投资建议」。

---

## 六、附录：关键文件与模块索引

| 模块 | 路径/文件 | 说明 |
|------|-----------|------|
| 市场数据 | `backend/app/api/endpoints/market.py` | 期权链、报价、历史、扫描、推荐 |
| 市场服务 | `backend/app/services/tiger_service.py` | Tiger 调用、熔断、重试、缓存 |
| 市场服务 | `backend/app/services/market_data_service.py` | FMP/FinanceToolkit、基本面、历史等 |
| AI 报告 | `backend/app/api/endpoints/ai.py` | 报告创建、配额、任务创建 |
| 任务执行 | `backend/app/api/endpoints/tasks.py` | 任务轮询、执行入口、Data Enrichment、Phase A/B 编排 |
| AI 服务 | `backend/app/services/ai_service.py` | generate_report、generate_deep_research_report、Agent 初始化 |
| Gemini | `backend/app/services/ai/gemini_provider.py` | filter_option_chain、Deep Research、grounding |
| 多智能体 | `backend/app/services/agents/coordinator.py` | Phase A 编排（并行/顺序） |
| 多智能体 | `backend/app/services/agents/executor.py` | 单/并行/顺序执行 |
| 支付 | `backend/app/api/endpoints/payment.py` | Webhook、Checkout、Portal |
| 配额 | `backend/app/api/endpoints/ai.py`（常量） | FREE_AI_QUOTA、PRO_*_AI_QUOTA |
| 缓存 | `backend/app/services/cache.py` | Redis 封装、降级 |
| 常量 | `backend/app/core/constants.py` | CacheTTL、RetryConfig、TimeoutConfig |

---

---

## 最新技术更新（2026-02-06）

### 数据实时性技术突破

1. **FMP Quote API 直接调用**
   - 绕过 FinanceToolkit 的历史数据回退
   - 直接调用 FMP `/stable/quote` 端点
   - 确保获取当天实时价格，解决"数据延迟一天"问题

2. **智能缓存过期检测**
   - 后端：检查缓存数据的最新日期（US/Eastern 时区）
   - 如果数据不是今天，自动强制刷新
   - 前端：缓存时间从 24 小时优化到 5 分钟，窗口焦点时自动刷新

### 用户体验技术优化

1. **运行任务实时检测**
   - 前端每 5 秒轮询运行中的任务
   - 查询失败时安全 fallback，不阻塞用户
   - 防止重复提交，提升系统稳定性

2. **DOM 操作安全性**
   - 所有 `removeChild` 操作添加 `parentNode === document.body` 检查
   - 防止组件卸载时的 DOM 错误
   - 提升页面稳定性

### AI 服务技术增强

1. **429 错误自动重试**
   - 图像生成 API 添加 429 重试机制（最多 5 次）
   - 指数退避策略（15s, 30s, 60s...）
   - 改进的错误提示，包含官方文档链接

---

**文档结束**。本文档与《产品功能说明书》一起，构成 ThetaMind 技术融资与尽调所需的产品能力与技术架构说明。
