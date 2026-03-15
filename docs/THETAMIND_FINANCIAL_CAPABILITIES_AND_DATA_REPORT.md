# ThetaMind 金融能力与数据实现报告

**文档性质**：基于当前代码库的静态梳理，详细说明期权、期权策略组合、公司基本面等金融相关能力的实现与数据来源。  
**日期**：2026-02-21

---

## 一、期权 (Options) 能力与数据

### 1.1 数据来源与接入方式

| 项目 | 说明 |
|------|------|
| **主数据源** | **Tiger Brokers OpenAPI**（老虎证券官方 SDK：`tigeropen`），用于生产环境实时期权链与行情。 |
| **开发/降级** | `TIGER_USE_LIVE_API=false` 时使用本地 **Fixture**（`backend/app/data/fixtures/option_chain_fixture.json`），不调用 Tiger，避免开发/生产抢占。 |
| **实现位置** | `backend/app/services/tiger_service.py`（TigerService），通过 `run_in_threadpool` 调用同步 SDK，避免阻塞异步事件循环。 |

### 1.2 已实现的期权相关接口与能力

| 能力 | 方法 | 说明 |
|------|------|------|
| **期权到期日列表** | `get_option_expirations(symbol)` | 按标的返回可交易到期日列表（YYYY-MM-DD），支持缓存（如 24h TTL）。 |
| **期权链（含 Greeks）** | `get_option_chain(symbol, expiration_date, is_pro, force_refresh)` | 指定标的与到期日，返回 **Calls / Puts** 完整链；**Pro 用户** 可传 `force_refresh=True` 绕过缓存拉实时数据。 |
| **K 线/历史行情** | `get_kline_data(symbol, period, limit)` | 日/周/月等周期 K 线（open, high, low, close, volume），用于 Strategy Lab 蜡烛图及历史波动率等。 |
| **实时价格** | `get_realtime_price(symbol)` | 标的实时价，用于报价与期权链缺失时推断 spot。 |
| **市场扫描** | `get_market_scanner(market, criteria, market_value_min, volume_min, limit)` | 按涨跌幅、成交量、市值等条件扫描美股，支持分页与限流（10 次/分钟）。 |

### 1.3 期权链单腿数据结构（我们实际取到的字段）

每条 **Call / Put** 包含（来自 Tiger SDK 的 DataFrame 转换或 Fixture）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `strike` | number | 行权价。 |
| `bid` / `ask` | number | 买一/卖一（来自 `bid_price` / `ask_price`）。 |
| `volume` | number | 成交量。 |
| `open_interest` | number | 未平仓合约数。 |
| `delta`, `gamma`, `theta`, `vega`, `rho` | number | 希腊值（Tiger 通过 `return_greek_value=True` 返回）。 |
| `implied_vol` / `implied_volatility` | number | 隐含波动率（AI 分析与风控用）。 |
| `latest_price` | number | 最新成交价（若有）。 |

期权链整体还包含：

- **spot_price**（或 `underlying_price`）：标的现价。
- **calls** / **puts**：上述结构的数组。

### 1.4 对外暴露的 API

- **GET /api/v1/market/chain**：查询期权链，参数 `symbol`、`expiration_date`、`force_refresh`（Pro 可用）。  
- **GET /api/v1/market/expirations**：查询某标的的到期日列表。  
- **GET /api/v1/market/history**：历史 K 线（内部会优先 Tiger，失败时可回退 FMP）。  
- **GET /api/v1/market/quote**：股票报价（当前实现为 FMP/FinanceToolkit 推断，非 Tiger 实时）。

---

## 二、期权策略组合 (Strategy Engine) 能力与数据

### 2.1 定位与数据依赖

- **引擎**：`backend/app/services/strategy_engine.py`（StrategyEngine）。  
- **原则**：纯数学与 Greeks 逻辑，**不调用 AI**；期权链与 Greeks 统一来自 **Tiger**（`tiger_service.get_option_chain`），Greeks 缺失时仅做占位（不再从其他源拉取）。  
- **输入**：标的、到期日、现价、**市场观点 (Outlook)**、**风险偏好 (RiskProfile)**、资金规模等。

### 2.2 已实现的策略算法

| 观点 (Outlook) | 策略类型 | 算法方法 | 简要逻辑 |
|----------------|----------|----------|----------|
| **NEUTRAL** | 铁鹰 (Iron Condor) | `_algorithm_iron_condor` | 高 IV 中性：Short Call/Put 按 Delta≈0.20/0.30 选腿，Long 翼宽 $5/$10，校验净信用≥翼宽 1/3、\|Net Delta\|&lt;0.10、DTE 30–60 更优。 |
| **VOLATILE** | 多头跨式 (Long Straddle) | `_algorithm_long_straddle` | 低 IV 波动博弈：ATM Call + ATM Put，校验净 debit &lt;  spot 一定比例、Gamma/Theta 等。 |
| **BULLISH** | 牛市看涨价差 (Bull Call Spread) | `_algorithm_bull_call_spread` | 买入较低行权 Call、卖出较高行权 Call，净 debit &lt; 价差宽度 50% 等。 |
| **BEARISH** | — | 未实现 | 文档注明可做 Bear Put Spread，当前仅 log，返回空。 |

### 2.3 策略输出结构（CalculatedStrategy）

- **name** / **description**：策略名称与描述。  
- **legs**：`OptionLeg[]`，每腿含 symbol、strike、ratio（+1/-1）、type（CALL/PUT）、greeks、bid/ask/mid_price、expiration_date、days_to_expiration。  
- **metrics**：如 **max_profit**、**max_loss**、**risk_reward_ratio**、**pop**（盈亏平衡概率）、**breakeven_points**、**net_greeks**（组合 Delta/Gamma/Theta/Vega/Rho）、**theta_decay_per_day**、**liquidity_score** 等。

### 2.4 对外暴露的 API

- **POST /api/v1/market/recommendations**：请求体含 `symbol`、`expiration_date`（可选，默认下周五）、`outlook`、`risk_profile`、`capital`；后端拉 Tiger 期权链 → StrategyEngine.generate_strategies → 返回通过校验的 `CalculatedStrategy[]`。

### 2.5 前端使用

- Strategy Lab 等可调用上述推荐接口，将返回的 legs 渲染为表格与盈亏图；当前实现中策略推荐与「一键套用」的入口与交互依前端页面而定。

---

## 三、公司基本面数据 (Company Fundamentals) 能力与数据

### 3.1 数据来源概览

| 层级 | 数据源 | 用途 |
|------|--------|------|
| **主源** | **FMP (Financial Modeling Prep)** | 通过 **FinanceToolkit** 拉取财务比率、报表、估值、技术指标、风险与绩效指标等；部分接口由 MarketDataService 直接调 FMP 稳定版 API（`financialmodelingprep.com/stable`）补全。 |
| **补全** | MarketDataService 内同步调用 FMP | `get_financial_profile` 中当 FinanceToolkit 比率/估值为空时，用 `ratios-ttm`、`key-metrics-ttm` 等接口补 PE/PB/ROE/ROA；公司 profile 为空时用 FMP `profile` 补。 |
| **Company Data 页** | FMP 直接 API（FundamentalDataService） | 公司数据页的「模块化」数据（概览、估值、比率、分析师、图表、新闻、日历、报表、SEC、内幕、治理等）由 **FundamentalDataService** 调用 FMP 多种 endpoint 聚合。 |

### 3.2 MarketDataService.get_financial_profile 取到的数据（供 AI / Strategy Lab / 分析用）

单次调用返回一个「财务画像」字典，包含（均为 FMP/FinanceToolkit 衍生，并做 NaN/Inf 清洗）：

| 大类 | 子项/字段说明 |
|------|----------------|
| **ratios** | 五大类：**profitability**（盈利能力）、**valuation**（估值）、**solvency**（偿债）、**liquidity**（流动性）、**efficiency**（效率）；或 `collect_all_ratios()` 的 **all**。缺省时用 FMP `ratios-ttm`、`key-metrics-ttm` 补 PE、P/B、ROE、ROA 等。 |
| **technical_indicators** | **momentum**（RSI、MACD 等）、**trend**（SMA、EMA、ADX 等）、**volatility**（ATR 等）、**volume**（OBV 等）；以及单指标：rsi、macd、bollinger_bands、sma、ema、atr、obv 等。 |
| **risk_metrics** | **all** 或分项：**var**、**cvar**、**max_drawdown**、**skewness**、**kurtosis** 等。 |
| **performance_metrics** | **sharpe_ratio**、**sortino_ratio**、**treynor_ratio**、**capm**、**jensens_alpha**、**information_ratio** 等（依赖历史收益数据）。 |
| **financial_statements** | **income**（利润表）、**balance**（资产负债表）、**cash_flow**（现金流量表）。 |
| **valuation** | **dcf**（现金流折现）、**ddm**（股利折现）、**wacc**、**enterprise_value**（企业价值拆解）。 |
| **dupont_analysis** | **standard**（标准杜邦）、**extended**（扩展杜邦）。 |
| **analysis** | 内部 `_generate_analysis` 生成：**health_score**（overall、factors、category：excellent/good/fair/poor）、**signals**、**warnings** 等。 |
| **volatility** | 历史波动率（年化等），来自 FinanceToolkit 或由历史收益计算。 |
| **profile** | 公司简介（名称、市值等），缺省时用 FMP `profile` 补。 |

以上数据被多智能体（Fundamental Analyst、Technical Analyst、Market Context、IV Environment 等）和 Deep Research 报告消费。

### 3.3 Company Data 页专用：FundamentalDataService 与 FMP 模块

Company Data 页按「模块」拉取，每模块对应一次或多次 FMP 调用（带缓存与配额）：

| 模块 | 主要 FMP 数据/接口 | 说明 |
|------|---------------------|------|
| **overview** | profile, quote, stock-price-change, market-capitalization, shares-float, stock-peers + earnings-calendar（下一财季） | 公司概览、报价、涨跌、市值、流通股、同行、即将财报。 |
| **valuation** | DCF/估值相关（如 FMP 的 DCF、levered DCF 等） | 估值仪表盘。 |
| **ratios** | ratios, key-metrics（或 ratios-ttm/key-metrics-ttm） | 财务比率与关键指标。 |
| **analyst** | analyst-estimates, grades, ratings-historical, price-target 等 | 分析师预期、评级、目标价。 |
| **charts** | historical-price-eod 等 | 历史价格用于图表。 |
| **news** | news/stock | 公司新闻（单独接口，通常不占「模块」配额）。 |
| **calendar** | earnings-calendar, dividends-calendar, splits-calendar | 财报/股息/拆股日历。 |
| **statements** | income-statement, balance-sheet-statement, cash-flow-statement | 三大报表（年/季）。 |
| **sec_filings** | sec-filings-search/symbol 等 | SEC 申报。 |
| **insider** | insider-trading/search | 内幕交易。 |
| **governance** | governance-executive-compensation | 治理与高管薪酬。 |

配额：Free 2 次/日、Pro 100 次/日（按「每标的每日首次加载」扣减，缓存命中不扣）。

### 3.4 对外暴露的 API（公司/基本面相关）

- **GET /api/v1/market/profile**：`get_financial_profile` 的 HTTP 接口（带缓存与 run_in_threadpool），返回上述完整财务画像。  
- **GET /api/v1/company-data/quota**：公司数据页配额（used/limit/is_pro）。  
- **GET /api/v1/company-data/search**：标的/公司搜索（FMP search-symbol + search-name，失败时回退本地 DB）。  
- **GET /api/v1/company-data/overview**、**/full**（含 modules 参数）：按模块拉取公司数据（overview、valuation、ratios、analyst、charts 等）。  
- **GET /api/v1/market/financial/key-metrics-ttm**、**ratios-ttm**：FMP TTM 指标与比率（供别处复用）。  
- **GET /api/v1/market/analyst/estimates**、**price-target**、**grades**、**ratings** 等：分析师与评级类数据。  

前端 **Company Data 页**（`CompanyDataPage.tsx`）使用 **companyDataApi** 与 **marketService**，展示概览、估值、比率、分析师、图表、新闻、SEC、内幕、治理等。

---

## 四、市场与行情类（与期权/策略/基本面配套）

### 4.1 行情与历史

- **GET /api/v1/market/quote**：股票报价（FinanceToolkit/FMP，含 price、change、volume 等）。  
- **GET /api/v1/market/history**、**/historical/{interval}**：K 线/历史行情（优先 Tiger get_kline_data，失败时可用 FMP 历史价）。  
- **GET /api/v1/market/technical/{indicator}**：单技术指标（如 RSI）。  

### 4.2 市场广度与扫描

- **GET /api/v1/market/market/sector-performance**、**industry-performance**：板块/行业表现（FMP）。  
- **GET /api/v1/market/market/biggest-gainers**、**biggest-losers**、**most-actives**：涨跌榜与活跃榜（FMP）。  
- **POST /api/v1/market/scanner**：Tiger 市场扫描（top_gainers/top_losers/most_active/high_volume + 市值/成交量过滤）。  

### 4.3 批量与搜索

- **GET /api/v1/market/quotes/batch**：批量报价。  
- **GET /api/v1/market/search**：标的搜索（本地 DB 或 FMP，用于 Strategy Lab 等）。  

---

## 五、数据来源汇总表（我们取到了哪些金融数据）

| 数据类别 | 具体数据项 | 主要来源 | 备注 |
|----------|------------|----------|------|
| 期权链 | 到期日、Calls/Puts、strike/bid/ask/volume/OI、Greeks、IV | Tiger OpenAPI | 生产实时；开发可用 Fixture |
| 标的行情 | 实时价、K 线（OHLCV） | Tiger（K 线）、FMP/FinanceToolkit（报价推断） | 历史 K 线可回退 FMP |
| 财务比率 | PE、PB、ROE、ROA、负债率、流动性、效率等 5 类 | FMP（FinanceToolkit + ratios-ttm/key-metrics-ttm） | 供 AI 与 Company 页 |
| 技术指标 | RSI、MACD、布林、SMA/EMA、ADX、ATR、OBV 等 | FMP（FinanceToolkit） | 供 AI 与图表 |
| 风险指标 | VaR、CVaR、最大回撤、偏度、峰度等 | FMP（FinanceToolkit） | 供 AI |
| 绩效指标 | Sharpe、Sortino、Treynor、CAPM、Alpha、Info Ratio | FMP（FinanceToolkit） | 需历史收益 |
| 三大报表 | 利润表、资产负债表、现金流量表 | FMP（FinanceToolkit + FMP statements） | 年/季 |
| 估值模型 | DCF、DDM、WACC、企业价值拆解 | FMP（FinanceToolkit） | 供 AI 与估值仪表盘 |
| 杜邦分析 | 标准杜邦、扩展杜邦 | FMP（FinanceToolkit） | 供 AI |
| 公司画像 | 名称、市值、简介等 | FMP（profile） | 缺省时直接调 FMP |
| 健康分与信号 | health_score、warnings、signals | 自算（_generate_analysis） | 基于上述比率与指标 |
| 历史波动率 | 年化波动率等 | FinanceToolkit 或收益推算 | 供 IV 分析等 |
| 板块/行业表现 | 板块与行业涨跌 | FMP 直接 API | 市场广度 |
| 涨跌/活跃榜 | 涨幅、跌幅、成交量排行 | FMP 直接 API | Discovery |
| 分析师数据 | 预期、评级、目标价、共识 | FMP 直接 API | Company 页 + 市场 API |
| 新闻/日历/报表/SEC/内幕/治理 | 公司新闻、财报日历、报表、SEC、内幕、治理 | FMP（FundamentalDataService） | Company Data 页模块 |
| 市场扫描列表 | 按涨跌幅/成交量/市值筛选的股票列表 | Tiger market_scanner | Discovery |

---

## 六、实现位置索引（便于后续扩展与排错）

| 能力 | 后端核心实现 | 对外 API |
|------|--------------|----------|
| 期权到期日 | `tiger_service.get_option_expirations` | GET /market/expirations |
| 期权链 | `tiger_service.get_option_chain` | GET /market/chain |
| K 线 | `tiger_service.get_kline_data` | GET /market/history、/historical |
| 实时价 | `tiger_service.get_realtime_price` | 内部使用或报价推断 |
| 策略推荐 | `strategy_engine.generate_strategies` | POST /market/recommendations |
| 财务画像（AI/分析用） | `market_data_service.get_financial_profile` | GET /market/profile |
| 公司数据页模块 | `fundamental_data_service.fetch_*` | GET /company-data/* |
| 市场扫描 | `tiger_service.get_market_scanner` | POST /market/scanner |
| 板块/行业/涨跌榜 | `market_data_service.get_sector_performance` 等 | GET /market/market/*、/analyst/* |

---

**说明**：本报告仅描述当前代码中已实现的能力与数据字段；未实现的（如 Bear Put Spread、IV Skew 曲线、DCF 前端仪表盘细节）未列入。后续若新增数据源或字段，建议在本文档中同步更新「数据来源」与「取到的数据项」两节。
