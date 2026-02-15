# Company Data 页面增强设计文档

**版本**: 1.0  
**日期**: 2025-02-06  
**状态**: 设计阶段（文档先行，代码待实施）

---

## 一、总则与约束

### 1.1 目标

将 Company Data 页面打造成真正体现 **FMP Premium** 价值的专业数据平台，而非简单的 Overview 聚合。重点方向：

- **专业研究**：财报、SEC 申报、内部人交易、公司治理
- **信息时效**：新闻聚合、Market Calendar（财报/股息/拆股）
- **专业呈现**：公式与评级方法论说明，提升可信度

### 1.2 强制约束（不可违反）

| 约束 | 说明 |
|------|------|
| **Full fundamentals 不动** | 第二个 Tab「Full fundamentals」及其 `FundamentalDataContent`（ProfileDataDialog）**完全保留**，不修改任何逻辑、样式、数据源 |
| **不改坏现有功能** | Overview 现有区块（Overview 卡片、Valuation、Ratios、Analyst、Market Data、Peers）的行为与展示逻辑**保持兼容**；仅做增量扩展 |
| **站点风格一致** | 新增 UI 必须与 ThetaMind 整体风格一致：Shadcn/UI、Tailwind、Card 布局、`text-muted-foreground`、主题色等 |

### 1.3 技术决策

| 决策 | 说明 |
|------|------|
| **不引入 fmpsdk** | 继续使用 `MarketDataService._call_fmp_api` 直接调用 FMP REST API |
| **FMP 计划** | Premium（无 13F、无 Earnings Transcript） |
| **Quota 规则** | `news`、`calendar`、`sec`、`insider`、`governance` 等**不计入** Company Data 配额；仅 `overview`、`valuation`、`ratios`、`analyst`、`charts`、`financials`（三大报表）计入 |

---

## 二、页面布局与 Tab 结构

### 2.1 当前结构（保持不变）

```
Company Data Page
├── Header（标题、配额卡片）
├── SymbolSearch（选股）
└── Tabs
    ├── Overview — {company name}
    └── Full fundamentals  ← 完全不动
```

### 2.2 目标结构（Phase 1–2 后）

```
Company Data Page
├── Header（标题、配额卡片）
├── SymbolSearch（选股）
└── Tabs
    ├── Overview — {company name}   ← 首屏增强：+ 新闻流 + 日历
    ├── News & Calendar             ← 新增 Tab
    ├── Financials & SEC            ← 新增 Tab（财报 + SEC 申报）
    ├── Insider & Governance        ← 新增 Tab（可选，视 API 可用性）
    └── Full fundamentals           ← 完全不动
```

### 2.3 Tab 职责

| Tab | 职责 | 数据来源 | 配额 |
|-----|------|----------|------|
| Overview | 速览：公司名、价格、涨跌、市值、Beta、Next earnings、1D~1Y 涨跌、DCF、Ratios、Analyst、K 线、Peers；**新增**新闻摘要（3–5 条）、日历摘要（近期财报/股息） | full API + news + calendar | 计入 |
| News & Calendar | 完整新闻列表、财报/股息/拆股日历 | news/*, *-calendar | 不计 |
| Financials & SEC | 三大报表（表格 + 下载）、SEC 10-K/10-Q/8-K 列表 + 链接 | statements, sec-filings-* | 财报计入，SEC 不计 |
| Insider & Governance | 内部人交易、高管名单与薪酬 | insider-*, key-executives 等 | 不计 |
| Full fundamentals | 与 Strategy Lab 一致的深度基本面 | getFinancialProfile | 不计（复用现有） |

---

## 三、Phase 1：首屏增强（新闻 + 日历 + 布局）

### 3.1 目标

在 Overview Tab 内**增量**添加：

1. **新闻流**：公司相关新闻 3–5 条，标题 + 摘要 + 链接 + 时间
2. **Calendar 摘要**：近期财报日、股息日、拆股日（若有）

### 3.2 后端

#### 3.2.1 新增模块（FundamentalDataService）

| 模块 | 方法 | FMP Endpoint | 说明 |
|------|------|--------------|------|
| news | `fetch_news(symbol, limit=5)` | `news/stock` 或 `news/stock-latest`（按 symbol 过滤） | 个股新闻，limit 控制条数 |
| calendar | `fetch_calendar(symbol)` | `earnings-calendar`, `dividends-calendar`, `splits-calendar` | 合并近期事件，按日期排序 |

#### 3.2.2 新增 API 端点（不计费）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/company-data/news?symbol=` | 返回新闻列表；**不扣配额** |
| GET | `/api/v1/company-data/calendar?symbol=` | 返回日历事件；**不扣配额** |

或：将 `news` 和 `calendar` 作为 `/full` 的可选 `modules` 参数，但**不触发配额扣除**（需在 `ensure_fundamental_quota_and_deduct` 前单独拉取，或单独 endpoint）。

**推荐**：单独 endpoint，逻辑清晰，前端按需调用。

#### 3.2.3 FMP Endpoint 映射

| 逻辑 | FMP 路径 | 参数 |
|------|----------|------|
| 个股新闻 | `news/stock` | `tickers=AAPL` 或 `symbols=AAPL`（以 FMP 文档为准） |
| 财报日历 | `earnings-calendar` | `from=YYYY-MM-DD&to=YYYY-MM-DD`（已有） |
| 股息日历 | `dividends-calendar` | `from=&to=` |
| 拆股日历 | `splits-calendar` | `from=&to=` |

### 3.3 前端

#### 3.3.1 Overview 内新增区块

在 `CompanyDataBlocks` 中，在 **Overview 卡片下方、Valuation 上方**（或紧跟 Overview 卡片）插入：

1. **News 卡片**（`hasNews` 时渲染）
   - 标题：`Recent News`
   - 内容：列表，每项：标题（可点击外链）、来源、时间
   - 样式：与现有 Card 一致，`text-sm`、`text-muted-foreground`

2. **Calendar 卡片**（`hasCalendar` 时渲染）
   - 标题：`Upcoming Events`
   - 内容：财报日、股息日、拆股日，按日期排序
   - 样式：与 Next earnings 类似，表格或列表

#### 3.3.2 数据获取

- `useQuery`：`["company-data-news", symbol]`、`["company-data-calendar", symbol]`
- `enabled: !!selectedSymbol`
- 不计费，无需与 quota 逻辑耦合

### 3.4 样式规范

- 使用 `Card`, `CardHeader`, `CardTitle`, `CardContent`
- 新闻标题：`font-medium`，链接用 `text-primary hover:underline`
- 时间：`text-muted-foreground text-xs`
- 与 Dashboard、Strategy Lab 等页面视觉统一

---

## 四、Phase 2：Tab 深化（Financials、News & Calendar、SEC、Insider & Governance）

### 4.1 News & Calendar Tab

- **新闻**：完整列表，分页或「加载更多」
- **日历**：完整财报/股息/拆股日历，可切换视图（列表/月视图 可选）

### 4.2 Financials & SEC Tab

#### 4.2.1 财报（三大报表）

| 内容 | FMP Endpoint | 展示 |
|------|--------------|------|
| 利润表 | `income-statement` | 表格，年/季切换 |
| 资产负债表 | `balance-sheet-statement` | 表格 |
| 现金流量表 | `cash-flow-statement` | 表格 |

**下载**：前端将表格数据导出为 CSV，或后端提供 `/export/income-statement?symbol=` 返回 CSV/XLSX（可选）。

#### 4.2.2 SEC 申报

| 内容 | FMP Endpoint | 展示 |
|------|--------------|------|
| 10-K/10-Q/8-K 列表 | `sec-filings-search/symbol` 或 `sec-filings-company-search/symbol` | 表格：类型、日期、标题、SEC 链接 |

SEC EDGAR 链接格式：`https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=xxx&type=10-K` 等（FMP 通常返回 `filingUrl` 或 `link`）。

### 4.3 Insider & Governance Tab

| 内容 | FMP Endpoint | 展示 |
|------|--------------|------|
| 内部人交易 | `insider-trading/search?symbol=` | 表格：日期、内部人、类型、股数、价格 |
| 高管名单 | `key-executives` | 表格：姓名、职位 |
| 高管薪酬 | `governance-executive-compensation` | 表格（若有数据） |

### 4.4 后端模块扩展

在 `FundamentalDataService` 中新增：

- `fetch_statements(symbol)`：income, balance, cashflow
- `fetch_sec_filings(symbol)`
- `fetch_insider(symbol)`
- `fetch_governance(symbol)`

对应 API：

- `GET /api/v1/company-data/statements?symbol=`（可扣配额，或与 full 共享缓存）
- `GET /api/v1/company-data/sec-filings?symbol=`（不计费）
- `GET /api/v1/company-data/insider?symbol=`（不计费）
- `GET /api/v1/company-data/governance?symbol=`（不计费）

配额规则：`statements` 与首次 `full` 共享「同 symbol 同日只扣 1 次」逻辑；news/calendar/sec/insider/governance 一律不扣。

---

## 五、Phase 3：公式与评级方法论整合

### 5.1 目标

提升专业感，让用户理解 DCF、评级、比率的计算逻辑。参考 FMP 文档：

- [Financial Formulas](https://site.financialmodelingprep.com/developer/docs/formula)
- [DCF Formula](https://site.financialmodelingprep.com/developer/docs/dcf-formula)
- [Recommendations Formula](https://site.financialmodelingprep.com/developer/docs/recommendations-formula)

### 5.2 DCF 说明

**位置**：Valuation 卡片内，DCF value、Levered DCF 旁。

**形式**：小问号图标 `(?)`，hover 或点击显示 Tooltip/Popover。

**内容摘要**（可内嵌或链接）：

- Market Cap = Weighted Avg Shares Diluted × Stock Price
- Enterprise Value = Market Cap + Long Term Debt + Short Term Debt
- Equity Value = EV − Net Debt
- DCF = Equity Value / Weighted Avg Shares Diluted
- 链接：`https://site.financialmodelingprep.com/developer/docs/dcf-formula`

### 5.3 评级方法论（Recommendations）

**位置**：Analyst 卡片内，Recommendation 旁。

**形式**：小问号图标，Tooltip/Popover。

**内容摘要**：

- 评分维度：DCF, ROE, ROA, Debt/Equity, P/E, P/B
- 每维度对应 Strong Buy / Buy / Neutral / Sell / Strong Sell
- 总分映射到 S+/A+/B+/C+/D 等
- 链接：`https://site.financialmodelingprep.com/developer/docs/recommendations-formula`

### 5.4 比率公式（Ratios）

**位置**：Key ratios 卡片内，PE、PB、ROE、Debt/Equity 等每个指标旁。

**形式**：每个 KPI 旁加小问号，Tooltip 显示公式。

**公式示例**（来自 FMP formula 文档）：

| 指标 | 公式 |
|------|------|
| P/E | price / (netIncome / shareNumber) |
| P/B | price / (totalStockHolderEquity / shareNumber) |
| ROE | netIncome / totalStockHolderEquity |
| Debt/Equity | totalLiabilities / totalStockHolderEquity |
| Current Ratio | currentAssets / currentLiabilities |

可在前端维护一份 `RATIO_FORMULAS: Record<string, string>`，或从配置文件加载。

### 5.5 UI 组件

- 使用 Shadcn `Tooltip` 或 `Popover`
- 图标：`HelpCircle` 或 `Info`（lucide-react）
- 样式：`text-muted-foreground hover:text-foreground`，不喧宾夺主

---

## 六、数据流与缓存

### 6.1 缓存策略

| 模块 | TTL | 键 |
|------|-----|-----|
| overview, valuation, ratios, analyst, charts | 15 min (overview), 1 h (其他) | `company_data:{symbol}:{module}` |
| news | 5–10 min | `company_data:{symbol}:news` |
| calendar | 1 h | `company_data:{symbol}:calendar` |
| statements | 1 h | `company_data:{symbol}:statements` |
| sec-filings | 1 h | `company_data:{symbol}:sec` |
| insider, governance | 1 h | `company_data:{symbol}:insider` 等 |

### 6.2 配额逻辑（再强调）

- **扣配额**：`/full`（modules=overview,valuation,ratios,analyst,charts）、`/statements` 首次请求某 symbol 时
- **不扣配额**：`/news`、`/calendar`、`/sec-filings`、`/insider`、`/governance`
- Full fundamentals Tab 使用 `getFinancialProfile`，与 Company Data 配额无关

---

## 七、实施检查清单

### Phase 1

- [x] 后端：`fetch_news`、`fetch_calendar` 方法
- [x] 后端：`GET /news`、`GET /calendar` 端点（不计费）
- [x] 前端：Overview 内 News 卡片
- [x] 前端：Overview 内 Calendar 卡片
- [x] 验证：Full fundamentals 无变化
- [x] 验证：现有 Overview 区块无回归

### Phase 2

- [x] 后端：`fetch_statements`、`fetch_sec_filings`、`fetch_insider`、`fetch_governance`
- [x] 后端：对应 API 端点
- [x] 前端：News & Calendar Tab
- [x] 前端：Financials & SEC Tab
- [x] 前端：Insider & Governance Tab
- [ ] 财报表格 + 下载（CSV）— 可选，后续补充
- [x] SEC 链接正确跳转

### Phase 3

- [x] DCF 说明 Tooltip
- [x] 评级方法论 Tooltip
- [x] 各比率公式 Tooltip
- [x] 公式文案与链接校对

---

## 八、风格与组件参考

### 8.1 现有组件

- `Card`, `CardHeader`, `CardTitle`, `CardContent`
- `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent`
- `Button`, `Badge`, `Progress`
- `SymbolSearch`, `CandlestickChart`, `FundamentalDataContent`

### 8.2 新增时需遵循

- 间距：`space-y-4`、`gap-4`、`p-4`
- 文字：`text-sm`、`text-muted-foreground`
- 边框：`border`、`border-border`
- 响应式：`sm:grid-cols-2`、`lg:grid-cols-4` 等

### 8.3 Full fundamentals 禁止修改范围

- `frontend/src/components/market/ProfileDataDialog.tsx` 内 `FundamentalDataContent` 及其所有子组件
- `CompanyDataPage.tsx` 中 `TabsContent value="fundamentals"` 的整块 JSX
- 其数据源 `marketService.getFinancialProfile`、`financialProfile` 等

---

## 九、附录：FMP Endpoint 速查（Premium 可用）

| 用途 | Endpoint |
|------|----------|
| 个股新闻 | `news/stock` (tickers/symbols) |
| 财报日历 | `earnings-calendar` |
| 股息日历 | `dividends-calendar` |
| 拆股日历 | `splits-calendar` |
| 利润表 | `income-statement` |
| 资产负债表 | `balance-sheet-statement` |
| 现金流量表 | `cash-flow-statement` |
| SEC 申报 | `sec-filings-search/symbol` 或 `sec-filings-company-search/symbol` |
| 内部人交易 | `insider-trading/search` |
| 高管 | `key-executives` |
| 高管薪酬 | `governance-executive-compensation` |

---

**文档完成**。请审阅后，按 Phase 1 → 2 → 3 顺序实施代码。
