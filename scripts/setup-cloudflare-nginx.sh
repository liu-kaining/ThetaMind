#!/bin/bash
# Cloudflare + Nginx 配置脚本
# 用法: ./setup-cloudflare-nginx.sh your-domain.com

set -e

if [ -z "$1" ]; then
    echo "用法: $0 <your-domain.com>"
    echo "示例: $0 thetamind.com"
    exit 1
fi

DOMAIN=$1

echo "=========================================="
echo "配置 Nginx for Cloudflare (${DOMAIN})"
echo "=========================================="

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then 
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

# 安装 Nginx（如果未安装）
if ! command -v nginx &> /dev/null; then
    echo "安装 Nginx..."
    apt-get update
    apt-get install -y nginx
    systemctl enable nginx
    systemctl start nginx
else
    echo "Nginx 已安装"
fi

# 创建 Nginx 配置
echo "创建 Nginx 配置..."
cat > /etc/nginx/sites-available/thetamind <<EOF
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};

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
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header CF-Connecting-IP \$http_cf_connecting_ip;
        proxy_set_header CF-Ray \$http_cf_ray;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 后端 API
    location /api {
        proxy_pass http://localhost:5300;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;  # Cloudflare 使用 HTTPS
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header CF-Connecting-IP \$http_cf_connecting_ip;
        proxy_set_header CF-Ray \$http_cf_ray;
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket 支持
    location /ws {
        proxy_pass http://localhost:5300;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header CF-Connecting-IP \$http_cf_connecting_ip;
    }
}
EOF

# 启用配置
if [ ! -L /etc/nginx/sites-enabled/thetamind ]; then
    ln -s /etc/nginx/sites-available/thetamind /etc/nginx/sites-enabled/
fi

# 删除默认配置（可选）
if [ -L /etc/nginx/sites-enabled/default ]; then
    echo "删除默认 Nginx 配置..."
    rm /etc/nginx/sites-enabled/default
fi

# 测试配置
echo "测试 Nginx 配置..."
nginx -t

# 重载 Nginx
echo "重载 Nginx..."
systemctl reload nginx

echo ""
echo "=========================================="
echo "Nginx 配置完成！"
echo "=========================================="
echo ""
echo "域名: ${DOMAIN}"
echo ""
echo "下一步："
echo "1. 在 Cloudflare 控制台："
echo "   - SSL/TLS 模式设置为 'Full'"
echo "   - 启用 'Always Use HTTPS'"
echo ""
echo "2. 更新 .env 文件："
echo "   VITE_API_URL=https://${DOMAIN}/api"
echo ""
echo "3. 重启前端："
echo "   docker compose restart frontend"
echo ""
echo "4. 测试访问："
echo "   curl -I https://${DOMAIN}"
echo ""

