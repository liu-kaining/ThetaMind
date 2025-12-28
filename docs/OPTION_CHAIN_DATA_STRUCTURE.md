# 期权链数据结构详细分析

## 📦 当前数据格式

### API 响应结构

```typescript
interface OptionChainResponse {
  symbol: string                    // "AAPL"
  expiration_date: string           // "2025-01-17"
  spot_price: number                // 150.25
  calls: Option[]                   // Call期权数组
  puts: Option[]                    // Put期权数组
  _source?: string                  // "api" | "cache"
}

interface Option {
  strike: number                    // 执行价 (必需)
  bid: number                       // 买价 (默认0)
  ask: number                       // 卖价 (默认0)
  volume: number                    // 成交量 (默认0)
  open_interest: number             // 持仓量 (默认0)
  
  // Greeks (可选)
  delta?: number                    // -1 到 1
  gamma?: number                    // 通常 > 0
  theta?: number                    // 通常 < 0 (时间衰减)
  vega?: number                     // 通常 > 0
  rho?: number                      // 通常很小
  
  // Greeks 嵌套格式（也支持）
  greeks?: {
    delta?: number
    gamma?: number
    theta?: number
    vega?: number
    rho?: number
  }
  
  // 隐含波动率 (可选)
  implied_volatility?: number       // 0-1 之间的小数 (如 0.25 = 25%)
  implied_vol?: number              // 同上（简写）
  
  // 其他字段（向后兼容）
  [key: string]: any
}
```

### 数据示例

```json
{
  "symbol": "AAPL",
  "expiration_date": "2025-01-17",
  "spot_price": 150.25,
  "calls": [
    {
      "strike": 145.0,
      "bid": 8.5,
      "ask": 8.7,
      "volume": 1250,
      "open_interest": 5000,
      "delta": 0.65,
      "gamma": 0.02,
      "theta": -0.15,
      "vega": 0.25,
      "implied_volatility": 0.25
    },
    {
      "strike": 150.0,
      "bid": 5.2,
      "ask": 5.4,
      "volume": 5000,
      "open_interest": 15000,
      "delta": 0.50,
      "gamma": 0.03,
      "theta": -0.18,
      "vega": 0.28,
      "implied_volatility": 0.28
    }
  ],
  "puts": [
    {
      "strike": 145.0,
      "bid": 2.1,
      "ask": 2.3,
      "volume": 800,
      "open_interest": 3000,
      "delta": -0.35,
      "gamma": 0.02,
      "theta": -0.15,
      "vega": 0.25,
      "implied_volatility": 0.25
    },
    {
      "strike": 150.0,
      "bid": 5.0,
      "ask": 5.2,
      "volume": 4000,
      "open_interest": 12000,
      "delta": -0.50,
      "gamma": 0.03,
      "theta": -0.18,
      "vega": 0.28,
      "implied_volatility": 0.28
    }
  ]
}
```

---

## 🔄 数据转换需求

### 转换1: 价格视图（Candlestick样式）

**目标格式：** Bar Chart 数据（模拟K线）

```typescript
interface PriceChartDataPoint {
  strike: number          // X轴：执行价
  mid: number            // 中间价 (bid + ask) / 2
  bid: number            // 买价
  ask: number            // 卖价
  spread: number         // 价差 (ask - bid)
  
  // 用于绘制"K线"样式
  open: number           // = bid
  high: number           // = ask
  low: number            // = bid
  close: number          // = mid
}

// 转换逻辑
function transformToPriceChartData(options: Option[]): PriceChartDataPoint[] {
  return options
    .filter(opt => opt.bid > 0 && opt.ask > 0)  // 过滤无效数据
    .map(opt => ({
      strike: opt.strike,
      mid: (opt.bid + opt.ask) / 2,
      bid: opt.bid,
      ask: opt.ask,
      spread: opt.ask - opt.bid,
      open: opt.bid,
      high: opt.ask,
      low: opt.bid,
      close: (opt.bid + opt.ask) / 2,
    }))
    .sort((a, b) => a.strike - b.strike)  // 按执行价排序
}
```

**可视化方式：**
- 使用 `recharts` 的 `BarChart`，自定义样式
- 每个Bar表示一个执行价的价差范围
- Bar的底部 = bid，顶部 = ask，中间线 = mid

---

### 转换2: IV视图（Area Chart）

**目标格式：** Area Chart 数据

```typescript
interface IVChartDataPoint {
  strike: number
  iv: number              // 隐含波动率 (%)
  ivPercent: number       // IV * 100 (用于显示)
}

// 转换逻辑
function transformToIVChartData(options: Option[]): IVChartDataPoint[] {
  return options
    .filter(opt => opt.implied_volatility !== undefined)
    .map(opt => ({
      strike: opt.strike,
      iv: opt.implied_volatility ?? opt.implied_vol ?? 0,
      ivPercent: (opt.implied_volatility ?? opt.implied_vol ?? 0) * 100,
    }))
    .sort((a, b) => a.strike - b.strike)
}

// 计算IV百分位数（用于颜色编码）
function calculateIVPercentiles(data: IVChartDataPoint[]): {
  p25: number
  p50: number
  p75: number
} {
  const ivs = data.map(d => d.iv).sort((a, b) => a - b)
  return {
    p25: ivs[Math.floor(ivs.length * 0.25)],
    p50: ivs[Math.floor(ivs.length * 0.50)],
    p75: ivs[Math.floor(ivs.length * 0.75)],
  }
}
```

**可视化方式：**
- 使用 `recharts` 的 `AreaChart`
- X轴：执行价
- Y轴：IV (%)
- 颜色编码：根据IV百分位数填充不同颜色

---

### 转换3: Greeks视图（Multi-Line Chart）

**目标格式：** Multi-Line Chart 数据

```typescript
interface GreeksChartDataPoint {
  strike: number
  delta?: number
  gamma?: number
  theta?: number
  vega?: number
  rho?: number
}

// 转换逻辑
function transformToGreeksChartData(options: Option[]): GreeksChartDataPoint[] {
  return options
    .map(opt => {
      // 从直接字段或嵌套对象中提取Greeks
      const getGreek = (name: string) => {
        return opt[name] ?? opt.greeks?.[name]
      }
      
      return {
        strike: opt.strike,
        delta: getGreek('delta'),
        gamma: getGreek('gamma'),
        theta: getGreek('theta'),
        vega: getGreek('vega'),
        rho: getGreek('rho'),
      }
    })
    .filter(point => 
      point.delta !== undefined || 
      point.gamma !== undefined || 
      point.theta !== undefined
    )  // 至少有一个Greek值
    .sort((a, b) => a.strike - b.strike)
}

// 归一化Greeks（可选，用于在同一Y轴显示）
function normalizeGreeks(data: GreeksChartDataPoint[]): GreeksChartDataPoint[] {
  // Delta: -1 到 1
  // Gamma: 通常 0 到 0.1
  // Theta: 通常 -0.5 到 0
  // Vega: 通常 0 到 0.5
  // Rho: 通常 -0.1 到 0.1
  
  // 如果需要归一化，可以使用 Min-Max 归一化
  // 但通常建议使用多个Y轴（双Y轴图表）
  return data
}
```

**可视化方式：**
- 使用 `recharts` 的 `ComposedChart` 或 `LineChart`
- 多个Line系列：Delta, Gamma, Theta, Vega, Rho
- 建议使用双Y轴（左Y轴：Delta/Gamma，右Y轴：Theta/Vega）

---

### 转换4: 活跃度视图（Bar Chart）

**目标格式：** Grouped Bar Chart 数据

```typescript
interface ActivityChartDataPoint {
  strike: number
  volume: number
  openInterest: number
  volumeFormatted: string    // 格式化后的显示（如 "1.2K"）
  oiFormatted: string
}

// 转换逻辑
function transformToActivityChartData(options: Option[]): ActivityChartDataPoint[] {
  return options
    .map(opt => ({
      strike: opt.strike,
      volume: opt.volume ?? 0,
      openInterest: opt.open_interest ?? 0,
      volumeFormatted: formatNumber(opt.volume ?? 0),
      oiFormatted: formatNumber(opt.open_interest ?? 0),
    }))
    .sort((a, b) => a.strike - b.strike)
}

// 格式化数字（用于tooltip显示）
function formatNumber(num: number): string {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
  return num.toString()
}
```

**可视化方式：**
- 使用 `recharts` 的 `BarChart`
- 分组柱状图：Volume 和 OI 并排显示
- 颜色：Volume = 蓝色，OI = 橙色

---

## 🎯 关键计算字段

### 计算字段1: Mid Price（中间价）

```typescript
const midPrice = (bid + ask) / 2
```

**用途：**
- 价格视图的中心线
- 期权选择的参考价格

---

### 计算字段2: Bid-Ask Spread（价差）

```typescript
const spread = ask - bid
const spreadPercent = (spread / midPrice) * 100
```

**用途：**
- 流动性指标（价差越小，流动性越好）
- 颜色编码（绿色=窄价差，红色=宽价差）

---

### 计算字段3: Moneyness（价内/价外程度）

```typescript
// For Call
const moneyness = (spotPrice - strike) / spotPrice  // 正数=实值，负数=虚值

// For Put
const moneyness = (strike - spotPrice) / spotPrice  // 正数=实值，负数=虚值

// 判断ATM
const isATM = Math.abs(moneyness) < 0.02  // 2%以内视为ATM
```

**用途：**
- ATM标识
- 执行价筛选（如"只显示ATM ± 10%"）

---

### 计算字段4: IV Rank（IV百分位排名）

```typescript
// 计算IV在所有期权中的排名（0-100）
function calculateIVRank(option: Option, allOptions: Option[]): number {
  const ivs = allOptions
    .map(opt => opt.implied_volatility ?? opt.implied_vol ?? 0)
    .filter(iv => iv > 0)
    .sort((a, b) => a - b)
  
  const currentIV = option.implied_volatility ?? option.implied_vol ?? 0
  const rank = ivs.findIndex(iv => iv >= currentIV)
  
  return (rank / ivs.length) * 100  // 0-100
}
```

**用途：**
- IV视图的颜色编码
- 高IV期权筛选（如"IV Rank > 75"）

---

## 🔍 数据验证和清理

### 数据验证规则

```typescript
interface ValidationResult {
  isValid: boolean
  errors: string[]
}

function validateOption(option: Option): ValidationResult {
  const errors: string[] = []
  
  // 必需字段
  if (!option.strike || option.strike <= 0) {
    errors.push("Invalid strike price")
  }
  
  // Bid/Ask 合理性检查
  if (option.bid < 0 || option.ask < 0) {
    errors.push("Bid/Ask cannot be negative")
  }
  
  if (option.bid > option.ask) {
    errors.push("Bid should not exceed Ask")
  }
  
  // Greeks 范围检查
  if (option.delta !== undefined && (option.delta < -1 || option.delta > 1)) {
    errors.push("Delta out of range (-1 to 1)")
  }
  
  if (option.implied_volatility !== undefined && 
      (option.implied_volatility < 0 || option.implied_volatility > 1)) {
    errors.push("IV out of range (0 to 1)")
  }
  
  return {
    isValid: errors.length === 0,
    errors,
  }
}
```

### 数据清理

```typescript
function cleanOptionChainData(chain: OptionChainResponse): OptionChainResponse {
  return {
    ...chain,
    calls: chain.calls
      .filter(opt => {
        const validation = validateOption(opt)
        return validation.isValid
      })
      .map(opt => ({
        ...opt,
        // 确保默认值
        bid: opt.bid ?? 0,
        ask: opt.ask ?? 0,
        volume: opt.volume ?? 0,
        open_interest: opt.open_interest ?? 0,
      })),
    puts: chain.puts
      .filter(opt => {
        const validation = validateOption(opt)
        return validation.isValid
      })
      .map(opt => ({
        ...opt,
        bid: opt.bid ?? 0,
        ask: opt.ask ?? 0,
        volume: opt.volume ?? 0,
        open_interest: opt.open_interest ?? 0,
      })),
  }
}
```

---

## 📊 数据聚合和统计

### 统计指标计算

```typescript
interface OptionChainStats {
  totalOptions: number
  atmStrike: number | null
  atmCall: Option | null
  atmPut: Option | null
  avgIV: number
  maxIV: number
  minIV: number
  avgSpread: number
  maxVolume: number
  maxOI: number
}

function calculateChainStats(chain: OptionChainResponse): OptionChainStats {
  const allOptions = [...chain.calls, ...chain.puts]
  
  // 找到ATM期权
  const atmStrike = chain.spot_price
  const atmCall = chain.calls.find(opt => 
    Math.abs(opt.strike - atmStrike) / atmStrike < 0.02
  ) || null
  const atmPut = chain.puts.find(opt => 
    Math.abs(opt.strike - atmStrike) / atmStrike < 0.02
  ) || null
  
  // IV统计
  const ivs = allOptions
    .map(opt => opt.implied_volatility ?? opt.implied_vol)
    .filter((iv): iv is number => iv !== undefined && iv > 0)
  
  const avgIV = ivs.length > 0 ? ivs.reduce((a, b) => a + b, 0) / ivs.length : 0
  const maxIV = ivs.length > 0 ? Math.max(...ivs) : 0
  const minIV = ivs.length > 0 ? Math.min(...ivs) : 0
  
  // 价差统计
  const spreads = allOptions
    .filter(opt => opt.bid > 0 && opt.ask > 0)
    .map(opt => opt.ask - opt.bid)
  const avgSpread = spreads.length > 0 
    ? spreads.reduce((a, b) => a + b, 0) / spreads.length 
    : 0
  
  // 成交量和持仓量最大值
  const maxVolume = Math.max(...allOptions.map(opt => opt.volume ?? 0))
  const maxOI = Math.max(...allOptions.map(opt => opt.open_interest ?? 0))
  
  return {
    totalOptions: allOptions.length,
    atmStrike,
    atmCall,
    atmPut,
    avgIV,
    maxIV,
    minIV,
    avgSpread,
    maxVolume,
    maxOI,
  }
}
```

---

## 🚀 性能优化建议

### 1. 数据缓存

```typescript
// 缓存转换后的数据
const chartDataCache = new Map<string, any>()

function getCachedChartData(
  chain: OptionChainResponse, 
  viewType: 'price' | 'iv' | 'greeks' | 'activity'
): any {
  const cacheKey = `${chain.symbol}-${chain.expiration_date}-${viewType}`
  
  if (chartDataCache.has(cacheKey)) {
    return chartDataCache.get(cacheKey)
  }
  
  let data
  switch (viewType) {
    case 'price':
      data = transformToPriceChartData(chain.calls)
      break
    case 'iv':
      data = transformToIVChartData(chain.calls)
      break
    // ... 其他视图
  }
  
  chartDataCache.set(cacheKey, data)
  return data
}
```

### 2. 数据采样（大数据量时）

```typescript
// 如果期权数量太多，可以采样显示
function sampleOptions(
  options: Option[], 
  maxPoints: number = 100
): Option[] {
  if (options.length <= maxPoints) {
    return options
  }
  
  // 等间隔采样
  const step = Math.floor(options.length / maxPoints)
  return options.filter((_, index) => index % step === 0)
}
```

### 3. 虚拟滚动（表格视图）

如果保留表格视图，对于大量数据，可以使用虚拟滚动：
- 只渲染可见行的DOM
- 使用 `react-window` 或 `react-virtualized`

---

## ✅ 数据完整性检查清单

- [ ] 所有期权都有有效的执行价（strike > 0）
- [ ] Bid/Ask 价格合理（bid <= ask）
- [ ] IV 值在合理范围内（0-1 或 0-100%）
- [ ] Greeks 值在合理范围内
- [ ] Call 和 Put 的执行价匹配（如果有相同执行价）
- [ ] Spot price 存在且合理
- [ ] 至少有一些期权有成交量和持仓量数据
- [ ] ATM 期权可以被识别（spot_price 附近有执行价）

---

**文档版本：** v1.0  
**创建日期：** 2025-01-XX  
**状态：** 技术参考文档

