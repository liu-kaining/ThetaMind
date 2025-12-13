# 故障排除指南 - 模拟数据不显示

## ✅ 已完成的配置

1. ✅ 模拟数据模式已启用 (`USE_MOCK_DATA=true`)
2. ✅ 后端服务正在运行
3. ✅ 前端服务正在运行

## 🔍 检查步骤

### 1. 确认已登录

**问题**：API需要认证，未登录无法获取数据

**解决**：
- 访问 http://localhost:3000
- 点击 "Login with Google"
- 完成Google OAuth登录
- 确认浏览器地址栏显示 `/dashboard` 或 `/strategy-lab`

### 2. 检查浏览器控制台

**步骤**：
1. 打开浏览器开发者工具（F12 或 Cmd+Option+I）
2. 切换到 "Console" 标签
3. 查看是否有红色错误信息
4. 切换到 "Network" 标签
5. 刷新页面
6. 查找 `/api/v1/market/chain` 或 `/api/v1/market/quote` 请求
7. 点击请求，查看：
   - Status Code（应该是 200）
   - Response（应该包含数据）

### 3. 检查后端日志

```bash
docker-compose logs -f backend
```

**应该看到**：
```
INFO: Using mock data for option chain: AAPL
INFO: Using mock data for stock quote: AAPL
```

### 4. 测试API端点

**需要JWT token**（从浏览器Network标签中获取）：

```bash
# 获取期权链
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:5300/api/v1/market/chain?symbol=AAPL&expiration_date=2026-01-17"

# 获取股票行情
curl -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:5300/api/v1/market/quote?symbol=AAPL"
```

## 🐛 常见问题

### 问题1: 页面显示 "Loading..." 但一直不加载

**可能原因**：
- 未登录
- API请求失败
- 网络问题

**解决**：
1. 检查是否已登录
2. 查看浏览器控制台的错误信息
3. 检查后端日志

### 问题2: 显示 "No data available"

**可能原因**：
- 模拟数据生成失败
- API返回空数据

**解决**：
1. 检查后端日志是否有错误
2. 确认 `USE_MOCK_DATA=true` 已设置
3. 重启后端：`docker-compose restart backend`

### 问题3: 401 Unauthorized 错误

**原因**：未登录或token过期

**解决**：
1. 重新登录
2. 清除浏览器缓存和cookies
3. 重新访问页面

### 问题4: 500 Internal Server Error

**原因**：后端代码错误

**解决**：
1. 查看后端日志：`docker-compose logs backend`
2. 检查错误信息
3. 确认所有依赖已安装

## 📊 验证数据是否正常

### 在Strategy Lab页面：

1. **搜索股票**：输入 `AAPL` 或 `TSLA`
2. **选择到期日期**：选择未来日期（如 2026-01-17）
3. **应该看到**：
   - 标的价格（Spot Price）
   - Calls 列表（包含执行价、bid、ask、Greeks）
   - Puts 列表（包含执行价、bid、ask、Greeks）

### 在Dashboard页面：

1. **搜索股票**：输入 `AAPL`
2. **应该看到**：
   - 当前价格
   - 涨跌幅
   - 交易量

## 🔧 快速修复命令

```bash
# 重启所有服务
docker-compose restart

# 查看后端日志
docker-compose logs -f backend

# 验证模拟数据配置
docker-compose exec backend python -c "from app.core.config import settings; print(f'USE_MOCK_DATA: {settings.use_mock_data}')"

# 测试模拟数据生成
docker-compose exec backend python -c "
from app.services.mock_data_generator import mock_data_generator
chain = mock_data_generator.generate_option_chain('AAPL', '2026-01-17')
print(f'✅ 生成成功: {len(chain[\"calls\"])} calls, {len(chain[\"puts\"])} puts')
"
```

## 📞 如果还是不行

请提供以下信息：

1. 浏览器控制台的错误信息
2. 后端日志的最后50行：`docker-compose logs --tail=50 backend`
3. Network标签中的API请求详情
4. 您访问的具体页面和操作步骤

