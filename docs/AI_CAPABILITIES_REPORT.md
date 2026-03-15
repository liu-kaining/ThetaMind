# ThetaMind 系统 AI 能力完整报告

**文档性质**：基于当前代码库的 AI 能力梳理，涵盖 AI Agent、Deep Research、报告生成、出图、AI 配置与配额。  
**日期**：2026-02-21

---

## 一、总览

| 能力模块 | 说明 | 入口/配置 |
|----------|------|-----------|
| **AI Agent（多智能体）** | 5 个期权专家 Agent 串并行执行，产出内部分析 | 报告流水线 Phase A |
| **Deep Research** | 规划问题 → Google 检索 → 合成投资备忘录 | 报告流水线 Phase B |
| **出报告** | 全文 Markdown 报告存储、导出 PDF、多语言 | `AIReport`、`/ai/reports` |
| **出图（Nano Banana）** | 策略结构/盈亏图 AI 生图，存 R2 | `generate_strategy_chart` 任务 |
| **AI 配置** | 报告模型列表、出图模型、Prompt 模板、Provider | 管理后台 + 环境变量 |

---

## 二、AI Agent（多智能体）

### 2.1 架构

- **位置**：`backend/app/services/agents/`
- **组件**：`BaseAgent`、`AgentRegistry`、`AgentExecutor`、`AgentCoordinator`
- **默认 Provider**：由 `AI_PROVIDER` 决定（gemini / zenmux / openai），Agent 调用统一走 AIService 的 provider

### 2.2 期权分析专用 Agent（5 个）

| Agent | 注册名 | 功能概要 | 实现文件 |
|-------|--------|----------|----------|
| **OptionsGreeksAnalyst** | `options_greeks_analyst` | Delta/Gamma/Theta/Vega 风险分析、风险评分与分类 | `options_greeks_analyst.py` |
| **IVEnvironmentAnalyst** | `iv_environment_analyst` | IV 环境（IV Rank/Percentile）、历史波动率、IV Crush、波动率机会 | `iv_environment_analyst.py` |
| **MarketContextAnalyst** | `market_context_analyst` | 市场环境（基本面+技术面+情绪）、与策略匹配度 | `market_context_analyst.py` |
| **RiskScenarioAnalyst** | `risk_scenario_analyst` | 最坏情况、尾部风险、压力测试、风险缓解建议 | `risk_scenario_analyst.py` |
| **OptionsSynthesisAgent** | `options_synthesis_agent` | 综合以上结果、生成内部初步报告、识别矛盾与建议 | `options_synthesis_agent.py` |

### 2.3 编排流程（Phase A）

- **Coordinator**：`AgentCoordinator.coordinate_options_analysis()`（见 `coordinator.py`）
- **Phase 1（并行）**：Greeks、IV、Market 三个 Agent 同时执行
- **Phase 2（顺序）**：Risk Scenario 依赖 Phase 1 结果
- **Phase 3（顺序）**：Synthesis 依赖全部结果，产出 `internal_preliminary_report` 与 `agent_summaries`
- **进度**：通过 `progress_callback(percent, message)` 回写任务 `execution_history` 与 `task_metadata.stages.phase_a.sub_stages`（greeks / iv / market / risk / synthesis）

### 2.4 其他已注册 Agent（非报告主流程）

- **FundamentalAnalyst**、**TechnicalAnalyst**：基本面/技术面分析
- **StockScreeningAgent**、**StockRankingAgent**：选股与排序  
当前 Deep Research 报告流水线仅使用上述 5 个期权分析 Agent。

---

## 三、Deep Research

### 3.1 定位

- 在「多智能体报告」流水线中为 **Phase B**，在 Phase A（多 Agent）、Phase A+（策略推荐）之后执行。
- 使用 **Google Search**（Gemini `google_search` / `google_search_retrieval`）做实时检索，再合成一份长文投资备忘录。

### 3.2 流程（Phase B 三步骤）

| 步骤 | 说明 | 进度区间 |
|------|------|-----------|
| **Step 0** | 若有 Phase A 结果，先整理 `planning_data`（含 internal_preliminary_report 或 agent_summaries 摘要） | ~2–5% |
| **Step 1：Planning** | 根据策略与内部分析，生成 1–5 个「必须用 Google 检索回答」的研究问题（JSON 数组） | ~5–15% |
| **Step 2：Research** | 对每个问题并发调用 `_call_gemini_with_search(use_search=True)`，汇总为 research_findings | ~15–70% |
| **Step 3：Synthesis** | 将 research_findings、内部分析、推荐策略、基本面等拼成 prompt，调用 Gemini 生成最终 Markdown 报告 | ~70–100% |

### 3.3 Google Search 使用

- **Gemini 2.x/3.x**：`tools: [{"google_search": {}}]`（Generative Language API 驼峰为 `google_search`）
- **Gemini 1.5**：`google_search_retrieval` + `dynamic_retrieval_config`
- 实现见 `gemini_provider.py` 中 `_call_gemini_http_api` 的 `use_search` 分支；Research 阶段每次请求开启 search。

### 3.4 报告结构（三部分 vs 单份）

- **三部分模式**（有 Phase A + Phase A+ 结果）：  
  **1. Fundamentals**（公司、估值、催化剂、分析师目标等，≥400 词）→ **2. Your Strategy Review**（Greeks/IV/风险/结论，≥400 词）→ **3. System-Recommended Strategies**（直接呈现系统推荐策略，不重新生成）
- **单份模式**（无 Agent/推荐）：基于 strategy_context + research_summary + 基本面，生成一份完整投资备忘录（含 Executive Summary、Market Alignment、Strategy Mechanics、Scenario Analysis、Final Verdict）。
- **语言**：支持 `language` 参数（如 `zh-CN`、`en-US`），在 synthesis prompt 末尾要求「全文使用指定语言」。

### 3.5 超时与降级

- Phase B 总超时：**30 分钟**（`PHASE_B_TIMEOUT = 1800`）。
- Synthesis 单次请求：最长约 **20 分钟**（`timeout_sec=1200`）。
- 超时后任务标记 Phase B 失败；无自动降级为「仅 Agent 简版报告」的开关（设计上可扩展）。

---

## 四、出报告（Report）

### 4.1 端到端流水线（当前唯一入口：异步任务）

1. **创建任务**：`POST /api/v1/ai/report`（`async_mode=true`）或等价流程，传入 `strategy_summary`、`option_chain`、`preferred_model_id`、`language`。
2. **Data Enrichment**：`_run_data_enrichment(strategy_summary)` 拉取 FMP 等数据，写入 `strategy_summary`（不抛错，失败则对应字段为空）：
   - `fundamental_profile`（财务画像）
   - `analyst_data`（estimates、price_target）
   - `iv_context`（历史波动率等）
   - `upcoming_events` / `catalyst`（财报日历）
   - `historical_prices`（缺失时补全）
3. **Phase A**：多智能体分析（见第二节），超时 8 分钟。
4. **Phase A+**：`ai_service.generate_strategy_recommendations()` 生成 1–2 条推荐策略。
5. **Phase B**：Deep Research（见第三节），超时 30 分钟。
6. **持久化**：报告内容写入 `ai_reports` 表（`report_content`、`model_used`、`created_at`），任务 `result_ref = ai_report.id`，状态 `SUCCESS`。

### 4.2 报告存储与 API

- **模型**：`AIReport`（user_id, report_content, model_used, created_at）。
- **列表**：`GET /api/v1/ai/reports`（当前用户）。
- **详情**：`GET /api/v1/ai/reports/{report_id}`。
- **导出 PDF**：`GET /api/v1/ai/reports/{report_id}/pdf`（依赖 `report_pdf_service`，需可用的 PDF 环境）。

### 4.3 任务阶段结构（供前端展示）

- `task_metadata.stages` 包含：  
  `data_enrichment` → `phase_a`（含 sub_stages: greeks, iv, market, risk, synthesis）→ `phase_a_plus` → `phase_b`（含 sub_stages: planning, research, synthesis）。
- Phase B 完成后可将 `research_questions` 写入 `task_metadata`（来自 Gemini 返回的 dict）。

---

## 五、出图（Nano Banana / 策略图生成）

### 5.1 能力说明

- **用途**：根据当前策略（strategy_summary 或 strategy_data + option_chain）生成「策略结构 + 盈亏示意」的**宽幅信息图**（16:9），用于展示、分享或报告配图。
- **Prompt**：`image_provider.py` 中 Wall Street 风格模板（现代扁平、绿/红/灰配色、Opening Strategy Structure + P&L at Expiration 等）。
- **不翻译专有名词**：Call、Put、Strike、Delta 等保持英文。

### 5.2 调用链

- **创建任务**：`POST /api/v1/ai/chart/generate`，body 含 `strategy_summary` 或 `strategy_data` + `option_chain`。
- **任务类型**：`generate_strategy_chart`。
- **执行**：`_handle_generate_strategy_chart_task` 调用 `ImageProvider.generate_strategy_chart_image()`，得到 base64 图像 → 上传 R2（若配置）→ 写入 `generated_images`（user_id、task_id、strategy_hash、r2_url 等）。
- **查图**：`GET /api/v1/ai/chart/{image_id}`（重定向到 R2）、`GET /api/v1/ai/chart/info/{image_id}`（含 r2_url）、`GET /api/v1/ai/chart/by-hash/{strategy_hash}`（按策略哈希取缓存）。

### 5.3 出图 Provider 与模型

- **选择顺序**：`AI_IMAGE_PROVIDER`（或沿用 `AI_PROVIDER`）→ openai / zenmux / gemini。
- **OpenAI 兼容**：`AI_BASE_URL` + `AI_API_KEY` + `AI_IMAGE_MODEL`。
- **ZenMux**：`ZENMUX_API_KEY`，Vertex 协议，模型如 `google/gemini-3-pro-image-preview`。
- **Gemini**：Google API Key 或 Vertex，使用 Gemini 图像模型（如 gemini-3-pro-image），非 Imagen API。
- **内置模型列表**：`constants.IMAGE_MODELS`，可通过管理后台配置键 `ai_image_models_json` 覆盖。

### 5.4 配额（按日）

- **Free**：1 次/日  
- **Pro 月付**：10 次/日  
- **Pro 年付**：30 次/日  
- 使用 `daily_image_usage`、`last_quota_reset_date`（UTC 日切重置）。

---

## 六、AI 配置

### 6.1 报告模型（Report Models）

- **来源**：优先读系统配置 `ai_report_models_json`（JSON 数组：`id`、`provider`、`label`、可选 `enabled`）；若无效或未配置则用 `constants.REPORT_MODELS`。
- **内置示例**：Gemini 3.1 Pro Preview、Gemini 3 Flash Preview、Gemini 3 Pro Preview、Gemini 2.5 Pro 等（见 `backend/app/core/constants.py`）。
- **ZenMux**：仅当配置了 `ZENMUX_API_KEY` 时，`GET /api/v1/ai/models` 才包含 provider 为 zenmux 的模型。
- **用户选择**：发起报告时传 `preferred_model_id`，AIService 通过 `_resolve_provider_and_model()` 解析出实际使用的 provider 与 model。

### 6.2 出图模型（Image Models）

- **来源**：优先读 `ai_image_models_json`，否则 `constants.IMAGE_MODELS`（如 OpenAI GPT Image 1.5、Gemini 3 Pro Image 等）。
- **管理端**：`GET /api/v1/admin/ai-models-defaults` 返回内置 report_models 与 image_models，供管理后台「恢复默认」使用。

### 6.3 Prompt 模板

- **配置键**：`ai.report_prompt_template`（通过 config_service 读取）。
- **默认**：各 Provider（Gemini、ZenMux、UniversalOpenAI）内部有 `DEFAULT_REPORT_PROMPT_TEMPLATE`；单报告路径（非多 Agent）会使用该模板或配置覆盖。
- **Deep Research**：Phase B 的 planning / research / synthesis 的 prompt 在 `gemini_provider.generate_deep_research_report()` 内硬编码，当前未从配置读取（可后续扩展）。

### 6.4 环境变量（摘要）

| 变量 | 作用 |
|------|------|
| `AI_PROVIDER` | 默认报告/Agent 使用的 provider：gemini / zenmux / openai |
| `AI_IMAGE_PROVIDER` | 出图 provider，缺省时与 AI_PROVIDER 一致 |
| `GOOGLE_API_KEY` / Vertex 相关 | Gemini 报告与出图 |
| `ZENMUX_API_KEY` | ZenMux 报告与出图 |
| `AI_BASE_URL`、`AI_API_KEY`、`AI_IMAGE_MODEL` | OpenAI 兼容出图 |

---

## 七、配额与限流

### 7.1 报告配额（按日，UTC 零点重置）

- **单位**：1 次简单报告 = 1 单位；**当前仅支持 Deep Research 模式，一次运行 = 5 单位**。
- **Free**：5 单位/日（即 1 次 Deep Research）。  
- **Pro 月付**：40 单位/日（8 次）。  
- **Pro 年付**：100 单位/日（20 次）。
- **校验**：创建任务前 `check_ai_quota(current_user, db, required_quota=5)`；多 Agent 任务在 handler 内通过 `increment_ai_usage_if_within_quota(..., quota_units=5)` 原子预留。

### 7.2 出图配额

- 见第五节；`check_image_quota()`、`daily_image_usage` 与 `get_image_quota_limit()` 协同。

### 7.3 其他

- **429**：Gemini 请求 429 时有多轮重试与退避，必要时回退到 Vertex。
- **熔断**：Gemini 有 circuit breaker，防止持续失败拖垮服务。

---

## 八、数据流简图

```
Strategy Lab (保存策略)
        │
        ▼
POST /api/v1/ai/report (async_mode=true)
        │
        ├─ 配额校验 (5 单位) → 创建任务 (multi_agent_report)
        │
        ▼
_handle_multi_agent_report_task
        │
        ├─ Data Enrichment (FMP: fundamental_profile, analyst_data, iv_context, catalyst, ...)
        ├─ Phase A: Coordinator → Greeks → IV → Market → Risk → Synthesis
        ├─ Phase A+: generate_strategy_recommendations
        ├─ Phase B: generate_deep_research_report (Planning → Research with Google → Synthesis)
        ├─ 写入 AIReport，task.result_ref = report_id
        └─ 扣减 daily_ai_usage += 5
        │
        ▼
GET /api/v1/tasks/{id} → 前端轮询 / 跳转报告页
GET /api/v1/ai/reports/{report_id} → 展示 / 导出 PDF
```

---

## 九、相关文件索引

| 能力 | 主要文件 |
|------|----------|
| Agent 注册与编排 | `backend/app/services/agents/`（base, registry, executor, coordinator, options_*） |
| AIService / 报告模型解析 | `backend/app/services/ai_service.py` |
| Deep Research 实现 | `backend/app/services/ai/gemini_provider.py`（generate_deep_research_report, _call_gemini_with_search） |
| 任务阶段与报告写入 | `backend/app/api/endpoints/tasks.py`（_handle_multi_agent_report_task, _run_data_enrichment, _get_multi_agent_stages_initial） |
| 报告 API / 配额 | `backend/app/api/endpoints/ai.py`（report, reports, get_ai_quota_limit, check_ai_quota） |
| 出图 | `backend/app/services/ai/image_provider.py`；任务处理在 `tasks.py`（generate_strategy_chart） |
| 报告模型 / 出图模型常量 | `backend/app/core/constants.py`（REPORT_MODELS, IMAGE_MODELS） |
| 管理端 AI 模型默认值 | `backend/app/api/admin.py`（ai-models-defaults）；配置键 ai_report_models_json, ai_image_models_json |

---

*本报告与现有实现保持一致；若后续增加新 Agent、新阶段或新的报告/出图模型，建议同步更新此文档。*
