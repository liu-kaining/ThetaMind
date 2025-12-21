# 简单 VM + Docker Compose 部署方案

## 为什么选择这个方案？

- ✅ **成本低**：单台 VM 即可（约 $10-30/月）
- ✅ **部署简单**：直接使用现有的 `docker-compose.yml`
- ✅ **快速上线**：验证市场需求后再优化
- ✅ **易于维护**：所有服务在一个地方，便于调试

## 推荐方案对比

### 方案 1：Google Cloud Compute Engine（推荐）
- **成本**：~$15-30/月（e2-medium 实例）
- **优势**：如果已有 Google Cloud 账号，配置简单
- **推荐配置**：e2-medium (2 vCPU, 4GB RAM)

### 方案 2：DigitalOcean Droplet
- **成本**：~$12/月（Basic 2GB/1 vCPU）或 $24/月（4GB/2 vCPU）
- **优势**：价格透明，配置简单，对个人开发者友好
- **推荐配置**：Basic 4GB/2 vCPU ($24/月)

### 方案 3：AWS EC2 / Azure VM
- **成本**：类似，但配置相对复杂
- **适用**：如果已有账号可以考虑

## 快速部署步骤（以 Google Cloud 为例）

### 步骤 1：创建 VM 实例

```bash
# 设置变量
PROJECT_ID="your-project-id"
INSTANCE_NAME="thetamind-vm"
ZONE="us-central1-a"  # 选择离你最近的区域

# 创建 VM 实例
gcloud compute instances create ${INSTANCE_NAME} \
  --project=${PROJECT_ID} \
  --zone=${ZONE} \
  --machine-type=e2-medium \
  --boot-disk-size=20GB \
  --boot-disk-type=pd-standard \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --tags=http-server,https-server \
  --metadata=startup-script='#!/bin/bash
    apt-get update
    apt-get install -y docker.io docker-compose-plugin
    systemctl enable docker
    systemctl start docker
    usermod -aG docker $USER
  '
```

### 步骤 2：配置防火墙规则（如果需要）

```bash
# 允许 HTTP 和 HTTPS
gcloud compute firewall-rules create allow-http-https \
  --allow tcp:80,tcp:443 \
  --source-ranges 0.0.0.0/0 \
  --target-tags http-server,https-server
```

### 步骤 3：SSH 到 VM

```bash
gcloud compute ssh ${INSTANCE_NAME} --zone=${ZONE}
```

### 步骤 4：克隆代码并配置

```bash
# 安装 Git（如果没有）
sudo apt-get update
sudo apt-get install -y git

# 克隆代码
git clone https://github.com/liu-kaining/ThetaMind.git
cd ThetaMind

# 创建 .env 文件（参考 .env.example）
cp .env.example .env
nano .env  # 编辑配置文件，填入所有必需的值
```

### 步骤 5：配置环境变量

编辑 `.env` 文件，确保包含所有必需的配置：

```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://thetamind:your_password@db:5432/thetamind
DB_USER=thetamind
DB_PASSWORD=your_secure_password
DB_NAME=thetamind

# JWT 配置
JWT_SECRET_KEY=your_jwt_secret_key_here

# Google OAuth
GOOGLE_CLIENT_ID=your_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_client_secret

# Google API Key
GOOGLE_API_KEY=your_google_api_key

# 其他配置...
```

### 步骤 6：启动服务

```bash
# 使用 Docker Compose 启动所有服务
docker compose up -d

# 查看日志
docker compose logs -f

# 检查服务状态
docker compose ps
```

### 步骤 7：配置 Nginx（可选，如果需要域名）

如果需要使用域名，可以配置 Nginx 反向代理：

```bash
# 安装 Nginx
sudo apt-get install -y nginx

# 配置反向代理
sudo nano /etc/nginx/sites-available/thetamind
```

Nginx 配置示例：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 后端 API
    location /api {
        proxy_pass http://localhost:5300;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# 启用配置
sudo ln -s /etc/nginx/sites-available/thetamind /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 步骤 8：配置 SSL（可选，使用 Let's Encrypt）

```bash
# 安装 Certbot
sudo apt-get install -y certbot python3-certbot-nginx

# 获取 SSL 证书
sudo certbot --nginx -d your-domain.com
```

## 日常维护

### 更新代码

```bash
cd /path/to/ThetaMind
git pull
docker compose down
docker compose up -d --build
```

### 查看日志

```bash
# 查看所有服务日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f backend
docker compose logs -f frontend
```

### 备份数据库

```bash
# 手动备份
docker compose exec db pg_dump -U thetamind thetamind > backup_$(date +%Y%m%d).sql

# 恢复备份
docker compose exec -T db psql -U thetamind thetamind < backup_20240120.sql
```

### 监控资源使用

```bash
# 查看容器资源使用
docker stats

# 查看系统资源
htop
df -h  # 查看磁盘使用
free -h  # 查看内存使用
```

## 成本估算

### Google Cloud Compute Engine (e2-medium)
- **实例**：~$24/月
- **磁盘**：~$3/月 (20GB)
- **网络**：~$1-5/月（根据流量）
- **总计**：~$28-32/月

### DigitalOcean Droplet (4GB/2 vCPU)
- **实例**：$24/月（包含磁盘和网络）
- **总计**：~$24/月

## 性能考虑

对于初期验证阶段，单台 VM 通常足够：

- **并发用户**：可以支持 50-100 个并发用户
- **数据库**：PostgreSQL 在 4GB RAM 下可以处理中等负载
- **Redis**：内存占用很小
- **扩展性**：如果需要，可以升级到更大的实例

## 迁移到云原生架构的时机

当以下情况出现时，考虑迁移到 Cloud Run / Cloud SQL：

1. ✅ **有稳定的付费用户**（证明市场存在）
2. ✅ **用户量增长**（单台 VM 性能不足）
3. ✅ **需要高可用性**（多区域部署）
4. ✅ **需要自动扩展**（应对流量峰值）
5. ✅ **有足够预算**（Google Cloud 赠金到位）

## 优势总结

✅ **成本低**：初期每月成本 ~$25-30  
✅ **部署简单**：使用现有 docker-compose.yml  
✅ **快速上线**：几小时内可以部署完成  
✅ **易于调试**：所有服务在同一个地方  
✅ **灵活迁移**：随时可以迁移到云原生架构  

## 注意事项

1. **安全**：
   - 使用强密码
   - 配置防火墙规则
   - 定期更新系统

2. **备份**：
   - 定期备份数据库
   - 考虑自动备份脚本

3. **监控**：
   - 设置基本监控（CPU、内存、磁盘）
   - 配置日志收集

4. **域名**：
   - 使用免费域名或购买域名（~$10-15/年）
   - 配置 DNS 指向 VM IP

## 下一步

1. 选择云服务商（推荐 DigitalOcean 或 GCP）
2. 创建 VM 实例
3. 按照步骤部署
4. 配置域名和 SSL
5. 上线测试

需要我帮你创建自动化的部署脚本吗？

