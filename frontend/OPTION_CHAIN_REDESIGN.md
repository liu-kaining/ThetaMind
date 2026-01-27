# 期权链表格重构 - 滚动、上下布局、希腊曲线弹窗

## 问题

用户反馈：
1. **分页问题**：期权链不应该使用分页，应该使用滚动，并且默认定位到当前股价附近的期权价格位置
2. **Visual View 无用**：Visual View 感觉没什么用，应该和表格结合起来
3. **希腊字母交互**：鼠标点击某个希腊字母时，应该弹窗显示曲线，交互要很棒
4. **布局问题**：Call 和 Put 应该同一个价格，要上下放，而不是左右放，左右不好设置策略的

## 解决方案

### 1. 移除分页，改为滚动

**文件**: `frontend/src/components/market/OptionChainTable.tsx`

**改动**:
- ✅ 移除 `currentPage`、`rowsPerPage`、`totalPages` 等分页相关状态
- ✅ 移除分页 UI 组件（按钮、页码显示）
- ✅ 添加 `scrollContainerRef` 用于滚动控制
- ✅ 实现自动滚动到 ATM（At The Money）附近的位置
- ✅ 使用 `allStrikes` 直接渲染所有数据，不再切片

**自动滚动逻辑**:
```typescript
// 找到最接近当前股价的 strike 索引
const atmStrikeIndex = React.useMemo(() => {
  if (!spotPrice || allStrikes.length === 0) return 0
  let closestIndex = 0
  let minDistance = Infinity
  allStrikes.forEach((strike, index) => {
    const distance = Math.abs(strike - spotPrice)
    if (distance < minDistance) {
      minDistance = distance
      closestIndex = index
    }
  })
  return closestIndex
}, [allStrikes, spotPrice])

// 自动滚动到 ATM strike
React.useEffect(() => {
  if (scrollContainerRef.current && allStrikes.length > 0) {
    setTimeout(() => {
      const container = scrollContainerRef.current
      if (!container) return
      
      const rows = container.querySelectorAll('tbody tr')
      if (rows.length > atmStrikeIndex) {
        const targetRow = rows[atmStrikeIndex] as HTMLElement
        if (targetRow) {
          const rowTop = targetRow.offsetTop
          const containerHeight = container.clientHeight
          const rowHeight = targetRow.clientHeight
          const scrollPosition = rowTop - (containerHeight / 2) + (rowHeight / 2)
          
          container.scrollTo({
            top: Math.max(0, scrollPosition),
            behavior: 'smooth'
          })
        }
      }
    }, 100)
  }
}, [allStrikes.length, atmStrikeIndex])
```

### 2. 改变表格布局：Call 和 Put 上下排列

**改动**:
- ✅ 每个 strike 显示两行：第一行 Call，第二行 Put
- ✅ 使用 `rowSpan={2}` 让 Strike 列跨两行
- ✅ 添加 "Type" 列显示 "CALL" 或 "PUT"
- ✅ Call 行使用蓝色主题，Put 行使用紫色主题
- ✅ Volume 和 OI 的数据条颜色区分：Call 用蓝色，Put 用紫色

**表格结构**:
```
Strike | Type | Bid | Ask | Δ | Γ | Θ | ν | ρ | IV | Vol | OI
-------|------|-----|-----|---|---|---|---|---|---|-----|----
$477.5 | CALL | ... | ... |...|...|...|...|...|...| ... | ...
       | PUT  | ... | ... |...|...|...|...|...|...| ... | ...
```

**优势**:
- ✅ 同一 strike 的 Call 和 Put 上下排列，更容易对比
- ✅ 设置策略时更容易选择同一 strike 的 Call 和 Put
- ✅ 视觉上更清晰，减少了水平滚动

### 3. 创建希腊字母曲线弹窗组件

**新文件**: `frontend/src/components/market/GreekCurveDialog.tsx`

**功能**:
- ✅ 显示指定希腊字母（Delta, Gamma, Theta, Vega, Rho, IV）的曲线图
- ✅ 同时显示 Call 和 Put 的曲线（蓝色和紫色）
- ✅ 支持高亮特定 strike 价格
- ✅ 显示 Spot Price 参考线
- ✅ 交互式 Tooltip 显示详细信息
- ✅ 响应式设计，适配不同屏幕尺寸

**支持的希腊字母**:
- Δ (Delta)
- Γ (Gamma)
- Θ (Theta)
- ν (Vega)
- ρ (Rho)
- IV (Implied Volatility)

**交互**:
- ✅ 点击表格中的希腊字母单元格，弹出对话框
- ✅ 点击表头的希腊字母列名，弹出对话框（显示所有 strike）
- ✅ 对话框支持关闭和响应式布局

### 4. 整合希腊曲线到表格

**改动**:
- ✅ 所有希腊字母单元格添加 `cursor-pointer` 和 `hover:bg-primary/20`
- ✅ 添加 `onClick` 事件处理，调用 `handleGreekClick`
- ✅ 表头的希腊字母列名也添加点击事件
- ✅ 在表格底部渲染 `GreekCurveDialog` 组件

**点击处理**:
```typescript
const handleGreekClick = (greekName: "delta" | "gamma" | "theta" | "vega" | "rho" | "iv", strike?: number, e?: React.MouseEvent) => {
  if (e) e.stopPropagation()
  setSelectedGreek(greekName)
  setSelectedStrike(strike)
  setGreekDialogOpen(true)
}
```

### 5. 移除 Visual View Tab

**文件**: `frontend/src/components/market/OptionChainVisualization.tsx`

**改动**:
- ✅ 移除 `Tabs`、`TabsList`、`TabsTrigger`、`TabsContent` 组件
- ✅ 移除 `OptionChainPriceView` 导入和使用
- ✅ 直接渲染 `OptionChainTable` 组件
- ✅ 简化组件结构

**之前**:
```tsx
<Tabs defaultValue="table">
  <TabsList>
    <TabsTrigger value="table">Table View</TabsTrigger>
    <TabsTrigger value="visual">Visual View</TabsTrigger>
  </TabsList>
  <TabsContent value="table">...</TabsContent>
  <TabsContent value="visual">...</TabsContent>
</Tabs>
```

**现在**:
```tsx
<OptionChainTable ... />
```

## 视觉效果改进

### 1. 表格布局
- ✅ Call 和 Put 上下排列，更容易对比
- ✅ 同一 strike 的数据集中在一起
- ✅ 减少了水平滚动需求

### 2. 交互体验
- ✅ 自动滚动到当前股价附近
- ✅ 希腊字母可点击，显示曲线图
- ✅ 悬停效果提示可点击
- ✅ 平滑滚动动画

### 3. 信息密度
- ✅ 移除分页后，所有数据一次性显示
- ✅ 用户可以自由滚动查看所有 strike
- ✅ 默认定位到最相关的区域（ATM 附近）

## 文件修改

1. **`frontend/src/components/market/OptionChainTable.tsx`**
   - 移除分页逻辑
   - 添加滚动和自动定位
   - 改变布局为上下排列
   - 添加希腊字母点击事件
   - 集成 GreekCurveDialog

2. **`frontend/src/components/market/GreekCurveDialog.tsx`** (新建)
   - 创建希腊曲线弹窗组件
   - 支持所有希腊字母和 IV
   - 响应式图表设计

3. **`frontend/src/components/market/OptionChainVisualization.tsx`**
   - 移除 Visual View tab
   - 简化组件结构

## 状态

✅ 期权链表格重构完成
- ✅ 移除分页，改为滚动
- ✅ 默认定位到当前股价附近
- ✅ Call 和 Put 上下排列
- ✅ 希腊字母曲线弹窗
- ✅ 移除 Visual View tab
- ✅ 交互体验优化

## 使用说明

1. **滚动查看**：表格支持上下滚动，查看所有 strike 价格
2. **自动定位**：页面加载时自动滚动到当前股价附近的期权
3. **查看曲线**：点击任何希腊字母单元格或表头，弹出曲线图
4. **设置策略**：点击 Bid/Ask 价格添加策略 leg
5. **对比数据**：同一 strike 的 Call 和 Put 上下排列，方便对比
