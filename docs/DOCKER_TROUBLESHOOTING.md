# Docker 构建问题排查指南

## 问题：无法拉取 Docker 镜像

### 错误信息
```
failed to solve: python:3.10-slim: failed to resolve source metadata
read: connection reset by peer
```

### 解决方案

#### 方案 1：使用国内 Docker 镜像加速器（推荐）

**对于 macOS/Windows Docker Desktop：**

1. 打开 Docker Desktop
2. 进入 Settings → Docker Engine
3. 添加以下配置：

```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
```

4. 点击 "Apply & Restart"

**对于 Linux：**

编辑 `/etc/docker/daemon.json`：

```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
```

然后重启 Docker：
```bash
sudo systemctl restart docker
```

#### 方案 2：手动拉取镜像

```bash
# 先手动拉取基础镜像
docker pull python:3.10-slim

# 然后再构建
docker-compose up -d --build
```

#### 方案 3：使用代理

如果你有代理，可以配置 Docker 使用代理：

**macOS/Windows:**
- Docker Desktop → Settings → Resources → Proxies
- 配置 HTTP/HTTPS 代理

**Linux:**
创建 `/etc/systemd/system/docker.service.d/http-proxy.conf`：

```ini
[Service]
Environment="HTTP_PROXY=http://proxy.example.com:8080"
Environment="HTTPS_PROXY=http://proxy.example.com:8080"
Environment="NO_PROXY=localhost,127.0.0.1"
```

然后：
```bash
sudo systemctl daemon-reload
sudo systemctl restart docker
```

#### 方案 4：重试构建

有时只是临时网络问题，可以重试：

```bash
# 清理构建缓存
docker system prune -f

# 重新构建
docker-compose up -d --build
```

### 验证镜像加速器是否生效

```bash
docker info | grep -A 10 "Registry Mirrors"
```

应该能看到配置的镜像地址。

### 其他常见问题

#### 环境变量未设置警告

这些警告是正常的，如果还没有配置 `.env` 文件：

```bash
# 创建 .env 文件
cp .env.example .env

# 编辑 .env 文件，填入必要的配置
```

#### Docker Compose 版本警告

`version: '3.8'` 在较新版本的 docker-compose 中已废弃，可以删除：

```yaml
# 删除第一行的 version: '3.8'
services:
  db:
    ...
```

