# 空间优化 - 减少空白区域

## 问题

用户反馈"太空了！"（Too empty!），Option Chain Table 和 Market Data 下方有大量空白空间。

## 解决方案

### 1. 增加卡片高度

**文件**: `frontend/src/pages/StrategyLab.tsx`

- **Option Chain Card**: 添加 `h-[calc(100vh-280px)] min-h-[600px]`
- **Market Data Card**: 添加 `h-[calc(100vh-280px)] min-h-[600px]`
- 使用 flex 布局让内容填充空间

### 2. 增加表格显示行数

**文件**: `frontend/src/components/market/OptionChainTable.tsx`

- **之前**: `rowsPerPage = 15`
- **现在**: `rowsPerPage = 30`
- 每页显示更多行，减少空白

### 3. 优化表格布局

**文件**: `frontend/src/components/market/OptionChainTable.tsx`

- Card 使用 `h-full flex flex-col`
- CardHeader 使用 `flex-shrink-0`（不压缩）
- CardContent 使用 `flex-1 overflow-hidden flex flex-col min-h-0`
- 表格容器使用 `flex-1 overflow-auto`（填充剩余空间）
- 分页控件使用 `flex-shrink-0`（固定在底部）

### 4. 优化图表高度

**文件**: `frontend/src/pages/StrategyLab.tsx`

- **之前**: `height={300}`
- **现在**: `height={600}`
- 图表更大，填充更多空间

### 5. 优化 Market Data Tabs

**文件**: `frontend/src/pages/StrategyLab.tsx`

- Tabs 使用 `flex-1 flex flex-col`（填充空间）
- TabsList 使用 `flex-shrink-0`（不压缩）
- TabsContent 使用 `flex-1 overflow-auto`（填充剩余空间）

### 6. 优化 OptionChainVisualization

**文件**: `frontend/src/components/market/OptionChainVisualization.tsx`

- 外层 div 使用 `h-full flex flex-col`
- Tabs 使用 `flex-1 flex flex-col`
- TabsContent 使用 `flex-1 overflow-hidden`

## 布局结构

```
Option Chain Card (h-[calc(100vh-280px)] min-h-[600px])
├─ CardHeader (flex-shrink-0)
├─ CardContent (flex-1 overflow-hidden flex flex-col)
   ├─ OptionChainVisualization (h-full flex flex-col)
   │  ├─ TabsList (flex-shrink-0)
   │  └─ TabsContent (flex-1 overflow-hidden)
   │     └─ OptionChainTable (h-full flex flex-col)
   │        ├─ CardHeader (flex-shrink-0)
   │        ├─ CardContent (flex-1 overflow-hidden flex flex-col)
   │        │  ├─ Table Container (flex-1 overflow-auto)
   │        │  └─ Pagination (flex-shrink-0)
```

## 效果

- ✅ Option Chain Table 显示更多行（30行/页 vs 15行/页）
- ✅ 表格填充整个卡片高度，减少空白
- ✅ Market Data 图表更大（600px vs 300px）
- ✅ 所有内容使用 flex 布局，充分利用空间
- ✅ 分页控件固定在底部，不会压缩

## 文件修改

1. `frontend/src/pages/StrategyLab.tsx`
   - 添加卡片固定高度
   - 优化 Market Data Tabs 布局
   - 增加图表高度

2. `frontend/src/components/market/OptionChainTable.tsx`
   - 增加 rowsPerPage 到 30
   - 优化 flex 布局
   - 分页控件使用 flex-shrink-0

3. `frontend/src/components/market/OptionChainVisualization.tsx`
   - 优化 flex 布局
   - 移除未使用的导入

## 状态

✅ 空间优化完成
- 表格和图表填充更多空间
- 减少空白区域
- 内容更紧凑，信息密度更高
