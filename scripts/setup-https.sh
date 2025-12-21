#!/bin/bash
# HTTPS 配置脚本（使用 Let's Encrypt + Certbot）
# 用法: ./setup-https.sh your-domain.com

set -e

if [ -z "$1" ]; then
    echo "用法: $0 <your-domain.com>"
    echo "示例: $0 thetamind.com"
    exit 1
fi

DOMAIN=$1
EMAIL=${2:-admin@${DOMAIN}}  # 可选：指定邮箱，默认使用 admin@domain

echo "=========================================="
echo "配置 HTTPS for ${DOMAIN}"
echo "=========================================="

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then 
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

# 检查 DNS 配置
echo "检查 DNS 配置..."
DOMAIN_IP=$(dig +short ${DOMAIN} | tail -n1)
CURRENT_IP=$(curl -s ifconfig.me)

if [ "$DOMAIN_IP" != "$CURRENT_IP" ]; then
    echo "警告: 域名 ${DOMAIN} 解析到 ${DOMAIN_IP}，但当前服务器 IP 是 ${CURRENT_IP}"
    echo "请确保 DNS 配置正确，然后继续"
    read -p "是否继续？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 安装 Certbot
echo "安装 Certbot..."
if ! command -v certbot &> /dev/null; then
    # 优先使用 Snap
    if command -v snap &> /dev/null; then
        echo "使用 Snap 安装 Certbot..."
        snap install --classic certbot
        ln -sf /snap/bin/certbot /usr/bin/certbot
    else
        echo "使用 apt 安装 Certbot..."
        apt-get update
        apt-get install -y certbot python3-certbot-nginx
    fi
else
    echo "Certbot 已安装"
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

# 创建 Nginx 配置目录
mkdir -p /var/www/certbot
chown -R www-data:www-data /var/www/certbot

# 创建初始 Nginx 配置（HTTP，用于证书验证）
echo "创建 Nginx 配置..."
cat > /etc/nginx/sites-available/thetamind <<EOF
# HTTP 服务器（用于 Let's Encrypt 验证）
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};

    # Let's Encrypt 验证路径
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # 临时重定向到后端（用于验证）
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# 启用配置
if [ ! -L /etc/nginx/sites-enabled/thetamind ]; then
    ln -s /etc/nginx/sites-available/thetamind /etc/nginx/sites-enabled/
fi

# 测试 Nginx 配置
echo "测试 Nginx 配置..."
nginx -t

# 重载 Nginx
systemctl reload nginx

# 获取 SSL 证书
echo "获取 SSL 证书..."
if certbot --nginx -d ${DOMAIN} -d www.${DOMAIN} --non-interactive --agree-tos --email ${EMAIL} --redirect; then
    echo "SSL 证书获取成功！"
else
    echo "SSL 证书获取失败，尝试使用 standalone 模式..."
    # 停止 Nginx 临时
    systemctl stop nginx
    
    certbot certonly --standalone -d ${DOMAIN} -d www.${DOMAIN} --non-interactive --agree-tos --email ${EMAIL}
    
    # 重新启动 Nginx
    systemctl start nginx
    
    # 手动更新 Nginx 配置
    echo "请手动更新 Nginx 配置以使用 SSL 证书"
    echo "证书位置:"
    echo "  /etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
    echo "  /etc/letsencrypt/live/${DOMAIN}/privkey.pem"
fi

# 创建完整的 HTTPS Nginx 配置
echo "创建完整的 HTTPS Nginx 配置..."
cat > /etc/nginx/sites-available/thetamind <<EOF
# HTTP 服务器（重定向到 HTTPS）
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};

    # Let's Encrypt 验证路径
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # 其他请求重定向到 HTTPS
    location / {
        return 301 https://\$host\$request_uri;
    }
}

# HTTPS 服务器
server {
    listen 443 ssl http2;
    server_name ${DOMAIN} www.${DOMAIN};

    # SSL 证书配置
    ssl_certificate /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    
    # SSL 优化配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # 前端
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;
    }

    # 后端 API
    location /api {
        proxy_pass http://localhost:5300;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;
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
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# 测试并重载 Nginx
echo "测试并重载 Nginx 配置..."
nginx -t
systemctl reload nginx

# 测试证书续期
echo "测试证书自动续期..."
certbot renew --dry-run

echo ""
echo "=========================================="
echo "HTTPS 配置完成！"
echo "=========================================="
echo ""
echo "域名: https://${DOMAIN}"
echo "证书位置: /etc/letsencrypt/live/${DOMAIN}/"
echo ""
echo "下一步："
echo "1. 更新 .env 文件中的 VITE_API_URL=https://${DOMAIN}/api"
echo "2. 重启前端容器: docker compose restart frontend"
echo "3. 测试 HTTPS: curl -I https://${DOMAIN}"
echo ""
echo "证书会自动续期，无需手动操作。"
echo ""

