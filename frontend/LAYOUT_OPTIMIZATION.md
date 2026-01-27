# StrategyLab 布局优化

## 问题

Data Panel 被挤压，显示不美观：
- 文本被挤压成多行
- 表格列太窄
- 整体布局不协调

## 解决方案

### 1. 调整三列布局比例

**之前**：`lg:grid-cols-5`
- 左列：`lg:col-span-1` (20%)
- 中列：`lg:col-span-3` (60%)
- 右列：`lg:col-span-1` (20%)

**现在**：`lg:grid-cols-8`
- 左列：`lg:col-span-2` (25%)
- 中列：`lg:col-span-4` (50%)
- 右列：`lg:col-span-2` (25%)

**改进**：右列（Data Panel）从 20% 增加到 25%，有更多空间显示内容。

### 2. 优化 Data Panel 显示

- **Card 标题**：减小字体大小 (`text-base`)
- **Card 描述**：使用更小的字体 (`text-xs`)
- **Tabs**：优化标签大小和间距
- **TabsContent**：添加 `flex-1 overflow-auto` 确保内容可以滚动

### 3. 优化 OptionChainTable

- **表格容器**：添加 `min-w-full` 和负边距优化滚动
- **列宽度**：
  - Strike 列：`min-w-[100px]`
  - Bid/Ask 列：`min-w-[80px]`
  - Greeks 列：`min-w-[60px]`，字体改为 `text-xs`
  - IV 列：`min-w-[70px]`
  - Volume/OI 列：`min-w-[70px]`
- **文本显示**：使用 `whitespace-nowrap` 防止文本换行
- **Padding**：优化各列的 padding (`px-1.5`, `px-2`, `px-3`)

### 4. 优化 OptionChainVisualization

- **移除多余的 Card 包装**：因为已经在 Data Panel 的 Card 内部，不需要双重嵌套
- **优化 Tabs 显示**：减小标签字体大小

## 文件修改

1. `frontend/src/pages/StrategyLab.tsx`
   - 调整三列布局比例
   - 优化 Data Panel Card 和 Tabs 显示

2. `frontend/src/components/market/OptionChainTable.tsx`
   - 优化表格列宽度和 padding
   - 优化文本显示，防止换行

3. `frontend/src/components/market/OptionChainVisualization.tsx`
   - 移除多余的 Card 包装
   - 优化 Tabs 显示

## 效果

- ✅ Data Panel 有更多空间（25% vs 20%）
- ✅ 表格列不再被挤压
- ✅ 文本不再换行
- ✅ 整体布局更协调美观

## 下一步

如果还需要进一步优化，可以考虑：
1. 响应式设计：在小屏幕上使用单列布局
2. 可调整列宽：允许用户拖拽调整列宽
3. 表格虚拟滚动：如果数据量很大，使用虚拟滚动提高性能
