# 多智能体 + Deep Research 设计实现检查清单

对照 `MULTI_AGENT_DEEP_RESEARCH_DESIGN.md` 的逐项实现状态（检查时间：按当前代码库）。

---

## 一、Data Enrichment（§2.2 任务执行前补齐）

| 项 | 设计要求 | 实现位置 | 状态 |
|----|----------|----------|------|
| fundamental_profile | get_financial_profile → strategy_summary.fundamental_profile | tasks.py `_run_data_enrichment` | ✅ |
| analyst_data | estimates + price_target → strategy_summary.analyst_data | tasks.py `_run_data_enrichment` | ✅ |
| iv_context | 历史波动率/IV → strategy_summary.iv_context | tasks.py `_run_data_enrichment`（从 fundamental_profile.volatility 提取） | ✅ |
| upcoming_events / catalyst | FMP earnings calendar → strategy_summary.upcoming_events, catalyst | tasks.py `_run_data_enrichment`（v3/earning_calendar） | ✅ |
| historical_prices | 缺失时拉取近 60 日日线 → strategy_summary.historical_prices | tasks.py `_run_data_enrichment`（get_historical_data） | ✅ |
| sentiment / market_sentiment | FMP 新闻 → strategy_summary.sentiment, market_sentiment | tasks.py `_run_data_enrichment`（v3/stock_news） | ✅ |
| option_chain 缺失 | 任务开始时用 Tiger 拉取 option_chain | tasks.py multi_agent_report 分支（get_option_chain） | ✅ |

---

## 二、流水线（§3.1）

| 阶段 | 设计 | 实现 | 状态 |
|------|------|------|------|
| 顺序 | Data Enrichment → Phase A → Phase A+ → Phase B | tasks.py multi_agent_report 分支 | ✅ |
| Phase A | 多智能体 Coordinator | ai_service.generate_report_with_agents | ✅ |
| Phase A+ | 系统推荐策略 1～2 个 | ai_service.generate_strategy_recommendations（gemini ±25% spot 过滤） | ✅ |
| Phase B | Deep Research Planning → Research → Synthesis | ai_service.generate_deep_research_report | ✅ |
| 报告三部分 | 标的基本面 + 用户策略点评 + 系统推荐策略 | gemini_provider 三部分结构 + recommended_strategies 格式化 | ✅ |

---

## 三、任务系统（§5）

| 项 | 设计 | 实现 | 状态 |
|----|------|------|------|
| task_metadata.stages | 含 id/name/status/started_at/ended_at/message，phase_a 与 phase_b 含 sub_stages | tasks.py `_get_multi_agent_stages_initial`、`_update_stage`，各阶段边界更新 | ✅ |
| task_metadata.progress | 0～100，各阶段回调更新 | tasks.py `_emit_progress`（0-5, 5-45, 45-50, 50-100） | ✅ |
| task_metadata.current_stage | 人类可读当前步骤 | 同上 | ✅ |
| agent_summaries | Phase A 结束后写入 | tasks.py 写入 task_metadata | ✅ |
| recommended_strategies | Phase A+ 结束后写入 | tasks.py 写入 task_metadata | ✅ |
| research_questions | Phase B Planning 后写入 | tasks.py 从 phase_b_result 写入 task_metadata | ✅ |
| 任务详情页（§5.3） | 进度、stages、摘要、研究问题、查看报告 | TaskDetailPage：progress、stages（含 sub_stages/时间）、research_questions、agent_summaries、「View Report」 | ✅ |

---

## 四、重试与超时（§5.5）

| 项 | 设计 | 实现 | 状态 |
|----|------|------|------|
| Data Enrichment 重试 | 失败可重试 1～2 次 | tasks.py 对 _run_data_enrichment 循环 2 次，失败则阶段 failed 并抛错 | ✅ |
| Phase A 超时 | 总超时 5 分钟 | tasks.py asyncio.wait_for(..., timeout=300) | ✅ |
| Phase B 超时 | 总超时 8 分钟 | tasks.py asyncio.wait_for(..., timeout=480) | ✅ |
| Phase A 某 agent 重试 | 可选：该 agent 重试 1 次 | 未实现（设计为可选） | ⚪ 可选 |
| Phase B 某步重试 | Planning/Research/Synthesis 可对该步重试 1～2 次 | 未实现（仅整体超时） | ⚪ 可选 |

---

## 五、单次报告兜底（§6.4）与 Prompt 配置（§6.5）

| 项 | 设计 | 实现 | 状态 |
|----|------|------|------|
| 单次 Report 增强 | Input 明确 Tiger/FMP 数据必须使用；顺序：市场/IV → Greeks/风险 → Verdict | gemini_provider DEFAULT_REPORT_PROMPT_TEMPLATE（来自 prompts.py） | ✅ |
| ai_report 也做 Data Enrichment | 单次报告路径也补齐 FMP 数据 | tasks.py ai_report 分支调用 _run_data_enrichment | ✅ |
| _format_prompt 带 FMP 数据 | 注入 fundamental_profile、iv_context、analyst_data | gemini_provider _format_prompt 写入 complete_strategy_data | ✅ |
| Prompt 版本与配置 | 模板集中、带版本（如 report_template_v1） | app/core/prompts.py（PROMPTS、get_prompt）、gemini_provider 引用 | ✅ |

---

## 六、One-Click Load 推荐策略（§3.4 体验）

| 项 | 设计 | 实现 | 状态 |
|----|------|------|------|
| 按报告查来源任务 | 根据 result_ref=reportId 查任务 | 后端 GET /tasks?result_ref=xxx；前端 taskService.getTasks({ result_ref }) | ✅ |
| 报告页展示推荐策略 | 展示 recommended_strategies，每条可「Load to Strategy Lab」 | ReportDetailPage：sourceTask、recommendedStrategies、System-Recommended Strategies 卡片 + 按钮 | ✅ |
| Strategy Lab 接收并加载 | 跳转时带 loadRecommended，Strategy Lab 填 symbol/expiration/legs | StrategyLab：useLocation、location.state.loadRecommended、useEffect 填表并 navigate replace 清 state | ✅ |

---

## 七、Deep Research 改造（§4）

| 项 | 设计 | 实现 | 状态 |
|----|------|------|------|
| Planning 输入 | strategy_summary + option_chain 摘要 + agent_summaries | gemini_provider generate_deep_research_report Planning 段 | ✅ |
| Planning 要求 | 基于内部分析提 4 个需 Google 搜索的问题 | prompt 中明确 | ✅ |
| Synthesis 输入 | agent_summaries + research_findings + strategy_summary + recommended_strategies | 同上 Synthesis 段 | ✅ |
| Synthesis 结构 | Executive Summary + Internal Expert + External Research + Synthesis & Verdict | prompt 中三部分 + 可选 Executive Summary | ✅ |

---

## 总结

- **已全部实现**：Data Enrichment（含 iv/upcoming_events/historical_prices/sentiment）、option_chain 缺失时 Tiger 拉取、流水线四阶段、三部分报告、task_metadata.stages（含 sub_stages/时间）、任务详情页展示、Data Enrichment 重试、Phase A/B 超时、单次报告兜底 + prompt 配置、One-Click Load（API + ReportDetailPage + StrategyLab）、Deep Research 输入与三部分结构。
- **可选未实现**：Phase A 单 agent 重试、Phase B 单步（Planning/Research/Synthesis）重试、task_metadata.workflow_results（设计为可选）。

若你需要，我可以再针对「Phase B 单步重试」或「workflow_results」给出具体实现方案或补丁。
