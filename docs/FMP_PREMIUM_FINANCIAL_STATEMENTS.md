# FMP Premium 计划 - 财报数据支持情况

## ✅ **可以获取财报数据！**

根据 FMP Premium 计划文档和代码实现，**Premium 计划完全支持财报数据获取**，并且**后端代码已经实现了财报数据的获取功能**。

---

## 📊 FMP Premium 支持的财报数据类型

### 1. **三大财务报表** ✅

#### Income Statement (利润表/损益表)
- **FMP API 端点**: `/income-statement`
- **Premium 支持**: ✅ **完全支持** (US, UK, Canada)
- **数据包含**:
  - Revenue (收入)
  - Net Income (净利润)
  - Cost of Revenue (营业成本)
  - Operating Expenses (营业费用)
  - Gross Profit (毛利润)
  - Operating Income (营业利润)
  - 其他损益表项目

#### Balance Sheet Statement (资产负债表)
- **FMP API 端点**: `/balance-sheet-statement`
- **Premium 支持**: ✅ **完全支持** (US, UK, Canada)
- **数据包含**:
  - Total Assets (总资产)
  - Total Liabilities (总负债)
  - Total Equity (股东权益)
  - Current Assets (流动资产)
  - Current Liabilities (流动负债)
  - 其他资产负债表项目

#### Cash Flow Statement (现金流量表)
- **FMP API 端点**: `/cash-flow-statement`
- **Premium 支持**: ✅ **完全支持** (US, UK, Canada)
- **数据包含**:
  - Operating Cash Flow (经营活动现金流)
  - Investing Cash Flow (投资活动现金流)
  - Financing Cash Flow (融资活动现金流)
  - Free Cash Flow (自由现金流)
  - 其他现金流量表项目

---

### 2. **财报数据变体** ✅

Premium 计划还支持以下财报数据变体：

#### TTM (Trailing Twelve Months) 数据
- Income Statements TTM (过去12个月利润表)
- Balance Sheet Statements TTM (过去12个月资产负债表)
- Cashflow Statements TTM (过去12个月现金流量表)

#### Growth (增长率) 数据
- Income Statement Growth (利润表增长率)
- Balance Sheet Statement Growth (资产负债表增长率)
- Cashflow Statement Growth (现金流量表增长率)
- Financial Statement Growth (财务报表增长率)

#### As Reported (按报告格式) 数据
- As Reported Income Statements (按报告格式利润表)
- As Reported Balance Statements (按报告格式资产负债表)
- As Reported Cashflow Statements (按报告格式现金流量表)
- As Reported Financial Statements (按报告格式财务报表)

#### Latest (最新) 数据
- Latest Financial Statements (最新财务报表)

---

### 3. **其他相关数据** ✅

#### Financial Reports (财务报告)
- Financial Reports Dates (财务报告日期)
- Financial Reports Form 10-K JSON (10-K 报告 JSON 格式)
- Financial Reports Form 10-K XLSX (10-K 报告 Excel 格式)

#### Revenue Segmentation (收入细分)
- Revenue Product Segmentation (产品收入细分)
- Revenue Geographic Segments (地理收入细分)

---

## 🔧 当前实现状态

### ✅ **后端已实现**

**代码位置**: `backend/app/services/market_data_service.py`

**实现方法**: `get_financial_profile()` → Section 5

**代码示例**:
```python
# Income Statement
income_statement = toolkit.get_income_statement()
if income_statement is not None and not income_statement.empty:
    profile["financial_statements"]["income"] = self._dataframe_to_dict(
        income_statement, ticker
    )

# Balance Sheet
balance_sheet = toolkit.get_balance_sheet()
if balance_sheet is not None and not balance_sheet.empty:
    profile["financial_statements"]["balance"] = self._dataframe_to_dict(
        balance_sheet, ticker
    )

# Cash Flow Statement
cash_flow = toolkit.get_cash_flow_statement()
if cash_flow is not None and not cash_flow.empty:
    profile["financial_statements"]["cash_flow"] = self._dataframe_to_dict(
        cash_flow, ticker
    )
```

**API 端点**: `GET /api/v1/market/profile?symbol={SYMBOL}`

**返回数据结构**:
```json
{
  "ticker": "AAPL",
  "financial_statements": {
    "income": {
      "2023-12-31": {
        "Revenue": 383285000000,
        "Net Income": 96995000000,
        "Cost of Revenue": 214137000000,
        ...
      },
      "2022-12-31": {...},
      ...
    },
    "balance": {
      "2023-12-31": {
        "Total Assets": 352755000000,
        "Total Liabilities": 290437000000,
        "Total Equity": 62318000000,
        ...
      },
      ...
    },
    "cash_flow": {
      "2023-12-31": {
        "Operating Cash Flow": 110543000000,
        "Investing Cash Flow": -109559000000,
        "Financing Cash Flow": -110748000000,
        ...
      },
      ...
    }
  }
}
```

---

### ⚠️ **前端未实现显示**

**当前状态**: 
- ✅ 后端可以获取财报数据
- ❌ 前端还没有显示财报数据的 UI 组件
- ❌ TypeScript 接口中还没有定义 `financial_statements` 字段

**如果需要显示财报数据，需要**:
1. 更新 `frontend/src/services/api/market.ts` 中的 `FinancialProfileResponse` 接口，添加 `financial_statements` 字段
2. 在 `StrategyLab.tsx` 或其他页面中添加财报数据展示组件
3. 可以创建专门的财报数据表格或图表组件

---

## 📋 FMP Premium vs Starter 对比

| 财报数据类型 | Starter 计划 | Premium 计划 |
|------------|-------------|-------------|
| Income Statement | ✅ Annual only | ✅ Full (年度 + 季度) |
| Balance Sheet | ✅ Annual only | ✅ Full (年度 + 季度) |
| Cash Flow Statement | ✅ Annual only | ✅ Full (年度 + 季度) |
| TTM Statements | ✅ 支持 | ✅ 支持 |
| Growth Statements | ❌ 不支持 | ✅ 支持 |
| As Reported Statements | ❌ 不支持 | ✅ 支持 |
| Form 10-K Reports | ❌ 不支持 | ✅ 支持 |
| Revenue Segmentation | ❌ 不支持 | ✅ 支持 |
| 历史数据范围 | 5年 | 30+年 |

---

## ✅ **结论**

### 可以获取财报数据吗？

**答案：✅ 可以！**

1. **FMP Premium 计划完全支持**：
   - ✅ Income Statement (利润表)
   - ✅ Balance Sheet (资产负债表)
   - ✅ Cash Flow Statement (现金流量表)
   - ✅ 以及各种变体（TTM、Growth、As Reported等）

2. **后端已经实现**：
   - ✅ `get_financial_profile()` 方法已经包含财报数据获取逻辑
   - ✅ 使用 FinanceToolkit 的 `get_income_statement()`, `get_balance_sheet()`, `get_cash_flow_statement()` 方法
   - ✅ 数据通过 `/api/v1/market/profile` 端点返回

3. **前端显示待实现**：
   - ⚠️ 前端还没有显示财报数据的 UI 组件
   - ⚠️ TypeScript 接口需要更新以包含 `financial_statements` 字段

### 推荐操作

1. **购买 FMP Premium 年付计划** ($708/年) 可以确保：
   - ✅ 获取完整、准确的财报数据
   - ✅ 支持年度和季度财报
   - ✅ 30+年的历史财报数据
   - ✅ 支持 US, UK, Canada 三个市场

2. **如果需要在前端显示财报数据**：
   - 可以创建财报数据展示组件
   - 可以添加财报数据表格或图表
   - 可以集成到 StrategyLab 页面或其他分析页面

---

**文档创建时间**: 2024-12-19
**相关文档**: 
- `docs/FMP_PREMIUM_PLAN_ANALYSIS.md`
- `docs/FMP_PREMIUM_FUNDAMENTALS_CONFIRMATION.md`
