# Tiger API 需求分析报告

## 问题 1: 是否只需要期权实时行情接口？是否需要股票行情接口？

### 当前实现分析

查看代码 `backend/app/api/endpoints/market.py` 和 `backend/app/services/strategy_engine.py`：

1. **策略生成流程**：
   - 调用 `tiger_service.get_option_chain()` 获取期权链
   - 从期权链数据中提取 `spot_price`（标的股票价格）
   ```python
   spot_price = chain_data.get("spot_price") or chain_data.get("underlying_price")
   ```

2. **期权链数据是否包含标的股票价格？**
   - 根据 Tiger SDK 文档，`get_option_chain()` 返回的数据通常包含标的股票的当前价格
   - 但需要确认：如果期权链接口返回了 `spot_price`/`underlying_price`，则**不需要**单独调用股票行情接口

### 结论

**理论上只需要期权实时行情接口**，因为：
- 期权链数据通常包含标的股票的当前价格（作为计算期权价格的基准）
- 策略引擎只需要 `spot_price` 来计算 Greeks 和选择执行价

**但需要验证**：
- Tiger API 的 `get_option_chain()` 是否确实返回 `spot_price`/`underlying_price`？
- 如果没有，则需要单独调用 `get_stock_briefs()` 获取股票价格

---

## 问题 2: 期权计算逻辑分析

### 当前实现（`backend/app/services/strategy_engine.py`）

#### 2.1 期权数据需求

策略引擎需要以下数据：
1. **期权价格**：`bid`, `ask`, `mid_price = (bid + ask) / 2`
2. **Greeks**：`delta`, `gamma`, `theta`, `vega`, `rho`
3. **执行价**：`strike` 或 `strike_price`
4. **标的股票价格**：`spot_price`（用于计算距离执行价的百分比）

#### 2.2 期权计算逻辑

**关键方法**：

1. **`_find_option()`**：根据目标 delta 查找最接近的期权
   - 需要：期权链数据 + spot_price
   - 用途：选择合适执行价的期权

2. **`_calculate_net_greeks()`**：计算组合的净 Greeks
   - 需要：每个 leg 的 Greeks 值
   - 计算：`net_greek = Σ(leg.ratio × leg.greek)`

3. **`_validate_liquidity()`**：验证流动性
   - 规则：`(ask - bid) / mid_price < 10%`
   - 需要：`bid`, `ask`, `mid_price`

4. **`_algorithm_iron_condor()` 等策略算法**：
   - 需要：spot_price（用于选择执行价）
   - 需要：期权链数据（包含所有执行价的期权）
   - 计算：max_profit, max_loss, breakeven points

#### 2.3 关键发现

**重要**：当前代码**依赖期权链中已计算的 Greeks**，而不是我们自己计算。

代码中只是**提取** Greeks，而不是计算：
```python
def _extract_greek(self, option: dict[str, Any], greek_name: str) -> float | None:
    # 只是从期权数据中提取已有的 Greeks
    # 不进行任何计算
```

这意味着：
- ✅ **如果期权链接口返回了 Greeks**（delta, gamma, theta, vega, rho），我们只需要提取即可
- ❌ **如果期权链接口没有返回 Greeks**，我们需要自己计算（需要 Black-Scholes 模型等）

---

## 问题 3: 是否可以使用历史股票数据？

### 分析

#### 3.1 实时 vs 历史数据

**实时期权数据的特点**：
- 期权价格实时变化（受标的股票价格、波动率、时间衰减影响）
- Greeks 实时变化
- 流动性指标实时变化

**历史股票数据的特点**：
- 只包含历史价格（开盘价、收盘价、最高价、最低价）
- 不包含期权数据
- 不包含 Greeks

#### 3.2 如果使用历史股票数据

**问题**：
1. **期权链必须实时**：期权价格和 Greeks 是实时变化的，历史数据无法替代
2. **spot_price 可以用历史收盘价替代**：如果只是用来：
   - 选择执行价（基于当前价格的位置）
   - 显示历史回测
   
   但这只适用于**回测场景**，不适用于**实时策略推荐**

#### 3.3 使用历史数据的场景

根据 Tiger API 文档（`basic` 示例），可以查询历史 K 线数据：
- `get_kbars()` 或类似方法
- 返回历史 OHLC 数据

**适用场景**：
1. ✅ **回测**：用历史数据模拟策略在过去的表现
2. ✅ **分析**：计算历史波动率、移动平均等
3. ❌ **实时推荐**：不能用历史数据，必须用实时期权链

### 结论

**对于实时策略推荐**：
- ❌ 不能只用历史股票数据
- ✅ 必须使用实时期权链数据（包含实时价格、Greeks、流动性）

**对于回测/分析功能**：
- ✅ 可以使用历史股票数据（K 线数据）
- ✅ 结合历史期权数据（如果有的话）

---

## 总结与建议

### 1. 数据需求确认

**需要验证的 API 接口**：

1. **`get_option_chain(symbol, expiry)`**：
   - ✅ 是否返回 `spot_price`/`underlying_price`？
   - ✅ 是否返回完整的 Greeks（delta, gamma, theta, vega, rho）？
   - ✅ 是否返回 `bid`, `ask` 价格？
   - ✅ 返回的数据结构是什么？

2. **`get_stock_briefs(symbols)`**（如果需要）：
   - 获取实时股票价格
   - 但需要 `usQuoteBasic` 权限

3. **历史数据接口**（可选）：
   - `get_kbars()` 或类似方法
   - 用于回测功能

### 2. 权限需求

**如果期权链包含 spot_price**：
- ✅ 只需要 `usOptionQuote`（美股期权行情权限）
- ❌ 不需要 `usQuoteBasic`（美股基础行情权限）

**如果期权链不包含 spot_price**：
- ✅ 需要 `usOptionQuote`
- ✅ 需要 `usQuoteBasic`（或使用历史数据）

### 3. 下一步行动

1. **验证期权链数据结构**：
   - 查看 Tiger SDK 返回的实际数据结构
   - 确认是否包含 `spot_price` 和 Greeks

2. **如果没有权限，考虑替代方案**：
   - 使用历史数据做回测
   - 使用其他数据源（如 Yahoo Finance、Alpha Vantage 等免费 API）
   - 或者申请权限

3. **期权计算逻辑**：
   - 如果 Tiger API 不返回 Greeks，需要实现 Black-Scholes 模型
   - 这需要：标的价格、执行价、到期时间、无风险利率、波动率

