# StrategyLab 布局重新设计

## 用户需求

1. ✅ 左侧菜单改为可折叠抽屉（桌面端和移动端都支持）
2. ✅ 期权链和股票实时数据非常重要，放到上面
3. ✅ 重新组织 Strategy Builder、Trade Execution、Portfolio Greeks 等布局

## 实现的改进

### 1. 左侧菜单可折叠抽屉

**文件**: `frontend/src/components/layout/MainLayout.tsx`

**改进**:
- 添加了 `sidebarOpen` 状态管理，支持桌面端和移动端
- 使用 `localStorage` 保存用户的折叠偏好
- 添加了折叠/展开按钮（在所有屏幕尺寸都可见）
- 主内容区域根据侧边栏状态动态调整 padding

**关键代码**:
```typescript
const [sidebarOpen, setSidebarOpen] = useState(() => {
  const saved = localStorage.getItem("sidebarOpen")
  if (saved !== null) return saved === "true"
  return window.innerWidth >= 1024  // 默认桌面端打开
})

// 主内容区域动态调整
<div className={cn(
  "flex flex-1 flex-col transition-all duration-300",
  sidebarOpen ? "lg:pl-64" : "lg:pl-0"
)}>
```

### 2. 新布局结构

**文件**: `frontend/src/pages/StrategyLab.tsx`

**新布局层次**:

```
┌─────────────────────────────────────────┐
│  Header: Strategy Lab                    │
├─────────────────────────────────────────┤
│  Top: Real-time Stock Data (最重要)     │
│  - Symbol, Exchange, Price, Source      │
├─────────────────────────────────────────┤
│  Option Chain (最重要，占据主要空间)    │
│  - 完整的期权链表格                      │
├─────────────────────────────────────────┤
│  Main Layout (12 columns)              │
│  ├─ Left (4 cols): Strategy Builder    │
│  │  - Symbol & Expiration Date          │
│  │  - Strategy Templates                │
│  │  - Option Legs                       │
│  │  - Save & Analyze buttons            │
│  │                                      │
│  └─ Right (8 cols):                    │
│     ├─ Trade Execution                  │
│     ├─ Portfolio Greeks                 │
│     ├─ Key Metrics                      │
│     ├─ Charts (Payoff & AI Chart)       │
│     ├─ Scenario Simulator               │
│     └─ Market Data Panel                │
│        - Market Chart                   │
│        - Fundamentals                   │
│        - Technicals                     │
└─────────────────────────────────────────┘
```

### 3. 布局优化详情

#### 顶部：实时股票数据
- **位置**: 页面最顶部，紧跟在标题后
- **内容**: Symbol, Exchange, Price (带实时更新效果), Source
- **重要性**: ⭐⭐⭐⭐⭐ 最重要

#### 期权链表格
- **位置**: 实时数据下方，独立的大卡片
- **空间**: 占据完整宽度，不再被挤压
- **重要性**: ⭐⭐⭐⭐⭐ 最重要
- **功能**: 可以直接点击 Bid/Ask 添加策略腿

#### 左侧：Strategy Builder (30%)
- **内容**:
  - Symbol 搜索
  - Expiration Date 选择
  - Strategy Templates
  - Option Legs 管理
  - Save & Analyze 按钮

#### 右侧：交易和分析工具 (70%)
- **Trade Execution**: Smart Price Advisor（智能价格建议）
- **Portfolio Greeks**: 组合 Greeks 显示
- **Key Metrics**: Max Profit, Max Loss, Win Rate
- **Charts**: Payoff Diagram 和 AI Chart
- **Scenario Simulator**: 情景模拟器
- **Market Data Panel**: 
  - Market Chart（实时K线图）
  - Fundamentals（基本面数据）
  - Technicals（技术指标）

### 4. 移除的组件

- ❌ 从左侧移除了 SmartPriceAdvisor（已移至右侧）
- ❌ 从右侧移除了 AnomalyRadar（保留在侧边栏底部）
- ❌ 从 Data Panel 移除了 Option Chain（已提升到顶部独立显示）

## 布局比例

- **左侧 Strategy Builder**: `lg:col-span-4` (33%)
- **右侧交易和分析**: `lg:col-span-8` (67%)

## 响应式设计

- **移动端**: 所有列堆叠显示
- **平板端**: 保持两列布局
- **桌面端**: 完整的三列布局（侧边栏 + 主内容两列）

## 用户体验改进

1. ✅ **期权链更突出**: 从右侧小面板提升到顶部独立大卡片
2. ✅ **实时数据更显眼**: 放在最顶部，一眼就能看到
3. ✅ **侧边栏可折叠**: 给主内容更多空间
4. ✅ **布局更清晰**: 按重要性分层，重要内容在上方
5. ✅ **减少滚动**: 关键信息都在首屏可见

## 文件修改清单

1. `frontend/src/components/layout/MainLayout.tsx`
   - 添加侧边栏折叠功能
   - 添加 localStorage 持久化
   - 优化响应式行为

2. `frontend/src/pages/StrategyLab.tsx`
   - 重新组织布局结构
   - 将期权链提升到顶部
   - 重新分配左右列内容
   - 优化 Market Data Panel

3. `frontend/src/components/market/OptionChainVisualization.tsx`
   - 移除多余的 Card 包装（已在顶部独立显示）

## 下一步优化建议

1. **可调整列宽**: 允许用户拖拽调整左右列宽度
2. **布局预设**: 保存用户偏好的布局配置
3. **快捷键**: 添加快捷键切换侧边栏
4. **动画优化**: 添加更流畅的过渡动画
