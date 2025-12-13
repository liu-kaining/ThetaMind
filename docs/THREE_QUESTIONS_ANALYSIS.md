# 三个核心问题分析

基于代码分析和 Tiger API 文档，直接回答您的三个问题。

---

## 问题 1: 是否只需要期权实时行情接口？是否需要股票行情接口？

### 答案：理论上只需要期权接口，但需要验证

**当前代码实现**：
```python
# backend/app/api/endpoints/market.py 第 63 行
spot_price = chain_data.get("spot_price") or chain_data.get("underlying_price")
```

代码**假设**期权链数据包含标的股票价格（spot_price）。

### 关键点

1. **如果期权链包含 spot_price**：
   - ✅ **只需要** `usOptionQuote` 权限
   - ❌ **不需要** `usQuoteBasic` 权限
   - ✅ 不需要单独调用股票行情接口

2. **如果期权链不包含 spot_price**：
   - ❌ 需要额外调用 `get_stock_briefs()` 获取股票价格
   - ❌ 需要 `usQuoteBasic` 权限（您目前没有）

### 需要验证

**下一步应该测试**：调用 `get_option_chain()` 查看返回的数据结构：
- 是否包含 `spot_price` 或 `underlying_price` 字段？
- 数据结构是什么样的？

---

## 问题 2: 期权计算逻辑分析

### 答案：代码只提取数据，不计算 Greeks

### 当前实现的核心逻辑

**查看 `backend/app/services/strategy_engine.py` 第 68-105 行**：

```python
def _extract_greek(self, option: dict[str, Any], greek_name: str) -> float | None:
    # 只是从期权数据中提取已有的 Greeks
    # 不进行任何计算
```

### 关键发现

1. **代码不计算 Greeks**：
   - 只是从期权链数据中**提取**已有的 delta, gamma, theta, vega, rho
   - 不实现 Black-Scholes 模型

2. **依赖 Tiger API 返回的数据**：
   - ✅ 期权价格（bid, ask）
   - ✅ Greeks（delta, gamma, theta, vega, rho）
   - ✅ 执行价（strike）
   - ✅ 标的股票价格（spot_price）

3. **计算流程**：
   ```
   期权链数据 → 提取 spot_price → 根据 delta 选择执行价 
   → 提取每个 leg 的价格和 Greeks → 计算策略指标
   ```

### 如果 Tiger API 不返回 Greeks

需要自己实现 Black-Scholes 模型计算 Greeks，需要：
- 标的价格、执行价、到期时间、无风险利率、隐含波动率

---

## 问题 3: 是否可以使用历史股票数据？

### 答案：实时推荐不行，回测可以

### 实时 vs 历史数据

**实时期权数据**：
- ✅ 实时期权价格（受市场影响实时变化）
- ✅ 实时 Greeks（随价格变化）
- ✅ 实时流动性（bid-ask spread）
- ✅ 标的股票当前价格

**历史股票数据**（K 线）：
- ✅ 历史股票价格（开盘、收盘、最高、最低）
- ❌ **不包含期权数据**
- ❌ **不包含 Greeks**

### 结论

**对于实时策略推荐**：
- ❌ **不能使用历史数据**
  - 期权价格是实时的，历史数据无法替代
  - Greeks 是实时的，历史数据无法替代

**对于回测功能**（未来功能）：
- ✅ 可以使用历史股票数据（K 线）
- ⚠️ 但需要历史期权数据（Tiger API 可能不提供）

### 关于文档中的 "basic" 示例

文档中的 `get_stock_briefs()` 示例：
- 可以获取**实时股票价格**
- 可以获取**历史 K 线数据**（如果有相应接口）
- 但**不能替代实时期权数据**

---

## 总结

### 核心结论

1. **数据需求**：
   - ✅ 主要依赖：`get_option_chain()` 接口
   - ❓ 需要验证：期权链是否包含 `spot_price` 和完整 Greeks
   - ❌ 如果期权链不包含 spot_price，需要 `usQuoteBasic` 权限或替代方案

2. **计算逻辑**：
   - ✅ 当前实现：只提取数据，不计算 Greeks
   - ⚠️ 依赖：Tiger API 必须返回完整的期权数据（价格 + Greeks）
   - ❌ 如果 API 不返回 Greeks，需要自己实现 Black-Scholes 模型

3. **历史数据**：
   - ❌ 实时推荐：不能用历史数据
   - ✅ 回测功能：可以用历史数据（但需要历史期权数据）

### 关键问题清单

在继续开发之前，需要回答：

1. ✅ **期权链是否包含 spot_price？**
   - 如果不包含，需要额外获取股票价格

2. ✅ **期权链是否包含 Greeks？**
   - 如果不包含，需要自己实现 Black-Scholes 模型

3. ✅ **如果没有权限，是否愿意使用替代数据源？**
   - 免费 API（Yahoo Finance、Alpha Vantage 等）
   - 付费 API（Polygon.io、IEX Cloud 等）

---

## 建议的下一步

### 步骤 1: 验证数据结构

即使没有权限，也可以：
1. 查看 Tiger SDK 的文档和源码
2. 查看 Tiger SDK 返回的数据结构定义
3. 或者先用模拟数据测试

### 步骤 2: 如果没有权限，考虑替代方案

**方案 A: 申请权限**
- 申请 `usOptionQuote` 权限（必须）
- 如果期权链不包含 spot_price，申请 `usQuoteBasic` 权限

**方案 B: 使用替代数据源**
- Yahoo Finance API（免费）
- Alpha Vantage（免费层）
- Polygon.io（有免费层）

**方案 C: 自己计算 Greeks**
- 实现 Black-Scholes 模型
- 需要从期权价格反推隐含波动率

---

## 参考文档

- Tiger Open API 基本功能：https://docs.itigerup.com/docs/basic
- 期权接口文档：https://docs.itigerup.com/docs/quote-option
- 其他示例：https://docs.itigerup.com/docs/other-example

