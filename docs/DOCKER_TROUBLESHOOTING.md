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

---

## 容器出网问题（backend 无法访问 FMP / 外网）

### 现象

- Company Data 搜索返回 **503**，日志里有 `FMP API request error` 或 `ConnectError`
- 其他依赖外网的接口（Tiger、Gemini 等）在容器内也可能超时或连不上

### 原因

容器默认使用 Docker 的 bridge 网络，在某些环境下：

- **DNS**：容器内解析不到外网域名（如 `financialmodelingprep.com`）
- **代理**：本机通过 HTTP/HTTPS 代理才能出网，但容器不会自动继承
- **防火墙/策略**：公司或云环境限制容器出网

### 解决方案

#### 方案 1：确认 DNS（已内置）

项目里 backend 已配置 `dns: 8.8.8.8, 8.8.4.4`。若你在国内且 8.8.8.8 不稳定，可在 `docker-compose.yml` 里把 backend 的 `dns` 改成可用 DNS，例如：

```yaml
backend:
  dns:
    - 223.5.5.5   # 阿里
    - 119.29.29.29 # 腾讯
```

改完后执行：

```bash
docker compose up -d --force-recreate backend
```

#### 方案 2：本机有代理时，让容器走代理

本机已能访问外网（通过代理）时，让 **容器内** 的请求也走同一代理：

1. 在 **项目根目录** 的 `.env` 里增加（改成你自己的代理地址和端口）：

   ```bash
   HTTP_PROXY=http://127.0.0.1:7890
   HTTPS_PROXY=http://127.0.0.1:7890
   NO_PROXY=localhost,127.0.0.1,db,redis
   ```

2. `docker-compose.yml` 里已经把这些变量传给 backend，无需改 compose 文件。

3. 重启 backend：

   ```bash
   docker compose up -d --force-recreate backend
   ```

注意：`HTTP_PROXY` 填的是 **宿主机** 上代理的地址。若代理只在宿主机监听，容器内需用 **host.docker.internal**（Mac/Windows Docker Desktop 支持）或宿主机实际 IP，例如：

```bash
# Mac/Windows Docker Desktop 示例
HTTP_PROXY=http://host.docker.internal:7890
HTTPS_PROXY=http://host.docker.internal:7890
```

#### 方案 3：backend 使用宿主机网络（仅 Linux）

在 **Linux** 上若不需要隔离网络，可让 backend 直接用宿主机网络，出网与宿主机一致：

在 `docker-compose.yml` 的 `backend` 下加：

```yaml
backend:
  network_mode: "host"
```

注意：用了 `network_mode: host` 后，`ports`、`networks` 对 backend 不再生效，访问方式会变成 `http://localhost:8000`（或你本机 IP），需相应改前端或 Nginx 的 upstream。一般只在排查出网问题时临时使用。

#### 方案 4：backend 不放进 Docker，只跑 DB/Redis 在 Docker（推荐开发/排查）

出网问题难搞时，可以 **只把 DB 和 Redis 放 Docker**，backend 在宿主机直接跑，这样 backend 和本机浏览器一样能访问 FMP/外网：

```bash
# 只启动 db + redis
docker compose up -d db redis

# 在宿主机跑 backend（需 Python/Poetry 环境）
cd backend
poetry run uvicorn app.main:app --reload --port 5300
```

`.env` 里 `DATABASE_URL` 和 `REDIS_URL` 要指向 Docker 里的服务，例如：

- `DATABASE_URL=postgresql+asyncpg://thetamind:你的密码@localhost:5432/thetamind`
- `REDIS_URL=redis://localhost:6379/0`

前端如需连这个 backend，把 `VITE_API_URL` 设为 `http://localhost:5300` 再构建/启动前端即可。

### 已做的兜底

即使 Docker 里 backend 连不上 FMP，**Company Data 搜索** 已支持回退到本地 `stock_symbols` 表，只要先跑过 [symbol 同步脚本](backend/README.md#syncing-stock-symbols-strategy-lab--search)，搜索仍可出结果。需要 FMP 详情的接口（如 overview、valuation）在容器出网恢复或改用「方案 4」后才会正常。

---

## 代理导致 Google 登录 / 外网请求失败（Connection refused）

### 现象

- Google 登录返回 **401**，日志里：`ProxyError... 127.0.0.1:7890 (或 :5300) ... Connection refused`
- 其他访问外网的请求（FMP、Gemini 等）也报同样代理错误

### 原因

在 `.env` 里设置了 `HTTP_PROXY=http://127.0.0.1:7890`（或其它端口）时，**容器内部**的 127.0.0.1 指向的是**容器自己**，不是宿主机，所以连不上你本机开的代理，导致 Connection refused。

### 解决办法

- **不需要让容器走代理时**：在 `.env` 里注释掉或删除 `HTTP_PROXY`、`HTTPS_PROXY`，重启 backend：
  ```bash
  docker compose up -d --force-recreate backend
  ```
- **需要让容器走宿主机代理时**：在 Mac/Windows 上把代理地址改成 `host.docker.internal`，例如：
  ```bash
  HTTP_PROXY=http://host.docker.internal:7890
  HTTPS_PROXY=http://host.docker.internal:7890
  ```
  并确保宿主机上代理已开启、且允许来自局域网的连接（如有选项）。

---

## Tiger 私钥解析失败（Could not deserialize key data）

### 现象

日志里出现：`request sign failed. Could not deserialize key data...`、`Failed to initialize TigerService`，随后有 `Tiger API is not reachable - service may be degraded`。

### 原因

`TIGER_PRIVATE_KEY` 必须是**完整的 PEM 格式** RSA 私钥（包含 `-----BEGIN PRIVATE KEY-----` 和 `-----END PRIVATE KEY-----`，中间换行保留）。常见错误：

- 填成占位符（如 `11111`）或错误内容
- 从别处复制时丢失换行，变成一行或多了空格
- 只填了 base64 内容，没有 BEGIN/END 两行

### 解决办法

1. 在 Tiger 开放平台重新下载或复制私钥，保证是完整 PEM（以 `-----BEGIN` 开头、以 `-----END` 结尾）。
2. 在 `.env` 里配置时：
   - 若用单行：可用 `\n` 表示换行（取决于你用的 env 解析方式）。
   - 或把私钥存成文件，在应用里用 `TIGER_PROPS_PATH` 或对应配置指向该文件。
3. 若暂时不用 Tiger（例如只用 Company Data、不做期权链），可保留当前配置；应用会降级运行，仅 Tiger 相关功能不可用。

