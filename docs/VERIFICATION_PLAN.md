# 验证计划：Tiger API 数据结构

## 验证目标

1. ✅ **确认 `get_option_chain()` 返回的数据结构**
   - 是否包含 `spot_price` 或 `underlying_price`？
   - 是否包含完整的 Greeks（delta, gamma, theta, vega, rho）？
   - 数据结构是什么样的？

2. ✅ **确认权限需求**
   - 如果期权链包含 spot_price，只需要 `usOptionQuote`
   - 如果期权链不包含 spot_price，还需要 `usQuoteBasic`

## 验证方法

### 方法 1: 查看 Tiger SDK 文档

根据搜索结果，Tiger API 文档：
- https://docs.itigerup.com/docs/quote-option
- https://quant.itigerup.com/openapi/zh/python/operation/quotation/option.html

需要查看：
1. `get_option_chain()` 方法的返回值结构
2. 返回的数据包含哪些字段

### 方法 2: 查看测试代码中的模拟数据

查看 `backend/tests/services/test_strategy_engine.py`：
- 测试代码中如何模拟期权链数据
- 模拟数据包含哪些字段

### 方法 3: 实际调用测试（需要权限）

如果有权限，可以：
1. 启动后端服务
2. 调用 `get_option_chain()` API
3. 打印返回的完整数据结构

### 方法 4: 查看 Tiger SDK 源码（如果安装）

检查 SDK 安装位置：
- 通常在 Python 的 site-packages 中
- 查看 `tigeropen/quote/quote_client.py` 中 `get_option_chain` 的实现

## 当前代码假设

从代码分析，我们假设：

1. **期权链数据结构**：
   ```python
   {
       "calls": [
           {
               "strike": 150.0,
               "bid": 5.0,
               "ask": 5.5,
               "delta": 0.5,
               "gamma": 0.01,
               "theta": -0.05,
               "vega": 0.1,
               "rho": 0.02,
               # ... 其他字段
           },
           # ...
       ],
       "puts": [
           # 类似结构
       ],
       "spot_price": 150.0,  # 或者 "underlying_price"
       # 或者可能在其他位置
   }
   ```

2. **代码提取逻辑**（`backend/app/api/endpoints/market.py:63`）：
   ```python
   spot_price = chain_data.get("spot_price") or chain_data.get("underlying_price")
   ```

## 需要验证的具体问题

### 问题 1: spot_price 位置

- [ ] spot_price 是否在期权链数据的顶层？
- [ ] 还是需要从其他位置提取？
- [ ] 字段名是 `spot_price`、`underlying_price` 还是其他？

### 问题 2: Greeks 数据

- [ ] 每个期权对象是否包含完整的 Greeks？
- [ ] 字段名是什么（delta, gamma, theta, vega, rho）？
- [ ] 是否嵌套在某个子对象中？

### 问题 3: 期权价格数据

- [ ] bid/ask 价格的字段名是什么？
- [ ] 是否包含 mid_price，还是需要计算？

## 下一步行动

1. ✅ **查看测试代码** - 了解我们期望的数据结构
2. ✅ **查看文档链接** - 了解官方文档说明
3. ⏳ **实际调用测试** - 需要权限后才能执行
4. ⏳ **查看 SDK 源码** - 如果 SDK 已安装

