# Tiger API 数据结构验证结果

## 验证方法

1. ✅ **分析测试代码**：查看我们期望的数据结构
2. ✅ **分析当前代码**：查看我们如何处理返回的数据
3. ✅ **搜索官方文档**：了解 Tiger API 的实际返回结构

---

## 验证结果

### 1. 我们期望的数据结构（从测试代码）

查看 `backend/tests/services/test_strategy_engine.py`，我们期望的数据结构是：

```python
{
    "calls": [
        {
            "strike": 105.0,
            "delta": 0.20,
            "bid": 2.0,
            "ask": 2.05,
            "greeks": {
                "delta": 0.20,
                "gamma": 0.01,
                "theta": -0.05,
                "vega": 0.1
            }
        },
        # ... 更多期权
    ],
    "puts": [
        {
            "strike": 95.0,
            "delta": -0.20,
            "bid": 2.0,
            "ask": 2.05,
            "greeks": {
                "delta": -0.20,
                "gamma": 0.01,
                "theta": -0.05,
                "vega": 0.1
            }
        },
        # ... 更多期权
    ],
    "spot_price": 100.0  # 在顶层
}
```

### 2. 当前代码如何处理数据（从代码分析）

查看 `backend/app/api/endpoints/market.py:63` 和 `backend/app/services/tiger_service.py`：

```python
# 提取 spot_price
spot_price = chain_data.get("spot_price") or chain_data.get("underlying_price")

# 提取 calls 和 puts
calls = chain_data.get("calls", [])
puts = chain_data.get("puts", [])

# 提取 Greeks（从每个期权对象中）
delta = option.get("delta")  # 直接字段
# 或者
delta = option.get("greeks", {}).get("delta")  # 嵌套在 greeks 对象中
```

### 3. Tiger API 实际返回结构（从文档和搜索结果）

根据搜索结果和文档分析：

#### 关键发现

1. **期权数据接口**：
   - Tiger API 提供 `get_option_briefs()` 或 `get_option_chain()` 接口
   - 返回期权的基本信息（代码、行权价、买卖盘价格等）

2. **spot_price 位置**：
   - ⚠️ **可能不在期权链数据中**
   - 根据搜索结果："如果 `get_option_briefs` 返回的数据中不包含标的股票的现价，则需要通过股票行情接口（如 `get_stock_briefs`）获取标的股票的实时价格"

3. **Greeks 数据**：
   - ⚠️ **可能不包含在基础期权数据中**
   - Tiger SDK 提供了期权计算工具（基于 quantlib），可以计算 Greeks
   - 需要提供：标的资产价格、行权价、无风险利率、股息率、波动率、到期日期等

---

## 三个问题的验证答案

### 问题 1: 是否只需要期权实时行情接口？

**答案：可能不够，需要验证**

**关键发现**：
- ❓ 期权链数据**可能不包含** `spot_price`
- ❓ 如果期权链不包含 spot_price，需要调用 `get_stock_briefs()` 获取股票价格
- ❌ 但您目前没有 `usQuoteBasic` 权限（无法调用股票行情接口）

**建议**：
1. **优先验证**：检查 `get_option_chain()` 是否返回 spot_price
2. **如果返回**：只需要 `usOptionQuote` 权限
3. **如果不返回**：需要 `usQuoteBasic` 权限，或者使用替代数据源

### 问题 2: 期权计算逻辑

**答案：需要验证 Tigers API 是否返回 Greeks**

**关键发现**：
- ⚠️ 当前代码**只提取** Greeks，不计算
- ⚠️ 如果 Tiger API 不返回 Greeks，需要自己实现 Black-Scholes 模型
- ✅ Tiger SDK 提供了期权计算工具（`tigeropen/examples/option_helpers/helpers.py`）
  - 基于 `quantlib` 库
  - 需要：标的价格、行权价、无风险利率、股息率、波动率、到期日期

**需要验证**：
- [ ] `get_option_chain()` 是否返回 Greeks？
- [ ] 如果返回，字段名是什么（`delta`、`greeks.delta` 等）？
- [ ] 如果返回，是否包含所有 Greeks（delta, gamma, theta, vega, rho）？

### 问题 3: 是否可以使用历史股票数据？

**答案：实时推荐不能用，回测可以**

**关键发现**：
- ❌ **实时策略推荐**：不能用历史数据
  - 期权价格是实时的
  - Greeks 是实时的
  - 流动性指标是实时的
- ✅ **回测功能**：可以用历史数据
  - Tiger API 提供 `get_stock_bars()` 获取历史 K 线数据
  - 但需要历史期权数据（Tiger API 可能不提供）

---

## 关键问题清单

### 需要验证的核心问题

1. ✅ **`get_option_chain()` 返回的数据结构是什么？**
   - 是否包含 `spot_price`/`underlying_price`？
   - 是否包含 `calls` 和 `puts` 数组？
   - 每个期权对象包含哪些字段？

2. ✅ **Greeks 数据是否包含在返回中？**
   - 如果包含，字段名是什么？
   - 如果包含，是否完整（delta, gamma, theta, vega, rho）？

3. ✅ **如果 Tiger API 不返回所需数据，替代方案是什么？**
   - 使用 Tiger SDK 的计算工具？
   - 使用其他数据源（Yahoo Finance 等）？
   - 自己实现 Black-Scholes 模型？

---

## 下一步行动建议

### 方案 A: 验证 Tiger API 返回结构（推荐）

1. **启动后端服务**
2. **尝试调用 `get_option_chain()` API**
3. **打印返回的完整数据结构**
4. **分析包含哪些字段**

### 方案 B: 查看 Tiger SDK 源码

1. **查找 SDK 安装位置**
2. **查看 `QuoteClient.get_option_chain()` 的实现**
3. **查看返回的数据模型定义**

### 方案 C: 查看官方文档和示例

1. **查看 Tiger API 文档**：https://docs.itigerup.com/docs/quote-option
2. **查看示例代码**：https://quant.itigerup.com/openapi/zh/python/operation/quotation/option.html
3. **查看期权计算工具**：`tigeropen/examples/option_helpers/helpers.py`

### 方案 D: 准备替代方案

如果验证后发现 Tiger API 不返回所需数据：

1. **使用 Tiger SDK 的计算工具**计算 Greeks
2. **使用免费 API**获取股票价格（Yahoo Finance、Alpha Vantage 等）
3. **实现自己的 Black-Scholes 模型**

---

## 验证脚本

创建一个测试脚本来验证数据结构：

```python
# backend/scripts/verify_option_chain_structure.py
"""
验证 Tiger API get_option_chain() 返回的数据结构
"""
from app.services.tiger_service import tiger_service
import json
import asyncio
from datetime import datetime, timedelta

async def verify_structure():
    """验证期权链数据结构"""
    # 计算未来日期
    future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    try:
        # 调用 API
        chain_data = await tiger_service.get_option_chain('AAPL', future_date)
        
        # 打印完整结构
        print("=" * 60)
        print("期权链数据结构")
        print("=" * 60)
        print(f"\n顶层字段: {list(chain_data.keys())}")
        
        # 检查 spot_price
        spot_price = chain_data.get("spot_price") or chain_data.get("underlying_price")
        print(f"\nspot_price: {spot_price}")
        
        # 检查 calls 和 puts
        calls = chain_data.get("calls", [])
        puts = chain_data.get("puts", [])
        print(f"\ncalls 数量: {len(calls)}")
        print(f"puts 数量: {len(puts)}")
        
        # 检查第一个期权的字段
        if calls:
            first_call = calls[0]
            print(f"\n第一个 call 期权的字段: {list(first_call.keys())}")
            print(f"示例数据: {json.dumps(first_call, indent=2, default=str)}")
            
            # 检查 Greeks
            if "greeks" in first_call:
                print(f"\nGreeks 字段: {list(first_call['greeks'].keys())}")
            if "delta" in first_call:
                print(f"\n直接包含 delta: {first_call.get('delta')}")
        
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_structure())
```

---

## 总结

### 关键发现

1. ⚠️ **spot_price 可能不在期权链中**：需要验证或使用替代方案
2. ⚠️ **Greeks 可能需要自己计算**：如果 Tiger API 不返回，需要使用 SDK 工具或自己实现
3. ❌ **实时推荐不能用历史数据**：必须使用实时期权数据

### 推荐行动

1. **优先验证数据结构**：实际调用 API 查看返回的数据
2. **准备替代方案**：如果 Tiger API 不满足需求，准备使用其他数据源或自己计算
3. **考虑申请权限**：如果需要 `usQuoteBasic` 权限，考虑申请或使用替代方案

