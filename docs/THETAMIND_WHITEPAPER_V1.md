# ThetaMind 技术架构与产品白皮书 (Whitepaper V1.0)

**文档状态**: 最新基准 (Baseline)
**更新日期**: 2026年2月21日
**产品定位**: 专业的的美股期权策略分析与风控平台 (US Stock Option Analysis Platform)

---

## 1. 核心理念与产品定位

ThetaMind 旨在为美股期权交易者提供机构级别的深度研报与风控分析服务。
我们坚守以下核心原则：
- **纯分析，不交易** (Analysis Only): 系统专注于风险揭示、希腊字母 (Greeks) 解析、隐含波动率 (IV) 评估以及盈亏推演，绝不触碰用户的资金或执行实际交易。
- **高可用与防灾** (Resilience): 面向生产环境的真实付费用户，系统各层级（特别是外部 API 如大模型、数据源）均配备断路器 (Circuit Breaker)、指数退避重试 (Exponential Backoff) 和安全降级机制。
- **精准与标准化** (Precision): 严格的 UTC 时区处理（后端）与美东时间展示（前端）；风控评分模型采用相对标准化指标（如每百美元 Delta/Vega 风险），拒绝粗暴的绝对值硬编码。

---

## 2. 产品功能矩阵 (Product Features)

ThetaMind 当前提供以下核心功能模块：

### 2.1 期权策略分析 (Options Strategy Analysis)
- 支持用户输入多腿 (Multi-leg) 期权策略组合。
- 实时计算组合的净 Greeks（Delta, Gamma, Theta, Vega）和关键财务指标（最大盈利、最大亏损、胜率 POP、盈亏平衡点）。
- 生成基础的单模型 AI 投资备忘录 (Investment Memo)。

### 2.2 多智能体深度研究 (Multi-Agent Deep Research) - **核心亮点**
这是 ThetaMind 的王牌功能，通过多阶段、多角色 AI 协作，产出上万字的深度投资研报：
1. **数据富化 (Data Enrichment)**: 自动拉取 Tiger Brokers 的期权链与 FMP Premium 的深度基本面数据（财务比率、分析师目标价、近期催化剂、市场情绪）。
2. **Phase A (内部专家评审)**: 
   - **Greeks 分析师**: 评估方向性风险与时间损耗效率。
   - **IV 环境分析师**: 评估当前波动率水位与历史排位 (IV Rank)。
   - **市场上下文分析师**: 结合基本面与趋势进行宏观研判。
   - **风险情景分析师**: 进行压力测试（Tail Risk）和极端行情推演。
   - **合成分析师 (Synthesis)**: 将上述 4 位专家的意见融合为内部初步简报。
3. **Phase A+ (策略推荐)**: 基于内部评审和最新的期权链，系统主动推荐 1-2 个胜率更高、风险更优的替代期权策略。
4. **Phase B (外部深度研究)**:
   - **动态规划 (Planning)**: AI 根据策略复杂度动态生成 1~5 个关键研究问题。
   - **并行搜索 (Research)**: 调度带有 Google Search 能力的 AI 并行解答这些问题。
   - **终局合成 (Final Synthesis)**: 将所有内外部数据、专家观点和推荐策略，融合成最终的三段式高管级投资备忘录 (Executive Memo)。

### 2.3 股票筛选与异动监控 (Screening & Anomaly)
- **智能选股 (Stock Screening & Ranking)**: 利用 AI 智能体根据用户自然语言策略筛选潜在标的。
- **每日精选 (Daily Picks)**: 解决“冷启动”问题，每日自动生成并推送精选期权策略卡片。
- **异动监测 (Anomaly Detection)**: 监控市场中的期权成交量激增 (Volume Surge) 或 IV 暴涨，提供 AI 洞察。

### 2.4 商业化与账户管理
- **Lemon Squeezy 支付集成**: 完善的 Webhook 审计追踪 (`payment_events` 表)，处理订阅状态。
- **AI 额度控制 (Quota System)**: 基础查询消耗 1 个 Credit，深度多智能体研究消耗 5 个 Credits，严格把控 API 成本。

---

## 3. 技术架构 (Technical Architecture)

ThetaMind 采用现代化的前后端分离单体仓库 (Monorepo) 架构。

### 3.1 基础设施与全栈选型
- **后端 (Backend)**: Python 3.9+, FastAPI (纯异步 AsyncIO)。
- **数据库 (Database)**: PostgreSQL, 使用 SQLAlchemy (Async) 作为 ORM，Alembic 进行数据迁移。JSONB 字段用于存储无模式的复杂元数据（如期权链、分析过程）。
- **前端 (Frontend)**: React 18, Vite, 严格的 TypeScript。
- **UI & 状态管理**: Shadcn/UI + Tailwind CSS 进行组件化渲染；Zustand 进行全局状态管理；TanStack Query (React Query) 管理服务端状态。
- **图表渲染**: Lightweight-charts (K线图) + Recharts (区域/折线图)。
- **网关**: Nginx 作为反向代理，处理路由与 SSL。

### 3.2 核心后端服务层 (Service Layer)
- **AI Service (`ai_service.py`)**: 
  - 核心大模型适配器，目前主备 Google Gemini (支持 `Generative Language API` 与企业级 `Vertex AI` 双通道)。
  - 内置基于 `tenacity` 的指数退避重试和 `pybreaker` 的熔断机制。
  - **Token 截断与防 429 防御**: 拥有专门的字典裁剪算法 (`_trim_fundamental_profile_for_planning`)，在序列化为 JSON 之前安全裁剪庞大的财务报表，确保 LLM 永远接收合法的 JSON 结构，杜绝幻觉。
  - 支持最新的思考模型 (Thinking Models) 和原生系统提示词 (System Instructions)。
- **Agent Framework (`agents/`)**: 
  - 规范的抽象基类 `BaseAgent`、并行/串行执行器 `AgentExecutor` 和流程协调器 `AgentCoordinator`。
  - Agent 与 AI Provider 的通信通过强类型的 `generate_text_response` 接口隔离，杜绝底层实现的抽象漏水 (Leaky Abstraction)。
- **Deep Research Orchestrator (`deep_research_orchestrator.py`)**:
  - 负责统筹耗时 15~30 分钟的超长异步任务。
  - 采用了业界标准的**原子化状态更新 (Atomic Mutator)** 设计。利用短生命周期的独立 `AsyncSessionLocal` 配合 `flag_modified`，彻底解决了 SQLAlchemy 并发更新 JSONB 字段时的脏读写 (Dirty Write / Lost Update) 竞态条件问题。
- **外部数据适配器**: 
  - `tiger_service.py`: 封装 Tiger Brokers OpenAPI，获取实时 Option Chain。
  - `fundamental_data_service.py` / `market_data_service.py`: 封装 FMP Premium 接口，提供稳健的回调与数据缓存。

---

## 4. 数据流与并发模型 (Data Flow & Concurrency)

### 4.1 异步任务流 (Background Tasks)
由于深度研究耗时极长，系统采用了 FastAPI 的 `BackgroundTasks` 机制投递任务。
1. API 层创建 `Task` 实体，状态置为 `PENDING`，向前端立即返回 `task_id`。
2. 后台触发 `process_task_async`，进入 `DeepResearchOrchestrator`。
3. Orchestrator 在执行每一个 Phase 时，通过回调函数非阻塞地创建新的数据库短连接，将进度百分比 (`progress`) 和执行日志 (`execution_history`) 原子的更新到 DB。
4. 前端通过定时轮询 (Polling) 接口获取实时进度条，并在任务变为 `SUCCESS` 后获取 `result_ref` 指向的 `AIReport` 实体。

### 4.2 风控算法标准化
在多智能体评审阶段，系统的风控算法（如 `_calculate_risk_score`）采用了**相对标准化模型**：
- **Delta/Vega 风险**: 使用 `每 100 美元正股的 Delta/Vega 暴露` 进行衡量，而非绝对数值。
- **Theta 风险**: 衡量 `每日 Theta 损耗占最大盈利 (Max Profit) 的比例`。
这种设计确保了策略模型对低价股（如 $10）和高价股（如 $500）均具备极高的评判准确度。

---

## 5. 安全、合规与生产约束 (Production Constraints)

1. **向后兼容性 (Backward Compatibility)**: 核心 API (如任务查询、报告结构) 的响应格式和状态机机理被严格锁定。任何新字段的增加必须提供默认值，绝不允许改变或删除已有契约。
2. **密钥与隐私**: 任何 API Key (Google, Tiger, FMP, Lemon Squeezy) 均通过 `.env` 注入，绝不在日志中打印；用户 PII 数据严格保密。
3. **安全回退 (Safe Fallbacks)**: 当外部数据源（如缺失 Greeks 数据）或 AI 节点发生异常时，系统会自适应降低置信度并在报告顶部注入免责声明 (Confidence Adjustment)，而不是导致整个工作流崩溃。

---

> **结语**: ThetaMind 现已构筑了极其坚固的后端护城河与智能的 AI 流水线。本文档作为 V1.0 架构基准，后续任何引入新智能体、新数据源或迁移新大模型的迭代，均需严格遵守本文档中确立的原子并发规范与 API 兼容准则。