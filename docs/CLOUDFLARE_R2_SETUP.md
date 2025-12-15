# Cloudflare R2 存储配置指南

## 概述

ThetaMind 现在支持将生成的 AI 图片存储到 Cloudflare R2，而不是存储在数据库中。这样可以：
- 减少数据库存储压力
- 提高图片访问速度（通过 CDN）
- 降低存储成本
- 支持更大的图片文件

## 配置步骤

### 1. 创建 Cloudflare R2 Bucket

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com/)
2. 进入 **R2** 页面
3. 点击 **Create bucket**
4. 输入 bucket 名称（例如：`thetamind-images`）
5. 选择区域（建议选择离用户最近的区域）
6. 创建 bucket

### 2. 创建 R2 API Token

1. 在 R2 页面，点击 **Manage R2 API Tokens**
2. 点击 **Create API token**
3. 配置权限：
   - **Permissions**: Read and Write
   - **Bucket access**: 选择你创建的 bucket
4. 点击 **Create API Token**
5. **重要**：保存以下信息（只显示一次）：
   - Access Key ID
   - Secret Access Key

### 3. 获取 Account ID

1. 在 Cloudflare Dashboard 右侧栏找到 **Account ID**
2. 复制 Account ID

### 4. 配置 Public URL（可选）

有两种方式访问 R2 中的图片：

#### 方式 1：使用 R2 Public URL（推荐）

1. 在 R2 bucket 设置中，启用 **Public Access**
2. R2 会自动生成一个公共 URL，格式：`https://pub-<random-id>.r2.dev`
3. 复制这个 URL

#### 方式 2：使用自定义域名

1. 在 R2 bucket 设置中，添加 **Custom Domain**
2. 配置 DNS 记录（CNAME）
3. 使用自定义域名作为 public URL

### 5. 配置环境变量

在 `.env` 文件中添加以下配置（参考项目根目录的 `.env.example` 文件）：

```bash
# Cloudflare R2 Storage Configuration
CLOUDFLARE_R2_ACCOUNT_ID=your_account_id_here
CLOUDFLARE_R2_ACCESS_KEY_ID=your_access_key_id_here
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_secret_access_key_here
CLOUDFLARE_R2_BUCKET_NAME=thetamind-images
CLOUDFLARE_R2_PUBLIC_URL_BASE=https://pub-xxx.r2.dev
```

**注意**：如果这些配置项留空或不配置，系统会自动回退到数据库存储（base64），不会影响功能。

### 6. 运行数据库迁移

```bash
cd backend
alembic upgrade head
```

这会添加 `r2_url` 字段到 `generated_images` 表。

## 工作原理

### 图片存储流程

1. **生成图片**：AI 生成图片后，系统会：
   - 优先尝试上传到 R2
   - 如果 R2 配置不完整或上传失败，回退到数据库存储（base64）

2. **图片访问**：
   - 如果图片有 `r2_url`，直接从 R2 获取
   - 如果没有 `r2_url`，从数据库读取 base64 数据（向后兼容）

### 存储路径格式

R2 中的图片路径格式：`strategy_chart/{user_id}/{strategy_hash}.{extension}`

- **一级目录**：`strategy_chart`（固定）
- **二级目录**：`{user_id}`（用户 UUID）
- **文件名**：`{strategy_hash}.{extension}`（策略哈希值，相同策略会复用同一张图片）

例如：`strategy_chart/123e4567-e89b-12d3-a456-426614174000/a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6.png`

**优势**：
- 相同策略（相同 symbol、expiration、legs）会使用相同的 hash，可以复用图片，节省存储和生成成本
- 如果 `strategy_hash` 不可用，会回退使用 `image_id`（UUID）作为文件名

## 向后兼容性

- 现有的数据库中的图片（base64）仍然可以正常访问
- 新生成的图片会优先存储到 R2
- 如果 R2 不可用，系统会自动回退到数据库存储

## 故障排查

### 图片无法上传到 R2

1. 检查环境变量是否正确配置
2. 检查 R2 API Token 权限是否正确
3. 检查 bucket 名称是否正确
4. 查看后端日志中的错误信息

### 图片无法访问

1. 检查 R2 bucket 是否启用了 Public Access
2. 检查 `CLOUDFLARE_R2_PUBLIC_URL_BASE` 是否正确
3. 检查图片 URL 是否可公开访问

### 回退到数据库存储

如果 R2 配置不完整或上传失败，系统会自动回退到数据库存储。这是正常的 fallback 机制，不会影响功能。

## 成本估算

Cloudflare R2 定价：
- **存储**：$0.015/GB/月
- **Class A 操作**（PUT, COPY, POST, LIST）：$4.50/百万次
- **Class B 操作**（GET, HEAD）：$0.36/百万次
- **出站流量**：免费（无 egress 费用）

对于 ThetaMind：
- 假设每张图片 500KB
- 1000 张图片 = 500MB = $0.0075/月
- 非常低的成本！

## 最佳实践

1. **启用 Public Access**：如果图片需要公开访问
2. **使用自定义域名**：提供更好的用户体验
3. **定期清理**：删除不再需要的图片以节省成本
4. **监控使用量**：在 Cloudflare Dashboard 中监控存储和请求量

## 相关文件

- `backend/app/services/storage/r2_service.py` - R2 存储服务
- `backend/app/api/endpoints/tasks.py` - 图片生成逻辑
- `backend/app/api/endpoints/ai.py` - 图片获取端点
- `backend/app/db/models.py` - 数据库模型（GeneratedImage）
- `backend/alembic/versions/008_add_r2_url_to_generated_images.py` - 数据库迁移

