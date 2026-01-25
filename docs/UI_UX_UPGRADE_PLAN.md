# ThetaMind UI/UX 升级实现计划

**目标**: 将"数据展示型"界面升级为"交互探索型"界面（Benchmark: OptionStrat）

---

## 📋 实现任务清单

### Phase 1: 核心组件升级

#### 1.1 P&L 图表交互引擎 (PayoffChart 升级)

**文件**: `frontend/src/components/charts/PayoffChart.tsx`

**功能**:
- [ ] **双线展示**:
  - Line 1 (Solid): 到期盈亏 (Expiration P&L) - 静态
  - Line 2 (Dashed/Colored): 实时/T+n 盈亏 (Current P&L) - 动态
- [ ] **交互滑块 (Control Panel)**:
  - Time Slider: "Date" - 拖动时 Line 2 逐渐向 Line 1 靠拢（Theta 衰减）
  - IV Slider: "Implied Volatility" - 拖动时展示 Vega 影响
- [ ] **增强 Tooltip**:
  - 显示: Price, Profit/Loss, Delta, Theta
  - 实时更新

**技术实现**:
- 使用 Recharts `Line` 组件
- 使用 `@radix-ui/react-slider` 实现滑块
- 计算 T+n 盈亏（考虑 Theta 衰减和 IV 变化）

---

#### 1.2 期权链表格升级 (OptionChainTable 升级)

**文件**: `frontend/src/components/market/OptionChainTable.tsx`

**功能**:
- [ ] **视觉降噪**:
  - ITM (实值): 浅黄色/浅紫色背景高亮
  - ATM (平值): Strike 附近加醒目分界线
- [ ] **Data Bars**:
  - Volume 和 OI 列：根据最大值渲染背景进度条
  - 使用 Tailwind `bg-blue-100` 且 `width: ${percent}%`
- [ ] **一键操作**:
  - 点击 Bid 价格 -> 自动添加 "Sell Leg"
  - 点击 Ask 价格 -> 自动添加 "Buy Leg"

**技术实现**:
- 计算 ITM/ATM 状态
- 使用 Tailwind 动态样式
- 添加点击事件处理

---

### Phase 2: 布局优化

#### 2.1 三栏式布局 (Desktop)

**文件**: `frontend/src/pages/StrategyLab.tsx`

**布局**:
- **Left (20%)**: 策略参数区
  - Strategy Selector
  - Expiration Date
  - Legs List
- **Center (50%)**: 交互图表区
  - P&L Chart
  - 关键指标 (Max Profit, Max Loss, Win Rate)
- **Right (30%)**: 实时异动/AI 助手
  - Live Radar (AnomalyRadar)
  - AI Copilot

**技术实现**:
- 使用 CSS Grid 或 Flexbox
- 响应式断点: `lg:grid-cols-5`

---

#### 2.2 移动端适配

**功能**:
- [ ] 隐藏期权链详情
- [ ] 只展示 P&L 图表和核心参数
- [ ] Bottom Sheet (抽屉式) 修改 Leg

**技术实现**:
- 使用 Tailwind 响应式类
- 创建 BottomSheet 组件（使用 Dialog）

---

### Phase 3: 颜色系统

#### 3.1 颜色定义

**颜色方案**:
- Profit (盈利): `emerald-500` (#10b981)
- Loss (亏损): `rose-500` (#f43f5e)
- Neutral/Info: `slate-800` (#1e293b), `cyan-400` (#22d3ee)
- AI 建议高亮: `cyan-400`

**实现**:
- [ ] 更新 Tailwind 配置（如果需要）
- [ ] 替换所有颜色引用

---

#### 3.2 暗黑模式默认启用

**文件**: `frontend/src/components/layout/MainLayout.tsx`

**实现**:
- [ ] 默认主题设置为 `dark`
- [ ] 移除主题切换（或保留但默认 dark）

---

### Phase 4: 实时感

#### 4.1 Flash Effect

**功能**:
- [ ] 当数据更新时，价格数字闪烁（绿色或红色）
- [ ] 提示用户这是实时数据

**技术实现**:
- 使用 CSS 动画 `@keyframes flash`
- 检测数据变化，触发动画
- 使用 `useEffect` 监听数据变化

---

## 🎯 实施顺序

1. **Phase 1.1**: P&L 图表交互引擎（核心功能）
2. **Phase 1.2**: 期权链表格升级（核心功能）
3. **Phase 3**: 颜色系统和暗黑模式（基础）
4. **Phase 2**: 布局优化（结构）
5. **Phase 4**: 实时感（增强）

---

## 📝 技术细节

### P&L 图表双线计算

```typescript
// 到期盈亏（静态）
const expirationPnl = calculatePnlAtExpiration(price, legs)

// 实时/T+n 盈亏（动态）
const currentPnl = calculatePnlAtTime(
  price,
  legs,
  daysRemaining, // 从 Time Slider 获取
  impliedVolatility // 从 IV Slider 获取
)
```

### Time Slider 逻辑

- 范围: 0 (Today) 到 `timeToExpiry` (Expiration)
- 拖动时: `daysRemaining = timeToExpiry - sliderValue`
- Line 2 逐渐向 Line 1 靠拢（Theta 衰减）

### IV Slider 逻辑

- 范围: 当前 IV ± 50%
- 拖动时: 重新计算 Greeks（Vega 影响）
- 更新 Line 2

### ITM/ATM 判断

```typescript
const isITM = (strike: number, spotPrice: number, type: 'call' | 'put') => {
  if (type === 'call') return strike < spotPrice
  return strike > spotPrice
}

const isATM = (strike: number, spotPrice: number) => {
  const percentDiff = Math.abs((strike - spotPrice) / spotPrice)
  return percentDiff < 0.02 // 2% 范围内视为 ATM
}
```

---

## ✅ 检查清单

- [ ] PayoffChart 双线展示
- [ ] Time Slider 交互
- [ ] IV Slider 交互
- [ ] 增强 Tooltip (Delta, Theta)
- [ ] OptionChainTable 视觉降噪
- [ ] Data Bars (Volume, OI)
- [ ] 一键操作 (Bid/Ask 点击)
- [ ] 三栏式布局
- [ ] 移动端适配
- [ ] 颜色系统更新
- [ ] 暗黑模式默认
- [ ] Flash Effect

---

**开始实施**: Phase 1.1 - P&L 图表交互引擎
