# FMP Premium 计划 - 基本面数据确认

## 📊 截图中的基本面数据支持情况

根据 FMP Premium 计划文档和代码实现，以下是截图显示的基本面数据在 Premium 计划中的支持情况：

### ✅ **完全支持的数据**

#### 1. **P/E Ratio (市盈率)**
- **FMP API 端点**: `/ratios` 或 `/ratios-ttm`
- **数据类别**: Valuation Ratios (估值比率)
- **Premium 支持**: ✅ **完全支持**
- **数据字段**: `PE`, `P/E`, `Price Earnings Ratio`, `Price-Earnings Ratio`
- **代码位置**: `frontend/src/pages/StrategyLab.tsx` (line 1168)
- **数据源**: `financialProfile?.ratios?.valuation`

#### 2. **P/B Ratio (市净率)**
- **FMP API 端点**: `/ratios` 或 `/ratios-ttm`
- **数据类别**: Valuation Ratios (估值比率)
- **Premium 支持**: ✅ **完全支持**
- **数据字段**: `PB`, `P/B`, `Price to Book Ratio`, `Price-Book Ratio`
- **代码位置**: `frontend/src/pages/StrategyLab.tsx` (line 1174)
- **数据源**: `financialProfile?.ratios?.valuation`

#### 3. **ROE (Return on Equity, 净资产收益率)**
- **FMP API 端点**: `/ratios` 或 `/ratios-ttm`
- **数据类别**: Profitability Ratios (盈利能力比率)
- **Premium 支持**: ✅ **完全支持**
- **数据字段**: `ROE`, `Return on Equity`
- **代码位置**: `frontend/src/pages/StrategyLab.tsx` (line 1180)
- **数据源**: `financialProfile?.ratios?.profitability`

#### 4. **ROA (Return on Assets, 资产收益率)**
- **FMP API 端点**: `/ratios` 或 `/ratios-ttm`
- **数据类别**: Profitability Ratios (盈利能力比率)
- **Premium 支持**: ✅ **完全支持**
- **数据字段**: `ROA`, `Return on Assets`
- **代码位置**: `frontend/src/pages/StrategyLab.tsx` (line 1186)
- **数据源**: `financialProfile?.ratios?.profitability`

### ⚠️ **部分支持的数据**

#### 5. **Health Score (健康评分)**
- **FMP API 端点**: `/financial-scores` (Premium 支持)
- **数据类别**: Financial Scores
- **Premium 支持**: ⚠️ **部分支持** (后端会自行计算)
- **说明**: 
  - FMP Premium 提供 "Financial Scores" 端点，但后端代码 (`backend/app/services/market_data_service.py`) 会基于财务比率自行计算 Health Score
  - 计算逻辑包括：债务比率、盈利能力、流动性等多个因素
  - 评分范围：0-100，分为 excellent (≥80), good (≥60), fair (≥40), poor (<40)
- **代码位置**: 
  - 计算: `backend/app/services/market_data_service.py` (line 1500-1538)
  - 显示: `frontend/src/pages/StrategyLab.tsx` (line 1188)
- **数据源**: `financialProfile?.analysis?.health_score`

---

## 📋 FMP Premium 计划中的相关端点

### 财务比率端点 (Financial Ratios)

根据 FMP Premium 计划文档，以下端点**完全支持**：

1. **Financial Ratios** (`/ratios`)
   - 提供所有类别的财务比率
   - 包括：Valuation, Profitability, Solvency, Liquidity, Efficiency
   - **Premium**: ✅ 完全支持 (US, UK, Canada)

2. **Financial Ratios TTM** (`/ratios-ttm`)
   - 提供过去12个月（Trailing Twelve Months）的财务比率
   - **Premium**: ✅ 完全支持 (US, UK, Canada)

3. **Financial Scores** (`/financial-scores`)
   - 提供财务评分数据
   - **Premium**: ✅ 完全支持 (US, UK, Canada)

### 与 Starter 计划的对比

| 数据项 | Starter 计划 | Premium 计划 |
|--------|-------------|-------------|
| Financial Ratios | ⚠️ Annual only (年度数据) | ✅ Full Ratios (完整数据) |
| Financial Ratios TTM | ✅ 支持 | ✅ 支持 |
| Financial Scores | ✅ 支持 | ✅ 支持 |
| 数据更新频率 | 较低 | 较高 |
| 历史数据范围 | 5年 | 30+年 |

---

## ✅ **结论**

### 截图中的基本面数据支持情况：

1. ✅ **P/E Ratio**: Premium 计划**完全支持**
2. ✅ **P/B Ratio**: Premium 计划**完全支持**
3. ✅ **ROE**: Premium 计划**完全支持**
4. ✅ **ROA**: Premium 计划**完全支持**
5. ⚠️ **Health Score**: Premium 计划提供 Financial Scores 端点，但后端会基于财务数据自行计算更详细的健康评分

### 数据获取方式：

- **后端实现**: `backend/app/services/market_data_service.py` → `get_financial_profile()`
- **数据源**: FinanceToolkit (可以从 FMP API 获取数据)
- **API 端点**: `/api/market/profile?symbol={SYMBOL}`
- **前端显示**: `frontend/src/pages/StrategyLab.tsx` → Fundamentals 部分

### 推荐：

**购买 FMP Premium 年付计划 ($708/年)** 可以确保：
- ✅ 获取完整、准确的财务比率数据（P/E, P/B, ROE, ROA）
- ✅ 更高的数据更新频率
- ✅ 30+年的历史数据范围
- ✅ 支持 US, UK, Canada 三个市场

**注意**: 即使使用 Premium 计划，Health Score 仍然由后端基于财务数据计算，而不是直接从 FMP API 获取。这是为了提供更符合 ThetaMind 业务逻辑的健康评分。

---

**文档创建时间**: 2024-12-19
**相关文档**: `docs/FMP_PREMIUM_PLAN_ANALYSIS.md`
