# Strategy Lab 期权数据获取用户动线

## 完整用户流程

### 1. 用户输入股票代码
- **位置**: Strategy Lab 页面 → SymbolSearch 组件
- **触发**: 用户在输入框中输入股票代码（如 "AAPL"）
- **组件**: `frontend/src/components/market/SymbolSearch.tsx`

### 2. 搜索股票符号
- **API 调用**: `GET /api/v1/market/search?q=AAPL&limit=10`
- **后端端点**: `backend/app/api/endpoints/market.py` → `GET /market/search`
- **数据源**: 从 `StockSymbol` 表查询 `is_active=True` 的股票
- **返回**: 股票列表（symbol, name, market）

### 3. 用户选择股票
- **触发**: 用户点击搜索结果中的某个股票
- **处理函数**: `handleSymbolSelect(selectedSymbol: string)`
- **位置**: `frontend/src/pages/StrategyLab.tsx:136-147`

```typescript
const handleSymbolSelect = async (selectedSymbol: string) => {
  setSymbol(selectedSymbol)  // 更新 symbol 状态
  // 获取股票报价（用于显示初始价格）
  try {
    const quote = await marketService.getStockQuote(selectedSymbol)
    if (quote.data?.price) {
      setSpotPrice(quote.data.price)
    }
  } catch (error) {
    console.error("Failed to fetch quote:", error)
  }
}
```

### 4. 自动获取期权链数据 ⭐ **核心流程**
- **触发机制**: React Query 的 `useQuery` hook 自动监听 `symbol` 和 `expirationDate` 的变化
- **位置**: `frontend/src/pages/StrategyLab.tsx:96-101`

```typescript
const { data: optionChain, isLoading: isLoadingChain, refetch: refetchOptionChain } = useQuery({
  queryKey: ["optionChain", symbol, expirationDate],
  queryFn: () => marketService.getOptionChain(symbol, expirationDate),
  enabled: !!symbol && !!expirationDate,  // 只有当 symbol 和 expirationDate 都有值时才触发
  refetchInterval: false,  // 不自动刷新（节省 API 配额）
})
```

**关键点**:
- `enabled: !!symbol && !!expirationDate` 确保只有在两个值都存在时才调用 API
- `queryKey` 包含 `symbol` 和 `expirationDate`，任何一个变化都会重新获取数据
- `refetchInterval: false` 禁用自动轮询，需要手动刷新（通过 `refetchOptionChain()`）

### 5. 前端 API 调用
- **API 方法**: `marketService.getOptionChain(symbol, expirationDate)`
- **位置**: `frontend/src/services/api/market.ts:50-64`
- **HTTP 请求**: `GET /api/v1/market/chain?symbol=AAPL&expiration_date=2024-01-19`

```typescript
getOptionChain: async (
  symbol: string,
  expirationDate: string
): Promise<OptionChainResponse> => {
  const response = await apiClient.get<OptionChainResponse>(
    "/api/v1/market/chain",
    {
      params: {
        symbol: symbol.toUpperCase(),
        expiration_date: expirationDate,
      },
    }
  )
  return response.data
}
```

### 6. 后端 API 端点处理
- **端点**: `GET /api/v1/market/chain`
- **位置**: `backend/app/api/endpoints/market.py:55-162`
- **处理函数**: `get_option_chain()`

**关键逻辑**:
1. 接收参数: `symbol` 和 `expiration_date`
2. 调用 Tiger Service: `tiger_service.get_option_chain(symbol, expiration_date, is_pro=current_user.is_pro)`
3. 数据标准化: 处理 calls/puts，提取 Greeks（delta, gamma, theta, vega, rho）
4. 返回标准化数据: `OptionChainResponse`

### 7. Tiger Service 获取期权链
- **方法**: `tiger_service.get_option_chain()`
- **位置**: `backend/app/services/tiger_service.py`
- **实现**: 调用 Tiger Open SDK 的 `get_option_chain()` 方法

**缓存策略**:
- Pro 用户: 5 秒缓存（实时数据）
- Free 用户: 15 分钟缓存（延迟数据）

### 8. 数据返回和显示
- **更新状态**: React Query 自动更新 `optionChain` 数据
- **显示位置**:
  1. **OptionChainTable**: 显示完整的期权链表格（Calls 和 Puts）
  2. **PayoffChart**: 使用期权数据计算盈亏图
  3. **StrategyGreeks**: 显示策略的 Greeks 值
  4. **SmartPriceAdvisor**: 显示智能价格建议

### 9. 用户交互
- **选择期权**: 用户可以从 `OptionChainTable` 中点击某个期权，自动添加到策略中
- **手动刷新**: 通过 `SmartPriceAdvisor` 组件的刷新按钮调用 `refetchOptionChain()`

## 数据流图

```
用户输入股票代码
    ↓
SymbolSearch 组件搜索
    ↓
GET /api/v1/market/search → 数据库查询 StockSymbol 表
    ↓
用户选择股票
    ↓
handleSymbolSelect() 更新 symbol 状态
    ↓
React Query useQuery 检测到 symbol 变化
    ↓
GET /api/v1/market/chain?symbol=XXX&expiration_date=YYYY-MM-DD
    ↓
后端 get_option_chain() 端点
    ↓
tiger_service.get_option_chain() → Tiger Open SDK
    ↓
返回期权链数据（calls, puts, spot_price, greeks）
    ↓
前端更新 optionChain 状态
    ↓
显示在 OptionChainTable、PayoffChart 等组件中
```

## 关键代码位置

### 前端
- **Strategy Lab 主组件**: `frontend/src/pages/StrategyLab.tsx`
- **股票搜索组件**: `frontend/src/components/market/SymbolSearch.tsx`
- **期权链表格**: `frontend/src/components/market/OptionChainTable.tsx`
- **API 服务**: `frontend/src/services/api/market.ts`

### 后端
- **市场数据端点**: `backend/app/api/endpoints/market.py`
- **Tiger Service**: `backend/app/services/tiger_service.py`
- **数据模型**: `backend/app/db/models.py` (StockSymbol)

## 注意事项

1. **自动触发**: 期权链数据获取是**自动的**，不需要用户手动点击按钮
2. **依赖条件**: 需要同时有 `symbol` 和 `expirationDate` 才会触发
3. **缓存机制**: 后端有缓存，Pro 用户 5 秒，Free 用户 15 分钟
4. **手动刷新**: 可以通过 `SmartPriceAdvisor` 组件的刷新按钮手动刷新数据
5. **API 配额**: 已禁用自动轮询，避免消耗过多 API 配额

## 可能的问题排查

1. **期权链不显示**:
   - 检查 `symbol` 和 `expirationDate` 是否都有值
   - 检查后端 API 是否正常返回数据
   - 检查 Tiger API 权限和配置

2. **数据不更新**:
   - 检查缓存是否过期
   - 手动调用 `refetchOptionChain()` 刷新
   - 检查网络请求是否成功

3. **Greeks 数据缺失**:
   - 检查 Tiger API 返回的数据结构
   - 检查数据标准化逻辑是否正确处理 Greeks

