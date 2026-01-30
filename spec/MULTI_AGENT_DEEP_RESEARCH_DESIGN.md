# ThetaMind：多智能体 + Deep Research 一体化设计

**版本**: 1.0  
**状态**: 设计稿（后续实现均以此为准）  
**前提**: 数据采用 Tiger + FMP Premium，不担心数据缺失，重点保证数据取足、质量最优。

---

## 〇、价值定位：推荐组合 vs 评点用户策略

### 当前实现（已确认）

- **AI 报告与用户期权组合的关系**：**强绑定**。报告任务由用户在 Strategy Lab 中点击「生成 AI 分析」触发，入参为**用户当前构建的那一个期权组合**（`strategy_summary` + `option_chain`）。
- **多智能体 + Deep Research 在做什么**：对**这一份用户策略**做评判——Greeks 解读、IV 环境、市场背景、情景分析、综合建议（hold/trim/avoid 等）。**没有**基于当前数据「产出一个或几个新的低成本、高胜率组合」。
- **结论**：当前流水线 = **只做「评点与纠偏用户策略」**，不做「为用户推荐/生成新组合」。

### 产品真正价值（目标）

1. **主价值**：基于当前数据（Tiger + FMP Premium）**产出一个或几个低成本、高胜率的期权组合**，供用户参考或一键加载到 Strategy Lab。
2. **次价值**：对用户**当前已选/已构建的策略**做评点和纠偏（当前报告已在做）。

### 现有能力与缺口

| 能力 | 现状 | 说明 |
|------|------|------|
| 评点用户策略 | ✅ 已有 | 多智能体 + Deep Research 报告，输入 = 用户当前组合，输出 = 投资备忘录 + 建议。 |
| 推荐/生成组合 | ⚠️ 部分有、未成主路径 | **Daily Picks**：从池子筛标的 → 构建策略（如 Iron Condor）→ AI 分析，产出的是「系统推荐的若干策略」，但与用户当前标的/偏好无绑定；**Market recommendations API**：算法推荐（Greeks 等），非多智能体/Deep Research，且未与报告流水线打通。 |

**缺口**：缺少一条「以推荐组合为主、评点为辅」的统一体验——例如在 Strategy Lab 或报告内，既能看到「系统基于当前数据推荐的 1～3 个组合」，又能看到「对你当前这份策略的评点与纠偏」。后续迭代可在本设计基础上，增加「推荐组合生成」流水线（可复用 Daily Picks 的构建逻辑 + 多智能体/Deep Research 的评析能力），并与任务系统、报告展示打通。

### 本设计采纳的演进方向（聚焦 AI 报告）

- **输入**：保持「用户选择的期权组合」为主输入，**同时传入完整期权链**（同一标的、同一到期日）。结合期权链 + 基本面（FMP Premium）+ 多智能体结论，**在报告流水线内**产出「系统推荐期权策略」。
- **报告结构（三部分）**：  
  1. **标的基本面摘要**：整体标的的基本面、估值、技术/情绪、催化剂（财报等）。  
  2. **用户期权组合点评**：对用户当前构建的策略做 Greeks、IV、风险与综合评点、纠偏建议。  
  3. **系统推荐期权策略**：基于当前期权链与基本面信息，给出 1～2 个具体期权组合建议（名称、腿、strike、简要逻辑与适用场景），供用户参考或一键加载。
- **不依赖 Daily Picks**：仅在本条 AI 多智能体报告流水线内完成「评点 + 推荐」，不在此设计中改动每日精选逻辑。

---

## 一、目标与原则

- **主打能力**：多智能体专家分析 + Deep Research 外部研究，二者强强联合，产出「内部分析扎实、外部信息补充、结论可执行」的投资备忘录。
- **数据原则**：在 FMP Premium 与 Tiger 可用前提下，**宁多勿少**——每个 agent 和 Deep Research 的输入都要「够用且略冗余」，避免因数据取少导致分析质量打折。
- **流程原则**：多智能体先跑，产出结构化专家结论；Deep Research 以这些结论为「主输入」，再做规划、搜索、合成；任务系统统一一条流水线，状态清晰、可重试、可观测。

---

## 二、多智能体数据规范（Data Specification）

### 2.1 数据源分工

| 数据源 | 用途 | 说明 |
|--------|------|------|
| **Tiger** | 期权链、实时/盘后价、单腿 Greeks、流动性 | 策略构建与 Greeks 已由上游（Strategy Lab / 任务入参）提供；任务内可再次拉取以刷新 spot、期权链（可选）。 |
| **FMP Premium** | 基本面、估值、技术指标、历史波动率、财报日历、分析师目标价、评级、新闻/情绪 | 通过 MarketDataService（FinanceToolkit + 直接 FMP 接口）拉取，供 Greeks 以外的所有 agent。Premium 下可用的直接 FMP 接口包括：earnings calendar、analyst estimates、price target、grades、ratings、key-metrics-ttm、batch-quote 等；FinanceToolkit 使用 FMP 作为 primary 时也会获得更全的 ratios/technical/volatility 数据。 |

### 2.2 任务入口统一输入（strategy_summary + option_chain）

以下字段必须在任务创建时或任务执行前准备好，并保证**宁多勿少**：

**strategy_summary 必须/强烈建议包含：**

- `symbol`, `strategy_name`, `expiration_date`, `spot_price`
- `legs[]`: 每腿 `action`, `type`, `strike`, `quantity`, `expiry`, `premium`；可选 `delta`/`gamma`/`theta`/`vega`/`rho`, `implied_volatility`/`implied_vol`
- `portfolio_greeks`: `delta`, `gamma`, `theta`, `vega`, `rho`（数值，已由上游或 `_ensure_portfolio_greeks` 计算）
- `strategy_metrics`: `max_profit`, `max_loss`, `breakeven_points[]`, `probability_of_profit`（若有）
- `trade_execution`: `net_cost`/`net_cash_flow`（若有）
- `historical_prices`: 近期日线（如过去 30/60 日）用于技术面与波动率——**建议由后端在任务开始前按 symbol 从 FMP/FinanceToolkit 拉取并注入**，避免 agent 内再拉
- `expiration_date` / `expiry` 与标的 **earnings_dates**（若 FMP 有）：建议在任务前拉取 FMP 财报日历，注入 `strategy_summary.catalyst` 或 `strategy_summary.upcoming_events`

**option_chain 必须/强烈建议包含：**

- `spot_price`, `underlying_price`（与 strategy_summary.spot_price 对齐）
- `calls[]` / `puts[]`：每档含 `strike`/`strike_price`, `bid`, `ask`, `volume`, `open_interest`；Greeks：`delta`, `gamma`, `theta`, `vega`, `rho`；`implied_volatility`/`implied_vol`
- **覆盖范围**：**完整期权链**（当前标的 + 当前到期日的全部档位，由前端从 `/market/chain` 获取后原样传入）。用途：(1) IV 环境、Skew 分析；(2) **系统推荐策略生成**——模型需基于全链或宽范围（如 ±25% spot）选出合适 strike 组合。若 token 受限，推荐步骤可仅传入 ±25% spot 的子集，但任务入口应保留完整链供后端按需裁剪。

**在「任务执行前」统一补齐的数据（建议在 tasks 层或独立 Data Enrichment 步骤）：**

1. **FMP Premium（通过 MarketDataService）**
   - **get_financial_profile(symbol)**：已包含 ratios、technical_indicators、risk、volatility、profile；**确保调用且结果写入 context 或 strategy_summary 的扩展字段**（如 `strategy_summary.fundamental_profile`），供 market_context_analyst 使用。
   - **历史波动率 / IV 历史**：若 FMP 或 FinanceToolkit 提供 52 周高低、IV 分位，拉取并注入 `strategy_summary.iv_context` 或 `option_chain.iv_history`，供 iv_environment_analyst。
   - **财报日历 / 重大事件**：FMP 的 earnings calendar、analyst dates；注入 `strategy_summary.upcoming_events` 或 `catalyst`。
   - **分析师数据**：price target、rating、grades（FMP 有则拉）；注入 `strategy_summary.analyst_data`，供 market 与 synthesis 使用。
   - **新闻/情绪**（若 FMP Premium 有）：摘要或 sentiment 注入 `strategy_summary.sentiment` 或 `market_sentiment`。
2. **Tiger**
   - 若任务创建时未带最新 option_chain 或 spot：在任务开始时用 Tiger 拉取一次当前期权链与 spot，更新 `option_chain` 与 `strategy_summary.spot_price`，再进入多智能体。

以上保证：**每个 agent 拿到的都是「已经取足」的 strategy_summary + option_chain + 扩展字段，agent 内只做「读与算」，不再依赖现场拉 FMP/Tiger 是否成功**（可选：agent 内允许只读补充，但不作为主路径）。

### 2.3 各 Agent 数据需求清单（确保不取少）

| Agent | 必需输入 | 推荐扩展输入 | 数据来源 |
|-------|----------|--------------|----------|
| **options_greeks_analyst** | strategy_summary.portfolio_greeks, legs[], strategy_metrics | option_chain 各腿 Greeks 分布（用于解释） | 上游/Tiger |
| **iv_environment_analyst** | strategy_summary + option_chain（IV/vol/OI）；legs 的 IV | historical_volatility, iv_rank/iv_percentile, 52w high/low IV；upcoming_events（财报） | FMP/FinanceToolkit + strategy_summary 注入 |
| **market_context_analyst** | symbol；strategy_summary.strategy_name, expiration_date | fundamental_profile（ratios, valuation, solvency）；technical_indicators；analyst_data；upcoming_events；sentiment | MarketDataService.get_financial_profile + 预注入 |
| **risk_scenario_analyst** | strategy_summary；Phase 1 三个 agent 的 _result_* | 同 strategy_summary（Greeks、盈亏、期限） | context 传递 |
| **options_synthesis_agent** | _all_results（上述 4 个 agent 的 data）；strategy_summary | 同上 | context 传递 |

**实施要点**：在任务流水线最前端增加「Data Enrichment」步骤（或合并到现有 _ensure_portfolio_greeks 之后）：  
调用 MarketDataService.get_financial_profile、FMP 财报/分析师/情绪（若 API 有），将结果写入 strategy_summary 的约定字段，再进入 Coordinator。

---

## 三、多智能体协作与 Deep Research 的交互

### 3.1 整体流水线（一条任务，三阶段）

```
[任务开始]
    → Data Enrichment（补齐 strategy_summary / option_chain，见 2.2）
    → Phase A：多智能体（Coordinator）
    → Phase A+：系统推荐策略（Strategy Recommendation）
    → Phase B：Deep Research（Planning → Research → Synthesis）
    → 写报告（三部分结构）、更新任务状态、写 task_metadata
[任务结束]
```

- **Phase A 多智能体**：与现有一致，Phase 1 并行（Greeks, IV, Market）→ Phase 2 串行（Risk）→ Phase 3 串行（Synthesis）。  
- **Phase A 输出**：`all_results` + **agent_summaries**（每个 agent 的 1～2 句摘要 + 3～5 条要点），供 Deep Research 与报告组装用。
- **Phase A+ 系统推荐策略**：  
  - **输入**：完整 option_chain（或 ±25% spot 子集以控 token）、strategy_summary（用户当前组合，作上下文）、fundamental_profile、**agent_summaries**（含 IV/市场/风险结论）。  
  - **产出**：**recommended_strategies**：1～2 个推荐期权组合，每个含策略名、腿（type/action/strike/quantity）、简要逻辑、适用场景、预估成本或 POP（若有）。可实现为新 agent（strategy_recommendation_agent）或单次 LLM 调用（结构化 JSON），供报告第三部分使用。  
- **Phase B Deep Research**：  
  - **Planning**：输入 = strategy_summary + option_chain 摘要 + **agent_summaries**。输出 = 4 个研究问题。  
  - **Research**：对 4 个问题分别 Google Search + 总结，得到 research_findings。  
  - **Synthesis**：输入 = **agent_summaries** + research_findings + strategy_summary + option_chain 摘要 + **recommended_strategies**；输出 = **三部分 Markdown 报告**（见 3.4）。

### 3.2 多智能体内部协作（现有 + 小增强）

- **Phase 1 并行**：Greeks / IV / Market 三者仅读 strategy_summary + option_chain（及预注入的 profile、iv_context 等），互不依赖，并行执行。  
- **Phase 2**：Risk 读 Phase 1 的 `_result_*`，做情景与压力分析。  
- **Phase 3**：Synthesis 读 `_all_results`，产出「内部综合报告」+ **agent_summaries**（给 Deep Research）。  
- **agent_summaries 结构建议**（供 Deep Research 消费）：

```json
{
  "options_greeks": "1-2句摘要",
  "options_greeks_bullets": ["要点1", "要点2", ...],
  "iv_environment": "1-2句摘要",
  "iv_environment_bullets": [...],
  "market_context": "1-2句摘要",
  "market_context_bullets": [...],
  "risk_scenario": "1-2句摘要",
  "risk_scenario_bullets": [...],
  "internal_synthesis_summary": "2-3句内部综合结论（可选）"
}
```

可由 options_synthesis_agent 在现有输出基础上多输出一段结构化摘要，或由 Coordinator 在 Phase 3 后根据各 agent 的 `data.analysis` 用模板生成。

### 3.3 与 Deep Research 的接口

- **输入**：  
  - `strategy_summary`（含 2.2 中全部字段及扩展）  
  - `option_chain`（摘要或关键档位用于 Planning/Synthesis；完整链或 ±25% 已用于 Phase A+ 推荐）  
  - **agent_summaries**（如上）  
  - **recommended_strategies**（Phase A+ 产出，供 Synthesis 写入报告第三部分）  
- **输出**：  
  - Planning → `research_questions[]`  
  - Research → `research_findings[]`（question + findings）  
  - Synthesis → **三部分** Markdown 报告（见 3.4）

### 3.4 报告固定结构（三部分）

最终报告必须包含以下三部分，顺序固定：

1. **标的基本面摘要（Fundamentals）**  
   - 标的概况、估值与财务要点、技术/情绪、近期催化剂（财报等）、分析师/目标价（若有）。  
   - 数据来源：market_context_analyst 结论 + fundamental_profile（Data Enrichment 注入）。

2. **用户期权组合点评（Your Strategy Review）**  
   - 对用户当前构建的期权组合做：Greeks 解读、IV 环境、市场契合度、风险情景、综合评点与纠偏建议（hold/trim/avoid 及理由）。  
   - 数据来源：agent_summaries + options_synthesis_agent 结论。

3. **系统推荐期权策略（System-Recommended Strategies）**  
   - 基于当前期权链与基本面，给出 1～2 个具体推荐组合：策略名称、腿（call/put、buy/sell、strike、quantity）、简要逻辑、适用场景、预估成本或 POP（若可算）。  
   - 数据来源：**recommended_strategies**（Phase A+ 产出）；Synthesis 只做格式化与自然语言呈现，不在此步重新生成推荐。

### 3.5 Phase A+ 推荐策略：输出结构约定

**recommended_strategies** 建议为数组，每项结构如下（便于后端解析、前端「一键加载」或报告渲染）：

```json
{
  "recommended_strategies": [
    {
      "strategy_name": "Bull Put Spread (示例)",
      "rationale": "1-2句逻辑与适用场景",
      "legs": [
        { "type": "put", "action": "sell", "strike": 220, "quantity": 1, "expiry": "2025-02-21" },
        { "type": "put", "action": "buy", "strike": 215, "quantity": 1, "expiry": "2025-02-21" }
      ],
      "estimated_net_credit": 0.85,
      "max_profit": 85,
      "max_loss": 415,
      "breakeven": 219.15
    }
  ]
}
```

- 所有 strike/expiry 必须来自当前传入的 option_chain，保证可加载。  
- 若 LLM 返回非结构化文本，可退化为「仅自然语言描述」放入报告第三部分，不解析为 legs。

---

## 四、Deep Research 改造方案（接住多智能体，强强联合）

### 4.1 当前问题

- 只收「策略 + 期权链」JSON，没有多智能体结论。  
- 规划问题泛泛，未针对「内部分析结论」提问。  
- 合成阶段未要求「先总结内部分析、再结合研究」，报告与多智能体脱节。

### 4.2 改造后的三阶段

**Step 1：Planning（规划研究问题）**

- **输入**：  
  - strategy_summary（含 Greeks、盈亏、期限、catalyst/upcoming_events、analyst_data 等）  
  - option_chain 摘要（spot、主要 strike、IV 水平）  
  - **agent_summaries**（Greeks/IV/Market/Risk 的摘要与要点）  
- **Prompt 要求**：  
  - 明确说明：「以下是内部专家分析结论（Greeks、IV、市场、风险），请基于这些结论，提出 4 个**必须通过 Google 搜索才能更好回答**的问题，用于补充或验证内部分析。」  
  - 问题需具体、可检索（如「某标的 2025 年 Q1 财报日期」「某标的当前华尔街目标价中位数」）。  
- **输出**：4 个字符串问题，存为 `research_questions`；若解析失败则用默认 4 问（与 symbol/strategy 相关）。

**Step 2：Research（外部研究）**

- 与现有一致：对每个问题 `_call_gemini_with_search(use_search=True)`，得到 findings。  
- 可选：对部分问题限制检索语言/地区（如英文、美国来源），在 prompt 中写明。  
- 结果存为 `research_findings`，供 Synthesis 使用。

**Step 3：Synthesis（合成最终报告）**

- **输入**：  
  - **agent_summaries**（完整结构化摘要 + 要点）  
  - **research_findings**（Q&A）  
  - strategy_summary（含 legs、portfolio_greeks、strategy_metrics、trade_execution、catalyst 等）  
  - option_chain 摘要（spot、IV、关键档位）  
  - **recommended_strategies**（Phase A+ 产出的 1～2 个推荐组合，含腿与逻辑）  
- **Prompt 要求**：  
  - **报告必须为三部分结构**（与 3.4 一致）：  
    1. **标的基本面摘要**：标的概况、估值与财务、技术/情绪、催化剂、分析师/目标价（来自 agent_summaries.market_context + fundamental 数据）。  
    2. **用户期权组合点评**：基于 agent_summaries 与 synthesis 结论，写 Greeks、IV、市场契合、风险情景、综合评点与纠偏建议。  
    3. **系统推荐期权策略**：将 **recommended_strategies** 格式化为可读 Markdown（策略名、腿、逻辑、适用场景、预估成本/POP），不在此步重新生成推荐内容。  
  - 可选：在报告最前增加 **Executive Summary**（2～3 句总览），再进入上述三部分。  
  - 明确：「内部分析为主，外部研究为补充与验证；若外部与内部冲突，需在报告中说明并给判断。」  
- **输出**：最终 Markdown 报告（三部分 + 可选 Executive Summary），作为任务唯一「报告正文」写入 AIReport。

### 4.3 数据流小结

- 多智能体 → 产出 `all_results` + **agent_summaries**。  
- **Phase A+** 消费 option_chain（完整或 ±25%）+ strategy_summary + fundamental_profile + **agent_summaries** → 产出 **recommended_strategies**。  
- Deep Research Planning 消费 strategy_summary + option_chain 摘要 + **agent_summaries**。  
- Deep Research Research 消费 4 个问题，产出 research_findings。  
- Deep Research Synthesis 消费 **agent_summaries** + research_findings + strategy_summary + option_chain 摘要 + **recommended_strategies** → **三部分**最终报告（标的基本面 + 用户策略点评 + 系统推荐策略）。

---

## 五、任务系统设计（兼容、详情透出、状态与重试）

### 5.1 任务类型与流水线

- **统一任务类型**：建议保留 `multi_agent_report` 或重命名为 `full_analysis_report`，表示「多智能体 + Deep Research + 系统推荐策略」一条龙。  
- **执行顺序**：Data Enrichment → Phase A（多智能体）→ **Phase A+（系统推荐策略）** → Phase B（Deep Research）→ 写库与状态更新。  
- 单智能体「仅 Deep Research」可保留为另一任务类型（如 `ai_report`），仅执行 Data Enrichment + Deep Research，不跑多智能体、不跑 Phase A+；此时 agent_summaries 为空，recommended_strategies 可为空，Deep Research 仅用 strategy + 网络研究。

### 5.2 任务状态与 task_metadata

**建议状态机**（在现有 PENDING/PROCESSING/SUCCESS/FAILED 基础上细化阶段）：

- **PENDING**：已创建，未开始。  
- **PROCESSING**：执行中；**task_metadata** 中记录当前阶段与进度。  
- **SUCCESS**：报告已写入，result_ref = ai_report.id。  
- **FAILED**：某阶段失败且重试耗尽；error_message 记录最后错误。

**task_metadata 建议结构**（保证任务详情页可完整透出）：

```json
{
  "progress": 0,
  "current_stage": "string",
  "stages": [
    {
      "id": "data_enrichment",
      "name": "Data Enrichment",
      "status": "success|running|failed|pending",
      "started_at": "ISO8601",
      "ended_at": "ISO8601",
      "message": "optional short message"
    },
    {
      "id": "phase_a",
      "name": "Multi-Agent Analysis",
      "status": "...",
      "sub_stages": [
        { "id": "greeks", "name": "Greeks Analyst", "status": "..." },
        { "id": "iv", "name": "IV Environment", "status": "..." },
        { "id": "market", "name": "Market Context", "status": "..." },
        { "id": "risk", "name": "Risk Scenario", "status": "..." },
        { "id": "synthesis", "name": "Internal Synthesis", "status": "..." }
      ]
    },
    {
      "id": "phase_a_plus",
      "name": "Strategy Recommendation",
      "status": "success|running|failed|pending",
      "started_at": "ISO8601",
      "ended_at": "ISO8601",
      "message": "optional"
    },
    {
      "id": "phase_b",
      "name": "Deep Research",
      "status": "...",
      "sub_stages": [
        { "id": "planning", "name": "Planning", "status": "..." },
        { "id": "research", "name": "Research (4 questions)", "status": "..." },
        { "id": "synthesis", "name": "Final Synthesis", "status": "..." }
      ]
    }
  ],
  "agent_summaries": { ... },
  "research_questions": [ ... ],
  "workflow_results": { ... }
}
```

- **progress**：0～100，由各阶段回调统一更新（Data Enrichment 0～5，Phase A 5～45，Phase A+ 45～50，Phase B 50～100）。  
- **current_stage**：人类可读的当前步骤说明（如 "Phase A: IV Environment Analyst" / "Phase A+: Strategy Recommendation" / "Phase B: Research Q3"）。  
- **stages**：用于详情页「阶段列表」展示；每个阶段/子阶段有 status、时间、可选 message。  
- **agent_summaries**：Phase A 结束后写入，供 Phase A+ 与 Deep Research 使用，也可在详情页展示「内部分析摘要」。  
- **recommended_strategies**：Phase A+ 结束后写入，供 Deep Research Synthesis 写入报告第三部分。  
- **research_questions**：Phase B Planning 结束后写入，详情页可展示「本次研究的 4 个问题」。  
- **workflow_results**：可选，存各 agent 的简要结果键名与状态，便于排查。

**execution_history**：保留现有按时间顺序的 event 列表（info/progress/error），每条可带 timestamp、type、message；便于日志与排查。

### 5.3 任务详情页应展示的内容

- **概览**：任务类型、状态、创建/开始/完成时间、耗时、若失败则错误信息。  
- **进度**：  
  - 用 `task_metadata.progress` 与 `task_metadata.current_stage` 驱动进度条与当前步骤文案。  
  - 用 `task_metadata.stages` 渲染「阶段/子阶段」列表（可折叠），每项显示：名称、状态、起止时间、可选短 message。  
- **内部分析摘要**：若存在 `task_metadata.agent_summaries`，以折叠面板展示（Greeks/IV/Market/Risk 摘要与要点）。  
- **研究问题**：若存在 `task_metadata.research_questions`，展示 4 个问题；可选展示 research_findings 的简短摘要（避免过长）。  
- **执行历史**：现有 execution_history 时间线（info/progress/error），便于排查。  
- **结果**：若 status=SUCCESS，显眼「查看报告」按钮，跳转报告详情页（result_ref）。

### 5.4 任务状态转换（简要）

- **PENDING** → **PROCESSING**：任务被 worker 捞取并开始执行（写 started_at、current_stage）。  
- **PROCESSING**：整个流水线执行期间保持；仅通过 task_metadata.progress / current_stage / stages 反映子阶段。  
- **PROCESSING** → **SUCCESS**：Phase B Synthesis 完成并成功写入 AIReport；写 result_ref、completed_at。  
- **PROCESSING** → **FAILED**：任一步骤在重试耗尽后仍失败；写 error_message、completed_at；task_metadata.stages 中失败阶段 status=failed、message=错误摘要。  
- 不设「部分成功」中间状态；若需「报告已写但某子阶段异常」，可在 task_metadata 中记 warning，任务仍为 SUCCESS。

### 5.5 异常与重试（稳定性）

- **阶段级重试**：  
  - Data Enrichment 失败：可重试 1～2 次（如 FMP 超时）；若仍失败则任务 FAILED，error_message 注明「数据拉取失败」。  
  - Phase A 某 agent 失败：  
    - 可选：该 agent 重试 1 次；若仍失败，将该 agent 结果标为「部分失败」，agent_summaries 中对应项为「暂缺」，其余 agent 继续；Synthesis 与 Deep Research 仍可基于已有结论执行。  
    - 若要求「全部成功才继续」，则 Phase A 任一步失败即进入阶段级重试或任务失败。  
  - Phase B Planning/Research/Synthesis 任一步失败：可对该步重试 1～2 次；若仍失败则任务 FAILED。  
- **任务级重试**：  
  - 用户或系统可对 FAILED 任务发起「重试」（新建同参数任务或复用原任务 id 再次执行）；实现上建议「新建任务」更清晰，原任务保留失败记录。  
  - 可选：支持「从某阶段续跑」（如 Phase A 成功、Phase B 失败，重试时仅重跑 Phase B）；需在 task_metadata 中持久化 Phase A 的 agent_summaries 与 all_results，重试时读入并跳过 Phase A。  
- **幂等与超时**：  
  - 单次任务执行内，各阶段只执行一次，不重复写 report；若 Phase B 已写 report 后某步报错，应视为部分成功（可选：标记任务为 SUCCESS 但 task_metadata 中记录某子阶段 warning）。  
  - 各阶段设置超时（如 Phase A 总超时 5 分钟，Phase B 总超时 8 分钟）；超时则当前阶段失败并进入重试或任务失败。  
- **日志与可观测性**：  
  - 所有阶段开始/结束/失败写 execution_history；关键错误写 error_message 与 task_metadata.stages[].message，便于支持与排查。

---

## 六、Prompt 体系设计（统一、完整、发挥 Tiger/FMP/多智能体 + Deep Research）

### 6.1 原则

- **分层**：系统级（角色/约束）→ 阶段级（Planning/Research/Synthesis）→ 实例级（注入当前 strategy、agent_summaries、research 结果）。  
- **可复用**：所有 prompt 模板集中管理（如配置或常量），便于迭代与 A/B。  
- **显式利用数据**：在 prompt 中明确列出「你将看到：Tiger 期权链与 Greeks、FMP 基本面与估值、多智能体专家结论、外部研究 Q&A」，并要求模型「必须引用这些输入再下结论」。

### 6.2 多智能体侧 Prompt

- **options_greeks_analyst**  
  - 系统：专业期权 Greeks 专家；输出需包含「风险等级」「关键风险点」「与策略结构的对应关系」。  
  - 用户：注入 strategy_summary（含 portfolio_greeks、legs、strategy_metrics）、option_chain 摘要；要求 1）解读每个 Greek 对策略的影响 2）指出最大风险来源 3）给出 3～5 条要点；**输出末尾增加一段「给 Deep Research 的 1～2 句摘要 + 3 条要点」**（便于自动拼 agent_summaries）。  

- **iv_environment_analyst**  
  - 系统：IV 与波动率专家；输出需包含 IV 贵/便宜/合理、IV Rank 解读、与到期/财报的关系。  
  - 用户：注入 iv_data（当前 IV、历史波动率、52w 高低、upcoming_events）、strategy 名称与到期；要求 1）IV 环境判断 2）IV crush 风险 3）3～5 条要点；**同样输出「给 Deep Research 的摘要 + 要点」**。  

- **market_context_analyst**  
  - 系统：基本面+技术面+市场情绪专家；输出需结合 FMP 数据（估值、盈利、评级、技术指标）。  
  - 用户：注入 fundamental_profile、technical_indicators、analyst_data、upcoming_events、strategy 与到期；要求 1）市场环境（多空/中性）2）估值与盈利简评 3）技术位与催化剂 4）3～5 条要点；**输出「给 Deep Research 的摘要 + 要点」**。  

- **risk_scenario_analyst**  
  - 系统：风险情景与压力测试专家；输出需包含最坏情景、尾部风险、与 Phase 1 结论的一致性。  
  - 用户：注入 strategy_summary + Phase 1 的 _result_*；要求 1）最大亏损情景 2）压力情景（如标的大涨/大跌、IV 变）3）3～5 条要点；**输出「给 Deep Research 的摘要 + 要点」**。  

- **options_synthesis_agent**  
  - 系统：投资备忘录撰写人；将上述 4 个专家结论合成为「内部综合报告」+ **结构化 agent_summaries**（供 Deep Research）。  
  - 用户：注入 _all_results + strategy_summary；要求 1）写一段内部综合报告（Markdown）2）**必须输出结构化 agent_summaries**（JSON 或固定格式）：每个 agent 的 1～2 句摘要 + 3～5 条要点；若某 agent 缺失则对应项为「暂缺」。

### 6.3 Deep Research 侧 Prompt

- **Planning**  
  - 系统：你是指派研究问题的首席分析师。输入包含：策略与期权链摘要、**内部专家分析结论（Greeks/IV/市场/风险）**。  
  - 用户：注入 strategy_summary（关键字段）、option_chain 摘要、**agent_summaries**；要求：基于内部分析，提出 4 个「必须通过 Google 搜索才能更好回答」的具体问题；问题需可检索、有明确答案（如日期、数字、评级）；输出仅 JSON 数组 of 4 字符串。  

- **Research（每问）**  
  - 系统：你是研究专员，用 Google 搜索回答问题，并总结为事实与数据。  
  - 用户：当前问题 + 可选上下文（symbol、strategy 名称）；要求：检索最新信息，总结为要点，含数字与日期；简洁但完整。  

- **Synthesis**  
  - 系统：你是衍生品策略首席，撰写最终投资备忘录。**你必须先总结内部分析（Greeks、IV、市场、风险），再结合外部研究 4 问的答案，最后给出综合结论与建议。内部分析为主，外部研究为补充与验证。**  
  - 用户：注入 **agent_summaries**（完整）、research_findings（Q&A）、strategy_summary（legs、portfolio_greeks、strategy_metrics、catalyst）、option_chain 摘要。  
  - 结构要求（在 prompt 中写死）：  
    1. **Executive Summary**（2～3 句）  
    2. **Internal Expert Analysis**（Greeks / IV / Market / Risk 四块，每块用要点+短段）  
    3. **External Research**（4 个问题的研究发现）  
    4. **Synthesis & Verdict**（结论、风险收益评分、操作建议）  
  - 输出：仅 Markdown，无多余解释。

### 6.4 单次 Report 的 Prompt（兜底）

- 若保留「多智能体失败或未选多智能体时单次生成报告」：  
  - 使用 **DEFAULT_REPORT_PROMPT_TEMPLATE** 的增强版：在「Input Data」部分明确列出「若存在以下数据则必须使用：Tiger 期权链与 Greeks、FMP 基本面/估值/技术、财报与催化剂」。  
  - 要求：先市场与 IV  grounding，再 Greeks 与风险，最后 Verdict；与多智能体+Deep Research 的报告结构尽量对齐，便于体验一致。

### 6.5 Prompt 最佳实践与质量保障

- **角色与约束**：每个 prompt 开头固定「角色 + 约束」（如：你是…专家；输出必须基于下列输入，不得臆测；若某数据缺失则明确说明「无数据」）。  
- **输入显式列举**：在用户消息中明确写出「你将看到：1）… 2）…」，让模型知道数据来源（Tiger/FMP/多智能体），并要求「结论必须引用上述输入」。  
- **输出格式与长度**：  
  - Agent 分析：要求「3～5 条要点 + 1～2 句摘要」；Deep Research Synthesis 要求「Executive Summary 不超过 3 句」「每节有子标题」。  
  - Planning 输出：仅 JSON 数组，无多余 markdown；若模型返回 markdown 包裹，解析前 strip 掉。  
- **引用与可追溯**：在 Synthesis 中要求「内部分析引用专家结论（Greeks/IV/Market/Risk）」「外部研究引用 4 个问题的答案」；便于用户与审计追溯。  
- **版本与配置**：所有 prompt 模板放入配置或常量文件，带版本号或命名（如 `planning_v1`）；修改时保留旧版便于回滚与 A/B。

---

## 七、实施顺序建议（基于本设计落地）

1. **Data Enrichment**：在任务执行入口（tasks.py multi_agent_report 分支）中，在调用 Coordinator 前，增加「补齐 strategy_summary/option_chain」的逻辑（get_financial_profile、FMP 财报/分析师/情绪等），写入约定字段。  
2. **agent_summaries 产出**：在 options_synthesis_agent 中增加「结构化 agent_summaries」输出；Coordinator 在 Phase A 结束后将其写入 context，并传给 Phase B。  
3. **Deep Research 改造**：  
   - Planning：增加 agent_summaries 输入与「基于内部分析提 4 问」的指令。  
   - Synthesis：增加 agent_summaries + 规定报告结构（Internal Expert Analysis → External Research → Synthesis & Verdict）。  
4. **流水线串联**：ai_service 或 tasks 层实现「Phase A → Phase B」顺序调用；Phase B 接收 Phase A 的 agent_summaries 与 strategy_summary/option_chain。  
5. **task_metadata 与详情页**：  
   - 各阶段回调统一写 task_metadata（progress、current_stage、stages）；  
   - 前端任务详情页按 5.3 展示阶段、摘要、研究问题、执行历史、报告入口。  
6. **重试与稳定性**：按 5.4 实现阶段级重试与超时；任务失败时 error_message 与 stages 记录清晰。  
7. **Prompt 迭代**：将 6.2 / 6.3 的 prompt 文本落为常量或配置，便于后续优化与 A/B。

---

## 八、文档修订与后续

- 本文档为「多智能体 + Deep Research + 任务系统 + Prompt」的**唯一设计基准**；后续功能（含 Data Enrichment 具体字段、FMP Premium 具体接口、前端任务详情组件）均以此为准。  
- 修订时请更新版本号并注明变更点；实现时若遇与文档冲突，以文档为准并同步更新实现或文档。
