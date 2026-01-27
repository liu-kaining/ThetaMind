# StrategyLab 最终布局设计

## 用户需求

1. ✅ Option Chain Table 和 Market Data 都放在最上面
2. ✅ Strategy Builder、Trade Execution、Charts 放一块
3. ✅ Portfolio Greeks 和 Key Metrics 可以小一些，放在 Charts 上面

## 最终布局结构

```
┌─────────────────────────────────────────────────────────┐
│  Header: Strategy Lab                                   │
├─────────────────────────────────────────────────────────┤
│  Real-time Stock Data                                   │
│  - Symbol, Exchange, Price, Source                     │
├─────────────────────────────────────────────────────────┤
│  Top Section (2 columns)                               │
│  ├─ Option Chain Table (50%)                           │
│  │  - 完整的期权链表格                                  │
│  │  - 点击 Bid/Ask 添加策略腿                          │
│  │                                                      │
│  └─ Market Data (50%)                                  │
│     - Market Chart (K线图)                             │
│     - Fundamentals (基本面数据)                       │
│     - Technicals (技术指标)                            │
├─────────────────────────────────────────────────────────┤
│  Main Layout (12 columns)                              │
│  ├─ Left (4 cols): Strategy Builder                    │
│  │  - Symbol & Expiration Date                         │
│  │  - Strategy Templates                               │
│  │  - Option Legs                                      │
│  │  - Save & Analyze buttons                           │
│  │                                                      │
│  └─ Right (8 cols):                                    │
│     ├─ Trade Execution                                 │
│     │  - Smart Price Advisor                           │
│     │                                                  │
│     ├─ Portfolio Greeks + Key Metrics (并排)          │
│     │  - Portfolio Greeks (左侧)                       │
│     │  - Key Metrics (右侧，紧凑显示)                  │
│     │                                                  │
│     ├─ Charts                                          │
│     │  - Payoff Diagram                                │
│     │  - AI Chart                                      │
│     │                                                  │
│     └─ Scenario Simulator                              │
└─────────────────────────────────────────────────────────┘
```

## 布局层次

### 1. 顶部：实时股票数据
- **位置**: 页面最顶部
- **内容**: Symbol, Exchange, Price (实时更新), Source
- **样式**: 带主色调边框的卡片

### 2. 顶部区域：Option Chain + Market Data（并排）
- **布局**: `lg:grid-cols-2` (50% / 50%)
- **左侧**: Option Chain Table
  - 完整的期权链表格
  - 可以直接点击 Bid/Ask 添加策略腿
- **右侧**: Market Data
  - Tabs: Market Chart / Fundamentals / Technicals
  - Market Chart: K线图（高度300px）
  - Fundamentals: PE, PB, ROE, Health
  - Technicals: RSI, MACD, SMA 20, Signal

### 3. 主布局：Strategy Builder + 交易分析工具
- **布局**: `lg:grid-cols-12`
- **左侧 (4 cols, 33%)**: Strategy Builder
  - Symbol 搜索
  - Expiration Date 选择
  - Strategy Templates
  - Option Legs 管理
  - Deep Research 信息
  - Save & Analyze 按钮

- **右侧 (8 cols, 67%)**: 交易和分析工具
  - **Trade Execution**: Smart Price Advisor（智能价格建议）
  - **Portfolio Greeks + Key Metrics** (并排，紧凑):
    - Portfolio Greeks（左侧）
    - Key Metrics（右侧，紧凑显示：Max Profit, Max Loss, Win Rate）
  - **Charts**: Payoff Diagram 和 AI Chart
  - **Scenario Simulator**: 情景模拟器

## 关键改进

1. ✅ **Option Chain 和 Market Data 都在顶部**
   - 并排显示，各占50%宽度
   - 最重要的数据一眼可见

2. ✅ **Strategy Builder、Trade Execution、Charts 放在一起**
   - 左侧：Strategy Builder
   - 右侧：Trade Execution → Greeks/Metrics → Charts → Simulator
   - 工作流程更顺畅

3. ✅ **Portfolio Greeks 和 Key Metrics 紧凑显示**
   - 并排显示（2列网格）
   - Key Metrics 使用更小的 padding 和字体
   - 放在 Charts 上面，不占用太多空间

4. ✅ **移除了重复的 Market Data Panel**
   - 只在顶部显示一次
   - 避免内容重复

## 响应式设计

- **移动端**: 所有列堆叠显示
- **平板端**: 保持两列布局
- **桌面端**: 完整的多列布局

## 文件修改

1. `frontend/src/pages/StrategyLab.tsx`
   - 重新组织布局结构
   - Option Chain 和 Market Data 并排放在顶部
   - Portfolio Greeks 和 Key Metrics 紧凑并排显示
   - 移除了右侧列中重复的 Market Data Panel

## 状态

✅ 布局重新设计完成
- Option Chain Table 和 Market Data 都在顶部
- Strategy Builder、Trade Execution、Charts 放在一起
- Portfolio Greeks 和 Key Metrics 紧凑显示在 Charts 上面
