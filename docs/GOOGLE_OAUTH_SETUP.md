# Google OAuth 配置指南

## 问题：Google OAuth 配置错误

### 常见错误类型：

1. **"no registered origin" / "Error 401: invalid_client"**
   - 表示授权 JavaScript 源未配置

2. **"origin_mismatch" / "Error 400: origin_mismatch"**
   - 表示当前访问的 URL 与 Google Cloud Console 中配置的授权源不匹配
   - **这是最常见的问题！**

### 解决方案

这表示 Google OAuth 的授权 JavaScript 源未在 Google Cloud Console 中正确配置，或者当前访问的 URL 与配置的不匹配。

---

## 解决方案

### 步骤 1: 访问 Google Cloud Console

1. 打开 [Google Cloud Console](https://console.cloud.google.com/)
2. 选择你的项目（或创建新项目）
3. 导航到 **APIs & Services** → **Credentials**

### 步骤 2: 找到你的 OAuth 2.0 Client ID

1. 在 "OAuth 2.0 Client IDs" 列表中找到你的客户端 ID
2. 点击编辑（铅笔图标）

### 步骤 3: 添加授权 JavaScript 源（最重要！）

**这是解决 `origin_mismatch` 错误的关键步骤！**

在 "Authorized JavaScript origins" 部分，添加以下所有可能的访问地址：

**开发环境（必须全部添加）：**
```
http://localhost
http://localhost:80
http://localhost:3000
http://localhost:5173
http://127.0.0.1
http://127.0.0.1:80
http://127.0.0.1:3000
http://127.0.0.1:5173
```

**重要提示：**
- 如果你通过 `http://localhost` 访问（没有端口号），必须添加 `http://localhost`
- 如果你通过 `http://localhost:3000` 访问，必须添加 `http://localhost:3000`
- **必须添加所有你可能使用的 URL 组合！**
- 不能有尾部斜杠（`/`）
- 必须完全匹配（区分大小写）

### 步骤 4: 添加授权重定向 URI（可选但推荐）

在 "Authorized redirect URIs" 部分，添加相同的 URI：

**开发环境：**
```
http://localhost
http://localhost:80
http://localhost:3000
http://localhost:5173
http://127.0.0.1
http://127.0.0.1:80
http://127.0.0.1:3000
http://127.0.0.1:5173
```

**生产环境：**
```
https://yourdomain.com
https://www.yourdomain.com
```

### 步骤 5: 保存并等待生效

1. 点击 "Save"
2. 等待 1-2 分钟让更改生效
3. 清除浏览器缓存或使用无痕模式测试

---

## 验证配置

### 检查当前使用的 Client ID

查看 `.env` 文件中的 `GOOGLE_CLIENT_ID`：

```bash
grep GOOGLE_CLIENT_ID .env
```

### 检查前端配置

确保 `frontend/src/App.tsx` 中正确读取了环境变量：

```typescript
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ""
```

### 检查 Docker 构建

确保 Docker 构建时传递了环境变量（已在 `docker-compose.yml` 中配置）：

```yaml
build:
  args:
    - VITE_GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
```

---

## 常见问题

### Q: 为什么需要添加多个 URI？

A: 因为开发时可能使用不同的端口（Vite 默认 5173，Docker 可能映射到 3000），生产环境使用不同域名。

### Q: 更改后多久生效？

A: 通常立即生效，但有时需要等待 1-2 分钟。如果仍有问题，尝试：
- 清除浏览器缓存
- 使用无痕模式
- 重新构建 Docker 容器

### Q: 如何确认 Client ID 是否正确？

A: 在 Google Cloud Console 中：
1. 查看 Client ID（格式：`xxx.apps.googleusercontent.com`）
2. 与 `.env` 文件中的值对比
3. 确保完全一致（包括连字符）

---

## 快速检查清单

- [ ] Google Cloud Console 中已创建 OAuth 2.0 Client ID
- [ ] Client ID 已添加到 `.env` 文件（`GOOGLE_CLIENT_ID`）
- [ ] **授权 JavaScript 源已添加（包含所有可能的访问 URL）**
- [ ] 授权重定向 URI 已添加（包含所有使用的端口）
- [ ] **当前访问的 URL 已在 JavaScript 源列表中**
- [ ] Docker 构建时传递了环境变量
- [ ] 已重新构建前端容器
- [ ] 已清除浏览器缓存

## 如何确认当前访问的 URL？

1. 查看浏览器地址栏中的完整 URL
2. 例如：如果你看到 `http://localhost:3000/login`，那么 JavaScript 源应该是 `http://localhost:3000`
3. 如果你看到 `http://localhost/login`，那么 JavaScript 源应该是 `http://localhost`

---

## 测试步骤

1. 重新构建前端：
   ```bash
   docker-compose up -d --build frontend
   ```

2. 访问登录页面：
   ```
   http://localhost:3000/login
   ```

3. 点击 "Sign in with Google" 按钮

4. 应该能正常跳转到 Google 登录页面，不再出现 "no registered origin" 错误

---

**注意：** 如果使用 Docker 部署，确保生产环境的域名也添加到 Google Cloud Console 的授权 URI 列表中。

