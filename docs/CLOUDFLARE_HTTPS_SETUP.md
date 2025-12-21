# Cloudflare HTTPS 配置指南

## 为什么这个方案更简单？

- ✅ **无需在 VM 上配置 SSL 证书**
- ✅ **Cloudflare 自动处理 HTTPS**
- ✅ **免费 CDN 加速**
- ✅ **DDoS 防护**
- ✅ **配置更简单**

## Cloudflare 配置步骤

### 1. 配置 DNS 记录

在 Cloudflare 控制台：

1. 添加 **A 记录**：
   - **Type**: A
   - **Name**: @ (或 your-domain.com)
   - **Content**: 你的 VM 公网 IP
   - **Proxy status**: ✅ Proxied（橙色云朵）- **重要！必须开启代理**

2. 可选：添加 www 子域名：
   - **Type**: A
   - **Name**: www
   - **Content**: 你的 VM 公网 IP（或使用 CNAME 指向主域名）
   - **Proxy status**: ✅ Proxied

### 2. 配置 SSL/TLS 设置

1. 进入 **SSL/TLS** 菜单
2. 选择 **Full** 或 **Full (strict)** 模式
   - **Full**: Cloudflare 到源站使用加密连接（推荐）
   - **Full (strict)**: 需要源站有有效证书（如果 VM 有自签名证书）
3. 启用 **Always Use HTTPS**（自动将 HTTP 重定向到 HTTPS）
4. 启用 **Automatic HTTPS Rewrites**（可选）

### 3. 配置 Nginx（在 VM 上）

由于 Cloudflare 处理 HTTPS，VM 上的 Nginx 只需要提供 HTTP 服务：

```bash
# 安装 Nginx（如果未安装）
sudo apt-get update
sudo apt-get install -y nginx

# 创建配置文件
sudo nano /etc/nginx/sites-available/thetamind
```

Nginx 配置（HTTP only）：

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    # 客户端真实 IP（来自 Cloudflare）
    real_ip_header CF-Connecting-IP;
    set_real_ip_from 173.245.48.0/20;
    set_real_ip_from 103.21.244.0/22;
    set_real_ip_from 103.22.200.0/22;
    set_real_ip_from 103.31.4.0/22;
    set_real_ip_from 141.101.64.0/18;
    set_real_ip_from 108.162.192.0/18;
    set_real_ip_from 190.93.240.0/20;
    set_real_ip_from 188.114.96.0/20;
    set_real_ip_from 197.234.240.0/22;
    set_real_ip_from 198.41.128.0/17;
    set_real_ip_from 162.158.0.0/15;
    set_real_ip_from 104.16.0.0/13;
    set_real_ip_from 104.24.0.0/14;
    set_real_ip_from 172.64.0.0/13;
    set_real_ip_from 131.0.72.0/22;
    set_real_ip_from 2400:cb00::/32;
    set_real_ip_from 2606:4700::/32;
    set_real_ip_from 2803:f800::/32;
    set_real_ip_from 2405:b500::/32;
    set_real_ip_from 2405:8100::/32;
    set_real_ip_from 2a06:98c0::/29;
    set_real_ip_from 2c0f:f248::/32;

    # 前端
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header CF-Connecting-IP $http_cf_connecting_ip;
        proxy_set_header CF-Ray $http_cf_ray;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 后端 API
    location /api {
        proxy_pass http://localhost:5300;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;  # Cloudflare 使用 HTTPS
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header CF-Connecting-IP $http_cf_connecting_ip;
        proxy_set_header CF-Ray $http_cf_ray;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket 支持
    location /ws {
        proxy_pass http://localhost:5300;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header CF-Connecting-IP $http_cf_connecting_ip;
    }
}
```

```bash
# 启用配置
sudo ln -s /etc/nginx/sites-available/thetamind /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # 删除默认配置（可选）

# 测试配置
sudo nginx -t

# 重载 Nginx
sudo systemctl reload nginx
```

### 4. 更新前端配置

```bash
# 编辑 .env 文件
nano .env

# 设置 API URL 为 HTTPS
VITE_API_URL=https://your-domain.com/api

# 重启前端容器
docker compose restart frontend
```

### 5. 配置防火墙

确保只允许 Cloudflare 和你的 IP 访问：

```bash
# 允许 Cloudflare IP 范围（可选，如果使用 Cloudflare 代理）
# 参考：https://www.cloudflare.com/ips/

# 或者简单允许所有 HTTP 流量（推荐，因为 Cloudflare 会过滤）
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp  # SSH
sudo ufw enable
```

## 重要配置说明

### X-Forwarded-Proto

后端需要知道请求来自 HTTPS，所以设置：
```nginx
proxy_set_header X-Forwarded-Proto https;
```

### CF-Connecting-IP

获取客户端真实 IP（Cloudflare 会传递）：
```nginx
real_ip_header CF-Connecting-IP;
proxy_set_header CF-Connecting-IP $http_cf_connecting_ip;
```

### SSL 模式选择

- **Flexible**: Cloudflare ↔ 用户使用 HTTPS，Cloudflare ↔ 源站使用 HTTP（不推荐，安全风险）
- **Full**: Cloudflare ↔ 用户和源站都使用加密（推荐）
- **Full (strict)**: 需要源站有有效证书（如果 VM 没有证书，不要选这个）

## 验证配置

### 1. 检查 DNS 解析

```bash
# 应该返回 Cloudflare 的 IP（不是你的 VM IP）
dig your-domain.com

# 或者
nslookup your-domain.com
```

### 2. 测试 HTTPS

```bash
# 从外部测试（应该返回 200）
curl -I https://your-domain.com

# 检查 SSL 证书信息
curl -vI https://your-domain.com 2>&1 | grep -i "SSL\|certificate"
```

### 3. 检查后端日志

确保后端能正确识别 HTTPS 请求：
```bash
docker compose logs backend | grep -i "forwarded"
```

### 4. 在线测试

访问：https://www.ssllabs.com/ssltest/analyze.html?d=your-domain.com

应该看到 Cloudflare 的 SSL 证书（不是你的服务器证书）。

## 优势总结

✅ **无需配置 SSL 证书**：Cloudflare 自动处理  
✅ **免费 CDN**：全球加速  
✅ **DDoS 防护**：自动防护  
✅ **配置简单**：只需 HTTP 后端  
✅ **自动 HTTPS**：Always Use HTTPS 自动启用  

## 常见问题

### Q1: 为什么看不到真实 IP？

**原因**：没有正确配置 `CF-Connecting-IP`

**解决**：参考上面的 Nginx 配置，添加 `real_ip_header` 和 `set_real_ip_from`

### Q2: 后端认为请求是 HTTP？

**原因**：没有设置 `X-Forwarded-Proto`

**解决**：在 Nginx 配置中添加 `proxy_set_header X-Forwarded-Proto https;`

### Q3: WebSocket 连接失败？

**原因**：Cloudflare 免费版对 WebSocket 支持有限制

**解决**：
- 检查 Cloudflare 控制台的 WebSocket 设置
- 或使用 Cloudflare Workers 处理 WebSocket（需要付费版）

### Q4: 想要隐藏源站 IP？

**解决**：确保 DNS 记录使用 "Proxied" 模式（橙色云朵）

## 下一步

1. ✅ 配置 DNS 记录（Proxied 模式）
2. ✅ 设置 SSL/TLS 为 Full 模式
3. ✅ 配置 VM 上的 Nginx（HTTP only）
4. ✅ 更新前端 API URL 为 HTTPS
5. ✅ 测试访问

完成！现在你的网站已经通过 Cloudflare 提供 HTTPS 了。

