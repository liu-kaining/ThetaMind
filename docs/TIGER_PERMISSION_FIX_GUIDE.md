# Tiger API 权限错误解决方案

## 🔴 错误信息

```
Tiger API Permission Error: Your account does not have permission to access US option quote data. 
Please check your Tiger API permissions (usOptionQuote). 
Error: code=4 msg=4000:permission denied(current device does not have permission)
```

## 📋 问题原因

Tiger API 的权限机制要求：
1. **账户必须有相应的市场权限**（美股期权行情 `usOptionQuote`）
2. **权限需要在 Tiger 客户端中先激活**，API 才能抢占到
3. **权限可能和设备/IP绑定**，需要先在客户端中激活

## ⚡ 快速解决方案（已验证）

如果您的权限已经在客户端中激活过，但 API 仍报错，可以尝试：

1. **关闭本地 Tiger 客户端**（如果有运行的话）
2. **重启线上服务**：
   ```bash
   docker compose restart backend
   ```
3. 服务重启后会自动重新抢占权限，问题通常会解决

> 💡 **经验总结**：权限激活后，需要重启服务才能让权限重新抢占生效。如果本地客户端和服务同时运行，可能会有权限冲突。

## ✅ 解决方案（按优先级）

### 方案 1: 在 Tiger 客户端中激活权限（最推荐，90% 的情况）

**这是最有效的解决方案！**

**步骤**：

1. **打开 Tiger 客户端**（必须是客户端，不是网页版）
   - 手机 App：Tiger Trade
   - 桌面版：Tiger Trade Desktop
   - ⚠️ **不要用网页版**，网页版不会激活 API 权限

2. **登录您的账户**

3. **手动查询美股期权数据**（关键步骤）：
   - 搜索股票代码（如 `AAPL`）
   - 查看股票行情页面
   - **进入期权页面**，查看期权链数据
   - 可以多查看几个不同的股票（如 `TSLA`, `MSFT`）

4. **等待 5-10 分钟**，让权限在服务器端激活

5. **关闭本地 Tiger 客户端**（如果有运行的话），避免权限冲突

6. **重启后端服务**，让权限重新抢占：
   ```bash
   docker compose restart backend
   ```

7. **验证权限**：
   ```bash
   docker compose exec backend python -c "
   from app.services.tiger_service import tiger_service
   import asyncio
   
   async def check():
       client = tiger_service._client
       # 清除权限缓存，强制重新抢占
       client.permissions = None
       perms = await asyncio.to_thread(client.grab_quote_permission)
       print('\\n当前权限列表:')
       for p in perms:
           name = p.get('name', 'unknown')
           print(f'  ✅ {name}')
       
       # 检查是否有美股权限
       us_perms = [p for p in perms if 'usQuote' in p.get('name', '') or 'usOption' in p.get('name', '')]
       if us_perms:
           print('\\n✅ 美股权限已激活！')
       else:
           print('\\n❌ 仍未获取到美股权限，请继续在客户端中查询期权数据')
   
   asyncio.run(check())
   "
   ```

### 方案 2: 检查账户配置

1. **登录 Tiger 账户中心**
   - 网页版：https://www.tigerbrokers.com/
   - 检查账户状态是否正常

2. **确认账户类型**
   - 某些账户类型可能不支持美股市场
   - 确认账户已激活美股交易功能

3. **检查市场权限**
   - 进入"账户设置" → "市场权限"
   - 确认已开通：
     - ✅ 美股交易功能
     - ✅ 美股行情权限
     - ✅ 美股期权行情权限

### 方案 3: 联系 Tiger 客服

如果以上方案都无法解决：

1. **联系 Tiger 客服**
   - 客服电话：400-603-7555（中国）
   - 在线客服：https://www.tigerbrokers.com/
   - 说明需要开通 **API 方式的美股期权行情权限**（`usOptionQuote`）

2. **提供信息**：
   - 账户号码
   - 错误信息：`code=4 msg=4000:permission denied`
   - 说明：需要 API 方式访问美股期权行情数据

3. **询问**：
   - 账户是否支持 API 方式获取美股权限
   - 是否需要额外的配置或申请
   - 是否有其他限制

### 方案 4: 检查环境配置

检查 `.env` 或 `docker-compose.yml` 中的配置：

```bash
# 确保使用生产环境（不是沙箱）
TIGER_SANDBOX=false

# 确认账户信息正确
TIGER_ACCOUNT=你的账户号
TIGER_ID=你的开发者ID
```

## 🔍 验证步骤

### 1. 检查当前权限

```bash
docker compose exec backend python -c "
from app.services.tiger_service import tiger_service
import asyncio

async def check():
    client = tiger_service._client
    perms = client.permissions
    if perms:
        print('当前权限:')
        for p in perms:
            print(f'  - {p.get(\"name\")}')
    else:
        print('未获取到权限')

asyncio.run(check())
"
```

### 2. 强制重新抢占权限

```bash
docker compose exec backend python -c "
from app.services.tiger_service import tiger_service
import asyncio

async def refresh():
    client = tiger_service._client
    # 清除缓存
    client.permissions = None
    # 重新抢占
    perms = await asyncio.to_thread(client.grab_quote_permission)
    print('重新抢占后的权限:')
    for p in perms:
        print(f'  - {p.get(\"name\")}')

asyncio.run(refresh())
"
```

### 3. 测试 API 调用

```bash
docker compose exec backend python -c "
from app.services.tiger_service import tiger_service
import asyncio
from datetime import datetime, timedelta

async def test():
    try:
        # 获取 30 天后的到期日
        future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        result = await tiger_service.get_option_chain('AAPL', future_date)
        print('✅ API 调用成功！')
        print(f'获取到 {len(result.get(\"calls\", []))} 个 Call 期权')
    except Exception as e:
        print(f'❌ API 调用失败: {e}')

asyncio.run(test())
"
```

## ⚠️ 常见问题

### Q: 为什么权限抢占只获取到港股和A股权限？

**A**: 这是因为美股权限需要在 Tiger 客户端中先激活。Tiger 的权限机制是：
- 权限可能和设备/IP绑定
- 需要在客户端中手动使用一次，服务器端才会激活
- API 只能抢占已经在服务器端激活的权限

### Q: 我已经在客户端中查询过期权了，为什么还是不行？

**A**: 可能的原因：
1. **等待时间不够**：权限激活可能需要 5-10 分钟
2. **没有重启服务**：需要重启后端服务，让权限重新抢占
3. **权限缓存**：需要清除权限缓存，强制重新抢占
4. **账户配置问题**：可能需要联系客服确认账户是否支持 API 方式

### Q: 可以手动指定权限吗？

**A**: 不可以。Tiger API 的权限是通过 `grab_quote_permission()` 自动抢占的，只能抢占账户中已激活的权限。

## 📝 代码层面的改进

当前代码已经：
- ✅ 在启动时自动抢占权限
- ✅ 记录获取到的权限列表
- ✅ 检查是否有美股权限，并发出警告
- ✅ 提供清晰的错误信息

如果权限问题持续存在，建议：
1. 按照方案 1 在客户端中激活权限
2. 如果仍然不行，联系 Tiger 客服确认账户配置

## 🔗 参考链接

- [Tiger Open API 文档](https://docs.itigerup.com/docs/intro)
- [行情权限说明](https://docs.itigerup.com/docs/quote-common)
- [期权接口文档](https://docs.itigerup.com/docs/quote-option)

