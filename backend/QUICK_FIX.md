# Backend 快速修复指南

## 问题：backend 无法启动

### 最可能的原因：缺少依赖

---

## 🚀 快速修复（3 步）

### Step 1: 安装依赖

```bash
cd backend

# 如果遇到 SSL 证书问题，使用这个：
pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# 或者正常安装：
pip install -r requirements.txt
```

**如果还是失败**，使用虚拟环境：

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -r requirements.txt
```

---

### Step 2: 检查 .env 文件

```bash
# 从项目根目录
cd ..  # 回到项目根目录

# 如果 .env 不存在，复制示例文件
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件，填入必要的配置"
fi
```

**最少需要的配置**：
```env
DATABASE_URL=postgresql+asyncpg://thetamind:password@localhost:5432/thetamind
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your_secret_key_here_change_in_production
```

---

### Step 3: 启动服务器

```bash
cd backend

# 使用启动脚本（推荐）
./start_backend.sh

# 或者手动启动
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## ✅ 验证启动成功

访问以下 URL：

- **健康检查**: http://localhost:8000/health
- **API 文档**: http://localhost:8000/docs

如果看到 JSON 响应或 Swagger UI，说明启动成功！

---

## 🔍 常见错误

### 1. `ModuleNotFoundError: No module named 'fastapi'`

**解决**：运行 Step 1 安装依赖

---

### 2. `KeyError: 'DATABASE_URL'`

**解决**：运行 Step 2 创建 .env 文件

---

### 3. `could not connect to server` (PostgreSQL)

**解决**：
```bash
# 检查 PostgreSQL 是否运行
pg_isready

# 如果没有运行，启动它
# macOS:
brew services start postgresql@14
```

---

### 4. SSL 证书错误

**解决**：使用 `--trusted-host` 参数（见 Step 1）

---

## 📝 完整启动命令（一行）

```bash
cd backend && pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt && uvicorn app.main:app --reload
```

---

## 🐳 使用 Docker（最简单）

如果本地环境有问题，直接用 Docker：

```bash
# 从项目根目录
docker-compose up backend
```

这会自动处理所有依赖和配置。

---

## 需要帮助？

查看详细排查指南：`TROUBLESHOOTING.md`
