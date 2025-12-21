# 服务器重新部署指南

## 快速部署

在服务器上运行以下命令：

```bash
# 1. 进入项目目录
cd /path/to/ThetaMind

# 2. 确保代码是最新的（如果使用 git）
git pull

# 3. 运行部署脚本
bash scripts/vm-deploy.sh
```

## 部署脚本说明

`scripts/vm-deploy.sh` 脚本会自动执行以下操作：

1. **检查 Docker 和 Docker Compose** - 如果未安装会自动安装
2. **检查环境变量** - 验证 `.env` 文件中的必需配置
3. **停止现有容器** - `docker compose down`
4. **构建并启动服务** - `docker compose up -d --build`
5. **等待服务启动** - 等待 10 秒
6. **显示服务状态** - `docker compose ps`

## 手动部署（如果脚本有问题）

如果脚本运行有问题，可以手动执行：

```bash
# 1. 进入项目目录
cd /path/to/ThetaMind

# 2. 拉取最新代码（如果使用 git）
git pull

# 3. 停止现有容器
docker compose down

# 4. 重新构建并启动（不使用缓存）
docker compose build --no-cache
docker compose up -d

# 5. 查看日志
docker compose logs -f
```

## 只重新构建特定服务

如果只想重新构建某个服务：

```bash
# 只重新构建前端
docker compose build --no-cache frontend
docker compose up -d frontend

# 只重新构建后端
docker compose build --no-cache backend
docker compose up -d backend

# 只重新构建 Nginx（通常不需要，除非配置文件变更）
docker compose build --no-cache nginx
docker compose up -d nginx
```

## 验证部署

部署完成后，验证服务是否正常运行：

```bash
# 1. 检查所有容器状态
docker compose ps

# 2. 检查后端健康状态
curl http://localhost:5300/health

# 3. 检查前端
curl http://localhost:3000

# 4. 检查 Nginx（如果配置了）
curl http://localhost/health

# 5. 查看日志
docker compose logs backend --tail=50
docker compose logs frontend --tail=50
docker compose logs nginx --tail=50
```

## 常见问题

### 问题 1：构建失败

**检查日志**：
```bash
docker compose logs backend --tail=100
docker compose logs frontend --tail=100
```

**常见原因**：
- 环境变量未设置
- 依赖下载失败（网络问题）
- Docker 镜像拉取失败

### 问题 2：服务无法启动

**检查容器状态**：
```bash
docker compose ps
```

**查看详细日志**：
```bash
docker compose logs <service-name> -f
```

### 问题 3：端口冲突

**检查端口占用**：
```bash
sudo netstat -tulpn | grep :5300
sudo netstat -tulpn | grep :3000
sudo netstat -tulpn | grep :80
```

**解决方法**：修改 `.env` 文件中的端口配置，或停止占用端口的进程。

## 完整部署流程（首次部署）

如果是首次部署，需要：

1. **克隆代码**（如果使用 git）：
   ```bash
   git clone <repository-url>
   cd ThetaMind
   ```

2. **配置环境变量**：
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，填入所有必需的配置
   nano .env
   ```

3. **运行部署脚本**：
   ```bash
   bash scripts/vm-deploy.sh
   ```

## 相关文件

- `scripts/vm-deploy.sh` - 自动化部署脚本
- `docker-compose.yml` - Docker Compose 配置
- `.env.example` - 环境变量示例
- `docs/SIMPLE_VM_DEPLOYMENT.md` - VM 部署详细指南

