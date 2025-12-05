# Tiger API 权限问题排查指南

## 📋 问题描述

**现象**：
- 权限抢占只获取到：`hkStockQuoteLv2`, `aStockQuoteLv1`
- 缺少：`usQuoteBasic`, `usOptionQuote`
- API 调用返回：`permission denied(Current user and device do not have permissions in the US OPT quote market)`

**用户反馈**：
- 账户确实有 `usQuoteBasic` 和 `usOptionQuote` 权限

## 🔍 已检查的项目

### ✅ 代码层面
1. ✅ API 调用方式已修复
2. ✅ 环境配置已切换到生产环境 (`TIGER_SANDBOX=false`)
3. ✅ 权限抢占逻辑正常工作
4. ✅ 错误处理和日志完善

### ⚠️ 发现的问题
1. **权限抢占未获取到美股权限**
   - 多次尝试权限抢占，始终只获取到港股和A股权限
   - 说明服务器端返回的权限列表中没有美股权限

2. **环境配置问题（已修复）**
   - 之前 `docker-compose.yml` 中 `TIGER_SANDBOX` 默认值为 `true`
   - 已修复为 `false`，现在使用生产环境

## 🎯 可能的原因

根据 Tiger SDK 文档和权限机制，可能的原因：

### 1. 权限需要先激活（最可能）

**Tiger 的权限机制**：
- 权限可能需要在 Tiger 客户端中**手动使用一次**才能激活
- 权限可能和设备/IP绑定，需要先在客户端中激活

**解决方案**：
1. 打开 Tiger 客户端（手机或电脑）
2. 手动查询一次 **AAPL** 的股票行情
3. 手动查询一次 **AAPL** 的期权链
4. 等待几分钟，让权限在服务器端激活
5. 重新运行权限抢占，应该能获取到 `usQuoteBasic` 和 `usOptionQuote`

### 2. 权限名称不匹配

**可能的情况**：
- 权限在账户中显示的名称可能不同
- 服务器端使用的权限名称可能不同

**验证方法**：
- 在 Tiger 客户端中查看账户权限列表
- 确认权限名称是否确实是 `usQuoteBasic` 和 `usOptionQuote`

### 3. 账户配置问题

**可能的情况**：
- 账户类型可能不支持 API 方式获取美股权限
- 可能需要特定的账户配置或申请

**验证方法**：
- 联系 Tiger 客服，确认账户是否支持 API 方式获取美股权限
- 询问是否有其他配置要求

### 4. 权限系统延迟

**可能的情况**：
- 权限开通后，服务器端可能需要时间同步
- 权限抢占可能有缓存

**解决方案**：
- 等待一段时间后重试
- 清除权限缓存，强制重新抢占

## 🔧 排查步骤

### 步骤 1: 在 Tiger 客户端中激活权限

1. **打开 Tiger 客户端**（手机或电脑）
2. **查询美股行情**：
   - 搜索 "AAPL"
   - 查看股票行情
3. **查询美股期权**：
   - 进入 AAPL 的期权页面
   - 查看期权链
4. **等待 5-10 分钟**，让权限在服务器端激活

### 步骤 2: 重新测试权限抢占

```bash
docker-compose exec backend python -c "
from app.services.tiger_service import tiger_service
import asyncio

async def test():
    client = tiger_service._client
    client.permissions = None  # 清除缓存
    perms = await asyncio.to_thread(client.grab_quote_permission)
    print('权限列表:')
    for p in perms:
        print(f'  - {p.get(\"name\")}')

asyncio.run(test())
"
```

### 步骤 3: 测试 API 调用

```bash
docker-compose exec backend python -c "
from app.services.tiger_service import tiger_service
import asyncio
from datetime import datetime, timedelta

async def test():
    future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    result = await tiger_service.get_option_chain('AAPL', future_date)
    print('✅ 成功!')

asyncio.run(test())
"
```

## 📝 代码改进

已添加的改进：

1. **权限日志**：启动时会显示获取到的权限
2. **美股权限检查**：如果没有美股权限，会显示警告
3. **环境配置修复**：`TIGER_SANDBOX` 默认值已修复

## ✅ 验证清单

- [ ] 在 Tiger 客户端中手动查询过 AAPL 股票行情
- [ ] 在 Tiger 客户端中手动查询过 AAPL 期权链
- [ ] 等待 5-10 分钟后重新测试权限抢占
- [ ] 确认权限列表中包含 `usQuoteBasic` 和 `usOptionQuote`
- [ ] API 调用测试成功

## 🔗 参考文档

- [Tiger Open API 文档](https://docs.itigerup.com/docs/intro)
- [行情权限说明](https://docs.itigerup.com/docs/quote-common)
- [期权接口文档](https://docs.itigerup.com/docs/quote-option)

