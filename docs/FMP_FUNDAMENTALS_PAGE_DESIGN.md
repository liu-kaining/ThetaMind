# Company Fundamentals & Financial Data Page — Design Specification

## 1. Objectives & Constraints

### 1.1 Goals
- Add a **new, standalone page** for querying company financial and stock data, turning ThetaMind into a professional **company fundamental data query platform** to attract more users.
- All data on this page is fetched **directly from FMP API**; maximize use of the **Premium** plan ($59/mo: US + UK + Canada, 750 calls/min, 30 years history, full fundamentals, intraday, technicals, DCF, etc.).
- **No changes to existing features** (Strategy Lab, Option Chain, AI reports, etc.) — production users must not be affected.

### 1.2 Access Control (Quota)
| User Type | Daily Quota | Notes |
|-----------|-------------|--------|
| Free      | 2 queries   | Per calendar day (UTC). |
| Pro       | 100 queries | Same reset logic. |

- **One “query”** = one full load of a **single symbol** (one company lookup). Viewing another symbol or refreshing after cache expiry counts as another query.
- Quota is **consumed only when the user triggers a new symbol load** (search and select a symbol, or open a symbol from history). Repeated views of the same symbol within a short cache window do **not** consume additional quota.
- Quota reset: same as existing `daily_ai_usage` (e.g. midnight UTC or per-user `last_quota_reset_date`).

---

## 2. Product Overview

### 2.1 Entry Point
- **New menu item** in the main navigation (e.g. **“Company Data”** or **“Fundamentals”**).
- **Route**: e.g. `/company-data` or `/fundamentals` (no conflict with existing routes).
- **Auth**: Page is available to all logged-in users; quota applies. Optional: allow anonymous with 0 quota (show upgrade CTA) or require login.

### 2.2 Core Flow
1. User lands on the new page.
2. **Search / symbol entry**: Search by **symbol** or **company name** (FMP Symbol Search + Name Search). Display results; user selects one symbol.
3. **Quota check**: Before loading data, backend checks `daily_fundamental_queries_used < limit` (2 or 100). If over limit, return 403 with a clear message and “Upgrade” CTA.
4. **Load data**: Backend calls multiple FMP endpoints for the chosen symbol (see Section 4), aggregates, and returns one structured payload (or multiple sub-endpoints for progressive loading).
5. **Display**: Single-page layout with sections (Overview, Statements, Ratios, Analyst, Charts, etc.). All data is read-only and for informational use.

### 2.3 Caching (Important for Quota & FMP)
- **Server-side cache** (e.g. Redis or in-memory) keyed by `symbol` (and optionally by endpoint or section).
- **TTL**: e.g. 5–15 minutes for quote/profile; 1–24 hours for statements/ratios (configurable).
- **Quota**: Deduct only when **cache miss** (i.e. when we actually call FMP for this symbol in this day). Same symbol within TTL = no extra quota.
- **Existing Strategy Lab / other features**: Unchanged; they do not use this quota and continue to use current MarketDataService behavior.

---

## 3. FMP 数据获取清单（全量、分模块、专业呈现）

设计原则：**指标完善、专业、有冲击力** — 让用户明确感受到「查到的数据非常准确、完备、有价值」。数据按**模块**获取，支持**分模块加载**或**后台任务逐模块拉取**，避免单次请求过长；FMP Premium **750 次/分钟** 限制足够支撑多模块并行/串行调用。  
参考：[FMP Datasets](https://site.financialmodelingprep.com/datasets) | [FMP Developer Docs](https://site.financialmodelingprep.com/developer/docs)  
Base URL: `https://financialmodelingprep.com/stable/`

---

### 3.1 搜索与目录（不扣配额，仅搜索时用）

| FMP Endpoint | 用途 |
|--------------|------|
| `search-symbol?query=` | 按代码搜索（如 AAPL、VST） |
| `search-name?query=` | 按公司名搜索（如 Apple、Vistra） |
| `search-cik?cik=` | 按 CIK 搜索（SEC） |
| `search-cusip?cusip=` | 按 CUSIP 搜索 |
| `search-isin?isin=` | 按 ISIN 搜索 |
| `search-exchange-variants?symbol=` | 某标的在不同交易所的代码 |
| `company-screener` | 筛选：市值、价格、成交量、beta、sector、country 等 |
| `available-exchanges` | 交易所列表（筛选/标签） |
| `available-sectors` | 板块列表 |
| `available-industries` | 行业列表 |
| `available-countries` | 国家列表 |

---

### 3.2 模块 A：公司概览（Overview）— 首屏必加载

| FMP Endpoint | 数据内容 |
|--------------|----------|
| `profile?symbol=` | 公司名、sector、industry、exchange、描述、CEO、员工数、市值、beta、价格、网站、logo 等 |
| `profile-cik?cik=` | 按 CIK 取 profile（有 CIK 时备用） |
| `quote?symbol=` | 实时价、涨跌、涨跌幅、open/high/low、volume、52w 高低等 |
| `quote-short?symbol=` | 精简 quote（备选） |
| `stock-price-change?symbol=` | 1d/5d/1m/3m/6m/1y/5y 涨跌幅 |
| `market-capitalization?symbol=` | 当前市值（可补 profile） |
| `historical-market-capitalization?symbol=` | 历史市值曲线 |
| `shares-float?symbol=` | 流通股、总股本、float 等 |
| `stock-peers?symbol=` | 同业对标标的列表 |
| `company-notes?symbol=` | 公司票据信息（如有） |

---

### 3.3 模块 B：估值与 DCF（Valuation）

| FMP Endpoint | 数据内容 |
|--------------|----------|
| `discounted-cash-flow?symbol=` | DCF 估值、隐含股价 |
| `levered-discounted-cash-flow?symbol=` | 杠杆 DCF |
| `custom-discounted-cash-flow?symbol=` | 自定义假设 DCF（高级） |
| `custom-levered-discounted-cash-flow?symbol=` | 自定义杠杆 DCF |
| `enterprise-values?symbol=` | 历史 EV（企业价值） |

---

### 3.4 模块 C：财务报表（Financial Statements）— 核心专业数据

| FMP Endpoint | 数据内容 |
|--------------|----------|
| `income-statement?symbol=` | 利润表（年/季） |
| `balance-sheet-statement?symbol=` | 资产负债表（年/季） |
| `cash-flow-statement?symbol=` | 现金流量表（年/季） |
| `income-statement-ttm?symbol=` | 利润表 TTM |
| `balance-sheet-statement-ttm?symbol=` | 资产负债表 TTM |
| `cash-flow-statement-ttm?symbol=` | 现金流 TTM |
| `income-statement-growth?symbol=` | 利润表增长率（收入、利润等） |
| `balance-sheet-statement-growth?symbol=` | 资产负债表增长率 |
| `cash-flow-statement-growth?symbol=` | 现金流增长率 |
| `financial-growth?symbol=` | 综合财务增长指标 |
| `financial-reports-dates?symbol=` | 财报披露日期 |
| `latest-financial-statements?page=&limit=` | 最新财报摘要（可按 symbol 过滤） |
| `financial-reports-json?symbol=&year=&period=` | 10-K/10-Q 结构化 JSON（可选） |
| `financial-reports-xlsx?symbol=&year=&period=` | 10-K XLSX 下载链接（可选） |
| `revenue-product-segmentation?symbol=` | 收入产品分部 |
| `revenue-geographic-segmentation?symbol=` | 收入地区分部 |
| `income-statement-as-reported?symbol=` | 利润表 As Reported |
| `balance-sheet-statement-as-reported?symbol=` | 资产负债表 As Reported |
| `cash-flow-statement-as-reported?symbol=` | 现金流 As Reported |
| `financial-statement-full-as-reported?symbol=` | 完整 As Reported 三表 |

---

### 3.5 模块 D：比率与关键指标（Ratios & Key Metrics）— 专业指标集中展示

| FMP Endpoint | 数据内容 |
|--------------|----------|
| `key-metrics?symbol=` | 历史关键指标（PE、PB、ROE、ROA、毛利率等） |
| `ratios?symbol=` | 历史比率（盈利能力、流动性、杠杆、效率等） |
| `key-metrics-ttm?symbol=` | TTM 关键指标 |
| `ratios-ttm?symbol=` | TTM 比率 |
| `financial-scores?symbol=` | Altman Z-Score、Piotroski Score 等健康度评分 |
| `owner-earnings?symbol=` | 巴菲特「所有者收益」 |
| `enterprise-values?symbol=` | 企业价值（也可放在 Valuation 模块） |

---

### 3.6 模块 E：分析师与评级（Analyst & Ratings）

| FMP Endpoint | 数据内容 |
|--------------|----------|
| `analyst-estimates?symbol=&period=annual|quarter` | 分析师预测：EPS、收入等（年/季） |
| `price-target-summary?symbol=` | 目标价汇总（多时间维度） |
| `price-target-consensus?symbol=` | 目标价共识（高/低/中位数/共识） |
| `grades?symbol=` | 分析师评级动态（上调/下调/维持） |
| `grades-historical?symbol=` | 历史评级 |
| `grades-consensus?symbol=` | 评级共识（强买/买/持有/卖/强卖数量） |
| `ratings-snapshot?symbol=` | 财务健康评级快照 |
| `ratings-historical?symbol=` | 历史评级 |

---

### 3.7 模块 F：行情与图表（Market Data & Charts）

| FMP Endpoint | 数据内容 |
|--------------|----------|
| `historical-price-eod/light?symbol=` | EOD 日线（简版：date, close, volume） |
| `historical-price-eod/full?symbol=` | EOD 日线（OHLC、volume、change%、VWAP 等） |
| `historical-price-eod/dividend-adjusted?symbol=` | 股息调整后价格 |
| `historical-price-eod/non-split-adjusted?symbol=` | 未拆股调整价格（可选） |
| `historical-chart/1min?symbol=` | 1 分钟 K 线（Premium 盘内） |
| `historical-chart/5min?symbol=` | 5 分钟 |
| `historical-chart/15min?symbol=` | 15 分钟 |
| `historical-chart/30min?symbol=` | 30 分钟 |
| `historical-chart/1hour?symbol=` | 1 小时 |
| `historical-chart/4hour?symbol=` | 4 小时 |
| `technical-indicators/sma?symbol=&periodLength=&timeframe=` | 简单移动平均 |
| `technical-indicators/ema?symbol=` | 指数移动平均 |
| `technical-indicators/wma?symbol=` | 加权移动平均 |
| `technical-indicators/dema?symbol=` | 双指数移动平均 |
| `technical-indicators/tema?symbol=` | 三指数移动平均 |
| `technical-indicators/rsi?symbol=` | RSI |
| `technical-indicators/standarddeviation?symbol=` | 标准差 |
| `technical-indicators/williams?symbol=` | 威廉指标 |
| `technical-indicators/adx?symbol=` | ADX |

---

### 3.8 模块 G：股息、拆股与回购

| FMP Endpoint | 数据内容 |
|--------------|----------|
| `dividends?symbol=` | 股息历史（日期、金额、类型等） |
| `dividends-calendar` | 股息日历（可按 symbol 过滤前端） |
| `splits?symbol=` | 拆股/合股历史 |
| `splits-calendar` | 拆股日历 |

---

### 3.9 模块 H：财报、业绩与重大事件

| FMP Endpoint | 数据内容 |
|--------------|----------|
| `earnings?symbol=` | 历史业绩（EPS、预期、实际、surprise 等） |
| `earnings-calendar` | 业绩日历（可按 symbol 过滤） |
| `mergers-acquisitions-search?name=` | M&A 搜索（公司名/标的） |
| `mergers-acquisitions-latest?page=&limit=` | 最新 M&A（可筛与当前 symbol 相关） |
| `earning-call-transcript-dates?symbol=` | 业绩会电话会日期 |
| `earning-call-transcript?symbol=&year=&quarter=` | 业绩会文字稿（按需加载） |
| `earnings-transcript-list` | 有 transcript 的标的列表（可选） |

---

### 3.10 模块 I：新闻与公告

| FMP Endpoint | 数据内容 |
|--------------|----------|
| `news/stock?symbols=` | 按标的搜股票新闻 |
| `news/stock-latest?page=&limit=` | 最新股票新闻（可配合 symbol 筛选） |
| `news/press-releases?symbols=` | 公司新闻/公告 |
| `news/press-releases-latest?page=&limit=` | 最新公告（可筛） |
| `fmp-articles?page=&limit=` | FMP 站内文章（可选） |

---

### 3.11 模块 J：公司治理与高管（Governance）

| FMP Endpoint | 数据内容 |
|--------------|----------|
| `key-executives?symbol=` | 高管名单（姓名、职位、薪酬等） |
| `governance-executive-compensation?symbol=` | 高管薪酬明细（美国） |
| `employee-count?symbol=` | 员工数（当前） |
| `historical-employee-count?symbol=` | 历史员工数 |

---

### 3.12 模块 K：机构持仓与 13F（Institutional Ownership）

| FMP Endpoint | 数据内容 |
|--------------|----------|
| `institutional-ownership/symbol-positions-summary?symbol=&year=&quarter=` | 该标的机构持仓汇总 |
| `institutional-ownership/extract-analytics/holder?symbol=&year=&quarter=` | 持仓机构及变动分析 |
| `institutional-ownership/latest?page=&limit=` | 最新 13F 申报（可筛） |
| `institutional-ownership/dates?cik=` | 某 CIK 的 13F 申报日期（需先有 CIK） |

---

### 3.13 模块 L：内部人交易（Insider Trading）

| FMP Endpoint | 数据内容 |
|--------------|----------|
| `insider-trading/search?symbol=&page=&limit=` | 按标的搜内部人交易 |
| `insider-trading/statistics?symbol=` | 内部人买卖统计 |
| `acquisition-of-beneficial-ownership?symbol=` | 受益所有权变动 |
| `insider-trading-transaction-type` | 交易类型列表（下拉/标签用） |

---

### 3.14 模块 M：SEC 申报（SEC Filings）

| FMP Endpoint | 数据内容 |
|--------------|----------|
| `sec-filings-search/symbol?symbol=&from=&to=` | 按标的查 8-K/10-K/10-Q 等 |
| `sec-filings-company-search/symbol?symbol=` | 公司 SEC 申报摘要 |
| `sec-filings-financials?from=&to=&page=&limit=` | 财报类申报列表 |
| `sec-filings-8k?from=&to=&page=&limit=` | 8-K 重大事件 |
| `sec-profile?symbol=` | SEC 公司档案（描述、高管等） |
| `industry-classification-search` / `all-industry-classification` | SIC/行业分类（可选） |

---

### 3.15 模块 N：ETF 持仓与资金流向（ETF Exposure）

| FMP Endpoint | 数据内容 |
|--------------|----------|
| `etf/asset-exposure?symbol=` | **哪些 ETF 持有该股票**（持仓权重、市值） |
| `etf/holdings?symbol=` | 某 ETF 的持仓（当标的为 ETF 时用） |
| `etf/info?symbol=` | ETF 基本信息（当标的为 ETF 时用） |
| `funds/disclosure-holders-latest?symbol=` | 基金/ETF 披露持仓（美国） |

---

### 3.16 模块 O：板块与行业表现（Sector / Industry Context）

| FMP Endpoint | 数据内容 |
|--------------|----------|
| `sector-performance-snapshot?date=` | 当日板块表现（公司所在 sector 对比） |
| `industry-performance-snapshot?date=` | 当日行业表现 |
| `historical-sector-performance?sector=` | 板块历史表现（公司所在 sector） |
| `historical-industry-performance?industry=` | 行业历史表现 |
| `sector-pe-snapshot?date=` | 板块 PE |
| `industry-pe-snapshot?date=` | 行业 PE |
| `historical-sector-pe?sector=` | 板块历史 PE |
| `historical-industry-pe?industry=` | 行业历史 PE |

---

### 3.17 模块 P：ESG（环境、社会与治理）

| FMP Endpoint | 数据内容 |
|--------------|----------|
| `esg-disclosures?symbol=` | ESG 披露 |
| `esg-ratings?symbol=` | ESG 评分 |
| `esg-benchmark` | ESG 基准对比（可选） |

---

### 3.18 模块 Q：国会交易（Senate / House — 美国）

| FMP Endpoint | 数据内容 |
|--------------|----------|
| `senate-trades?symbol=` | 参议员交易该标的记录 |
| `house-trades?symbol=` | 众议员交易该标的记录 |
| `senate-latest?page=&limit=` | 最新参议院披露（可筛） |
| `house-latest?page=&limit=` | 最新众议院披露（可筛） |

---

### 3.19 模块 R：盘前盘后（After-Hours）

| FMP Endpoint | 数据内容 |
|--------------|----------|
| `aftermarket-quote?symbol=` | 盘后报价 |
| `aftermarket-trade?symbol=` | 盘后成交（可选） |
| `batch-aftermarket-quote?symbols=` | 批量盘后报价 |

---

### 3.20 模块 S：退市与风险（可选）

| FMP Endpoint | 数据内容 |
|--------------|----------|
| `delisted-companies?page=&limit=` | 退市名单（用于标注或警示） |

---

### 3.21 模块 T：经济学与宏观（页面侧栏或全局，非按 symbol）

| FMP Endpoint | 数据内容 |
|--------------|----------|
| `treasury-rates` | 国债利率（估值参考） |
| `market-risk-premium` | 市场风险溢价 |
| `economic-indicators?name=` | 经济指标（GDP、通胀等） |
| `economic-calendar` | 经济数据发布日历 |

---

### 3.22 数据模块与加载策略小结

| 模块 | 建议加载顺序 | 预估 FMP 调用数 | 说明 |
|------|--------------|-----------------|------|
| A 概览 | 1（首屏） | ~8–10 | 必选，立即展示 |
| B 估值/DCF | 2 | ~4–5 | 首屏或紧随其后 |
| C 财务报表 | 2 或 3 | ~12–18 | 核心专业数据，可拆子模块 |
| D 比率与指标 | 2 或 3 | ~7 | 与 C 并行或接续 |
| E 分析师 | 3 | ~6–8 | 首屏后可异步 |
| F 行情图表 | 2 或 3 | 1–3（EOD）+ 可选 intraday + 技术指标 | 图表先 EOD，再按需 intraday/指标 |
| G 股息拆股 | 3 | ~2–4 | 异步 |
| H 业绩与事件 | 3 | ~4–6 | 异步 |
| I 新闻 | 3 | ~2–3 | 异步 |
| J 治理与高管 | 3 | ~3–4 | 异步 |
| K 机构持仓 | 4 | ~2–4 | 按需或异步 |
| L 内部人交易 | 4 | ~2–3 | 按需或异步 |
| M SEC 申报 | 4 | ~2–4 | 按需或异步 |
| N ETF 持仓 | 3 或 4 | ~2 | 异步 |
| O 板块行业 | 3 | ~2–4（用 profile 的 sector/industry） | 异步 |
| P ESG | 4 | ~2–3 | 按需或异步 |
| Q 国会交易 | 4 | ~2 | 按需（美国标的） |
| R 盘后 | 2 或 3 | ~1–2 | 可选 |
| S 退市 | 4 | 0–1 | 可选 |
| T 宏观 | 全局 1 次 | 1–2 | 页面级一次请求 |

- **首屏（约 20–30 次调用）**：A + B + D 部分 + F(EOD) + E 部分，保证「一眼看到专业、完备」。
- **第二波（懒加载/滚动或 Tab）**：C 全量、G、H、I、J、N、O、R。
- **第三波（按需展开）**：K、L、M、P、Q、S。
- 单标的全量拉满约 **80–120 次** FMP 调用，分 2–4 批、每批并行可控制在 750/min 内，且用户体验可做成「先核心后扩展」。

---

## 4. Backend API Design (New Only)

### 4.1 New Tables / Fields (Minimal)
- **User**: Add `daily_fundamental_queries_used: int` and optionally `last_fundamental_quota_reset_date: date` (or reuse existing quota reset logic with a new counter).
- **Optional**: `fundamental_queries_log` table (user_id, symbol, created_at) for analytics and abuse prevention; not required for MVP.

### 4.2 New API Endpoints (All Under e.g. `/api/v1/company-data` or `/api/v1/fundamentals`)

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/quota` | Yes | Return `{ used, limit, is_pro }` (2 or 100). |
| GET | `/search?q=...` | Yes | Proxy FMP search-symbol + search-name（+ 可选 search-cik/cusip/isin）；返回 `{ symbol, name, exchange }`。**不扣配额**。 |
| GET | `/overview?symbol=` | Yes | 扣配额（cache miss 时）；返回模块 A（概览）。可单独用于「只查概览」或首屏。 |
| GET | `/full?symbol=` | Yes | **推荐**：扣配额一次，返回多模块聚合 JSON。可带 query：`?modules=A,B,D,E,F` 只取指定模块，仍只扣 1 次配额（同 symbol 同日内）。 |
| GET | `/module/{module_id}?symbol=` | Yes | 按模块拉取（见 3.22 模块编号）。扣配额仅当该 symbol 今日首次被请求时；同一 symbol 后续只读缓存。`module_id` 例：`overview`, `valuation`, `statements`, `ratios`, `analyst`, `charts`, `dividends`, `earnings`, `news`, `governance`, `institutional`, `insider`, `sec`, `etf`, `sector`, `esg`, `congress`, `afterhours`。 |
| POST | `/load-task?symbol=` | Yes | **可选**：创建「后台加载任务」；立即返回 `task_id`。前端轮询 `GET /load-task/{task_id}` 取各模块完成状态与数据；适合「全量 80+ 调用」分批执行，不阻塞首屏。配额在任务创建时扣 1 次。 |

- **Quota 规则**：同一用户、同一 symbol、同一自然日（UTC）只扣 **1 次** 配额；不论用 `/full`、`/overview` 还是 `/module/xxx` 或 `/load-task`，只要该 symbol 今日已有缓存或已扣过配额，则不再扣。
- **Cache**：按 `(symbol, module_id)` 或 `(symbol, full)` 缓存；TTL 建议概览/quote 短（5–15 min），报表/比率/分析师等长（1–24 h）。

### 4.3 FMP 调用策略（分模块、可任务化）
- **首屏**：只调模块 A（+ 可选 B、D 部分、F 的 EOD），约 20–30 次 FMP 调用，并行执行，控制在 750/min 内。
- **按模块拉取**：每个模块内部并行请求 FMP；模块之间可串行或按前端「Tab/展开」再请求，避免单次 80+ 并发。
- **任务式加载**：后端可启后台 job，按 3.22 顺序分批调用 FMP（如先 A/B/D/F/E，再 C/G/H/I/J/N/O，再 K/L/M/P/Q），结果写缓存并更新 task 状态；前端轮询或 WebSocket 取进度与数据。
- **Batching**：能用 batch 的用 batch（如 `batch-quote?symbols=`），减少请求数。
- **单接口失败**：单 FMP 接口失败只影响对应模块，返回 partial 数据 + 该模块 `error` 信息，不拖垮整页。

### 4.4 Quota Logic (Pseudocode)
```
limit = user.is_pro ? 100 : 2
# Reset daily (e.g. UTC midnight)
if user.last_fundamental_quota_reset_date < today_utc:
  user.daily_fundamental_queries_used = 0
  user.last_fundamental_quota_reset_date = today_utc

if user.daily_fundamental_queries_used >= limit:
  return 403, "Daily limit reached. Upgrade to Pro for 100 queries/day."

# On cache miss for this symbol today:
user.daily_fundamental_queries_used += 1
# then call FMP and return data
```

---

## 5. Frontend Page Structure（按模块展示，专业、完备、有冲击力）

单页布局（滚动 + Tab/手风琴），数据 100% 来自 FMP；**不改动** Strategy Lab 等现有页面。

### 5.1 页头
- **标题**：如「Company Data」/「公司数据」或「Fundamentals」/「基本面」。
- **搜索**：支持代码、公司名（FMP search-symbol + search-name）；可选 CIK/CUSIP/ISIN（高级）。
- **配额**：「今日已用 X / 2 次」（免费）或「X / 100 次」（Pro）；接近用尽时展示「升级」入口。
- **数据来源标识**：可标注「数据来源：Financial Modeling Prep」以增强专业感与可信度。

### 5.2 选定 Symbol 后的模块化展示（与 3.2–3.20 对应）

| 前端区块 | 对应模块 | 展示要点（尽量全、专业） |
|----------|----------|---------------------------|
| **概览** | A | 公司名、logo、sector/industry/exchange、描述、CEO、员工数、市值、beta、实时价、涨跌、成交量、52w 高低；1d/5d/1m/3m/6m/1y/5y 涨跌幅；流通股/总股本；**同业对标列表**（可点击跳转）；历史市值曲线（小图）。 |
| **估值与 DCF** | B | DCF 估值、杠杆 DCF、隐含股价；自定义 DCF 入口（高级）；历史 EV 表格/图。 |
| **财务报表** | C | **利润表/资产负债表/现金流量表**：年、季、TTM 切换；**增长表**（收入、利润、现金流同比等）；披露日期；**收入分部**（产品、地区）；可选 As Reported 三表、10-K/10-Q 链接。 |
| **比率与关键指标** | D | **TTM + 历史**：PE、PB、PS、ROE、ROA、毛利率、净利率、流动比率、速动比率、负债率、周转率等；**Altman Z-Score、Piotroski Score**；**所有者收益**。表格 + 可选迷你图趋势。 |
| **分析师与评级** | E | 分析师预测（EPS、收入，年/季）；目标价汇总与共识（高/低/中位）；**评级共识**（强买/买/持有/卖/强卖数量或占比）；历史评级与目标价；财务健康评级快照。 |
| **行情与图表** | F | **EOD 主图**（蜡烛/线）；可选股息调整、未拆股调整；**Intraday**（1m/5m/15m/1h/4h 切换）；**技术指标**：SMA/EMA/RSI/ADX 等叠加或副图。 |
| **股息与拆股** | G | 股息历史表（日期、金额、类型）；股息日历（即将派息）；拆股/合股历史；拆股日历。 |
| **业绩与事件** | H | 历史业绩表（EPS、预期、实际、surprise）；**业绩日历**（即将披露）；M&A 相关事件；**业绩会电话会**日期 + 按需展开文字稿。 |
| **新闻与公告** | I | 股票新闻列表（标题、摘要、来源、时间、链接）；公司公告/新闻稿。 |
| **公司治理与高管** | J | 高管名单（姓名、职位、薪酬等）；高管薪酬明细（美国）；当前及历史员工数。 |
| **机构持仓** | K | 该标的机构持仓汇总（持仓家数、变动）；主要机构及持仓变动；13F 相关链接或摘要。 |
| **内部人交易** | L | 内部人买卖记录表；买卖统计；受益所有权变动。 |
| **SEC 申报** | M | 8-K/10-K/10-Q 等申报列表（日期、类型、链接）；公司 SEC 档案摘要。 |
| **ETF 持仓** | N | **哪些 ETF 持有该股票**（ETF 名称、权重、持仓市值）；若标的为 ETF 则展示其持仓与信息。 |
| **板块与行业** | O | 公司所在 sector/industry 的当日与历史表现、PE 对比（与大盘或同业对比）。 |
| **ESG** | P | ESG 披露与评分；与行业/基准对比（若有）。 |
| **国会交易** | Q | 参议员/众议员交易该标的记录（美国）。 |
| **盘后** | R | 盘后报价与成交（若有）。 |
| **风险提示** | S | 若在退市名单中则提示。 |

- **首屏优先**：先渲染 A（概览）+ B（估值）+ D（比率）+ F（EOD 图）+ E（分析师摘要），再懒加载或 Tab 切换 C/G/H/I/J/N/O，最后按需展开 K/L/M/P/Q/R/S。
- **加载方式**：可用 `/full?symbol=&modules=A,B,D,F,E` 首屏；其余用 `/module/{id}?symbol=` 或后台任务 + 轮询，每块独立 skeleton/loading，**单块失败仅该块显示「暂无数据」或「暂时不可用」**。

### 5.3 UX 与合规
- **Loading**：每模块独立 skeleton 或 spinner；可选「全量加载进度条」当使用 load-task 时。
- **空/错误**：某模块无数据或 FMP 报错时，该块显示「暂无数据」或「暂时不可用」，不整页报错。
- **导出**（Phase 2）：表格支持 CSV/Excel 导出。
- **只读**：本页不提供交易、下单或策略创建；仅展示与导出数据。
- **数据来源**：页脚或区块内注明 FMP，增强「准确、完备、有价值」的感知。

---

## 6. 数据展示策略（表格·图表·链接·下载）

目标：**展示专业、有冲击力** — 该用表格用表格、该用曲线用曲线、该用饼图用饼图，配合链接与下载，让用户愿意用、愿意付费。与现有系统风格一致（Shadcn/UI、lightweight-charts、recharts），必要时可引入更专业的图表组件。

### 6.1 展示类型与使用场景

| 展示类型 | 适用场景 | 示例数据 |
|----------|----------|----------|
| **纯表格** | 多行多列、需精确读数、可排序/筛选 | 利润表、资产负债表、现金流、比率历史、业绩列表、股息历史、内部人交易、SEC 申报列表、高管名单 |
| **表格 + 迷你图（Sparkline）** | 表格中某一列需要看趋势 | 比率/指标表中的「近 N 期」趋势、每股收益/收入年度趋势 |
| **折线图 / 面积图** | 单变量或多变量随时间变化 | 股价 EOD、历史市值、EV、收入/利润趋势、现金流趋势、技术指标（SMA/EMA/RSI） |
| **蜡烛图** | 价格 OHLC、盘内/日线 | EOD 主图、1m/5m/15m/1h/4h 盘内 |
| **柱状图（Bar）** | 分类对比、占比、分布 | 分析师评级分布（强买/买/持有/卖/强卖）、收入分部（产品/地区）、板块/行业表现对比、年度收入/利润对比 |
| **饼图 / 环形图** | 构成占比 | 收入产品分部、收入地区分部、ETF 持仓权重（哪些 ETF 持有该股）、机构持仓占比 |
| **KPI 卡片 / 指标块** | 单值或少量关键数 | 概览中的市值/价格/涨跌、DCF 估值、目标价共识、Altman Z / Piotroski、当前 PE/PB |
| **链接 / 可下载** | 外链或导出 | SEC 申报链接、10-K/10-Q 原文、新闻链接、业绩会文字稿链接、导出 CSV/Excel/图表 PNG |

### 6.2 按模块的展示策略矩阵

| 模块 | 表格 | 曲线/面积 | 蜡烛图 | 柱状图 | 饼图/环形 | 迷你图 | KPI 卡片 | 链接/下载 |
|------|------|------------|--------|--------|-----------|--------|----------|-----------|
| **A 概览** | 同业列表（可点跳转） | 历史市值曲线 | — | — | — | 1d/5d/1m/3m/6m/1y 涨跌可做小条 | 价格、涨跌、市值、beta、流通股等 | — |
| **B 估值/DCF** | 历史 EV 按年 | EV 趋势线 | — | — | — | — | DCF 值、杠杆 DCF、隐含股价 | 自定义 DCF 可链出或弹窗 |
| **C 财务报表** | 三表（年/季/TTM）、增长表、分部表 | 收入/利润/现金流趋势（可选） | — | 年度收入/利润柱状（可选） | 收入产品/地区分部（饼或环形） | 表内「近几期」趋势列 | 本期关键数（收入、净利润） | 10-K/10-Q 链接、XLSX/JSON 下载 |
| **D 比率与指标** | TTM + 历史比率/指标表 | 关键比率时间序列（PE、ROE 等） | — | — | — | 表内比率趋势迷你图 | Altman Z、Piotroski、当前 PE/PB | 导出表格 |
| **E 分析师** | 预测表、历史评级表 | 目标价随时间（可选） | — | **评级分布柱状图**（强买/买/持有/卖/强卖） | — | — | 共识目标价、评级数量 | 外链研报（若有） |
| **F 行情与图表** | — | 技术指标线（SMA/EMA/RSI 副图） | **EOD + 盘内蜡烛图** | 成交量柱状（或沿用 lightweight 成交量） | — | — | 当前价、涨跌 | 导出图表 PNG |
| **G 股息与拆股** | 股息历史、拆股历史、股息/拆股日历 | 股息率或派息额趋势（可选） | — | — | — | — | 当前股息率、下次派息日 | 导出列表 |
| **H 业绩与事件** | 业绩历史、业绩日历、M&A 列表 | — | — | EPS 实际 vs 预期柱状（可选） | — | — | 下次业绩日、上次 EPS | 业绩会文字稿链接 |
| **I 新闻与公告** | 新闻列表（标题、来源、时间） | — | — | — | — | — | — | **每条外链**（原文）、RSS/导出（可选） |
| **J 公司治理与高管** | 高管名单表、薪酬明细表、员工数历史 | 员工数趋势（可选） | — | 薪酬构成柱状（可选） | — | — | 高管人数、总薪酬 | SEC 高管披露链接 |
| **K 机构持仓** | 持仓机构及变动表、13F 摘要 | 持仓占比或户数趋势 | — | 机构持仓变动柱状 | 机构类型占比（饼/环形，若有） | — | 持仓家数、总持股比例 | 13F 申报链接 |
| **L 内部人交易** | 交易记录表、统计表 | — | — | 买卖金额/笔数柱状（可选） | — | — | 近期买卖汇总 | SEC 披露链接 |
| **M SEC 申报** | 申报列表（日期、类型、链接） | — | — | — | — | — | — | **每条申报链接**、批量导出 |
| **N ETF 持仓** | 持有该股的 ETF 列表（名称、权重、市值） | — | — | 持仓权重柱状（或条形） | **ETF 权重环形图**（前 N 只） | — | 被持有 ETF 数量 | ETF 详情链接 |
| **O 板块与行业** | 板块/行业 PE 或表现列表 | 板块/行业历史表现线 | — | **板块/行业当日涨跌柱状** | — | — | 公司所在 sector/industry 当日表现 | — |
| **P ESG** | ESG 指标表、历史评分表 | ESG 评分趋势（可选） | — | 与行业对比柱状 | — | — | 综合 ESG 分 | 披露链接 |
| **Q 国会交易** | 议员交易记录表 | — | — | 交易方向/金额柱状（可选） | — | — | 近期交易笔数 | 披露链接 |
| **R 盘后** | 盘后成交列表（可选） | — | — | — | — | — | 盘后价、涨跌 | — |
| **S 退市** | — | — | — | — | — | — | 警示文案（若有） | — |

### 6.3 图表与组件选型（与现有技术栈一致，可扩展）

- **表格**
  - **首选**：现有 Shadcn **Table**（`TableHeader` / `TableBody` / `TableRow` / `TableCell`），与 Admin、Reports、OptionChain 一致；支持排序、分页、固定表头（横向/纵向滚动）。
  - **增强**：可对「公司数据」页的表格统一支持：列排序、列筛选、**导出 CSV/Excel**（前端或后端生成）；大表使用虚拟滚动（如 `@tanstack/react-virtual`）保证性能。
- **蜡烛图 / 成交量**
  - **沿用**：**lightweight-charts**（现有 `CandlestickChart`），用于 EOD 与盘内 1m/5m/15m/1h/4h；主图蜡烛 + 成交量柱，风格与 Strategy Lab 一致。
- **折线图 / 面积图 / 柱状图 / 饼图**
  - **首选**：**recharts**（现有 `PayoffChart` 已用），用于：历史市值、EV、收入/利润/现金流趋势、技术指标线、板块/行业柱状、评级分布柱状、收入分部饼/环形、ETF 权重环形图等。
  - **一致性**：配色与主题沿用 CSS 变量（`--primary`、`--muted`、`--border` 等），支持亮/暗色；图例、Tooltip、坐标轴格式（数字千分位、百分比、日期）统一规范。
- **迷你图（Sparkline）**
  - **实现**：可用 **recharts** 的 `LineChart` + `Line` 小型化（无轴或仅横轴），嵌入表格单元格；或引入轻量 **react-sparklines** / 自研基于 SVG 的迷你图，保持风格一致。
- **链接与下载**
  - **链接**：全部使用 `<a href="..." target="_blank" rel="noopener noreferrer">`，图标（如 `ExternalLink`）+ 文案；SEC、10-K/10-Q、新闻、业绩会 transcript 等一律可点击跳转。
  - **下载**：表格导出 CSV/Excel（前端 `Blob` + 下载或后端生成）；图表导出 PNG 沿用现有方式（如 `html2canvas` + 下载或 recharts/lightweight-charts 自带导出）。
- **KPI 卡片**
  - **首选**：Shadcn **Card** + 大号数字 + 小标签；正负值用颜色区分（涨绿跌红或品牌色）；可与现有 Dashboard/Admin 卡片风格一致。
- **可选增强（更专业）**
  - 若需更强金融场景表现：可评估 **Tremor**（基于 Tailwind 的图表库，与 Shadcn 风格易统一）或 **Nivo**（丰富饼图/环形图）；**不替换**现有 lightweight-charts / recharts，仅对「公司数据」页新增图表类型时按需引入，并统一主题与无障碍。

### 6.4 交互与无障碍

- **表格**：支持键盘导航、表头 `scope`、屏幕阅读器友好；大表提供「跳转到页首/页尾」。
- **图表**：为 recharts/lightweight-charts 配置 `aria-label`、图例与 Tooltip 可读；关键结论（如「当前 PE」「目标价共识」）在 KPI 卡片或标题中复述，不依赖看图。
- **链接**：外链明确标注「新窗口打开」或图标；下载链接标明格式（如「下载 CSV」「10-K PDF」）。

### 6.5 小结

| 展示形态 | 组件/库 | 使用位置 |
|----------|----------|----------|
| 表格 | Shadcn Table，可选虚拟滚动 + 导出 | 所有列表型数据（报表、比率、业绩、股息、内部人、SEC、新闻、高管、机构、ETF 列表等） |
| 蜡烛图 + 成交量 | lightweight-charts（现有 CandlestickChart） | 行情模块 EOD / 盘内 |
| 折线/面积/柱状/饼图 | recharts | 趋势、分布、分部、板块对比、评级分布、ETF 权重等 |
| 迷你图 | recharts 小型 Line 或 react-sparklines | 表内趋势列 |
| KPI 卡片 | Shadcn Card | 概览、估值、比率摘要、分析师共识等 |
| 链接/下载 | `<a>` + 导出 API 或 Blob | SEC、10-K、新闻、业绩会、表格/图表导出 |

整体保持与现有系统一致风格，数据展示专业、有层次，便于用户快速理解并形成「准确、完备、有价值」的印象，从而提升留存与付费意愿。

---

## 7. Security & Compliance

- **Auth**: All company-data endpoints require login (JWT/session). Quota is per user.
- **Rate limit**: Optional per-user rate limit (e.g. 10 req/min) to avoid abuse.
- **FMP key**: Remain server-side only; never expose to frontend.
- **PII**: Do not log symbol queries with user identity in plaintext in public logs; internal analytics OK.

---

## 8. Implementation Phases (Recommendation)

### Phase 1 (MVP)
- New route + menu item; search (symbol/name); quota (2/100); one “full” load per symbol; cache (e.g. 15 min).
- Sections: Overview (profile + quote + price change), Statements (income, balance, cash flow — TTM + annual), Ratios & Metrics TTM, Analyst (estimates + price target + grades), DCF/Valuation, Dividends, Earnings, News, one EOD chart.
- Backend: New router, quota middleware, FMP aggregation service (reuse existing FMP client/key), cache layer.

### Phase 2
- Peers, governance (executives), intraday chart, technical indicators, statement growth, more news.
- Optional: Screener (sector/industry/country filter), “Compare with peer” table.

### Phase 3
- Export (CSV/Excel), saved symbols / watchlist for this page only, optional email alerts (earnings date, etc.).

---

## 9. Summary

| Item | Decision |
|------|----------|
| **New page only** | Yes; no changes to Strategy Lab, Option Chain, or AI reports. |
| **Data source** | 100% FMP API (Premium); direct backend calls. |
| **Quota** | Free 2/day, Pro 100/day; one “query” = one symbol per day (any module/full); cache to avoid repeated deduction. |
| **Menu** | New item “Company Data” / “Fundamentals”. |
| **Data scope** | **全量设计**：覆盖 FMP 文档中与单标的相关的 Search、Company Info、Quote、Statements、Ratios、DCF、Analyst、Charts、Technical、Dividends/Splits、Earnings、News、Governance、13F、Insider、SEC、ETF Exposure、Sector/Industry、ESG、Congress、After-Hours 等（见 Section 3）。 |
| **Loading** | 分模块加载；支持 `/full`、`/module/{id}`、可选 `POST /load-task` 后台任务；750 次/分钟限流内分批并行。 |
| **Frontend** | 首屏：概览 + 估值 + 比率 + EOD 图 + 分析师；其余模块懒加载/Tab/按需展开；每块独立 loading/error。 |
| **展示策略** | 表格（Shadcn Table）+ 曲线/面积/柱状/饼图（recharts）+ 蜡烛图（lightweight-charts）+ KPI 卡片 + 链接/下载；按模块使用表格、图表、饼图、柱状图、迷你图、外链与导出（见 Section 6）。 |
| **Backend** | New route group, quota + cache (per symbol/day), FMP aggregation by module; optional task queue for full load. |

本方案对齐 [FMP Datasets](https://site.financialmodelingprep.com/datasets) 与 [Developer Docs](https://site.financialmodelingprep.com/developer/docs) 中与公司/股票相关的全部数据集，力求**指标完善、专业、有冲击力**，让用户明确感知「查到的数据非常准确、完备、有价值」。
