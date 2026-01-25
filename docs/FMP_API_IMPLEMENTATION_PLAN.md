# FMP API 核心功能实现计划

**目标**: 为实时交易量化分析策略系统实现核心 FMP API  
**优先级**: 基于量化交易策略系统的实际需求  
**状态**: 规划阶段

---

## 📊 核心 API 分类

### 🔴 P0 - 实时交易必需 (最高优先级)

#### 1. 实时报价数据
- [x] ✅ **Stock Quote API** - 已实现 (`/api/v1/market/quote`)
- [ ] ⏳ **Batch Quote API** - 批量报价（监控多个标的）
- [ ] ⏳ **Aftermarket Quote API** - 盘后报价
- [ ] ⏳ **Quote Short API** - 快速报价（轻量级）

**用途**: 实时监控价格、成交量、涨跌幅

---

#### 2. 历史价格数据（多时间间隔）
- [x] ✅ **Daily Historical Price** - 已实现（通过 FinanceToolkit）
- [ ] ⏳ **1-Minute Interval** - 1分钟K线（日内交易必需）
- [ ] ⏳ **5-Minute Interval** - 5分钟K线
- [ ] ⏳ **15-Minute Interval** - 15分钟K线
- [ ] ⏳ **30-Minute Interval** - 30分钟K线
- [ ] ⏳ **1-Hour Interval** - 1小时K线
- [ ] ⏳ **4-Hour Interval** - 4小时K线

**用途**: 技术分析、策略回测、多时间框架分析

---

#### 3. 技术指标 API
- [x] ✅ **部分技术指标** - 已实现（通过 FinanceToolkit）
- [ ] ⏳ **SMA (Simple Moving Average)** - 简单移动平均
- [ ] ⏳ **EMA (Exponential Moving Average)** - 指数移动平均
- [ ] ⏳ **RSI (Relative Strength Index)** - 相对强弱指标
- [ ] ⏳ **ADX (Average Directional Index)** - 平均趋向指标
- [ ] ⏳ **MACD** - 已实现（通过 FinanceToolkit）
- [ ] ⏳ **Bollinger Bands** - 已实现（通过 FinanceToolkit）

**用途**: 策略信号生成、技术分析

---

### 🟡 P1 - 策略分析必需 (高优先级)

#### 4. 市场表现数据
- [ ] ⏳ **Sector Performance Snapshot** - 板块表现
- [ ] ⏳ **Industry Performance Snapshot** - 行业表现
- [ ] ⏳ **Biggest Gainers** - 最大涨幅股票
- [ ] ⏳ **Biggest Losers** - 最大跌幅股票
- [ ] ⏳ **Most Actives** - 最活跃股票

**用途**: 市场扫描、机会发现、相对强弱分析

---

#### 5. 分析师数据
- [ ] ⏳ **Analyst Estimates** - 分析师预测（EPS, Revenue）
- [ ] ⏳ **Price Target Summary** - 目标价汇总
- [ ] ⏳ **Price Target Consensus** - 目标价共识
- [ ] ⏳ **Stock Grades** - 股票评级
- [ ] ⏳ **Ratings Snapshot** - 评级快照

**用途**: 基本面分析、估值参考

---

#### 6. 财务数据（已部分实现）
- [x] ✅ **Income Statement** - 已实现
- [x] ✅ **Balance Sheet** - 已实现
- [x] ✅ **Cash Flow Statement** - 已实现
- [x] ✅ **Key Metrics** - 已实现（通过 FinanceToolkit）
- [x] ✅ **Financial Ratios** - 已实现（通过 FinanceToolkit）
- [ ] ⏳ **Key Metrics TTM** - 过去12个月关键指标
- [ ] ⏳ **Ratios TTM** - 过去12个月财务比率

**用途**: 基本面分析、估值模型

---

#### 7. 估值模型
- [ ] ⏳ **DCF Valuation** - 现金流折现估值
- [ ] ⏳ **Levered DCF** - 杠杆DCF
- [x] ✅ **部分估值模型** - 已实现（通过 FinanceToolkit）

**用途**: 内在价值计算、投资决策

---

### 🟢 P2 - 增强功能 (中优先级)

#### 8. 实时事件日历
- [ ] ⏳ **Earnings Calendar** - 财报日历
- [ ] ⏳ **Dividends Calendar** - 分红日历
- [ ] ⏳ **Splits Calendar** - 拆股日历
- [ ] ⏳ **IPOs Calendar** - IPO日历

**用途**: 事件驱动策略、风险规避

---

#### 9. 新闻与公告
- [ ] ⏳ **Stock News** - 股票新闻
- [ ] ⏳ **Press Releases** - 公司公告
- [ ] ⏳ **General News** - 综合新闻

**用途**: 情绪分析、事件驱动策略

---

#### 10. 市场数据
- [ ] ⏳ **Market Hours** - 交易时间
- [ ] ⏳ **Holidays By Exchange** - 交易所假期
- [ ] ⏳ **Stock Price Change** - 价格变动统计

**用途**: 交易时间管理、市场状态判断

---

## 🎯 实现优先级总结

### 🔴 P0 - 必须立即实现（实时交易核心）

1. **批量报价 API** - 监控多个标的
2. **多时间间隔历史数据** - 1min, 5min, 15min, 30min, 1hour
3. **技术指标 API** - SMA, EMA, RSI, ADX（直接调用 FMP，不依赖 FinanceToolkit）

**原因**: 
- 实时交易需要多标的监控
- 量化策略需要多时间框架数据
- 技术指标是策略信号的基础

---

### 🟡 P1 - 策略分析必需（1-2周内）

4. **市场表现数据** - 板块/行业表现、涨跌幅排行
5. **分析师数据** - 目标价、评级、预测
6. **TTM 财务数据** - 过去12个月指标

**原因**:
- 市场扫描和机会发现
- 基本面分析支持
- 估值参考

---

### 🟢 P2 - 增强功能（后续）

7. **实时事件日历** - 财报、分红、拆股
8. **新闻与公告** - 情绪分析
9. **市场数据** - 交易时间、假期

---

## 📋 实现计划

### Phase 1: 实时数据核心（Week 1）

**目标**: 实现实时交易必需的数据获取能力

#### 1.1 批量报价 API
```python
# backend/app/services/market_data_service.py
def get_batch_quotes(self, symbols: List[str]) -> Dict[str, Any]:
    """Get real-time quotes for multiple symbols."""
    # 直接调用 FMP API: /stable/batch-quote?symbols=AAPL,MSFT,GOOG
```

#### 1.2 多时间间隔历史数据
```python
def get_historical_price(
    self, 
    symbol: str, 
    interval: str = "1day",  # 1min, 5min, 15min, 30min, 1hour, 1day
    limit: int = 100
) -> Dict[str, Any]:
    """Get historical price data with various intervals."""
    # 直接调用 FMP API: /stable/historical-chart/{interval}?symbol=AAPL
```

#### 1.3 技术指标 API（直接调用 FMP）
```python
def get_technical_indicator(
    self,
    symbol: str,
    indicator: str,  # sma, ema, rsi, adx, etc.
    period_length: int = 10,
    timeframe: str = "1day"
) -> Dict[str, Any]:
    """Get technical indicator data from FMP."""
    # 直接调用 FMP API: /stable/technical-indicators/{indicator}?symbol=AAPL&periodLength=10&timeframe=1day
```

---

### Phase 2: 策略分析支持（Week 2）

#### 2.1 市场表现数据
```python
def get_sector_performance(self, date: str = None) -> Dict[str, Any]:
    """Get sector performance snapshot."""
    
def get_industry_performance(self, date: str = None) -> Dict[str, Any]:
    """Get industry performance snapshot."""
    
def get_biggest_gainers(self) -> List[Dict[str, Any]]:
    """Get biggest stock gainers."""
    
def get_biggest_losers(self) -> List[Dict[str, Any]]:
    """Get biggest stock losers."""
    
def get_most_actives(self) -> List[Dict[str, Any]]:
    """Get most actively traded stocks."""
```

#### 2.2 分析师数据
```python
def get_analyst_estimates(
    self, 
    symbol: str, 
    period: str = "annual"  # annual, quarter
) -> Dict[str, Any]:
    """Get analyst financial estimates."""
    
def get_price_target_summary(self, symbol: str) -> Dict[str, Any]:
    """Get price target summary."""
    
def get_stock_grades(self, symbol: str) -> List[Dict[str, Any]]:
    """Get stock grades/ratings."""
```

#### 2.3 TTM 财务数据
```python
def get_key_metrics_ttm(self, symbol: str) -> Dict[str, Any]:
    """Get trailing twelve months key metrics."""
    
def get_ratios_ttm(self, symbol: str) -> Dict[str, Any]:
    """Get trailing twelve months financial ratios."""
```

---

### Phase 3: 增强功能（Week 3+）

#### 3.1 实时事件日历
```python
def get_earnings_calendar(
    self, 
    from_date: str = None, 
    to_date: str = None
) -> List[Dict[str, Any]]:
    """Get earnings calendar."""
    
def get_dividends_calendar(
    self,
    from_date: str = None,
    to_date: str = None
) -> List[Dict[str, Any]]:
    """Get dividends calendar."""
```

#### 3.2 新闻与公告
```python
def get_stock_news(
    self, 
    symbol: str = None, 
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Get stock news."""
    
def get_press_releases(
    self,
    symbol: str = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """Get company press releases."""
```

---

## 🔧 技术实现方案

### 方案选择

**选项 1**: 直接调用 FMP API（推荐）
- ✅ 实时数据，延迟低
- ✅ 数据完整，功能丰富
- ✅ 不依赖 FinanceToolkit 的封装
- ⚠️ 需要处理 API 限流和错误

**选项 2**: 通过 FinanceToolkit
- ✅ 已有封装，代码简洁
- ❌ 可能不支持所有 FMP API
- ❌ 可能有延迟或数据不完整

**决策**: **混合方案**
- **实时数据**（Quote, Historical Price, Technical Indicators）→ 直接调用 FMP API
- **基本面数据**（Financial Statements, Ratios）→ 继续使用 FinanceToolkit（已实现）

---

### 实现架构

```python
# backend/app/services/market_data_service.py

class MarketDataService:
    def __init__(self):
        self._fmp_api_key = settings.financial_modeling_prep_key
        self._fmp_base_url = "https://financialmodelingprep.com/stable"
        self._http_client = httpx.AsyncClient(timeout=30.0)
    
    async def _call_fmp_api(
        self, 
        endpoint: str, 
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Direct FMP API call with error handling and rate limiting."""
        url = f"{self._fmp_base_url}/{endpoint}"
        params = params or {}
        params["apikey"] = self._fmp_api_key
        
        try:
            response = await self._http_client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"FMP API error: {e}")
            raise
    
    # P0: Real-time data
    async def get_batch_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        """Get real-time quotes for multiple symbols."""
        symbols_str = ",".join(symbols)
        return await self._call_fmp_api("batch-quote", {"symbols": symbols_str})
    
    async def get_historical_price(
        self,
        symbol: str,
        interval: str = "1day",
        limit: int = 100
    ) -> Dict[str, Any]:
        """Get historical price data with various intervals."""
        endpoint_map = {
            "1min": "historical-chart/1min",
            "5min": "historical-chart/5min",
            "15min": "historical-chart/15min",
            "30min": "historical-chart/30min",
            "1hour": "historical-chart/1hour",
            "4hour": "historical-chart/4hour",
            "1day": "historical-price-eod/full",
        }
        endpoint = endpoint_map.get(interval, "historical-price-eod/full")
        return await self._call_fmp_api(endpoint, {"symbol": symbol})
    
    async def get_technical_indicator(
        self,
        symbol: str,
        indicator: str,
        period_length: int = 10,
        timeframe: str = "1day"
    ) -> Dict[str, Any]:
        """Get technical indicator data."""
        endpoint = f"technical-indicators/{indicator}"
        return await self._call_fmp_api(
            endpoint,
            {
                "symbol": symbol,
                "periodLength": period_length,
                "timeframe": timeframe,
            }
        )
    
    # P1: Market performance
    async def get_sector_performance(self, date: str = None) -> Dict[str, Any]:
        """Get sector performance snapshot."""
        params = {}
        if date:
            params["date"] = date
        return await self._call_fmp_api("sector-performance-snapshot", params)
    
    # ... 其他方法
```

---

## 📊 API 端点规划

### 后端 API 端点

```python
# backend/app/api/endpoints/market.py

# P0: Real-time data
@router.get("/quotes/batch")
async def get_batch_quotes(symbols: str) -> Dict[str, Any]:
    """Get real-time quotes for multiple symbols."""
    
@router.get("/historical/{interval}")
async def get_historical_price(
    symbol: str,
    interval: str,  # 1min, 5min, 15min, 30min, 1hour, 1day
    limit: int = 100
) -> Dict[str, Any]:
    """Get historical price data with various intervals."""
    
@router.get("/technical/{indicator}")
async def get_technical_indicator(
    symbol: str,
    indicator: str,  # sma, ema, rsi, adx
    period_length: int = 10,
    timeframe: str = "1day"
) -> Dict[str, Any]:
    """Get technical indicator data."""

# P1: Market performance
@router.get("/market/sector-performance")
async def get_sector_performance(date: str = None) -> Dict[str, Any]:
    """Get sector performance snapshot."""
    
@router.get("/market/biggest-gainers")
async def get_biggest_gainers() -> List[Dict[str, Any]]:
    """Get biggest stock gainers."""
    
@router.get("/market/biggest-losers")
async def get_biggest_losers() -> List[Dict[str, Any]]:
    """Get biggest stock losers."""
    
@router.get("/market/most-actives")
async def get_most_actives() -> List[Dict[str, Any]]:
    """Get most actively traded stocks."""

# P1: Analyst data
@router.get("/analyst/estimates")
async def get_analyst_estimates(
    symbol: str,
    period: str = "annual"
) -> Dict[str, Any]:
    """Get analyst financial estimates."""
    
@router.get("/analyst/price-target")
async def get_price_target_summary(symbol: str) -> Dict[str, Any]:
    """Get price target summary."""
    
@router.get("/analyst/grades")
async def get_stock_grades(symbol: str) -> List[Dict[str, Any]]:
    """Get stock grades/ratings."""
```

---

## ⚠️ 注意事项

### 1. API 限流
- FMP 付费版本有 API 调用限制
- 需要实现缓存机制
- 需要实现请求队列和限流

### 2. 错误处理
- 网络错误重试
- API 限流处理
- 数据格式验证

### 3. 缓存策略
- **实时数据**（Quote）: 缓存 1-5 秒
- **历史数据**（Historical）: 缓存 1-5 分钟
- **技术指标**: 缓存 5-10 分钟
- **市场表现**: 缓存 1-5 分钟
- **分析师数据**: 缓存 1 小时
- **财务数据**: 缓存 1 天

### 4. 数据同步
- 实时数据需要 WebSocket 或轮询
- 历史数据可以批量获取
- 技术指标可以按需计算或缓存

---

## 📝 下一步行动

1. ✅ **确认 FMP API Key** - 确保已配置付费 API Key
2. ⏳ **实现 Phase 1** - 实时数据核心（批量报价、多时间间隔、技术指标）
3. ⏳ **实现 Phase 2** - 策略分析支持（市场表现、分析师数据）
4. ⏳ **实现 Phase 3** - 增强功能（事件日历、新闻）

---

**创建日期**: 2025-01-24  
**目标**: 实时交易量化分析策略系统  
**优先级**: P0 > P1 > P2
