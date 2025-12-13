# Tiger API 状态报告

## ✅ 已修复的问题

1. **API 调用方式**：已修复 `get_option_chain` 的参数传递问题
2. **权限抢占**：权限抢占功能正常工作
3. **错误处理**：完善的错误处理和日志记录

## ⚠️ 当前问题

### 权限问题

**状态**：权限抢占成功，但账户缺少美股和美股期权权限

**当前获得的权限**：
- ✅ `hkStockQuoteLv2` (港股行情)
- ✅ `aStockQuoteLv1` (A股行情)
- ❌ `usStockQuote` (美股行情) - **缺失**
- ❌ `usOptionQuote` (美股期权行情) - **缺失**

**错误信息**：
```
code=4 msg=4000:permission denied(Current user and device do not have permissions in the US market)
code=4 msg=4000:permission denied(Current user and device do not have permissions in the US OPT quote market)
```

## 🔧 解决方案

### 方案 1: 在 Tiger 账户中开通权限（推荐）

1. **登录 Tiger 账户**
   - 网页版：https://www.tigerbrokers.com/
   - 或使用 Tiger 客户端

2. **检查市场权限**
   - 进入账户设置
   - 找到"市场权限"或"Market Permissions"
   - 确认已开通：
     - ✅ 美股行情 (US Stock Quote)
     - ✅ 美股期权行情 (US Option Quote)

3. **如果权限未开通**
   - 联系 Tiger 客服开通美股市场权限
   - 某些账户类型可能需要额外申请

### 方案 2: 检查账户配置

1. **确认账户类型**
   - 某些账户类型可能不支持美股市场
   - 检查账户是否已激活美股交易功能

2. **检查环境配置**
   - 当前配置：`TIGER_SANDBOX=false` (生产环境)
   - 如果使用测试账户，可能需要设置为 `true`

3. **手动触发权限抢占**
   - 在 Tiger 客户端中手动获取一次美股行情
   - 这可能会触发权限自动开通

### 方案 3: 联系 Tiger 技术支持

如果以上方案都无法解决问题，建议：
1. 联系 Tiger 客服
2. 提供账户信息：`TIGER_ACCOUNT=8650383`
3. 说明需要开通美股和美股期权行情权限
4. 询问是否有其他配置要求

## 📝 代码改进

已添加权限日志记录，在初始化时会显示获得的权限：

```python
# 在 TigerService.__init__ 中
permissions = self._client.permissions
if permissions:
    permission_names = [p.get('name', 'unknown') for p in permissions]
    logger.info(f"TigerService initialized. Permissions: {', '.join(permission_names)}")
```

## ✅ 测试建议

权限开通后，可以运行以下测试：

```bash
docker-compose exec backend python -c "
from app.services.tiger_service import tiger_service
import asyncio
from datetime import datetime, timedelta

async def test():
    future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    result = await tiger_service.get_option_chain('AAPL', future_date)
    print('✅ 成功!', result)

asyncio.run(test())
"
```

## 📊 当前状态总结

| 项目 | 状态 | 说明 |
|------|------|------|
| API 调用方式 | ✅ 已修复 | 参数传递正确 |
| 权限抢占 | ✅ 正常 | 可以成功抢占权限 |
| 美股行情权限 | ❌ 缺失 | 需要在账户中开通 |
| 美股期权权限 | ❌ 缺失 | 需要在账户中开通 |
| 错误处理 | ✅ 完善 | 有详细的错误日志 |

