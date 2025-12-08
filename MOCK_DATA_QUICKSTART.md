# 模拟数据快速启动指南

## 🚀 快速开始

### 1. 启用模拟数据

在项目根目录的 `.env` 文件中添加：

```bash
USE_MOCK_DATA=true
```

### 2. 重启后端服务

```bash
docker-compose restart backend
```

### 3. 访问前端

打开浏览器访问：`http://localhost:3000`

## ✅ 现在您可以测试的功能

### Strategy Lab（策略实验室）

1. **访问页面**：`http://localhost:3000/strategy-lab`
2. **选择股票**：在搜索框输入 `AAPL`、`TSLA`、`MSFT` 等
3. **选择到期日期**：选择任意未来日期（如 2026-01-17）
4. **查看期权链**：
   - 系统会自动加载模拟的期权链数据
   - 包含 Calls 和 Puts
   - 每个期权包含完整的 Greeks（Delta, Gamma, Theta, Vega, Rho）
   - 包含 bid/ask 价格、交易量、持仓量等

5. **构建策略**：
   - 点击 "Add Leg" 添加策略腿
   - 选择 Call 或 Put
   - 选择执行价（基于模拟数据）
   - 查看盈亏图（Payoff Chart）

6. **生成 AI 分析**：
   - 点击 "Generate AI Report"
   - 系统会调用 Gemini API 生成策略分析报告

### Dashboard（仪表板）

1. **访问页面**：`http://localhost:3000/dashboard`
2. **查看股票行情**：
   - 使用搜索框搜索股票
   - 查看价格、涨跌幅等信息

### 支持的股票代码

以下股票有预设的基础价格，数据更真实：

- **AAPL** - Apple Inc. ($150)
- **TSLA** - Tesla Inc. ($250)
- **MSFT** - Microsoft Corp. ($380)
- **GOOGL** - Alphabet Inc. ($140)
- **AMZN** - Amazon.com Inc. ($150)
- **NVDA** - NVIDIA Corp. ($500)
- **META** - Meta Platforms Inc. ($350)
- **SPY** - SPDR S&P 500 ETF ($450)
- **QQQ** - Invesco QQQ Trust ($380)

其他股票代码将使用 $100 作为基础价格。

## 📊 模拟数据特性

### 期权链数据

- ✅ 完整的 Calls 和 Puts 列表
- ✅ 每个期权包含所有 Greeks
- ✅ Bid/Ask 价格（合理的价差）
- ✅ 交易量和持仓量
- ✅ 隐含波动率
- ✅ 标的价格（spot_price）

### 股票行情数据

- ✅ 当前价格
- ✅ 涨跌幅和涨跌百分比
- ✅ 交易量
- ✅ 最高价、最低价、开盘价

### 策略分析

- ✅ 盈亏图计算
- ✅ 盈亏平衡点计算
- ✅ AI 报告生成（需要 Gemini API 配置）

## 🔍 验证功能

### 1. 检查后端日志

```bash
docker-compose logs -f backend
```

您应该看到类似这样的日志：

```
INFO: Using mock data for option chain: AAPL
INFO: Using mock data for stock quote: AAPL
```

### 2. 测试 API 端点

```bash
# 获取期权链（需要先登录获取 token）
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:5300/api/v1/market/chain?symbol=AAPL&expiration_date=2026-01-17"

# 获取股票行情
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:5300/api/v1/market/quote?symbol=AAPL"
```

## ⚠️ 注意事项

1. **数据是模拟的**：
   - 所有数据都是随机生成的
   - 仅用于测试前端功能和 UI
   - 不代表真实市场数据

2. **每次请求可能不同**：
   - 价格会有随机波动
   - 这是为了模拟真实市场

3. **Greeks 计算是简化的**：
   - 使用简化的 Black-Scholes 模型
   - 实际应用中应使用更精确的计算

## 🔄 切换到真实 API

当您获得真实的 Tiger API 权限后：

1. 在 `.env` 文件中设置：
   ```bash
   USE_MOCK_DATA=false
   ```

2. 配置 Tiger API 凭证：
   ```bash
   TIGER_ID=your_tiger_id
   TIGER_ACCOUNT=your_account
   TIGER_PRIVATE_KEY=your_private_key
   ```

3. 重启服务：
   ```bash
   docker-compose restart backend
   ```

## 🐛 故障排除

### 问题：模拟数据没有生效

**检查**：
1. 确认 `.env` 文件中 `USE_MOCK_DATA=true`
2. 确认后端服务已重启
3. 查看后端日志确认是否使用模拟数据

### 问题：前端显示错误

**检查**：
1. 确认后端服务正在运行：`docker-compose ps`
2. 检查后端日志：`docker-compose logs backend`
3. 检查前端控制台是否有错误

### 问题：无法登录

**检查**：
1. 确认 Google OAuth 配置正确
2. 检查 `GOOGLE_CLIENT_ID` 和 `GOOGLE_CLIENT_SECRET` 环境变量

## 📚 更多信息

详细文档请参考：`backend/MOCK_DATA_GUIDE.md`

