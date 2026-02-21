# 每日精选（Daily Picks）流程与 AI 能力说明

## 一、整体流程（3 步）

```
Step 1: Multi-Agent 选股 → 得到 ranked_stocks（取 top 3）
Step 2: 对每个 symbol 用 Tiger + StrategyEngine 构建一个期权策略（无 AI）
Step 3: 用 Gemini 生成卡片文案（headline / analysis / risks）
```

---

## 二、Step 1：选股是怎么筛的？

Step 1 调用 `agent_coordinator.coordinate_stock_screening(criteria)`，内部是 **3 个 Phase**。

### Phase 1：初筛（StockScreeningAgent）— **无 AI**

- **数据来源**：FMP API（`MarketDataService.search_tickers`），按 sector / industry / **market_cap** / country 查股票列表。
- **筛选逻辑（全是规则）**：
  - `market_cap`: 每日精选固定为 `"Large Cap"`
  - `min_volume`: 1,500,000，用 FMP 批量 quotes 过滤成交量
  - `earnings_days_ahead`: 5，只保留「未来 5 天内有财报」的股票（FMP earnings calendar）
  - `limit`: 10，最后只保留前 10 个
- **输出**：`candidates` = `[{ symbol, initial_score: 0.5 }, ...]`，**没有真正打分**，只是名单。

结论：**初筛 = FMP 数据 + 规则过滤，没有 AI 参与。**

---

### Phase 2：逐个候选做「基本面 + 技术面」分析 — **有 AI（仅文案）**

对 Phase 1 的每个 candidate，并行跑两个 Agent：

| Agent | 数据从哪来 | 是否调 AI | 分数从哪来 |
|-------|------------|-----------|------------|
| **FundamentalAnalyst** | FMP `get_financial_profile`（财务、估值、DuPont 等） | ✅ 调 Gemini：生成「基本面分析」文字 | **health_score** 来自 FMP profile 里已有的 `analysis.health_score`，**不是 AI 打的** |
| **TechnicalAnalyst** | FMP profile 里的 `technical_indicators`、`analysis` | ✅ 调 Gemini：生成「技术分析」文字 | **technical_score** 由代码里 `_calculate_technical_score()` **规则计算**（RSI/ADX/信号等），**不是 AI 打的** |

所以：Phase 2 里 **AI 只产出「分析文案」**，**不产出排序用的分数**；排序用的 fundamental/technical 分数都是**规则或 FMP 已有字段**。

---

### Phase 3：排名（StockRankingAgent）— **AI 选股（真正用 AI 排序）**

- **AI 负责排序**：把 Phase 2 的**完整分析文案**（基本面 + 技术面文字与分数）拼成 prompt，要求 Gemini 输出**严格 JSON**：`ranked_stocks` 数组，每项含 `symbol`、`composite_score`、`fundamental_score`、`technical_score`、`reason`，**按推荐顺序从好到差**。
- **解析 AI 输出**：解析 JSON，校验 symbol 与候选一致，得到 `ranked_stocks` 作为每日精选的排序结果。
- **回退**：若 AI 返回非 JSON、缺字段或解析失败，则回退到规则 `_calculate_composite_scores`（按 health_score + technical_score 平均排序）。

结论：**默认谁排前面、谁进 top 3 由 AI 根据基本面+技术面分析综合决定；仅当 AI 不可用时才用规则排序。**

---

## 三、Step 2：策略构建 — **无 AI**

- 对 top 3 的每个 symbol：
  - 用 **Tiger API** 拉期权链（下周五到期）。
  - **Outlook**（BULLISH/BEARISH/NEUTRAL）由规则定：  
    `technical_score >= 7 and fundamental_score >= 6 → BULLISH`，  
    `technical_score <= 3 and fundamental_score <= 4 → BEARISH`，否则 NEUTRAL。
  - 用 **StrategyEngine**（规则引擎）根据 outlook + 期权链生成一个策略（如 Iron Condor、Bull Call Spread），得到 legs、metrics（max_profit、max_loss 等）。

结论：**策略类型、腿、盈亏数字都是规则算的，没有 AI。**

---

## 四、Step 3：卡片文案 — **有 AI**

- 用 **Gemini** 根据「策略 + candidate 分数」生成：
  - headline  
  - analysis（2–3 句）  
  - risks  
  - risk_level、confidence_score 等
- 再通过 `_normalize_pick_for_frontend` 拼成前端需要的 `headline`、`analysis`、`max_profit`、`max_loss` 等。

结论：**你看到的「分析文案」是 AI 写的；数字（max_profit/max_loss）来自 Step 2 的 StrategyEngine。**

---

## 五、总结表

| 环节 | 是否用 AI | 说明 |
|------|-----------|------|
| 初筛（谁进候选池） | ❌ | FMP + 规则（市值/成交量/财报） |
| 基本面/技术面「分数」 | ❌ | health_score 来自 FMP；technical_score 规则计算 |
| 基本面/技术面「文字」 | ✅ | Gemini 生成 |
| **排名与 composite_score** | **✅** | **AI 根据分析全文输出 ranked_stocks（含 composite_score、reason）；解析失败时回退规则** |
| 策略类型与 legs / metrics | ❌ | StrategyEngine 规则 |
| 卡片 headline/analysis/risks | ✅ | Gemini 生成 |

**一句话**：  
**选股池 = FMP + 规则；谁排第几、谁进 top 3 = AI 根据基本面+技术面分析综合排序（JSON）；卡片文案 = Gemini。**  
仅当 AI 排名解析失败时才用规则（health + technical 平均）排序。
