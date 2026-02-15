# Company Data: Overview vs Full fundamentals 定位与设计

## 一、当前两 Tab 的差异（事实）

### 1. Overview（第一个 Tab）

**数据来源**：`/api/v1/company-data/full?modules=overview,valuation,ratios,analyst,charts`  
后端 `FundamentalDataService` 按模块调 FMP 多个接口，拼成一份数据。

| 区块 | 展示内容 | 后端 FMP 接口 | 实际情况 |
|-----|----------|----------------|----------|
| Overview | 公司名、Price、Change%、Market Cap、Beta、1D/5D/1M/3M/6M/1Y 涨跌幅 | profile, quote, stock-price-change | quote/profile 常有；stock-price-change 等常空 |
| Valuation & DCF | DCF value、Levered DCF | discounted-cash-flow, levered-discounted-cash-flow, enterprise-values | **经常空**（Premium/限流） |
| Ratios & key metrics | PE、PB、ROE、Debt/Equity、financial_scores | key-metrics-ttm, ratios-ttm, financial-scores | 部分标的有，很多 "—" |
| Analyst | Target (median)、Recommendation | price-target-consensus, grades-consensus 等 | **经常空** |
| Market Data | K 线图 | **非 FMP**：`/api/v1/market/history`（Tiger/行情） | 稳定有 |
| Peers | 相关标的 | stock-peers | 有时有 |

问题：**很多卡片依赖的 FMP 接口经常无数据**，页面上大量 "—" 和空区块，体验像「半成品」。

---

### 2. Full fundamentals（第二个 Tab）

**数据来源**：`getFinancialProfile` → `MarketDataService.get_financial_profile()`（Strategy Lab 同款）  
一次大请求，FinanceToolkit + FMP 回退，耗时长（30–60s），数据更全。

| 内容 | 说明 |
|------|------|
| 子 Tab | Financial Ratios · Statements · Valuation · Analysis · Technical & Risk · Profile |
| 数据形态 | 多年度表格、比率图表、财报科目、估值模型、技术/风险等 |
| 定位 | 「深度研究用」的完整基本面，和 Strategy Lab 弹窗一致 |

问题：**不重复**；和 Overview 的差异是「深度 vs 速览」。真正需要重新设计的是 **Overview 该展示什么、展示多少**。

---

## 二、两 Tab 应有的定位（建议）

| | Overview | Full fundamentals |
|--|----------|--------------------|
| **目标** | 一眼看清：这是什么公司、现在什么价、近期走势、有没有更多可点 | 做决策/写报告时查：比率、财报、估值、技术面 |
| **数据** | 只展示**我们能稳定拿到**的内容，宁少勿空 | 接受长加载，展示能拿到的全部深度数据 |
| **用户动作** | 扫一眼 → 需要再点「Full fundamentals」 | 在 Tab 内切换 Ratios / Statements / Valuation 等 |

所以：**Overview 不要和 Full fundamentals 抢「深度」；Overview 做「速览 + 入口」，且尽量不出现大块空白。**

---

## 三、Overview 重新设计方向（讨论用）

### 方案 A：极简可靠型（推荐）

**只保留「大概率有数据」的区块，其余不展示或收起到「更多」里。**

- **保留并突出：**
  - **公司名 + 行情一行**：Price、Change%、Market Cap（来自 profile/quote，通常有）
  - **Market Data**：K 线图（来自 market/history，稳定）
  - **Peers**：有则展示，无则整块不渲染
- **弱化或条件展示：**
  - **Valuation / Ratios / Analyst**：  
    仅当**至少有一个子项有有效值**时才渲染对应卡片；若全空，不显示该卡片，避免一屏 "—"。
- **可选**：在顶部加一句短文案，如「深度比率与财报见 Full fundamentals」，并带跳转/高亮到第二个 Tab。

这样 Overview 页「有就有、没有就不画」，不会出现「DCF —」「Target —」这种无信息区块。

---

### 方案 B：单屏入口型

Overview 只做「一屏」：

- 公司名、价格、涨跌、市值（1 行）
- 一张 **Market Data** 图
- 一句 CTA：「查看完整比率、财报与估值 → Full fundamentals」

不做 Valuation/Ratios/Analyst 卡片，全部深度内容都在 Full fundamentals。  
优点：逻辑最简单、不会出现空卡片；缺点：Overview 信息量偏少，若用户期望「至少看到 PE/目标价」需要点一下 Tab。

---

### 方案 C：按数据动态组版

- 仍然请求 `overview, valuation, ratios, analyst`（或按需减模块以省配额）。
- 前端**按返回结果动态决定**展示哪些卡片：  
  例如只有 `ratios` 里 PE 有值就只展示「关键比率」一张小卡（PE/PB/ROE 等能算出来的）；  
  DCF、Analyst 全空则完全不画 Valuation / Analyst 区块。
- 顶部固定：公司名 + 行情 + Market Data 图；下面若干「有数据才出现」的卡片 + Peers。

兼顾「能展示的尽量展示」和「不展示空壳」，但前端逻辑稍复杂（字段多、key 不统一时要做好兼容）。

---

## 四、需要你拍板的点

1. **Overview 目标**：更偏向「极简入口」（方案 B）还是「能展示的都展示，但不展示空的」（方案 A/C）？
2. **Quota 与请求**：若 Overview 不再展示 Valuation/Analyst，是否还要默认请求 `valuation, analyst` 模块？（不请求可省配额、减少无效展示）
3. **Copy**：是否在 Overview 明确写一句「深度数据见 Full fundamentals」，并引导点击第二个 Tab？
4. **Peers / 其它**：Peers 是否保留在 Overview；是否还需要「价格区间（如 52w 高/低）」等（若 quote/profile 有就展示）？

你定一个方向（A/B/C 或混合），我可以按该方向给出具体字段清单和前端改动点（哪些卡片保留、哪些条件渲染、接口是否减模块）。

---

## 五、已实现：方案 C + 核心数据（2025-02）

### 定位

- **Overview**：FMP 核心、一眼能用的「速览」；只展示有数据的区块（方案 C）。
- **Full fundamentals**：不变；深度比率/报表/估值/技术面。

### Overview 核心数据（FMP 独有或 headline）

| 数据 | 来源 | 说明 |
|------|------|------|
| 公司名 / 价格 / 涨跌% / 市值 / Beta | profile, quote | 多 key 回退（companyName/Company Name, price/Price, mktCap/marketCap 等） |
| **Next earnings** | earnings-calendar（overview 内拉取） | 下一财报日 + EPS 预估；期权/催化剂的独有信息 |
| 1D/5D/1M/3M/6M/1Y 涨跌幅 | stock-price-change | 有任一周期才展示整块 |
| DCF / Levered DCF | valuation | 有任一才展示 Valuation 卡片 |
| PE / PB / ROE / Debt/Equity、financial_scores | ratios (key-metrics-ttm, ratios-ttm, financial-scores) | 有任一才展示 Key ratios 卡片 |
| 目标价中位数 / 推荐 | analyst (price-target-consensus, grades-consensus 等) | 有任一才展示 Analyst 卡片 |
| K 线图 | market/history（非 FMP） | 始终展示 |
| Peers | stock-peers | 有则展示 |

### 实现要点

- **有数据才展示**：Overview 卡片仅当至少一个字段有有效值时才渲染；Valuation/Ratios/Analyst 同理。
- **FMP key 回退**：profile/quote/ratios/analyst 多种 FMP 返回 key（如 peRatioTTM、priceToEarningsRatioTTM）均做兼容。
- **Next earnings**：后端 `fetch_overview` 内请求 earnings-calendar（from today, to+90d），按 symbol 取第一条写入 `overview.next_earnings`；前端有 date/earningsDate 或 epsEstimated 时展示一行。

---

## 六、相关设计文档

- **[COMPANY_DATA_ENHANCEMENT_DESIGN.md](./COMPANY_DATA_ENHANCEMENT_DESIGN.md)**：Company Data 页面 Phase 1–3 增强设计（新闻、日历、财报、SEC、公式说明等），Full fundamentals 保持不动。
