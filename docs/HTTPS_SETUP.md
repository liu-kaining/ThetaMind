# HTTPS 配置指南（使用 Let's Encrypt 免费 SSL 证书）

## 方案选择

### 方案 1：使用 Certbot + Nginx（推荐）
- ✅ **完全免费**（Let's Encrypt）
- ✅ **自动续期**
- ✅ **配置简单**
- ✅ **适合单机部署**

### 方案 2：使用 Cloudflare（可选）
- ✅ **免费 CDN + SSL**
- ⚠️ 需要域名使用 Cloudflare DNS

## 前提条件

1. **已购买域名**（如：thetamind.com）
2. **域名 DNS 已配置**，指向 VM 的公网 IP
3. **VM 已部署并运行**（docker-compose 已启动）
4. **端口 80 和 443 已开放**（防火墙规则）

## 方案 1：使用 Certbot（推荐）

### 步骤 1：确保域名 DNS 已配置

```bash
# 检查 DNS 解析
dig your-domain.com
# 或
nslookup your-domain.com

# 应该返回你的 VM 公网 IP
```

### 步骤 2：安装 Certbot

在 VM 上执行：

```bash
# 更新系统
sudo apt-get update

# 安装 Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# 或者使用 Snap（推荐，更新更及时）
sudo snap install --classic certbot
sudo ln -sf /snap/bin/certbot /usr/bin/certbot
```

### 步骤 3：配置 Nginx（在 Docker 容器外）

由于 Certbot 需要直接访问 Nginx，我们需要在 VM 主机上安装并配置 Nginx，而不是使用 Docker 中的 Nginx。

#### 选项 A：在主机上使用 Nginx（推荐用于 SSL）

```bash
# 安装 Nginx
sudo apt-get install -y nginx

# 创建 Nginx 配置
sudo nano /etc/nginx/sites-available/thetamind
```

Nginx 配置内容：

```nginx
# HTTP 服务器（重定向到 HTTPS）
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Let's Encrypt 验证路径
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # 其他请求重定向到 HTTPS
    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS 服务器
server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL 证书配置（Certbot 会自动填充）
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # SSL 优化配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # 前端
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
    }

    # 后端 API
    location /api {
        proxy_pass http://localhost:5300;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
    }

    # WebSocket 支持（如果需要）
    location /ws {
        proxy_pass http://localhost:5300;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# 启用配置
sudo ln -s /etc/nginx/sites-available/thetamind /etc/nginx/sites-enabled/
sudo nginx -t  # 测试配置
sudo systemctl reload nginx
```

### 步骤 4：获取 SSL 证书

```bash
# 方法 1：使用 Nginx 插件（最简单）
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# 方法 2：使用 Standalone 模式（如果 Nginx 插件不可用）
sudo certbot certonly --standalone -d your-domain.com -d www.your-domain.com
```

按照提示操作：
1. 输入邮箱地址（用于接收续期提醒）
2. 同意服务条款
3. 选择是否分享邮箱地址（可选）
4. Certbot 会自动配置 SSL 证书

### 步骤 5：配置自动续期

Let's Encrypt 证书有效期 90 天，需要定期续期：

```bash
# 测试续期
sudo certbot renew --dry-run

# 设置自动续期（systemd timer，已自动配置）
# 检查是否启用
sudo systemctl status certbot.timer
```

自动续期会在证书到期前 30 天自动执行。

### 步骤 6：更新 Docker Compose 配置（可选）

如果使用主机上的 Nginx，可以关闭 Docker Compose 中的 Nginx 服务：

```yaml
# 在 docker-compose.yml 中注释掉 nginx 服务
# nginx:
#   ...
```

或者直接移除 nginx 服务，因为主机上的 Nginx 已经处理了所有请求。

### 步骤 7：更新前端配置

确保前端的 API URL 使用 HTTPS：

```bash
# 在 .env 文件中
VITE_API_URL=https://your-domain.com/api
```

然后重启前端容器：

```bash
docker compose restart frontend
```

## 方案 2：使用 Cloudflare（更简单）

如果域名使用 Cloudflare DNS，可以启用 Cloudflare 的 SSL：

### 步骤 1：配置 Cloudflare

1. 登录 Cloudflare 控制台
2. 选择你的域名
3. 进入 **SSL/TLS** 设置
4. 选择 **Full** 或 **Full (strict)** 模式
5. 启用 **Always Use HTTPS**

### 步骤 2：配置 DNS

确保 DNS 记录指向你的 VM IP：
- Type: A
- Name: @ (或 your-domain.com)
- Content: 你的 VM IP
- Proxy status: Proxied（橙色云朵）

### 步骤 3：配置 Nginx

在主机上配置 Nginx，接受来自 Cloudflare 的 HTTPS 请求：

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # Cloudflare 会处理 SSL，我们只需要 HTTP
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api {
        proxy_pass http://localhost:5300;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

这种方式更简单，但 Cloudflare 免费版有一些限制（如不支持 WebSocket 的某些功能）。

## 验证 HTTPS 配置

```bash
# 测试 HTTPS 连接
curl -I https://your-domain.com

# 检查 SSL 证书
openssl s_client -connect your-domain.com:443 -servername your-domain.com

# 在线测试（推荐）
# 访问：https://www.ssllabs.com/ssltest/analyze.html?d=your-domain.com
```

## 常见问题

### Q1: Certbot 验证失败

**原因：** DNS 未正确配置，或防火墙阻止了端口 80

**解决：**
1. 检查 DNS 解析：`dig your-domain.com`
2. 检查防火墙：确保端口 80 和 443 开放
3. 确保 Nginx 正在运行并监听端口 80

### Q2: 证书续期失败

**原因：** Nginx 配置错误或端口被占用

**解决：**
```bash
# 手动测试续期
sudo certbot renew --dry-run

# 查看详细日志
sudo certbot renew --dry-run --verbose
```

### Q3: 混合内容警告（Mixed Content）

**原因：** 前端使用 HTTPS，但 API 请求使用 HTTP

**解决：**
- 确保 `VITE_API_URL` 使用 HTTPS
- 检查前端代码中是否有硬编码的 HTTP URL

### Q4: WebSocket 连接失败

**原因：** Nginx 代理配置不完整

**解决：** 参考上面的 WebSocket 配置示例

## 安全最佳实践

1. **强制 HTTPS**：HTTP 自动重定向到 HTTPS
2. **HSTS**：添加 HTTP Strict Transport Security 头
3. **更新 Nginx**：定期更新系统包
4. **防火墙配置**：只开放必要的端口（80, 443, 22）

### 添加 HSTS 头

在 Nginx 配置中添加：

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

## 成本

- **Let's Encrypt SSL 证书**：完全免费
- **域名**：~$10-15/年
- **总计**：只需域名费用

## 总结

推荐使用 **Certbot + Let's Encrypt** 方案：
- ✅ 完全免费
- ✅ 自动续期
- ✅ 配置一次，长期使用
- ✅ 适合生产环境

需要我帮你创建一个自动化脚本来配置 HTTPS 吗？

