# 模拟数据使用指南

## 概述

模拟数据功能允许您在没有真实 API 权限的情况下测试前端功能，包括：
- 期权链数据（calls, puts, spot_price, Greeks）
- 股票行情数据（price, change, change_percent, volume）
- 策略推荐功能

## 启用模拟数据

### 方法 1: 环境变量（推荐）

在 `.env` 文件中添加：

```bash
USE_MOCK_DATA=true
```

然后重启后端服务：

```bash
docker-compose restart backend
```

### 方法 2: Docker Compose 环境变量

在 `docker-compose.yml` 中，`USE_MOCK_DATA` 已经配置为从环境变量读取，默认值为 `false`。

## 模拟数据特性

### 1. 期权链数据

- **生成逻辑**：
  - 基于股票代码的基础价格（AAPL: $150, TSLA: $250, MSFT: $380 等）
  - 生成围绕标的价格的执行价（±30% 范围，每 $5 一个）
  - 计算 Greeks（Delta, Gamma, Theta, Vega, Rho）使用简化的 Black-Scholes 模型
  - 生成合理的 bid/ask 价差（2-5%）
  - 包含交易量和持仓量数据

- **数据格式**：
  - 完全符合 `OptionChainResponse` 格式
  - 包含所有必需的字段（strike, bid, ask, volume, open_interest, Greeks）
  - 支持直接字段和嵌套 `greeks` 对象两种格式

### 2. 股票行情数据

- **生成逻辑**：
  - 基于股票代码的基础价格
  - 生成 ±2% 的价格波动
  - 计算涨跌幅和涨跌百分比
  - 生成交易量数据

- **数据格式**：
  - 完全符合 `StockQuoteResponse` 格式
  - 包含 price, change, change_percent, volume 等字段

### 3. 策略推荐

- 使用模拟期权链数据生成策略推荐
- 所有策略计算逻辑正常工作
- 可以测试完整的策略分析流程

## 测试前端功能

启用模拟数据后，您可以：

1. **查看期权链**：
   - 访问 Strategy Lab 页面
   - 选择股票代码（如 AAPL, TSLA, MSFT）
   - 选择到期日期
   - 查看生成的期权链数据

2. **构建策略**：
   - 添加策略腿（calls/puts）
   - 查看盈亏图（Payoff Chart）
   - 查看策略分析

3. **查看股票行情**：
   - 在 Dashboard 或 Strategy Lab 中查看股票价格
   - 查看涨跌幅信息

## 注意事项

1. **数据是模拟的**：
   - 所有数据都是随机生成的，不代表真实市场数据
   - 仅用于测试前端功能和 UI 展示

2. **Greeks 计算是简化的**：
   - 使用简化的 Black-Scholes 模型
   - 实际应用中应该使用更精确的计算方法

3. **价格波动是随机的**：
   - 每次请求可能返回不同的价格
   - 这是为了模拟真实市场的波动

4. **不支持历史数据**：
   - 模拟数据生成器不生成历史 K 线数据
   - 如果需要测试 K 线图，需要实现历史数据生成功能

## 禁用模拟数据

要禁用模拟数据并切换回真实 API：

1. 在 `.env` 文件中设置：
   ```bash
   USE_MOCK_DATA=false
   ```

2. 或者删除该环境变量（默认值为 `false`）

3. 重启后端服务：
   ```bash
   docker-compose restart backend
   ```

## 支持的股票代码

模拟数据生成器内置了以下股票的基础价格：

- AAPL: $150
- TSLA: $250
- MSFT: $380
- GOOGL: $140
- AMZN: $150
- NVDA: $500
- META: $350
- SPY: $450
- QQQ: $380

其他股票代码将使用 $100 作为基础价格。

## 技术实现

- **文件位置**：`backend/app/services/mock_data_generator.py`
- **配置位置**：`backend/app/core/config.py`（`use_mock_data` 字段）
- **API 集成**：`backend/app/api/endpoints/market.py`

## 示例

### 测试期权链 API

```bash
# 启用模拟数据后
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:5300/api/v1/market/chain?symbol=AAPL&expiration_date=2026-01-17"
```

### 测试股票行情 API

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:5300/api/v1/market/quote?symbol=AAPL"
```

## 下一步

当您获得真实的 API 权限后：
1. 设置 `USE_MOCK_DATA=false`
2. 配置真实的 Tiger API 凭证
3. 重启服务
4. 系统将自动切换到真实 API 数据

