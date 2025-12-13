# Tiger API 权限问题修复指南

## 问题描述

权限抢占成功，但只获得了：
- ✅ `hkStockQuoteLv2` (港股行情)
- ✅ `aStockQuoteLv1` (A股行情)
- ❌ `usQuoteBasic` (美股基础行情) - **缺失**
- ❌ `usOptionQuote` (美股期权行情) - **缺失**

## 权限名称确认

根据文档和错误信息，需要的权限是：
- `usQuoteBasic` - 美股基础行情权限
- `usOptionQuote` - 美股期权行情权限

## 解决方案

### 方案 1: 在 Tiger 客户端中激活权限（推荐）

**重要**：权限需要在 Tiger 客户端中先激活，API 才能抢占到。

**步骤**：
1. 打开 **Tiger 客户端**（桌面版或移动端，不是网页版）
2. 登录账户：`8650383`
3. 在客户端中执行以下操作：
   - 搜索并查看美股行情（如 `AAPL`）
   - 查看美股期权链（如 `AAPL` 的期权）
   - 这会触发权限激活
4. 等待几分钟后，重新运行权限抢占
5. 检查是否获得了 `usQuoteBasic` 和 `usOptionQuote` 权限

### 方案 2: 检查账户配置

1. **登录 Tiger 账户**
   - 网页版：https://www.tigerbrokers.com/
   - 客户端：Tiger Trade App

2. **检查账户设置**
   - 进入"账户设置"或"市场权限"
   - 确认已开通：
     - ✅ 美股交易功能
     - ✅ 美股行情权限
     - ✅ 美股期权行情权限

3. **检查账户类型**
   - 某些账户类型可能不支持美股市场
   - 联系 Tiger 客服确认账户是否支持美股

### 方案 3: 检查环境配置

当前配置：
- `TIGER_SANDBOX=false` (生产环境)
- `TIGER_ACCOUNT=8650383`

如果使用的是测试账户，可能需要：
- 设置为 `TIGER_SANDBOX=true`
- 或使用模拟账户进行测试

## 验证步骤

权限激活后，运行以下命令验证：

```bash
docker-compose exec backend python -c "
from app.services.tiger_service import tiger_service
import asyncio

async def check():
    perms = await asyncio.to_thread(tiger_service._client.grab_quote_permission)
    names = [p.get('name') for p in perms]
    print('权限列表:', names)
    if 'usQuoteBasic' in names:
        print('✅ usQuoteBasic 已获得')
    if 'usOptionQuote' in names:
        print('✅ usOptionQuote 已获得')

asyncio.run(check())
"
```

## 常见问题

### Q: 为什么权限抢占只返回港股和A股权限？

A: 权限抢占只会返回账户中**已激活**的权限。如果权限未在客户端中激活，API 无法抢占到。

### Q: 我已经在网页版中开通了美股权限，为什么还是不行？

A: 权限需要在**客户端**中激活，网页版的操作可能不会触发权限激活。必须使用 Tiger Trade 客户端。

### Q: 权限激活后需要等多久？

A: 通常几分钟内就会生效。如果等待较长时间仍未生效，可能需要联系 Tiger 客服。

## 相关文档

- Tiger Open API 文档：https://docs.itigerup.com/docs/intro
- 行情权限说明：https://docs.itigerup.com/docs/quote-permission

