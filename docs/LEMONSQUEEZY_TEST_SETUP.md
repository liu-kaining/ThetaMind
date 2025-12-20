# LemonSqueezy 测试模式配置指南

本指南将帮助你在测试模式下配置和验证 LemonSqueezy 支付集成。

## 📋 前置要求

- ✅ 已安装并配置 ngrok
- ✅ 后端服务正在运行（默认端口 5300）
- ✅ 已创建 LemonSqueezy 账户（Test Mode）

---

## 🔧 步骤 1: 获取 LemonSqueezy 配置信息

### 1.1 获取 API Key

1. 登录 [LemonSqueezy Dashboard](https://app.lemonsqueezy.com/)
2. 确保处于 **Test Mode**（右上角切换）
3. 进入 **Settings** → **API**
4. 点击 **Create API Key**
5. 复制生成的 API Key（格式：`sk_test_...`）

### 1.2 获取 Store ID

1. 在 Dashboard 中进入 **Stores**
2. 选择你的测试 Store
3. 复制 **Store ID**（在 Store 详情页面或 URL 中）

### 1.3 获取 Variant ID

1. 进入 **Products** → 选择你的产品
2. 选择 **Variants** 标签
3. 复制 **Variant ID**（月付和年付各一个）
   - 月付 Variant ID
   - 年付 Variant ID（如果有）

### 1.4 配置 Store 重定向 URL（支付成功后跳转）

1. 进入 **Settings** → **Stores**
2. 选择你的 Store
3. 进入 **Settings** 标签
4. 找到 **Redirect URL** 或 **Success URL** 设置
5. 填写你的前端支付成功页面 URL：
   - 开发环境：`http://localhost:3000/payment/success`
   - 或使用 ngrok：`https://your-frontend-ngrok-url.ngrok-free.dev/payment/success`
6. 保存设置

### 1.5 创建 Webhook Secret

1. 进入 **Settings** → **Webhooks**
2. 点击 **Create Webhook**
3. 先不要填写 URL（等 ngrok 配置好后再填）
4. 选择要监听的事件：
   - `subscription_created`
   - `subscription_updated`
   - `subscription_expired`
   - `subscription_cancelled`
5. 保存后，复制 **Signing Secret**（格式：`whsec_...`）

---

## 🌐 步骤 2: 配置 ngrok

### 2.1 启动 ngrok

在终端运行：

```bash
ngrok http 5300
```

**注意**：如果你的后端运行在其他端口，请相应调整。

### 2.2 获取 ngrok URL

ngrok 启动后会显示类似以下信息：

```
Forwarding  https://xxxx-xx-xx-xx-xx.ngrok-free.app -> http://localhost:5300
```

复制 `https://xxxx-xx-xx-xx-xx.ngrok-free.app` 这个 URL。

### 2.3 测试 ngrok 连接

在浏览器中访问：

```
https://your-ngrok-url.ngrok-free.app/health
```

应该返回：

```json
{
  "status": "healthy",
  "environment": "development"
}
```

---

## 🔐 步骤 3: 配置后端环境变量

在 `.env` 文件中添加以下配置：

```env
# Lemon Squeezy Payment (Test Mode)
LEMON_SQUEEZY_API_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxx
LEMON_SQUEEZY_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxx
LEMON_SQUEEZY_STORE_ID=xxxxxxxx
LEMON_SQUEEZY_VARIANT_ID=xxxxxxxx  # 月付 Variant ID
LEMON_SQUEEZY_VARIANT_ID_YEARLY=xxxxxxxx  # 年付 Variant ID（可选）
LEMON_SQUEEZY_FRONTEND_URL=http://localhost:3000  # 前端 URL，用于支付成功后重定向（如果使用 ngrok，填写 ngrok 的前端 URL）
```

**重要**：
- 确保所有值都正确填写
- 不要有多余的空格或引号
- 保存后重启后端服务

---

## 🔗 步骤 4: 配置 LemonSqueezy Webhook

### 4.1 设置 Webhook URL

1. 回到 LemonSqueezy Dashboard → **Settings** → **Webhooks**
2. 编辑之前创建的 Webhook（或创建新的）
3. 填写 **Webhook URL**：

```
https://your-ngrok-url.ngrok-free.app/api/v1/payment/webhook
```

**注意**：
- 使用 HTTPS URL（ngrok 自动提供）
- 确保路径是 `/api/v1/payment/webhook`
- 不要忘记 `/api/v1` 前缀

### 4.2 选择事件类型

确保选择了以下事件：
- ✅ `subscription_created`
- ✅ `subscription_updated`
- ✅ `subscription_expired`
- ✅ `subscription_cancelled`

### 4.3 保存 Webhook

点击 **Save** 保存配置。

---

## 🧪 步骤 5: 验证配置

### 5.1 检查后端日志

重启后端服务后，检查日志确认配置已加载：

```bash
docker-compose logs backend | grep -i lemon
```

应该看到配置已加载（没有错误）。

### 5.2 测试 Webhook 端点

使用 curl 测试 webhook 端点是否可访问：

```bash
curl -X POST https://your-ngrok-url.ngrok-free.app/api/v1/payment/webhook \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

应该返回：

```json
{
  "status": "error",
  "message": "Missing signature"
}
```

这是正常的，因为我们没有提供签名。重要的是端点可以访问。

### 5.3 测试创建 Checkout

1. 登录前端应用
2. 进入 **Settings** 页面
3. 点击 **Upgrade to Pro** 按钮
4. 应该能看到 LemonSqueezy 的 checkout 页面

如果看到错误，检查：
- 后端日志中的错误信息
- `.env` 文件中的配置是否正确
- API Key 是否有权限

---

## 🎯 步骤 6: 测试完整流程

### 6.1 创建测试订阅

1. 在前端点击 **Upgrade to Pro**
2. 在 LemonSqueezy checkout 页面：
   - 使用测试卡号：`4242 4242 4242 4242`
   - 任意未来日期作为过期日期
   - 任意 CVC
   - 任意邮编
3. 完成支付

### 6.2 验证 Webhook 处理

1. **检查后端日志**：

```bash
docker-compose logs backend | grep -i webhook
```

应该看到：
- `Successfully processed webhook: subscription_created`
- `Activated Pro subscription for user ...`

2. **检查数据库**：

```sql
-- 查看 payment_events 表
SELECT * FROM payment_events ORDER BY created_at DESC LIMIT 5;

-- 查看用户订阅状态
SELECT id, email, is_pro, subscription_id, subscription_type, plan_expiry_date 
FROM users 
WHERE email = 'your-test-email@example.com';
```

3. **检查前端**：

刷新前端页面，用户应该看到：
- ✅ Pro 徽章
- ✅ 升级按钮变为 "Manage Subscription"

### 6.3 测试 Webhook 事件

在 LemonSqueezy Dashboard 中：

1. 进入 **Subscriptions**
2. 找到测试订阅
3. 可以测试：
   - **Cancel Subscription** → 应该触发 `subscription_cancelled`
   - **Expire Subscription**（手动） → 应该触发 `subscription_expired`

每次操作后检查后端日志和数据库确认事件已处理。

---

## 🐛 故障排查

### 问题 1: Webhook 返回 404

**原因**：ngrok URL 或路径不正确

**解决**：
- 确认 ngrok URL 正确
- 确认路径是 `/api/v1/payment/webhook`（不是 `/payment/webhook`）
- 检查后端服务是否在运行

### 问题 2: Webhook 签名验证失败

**原因**：`LEMON_SQUEEZY_WEBHOOK_SECRET` 配置错误

**解决**：
- 确认 `.env` 中的 `LEMON_SQUEEZY_WEBHOOK_SECRET` 与 LemonSqueezy Dashboard 中的 **Signing Secret** 一致
- 重启后端服务

### 问题 3: Checkout 创建失败

**原因**：API Key、Store ID 或 Variant ID 配置错误

**解决**：
- 检查 `.env` 中的所有 LemonSqueezy 配置
- 确认 API Key 有正确权限
- 确认 Store ID 和 Variant ID 正确
- 查看后端日志中的详细错误信息

### 问题 4: ngrok URL 变化

**原因**：免费版 ngrok URL 每次重启都会变化

**解决**：
- 使用 ngrok 的固定域名功能（需要付费）
- 或者每次重启 ngrok 后更新 LemonSqueezy Webhook URL

### 问题 5: Webhook 事件未处理

**原因**：数据库连接问题或事件处理逻辑错误

**解决**：
- 检查后端日志中的错误信息
- 检查数据库连接
- 查看 `payment_events` 表中的 `processed` 字段
- 如果 `processed=False`，查看日志中的错误详情

---

## 📝 测试检查清单

- [ ] ngrok 已启动并可以访问后端
- [ ] `.env` 文件已配置所有 LemonSqueezy 变量
- [ ] 后端服务已重启并加载新配置
- [ ] LemonSqueezy Webhook URL 已配置
- [ ] Webhook Secret 已配置
- [ ] 可以创建 Checkout 链接
- [ ] 测试支付可以完成
- [ ] Webhook 事件可以正常接收和处理
- [ ] 用户订阅状态正确更新
- [ ] 前端正确显示 Pro 状态

---

## 🔄 从测试模式切换到生产模式

当准备上线时：

1. **切换 LemonSqueezy 到生产模式**
   - 在 Dashboard 右上角切换
   - 获取生产环境的 API Key、Store ID、Variant ID

2. **更新环境变量**
   - 使用生产环境的配置值
   - 更新 Webhook URL 为生产域名

3. **配置生产 Webhook**
   - 使用生产域名：`https://yourdomain.com/api/v1/payment/webhook`
   - 更新 Webhook Secret

4. **测试生产流程**
   - 使用真实支付方式测试
   - 验证所有 Webhook 事件

---

## 📚 相关文档

- [LemonSqueezy API 文档](https://docs.lemonsqueezy.com/api)
- [LemonSqueezy Webhooks 文档](https://docs.lemonsqueezy.com/help/webhooks)
- [项目支付实现文档](./PAYMENT_IMPLEMENTATION.md)

---

## 💡 提示

1. **保持 ngrok 运行**：测试期间不要关闭 ngrok，否则 Webhook 无法接收
2. **查看日志**：遇到问题时，首先查看后端日志
3. **测试卡号**：LemonSqueezy 测试模式可以使用 `4242 4242 4242 4242`
4. **事件顺序**：订阅创建时可能同时触发多个事件，系统会自动处理重复事件（idempotency）
