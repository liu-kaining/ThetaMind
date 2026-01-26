# Backend 启动问题排查指南

## 问题：backend 无法启动

### 常见原因和解决方案

---

## 1. 缺少依赖（最常见）

**错误信息**：
```
ModuleNotFoundError: No module named 'fastapi'
```

**解决方案**：

#### 方法 A: 使用 pip 安装（推荐）

```bash
cd backend
pip install -r requirements.txt
```

#### 方法 B: 如果遇到 SSL 证书问题

```bash
pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt
```

#### 方法 C: 使用虚拟环境（最佳实践）

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

---

## 2. 缺少 .env 文件

**错误信息**：
```
KeyError: 'DATABASE_URL'
```

**解决方案**：

```bash
# 从项目根目录
cp .env.example .env

# 然后编辑 .env 文件，填入必要的配置
# 至少需要：
# - DATABASE_URL
# - REDIS_URL
# - JWT_SECRET_KEY
```

---

## 3. 数据库连接失败

**错误信息**：
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**解决方案**：

1. **检查 PostgreSQL 是否运行**：
   ```bash
   # macOS
   brew services list | grep postgresql
   
   # 或者
   pg_isready
   ```

2. **检查 DATABASE_URL 配置**：
   ```bash
   # .env 文件中的 DATABASE_URL 应该是：
   DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/dbname
   ```

3. **创建数据库**（如果不存在）：
   ```bash
   createdb thetamind
   ```

---

## 4. Redis 连接失败

**错误信息**：
```
redis.exceptions.ConnectionError: Error connecting to Redis
```

**解决方案**：

1. **检查 Redis 是否运行**：
   ```bash
   # macOS
   brew services list | grep redis
   
   # 或者
   redis-cli ping
   # 应该返回 PONG
   ```

2. **启动 Redis**（如果没有运行）：
   ```bash
   # macOS
   brew services start redis
   
   # 或者直接运行
   redis-server
   ```

3. **Redis 是可选的**：如果 Redis 不可用，backend 会继续运行（但有警告）

---

## 5. Python 版本不兼容

**要求**：Python 3.10+

**检查版本**：
```bash
python --version
```

**解决方案**：

如果版本太低，需要升级 Python：

```bash
# macOS (使用 Homebrew)
brew install python@3.11

# 或者使用 pyenv
pyenv install 3.11.0
pyenv local 3.11.0
```

---

## 6. 端口被占用

**错误信息**：
```
OSError: [Errno 48] Address already in use
```

**解决方案**：

1. **查找占用端口的进程**：
   ```bash
   lsof -i :8000
   ```

2. **杀死进程**：
   ```bash
   kill -9 <PID>
   ```

3. **或者使用其他端口**：
   ```bash
   uvicorn app.main:app --reload --port 8001
   ```

---

## 快速启动脚本

使用提供的启动脚本：

```bash
cd backend
./start_backend.sh
```

这个脚本会自动：
- 检查 Python 版本
- 检查 .env 文件
- 检查并安装依赖
- 启动服务器

---

## 手动启动步骤

如果启动脚本不工作，手动执行：

```bash
# 1. 进入 backend 目录
cd backend

# 2. 安装依赖（如果还没安装）
pip install -r requirements.txt

# 3. 确保 .env 文件存在
# (从项目根目录)
cp ../.env.example ../.env
# 然后编辑 ../.env

# 4. 启动服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 使用 Docker（推荐用于生产环境）

如果本地环境有问题，可以使用 Docker：

```bash
# 从项目根目录
docker-compose up backend
```

这会在容器中运行 backend，自动处理所有依赖。

---

## 检查启动是否成功

启动后，访问：

- **健康检查**: http://localhost:8000/health
- **API 文档**: http://localhost:8000/docs
- **根路径**: http://localhost:8000/

如果看到 JSON 响应，说明启动成功！

---

## 仍然无法启动？

1. **查看完整错误日志**：
   ```bash
   python -m app.main 2>&1 | tee backend_error.log
   ```

2. **检查日志文件**：
   - 查看 `backend_error.log` 中的完整错误信息

3. **常见问题检查清单**：
   - [ ] Python 版本 >= 3.10
   - [ ] 依赖已安装 (`pip list | grep fastapi`)
   - [ ] .env 文件存在且配置正确
   - [ ] PostgreSQL 运行中
   - [ ] Redis 运行中（可选）
   - [ ] 端口 8000 未被占用

---

## 获取帮助

如果以上方法都不行，请提供：
1. Python 版本 (`python --version`)
2. 完整错误信息
3. .env 文件内容（隐藏敏感信息）
4. 操作系统信息
