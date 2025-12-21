# frontend/src/lib/ 目录修复指南

## 问题原因

`.gitignore` 文件中的 `lib/` 规则导致 `frontend/src/lib/` 目录被 Git 忽略，因此：
- ✅ 本地有这个目录（文件系统中有）
- ❌ 服务器上没有这个目录（Git 没有跟踪，没有提交）

## 已修复

已更新 `.gitignore`，添加了例外规则：
```
!frontend/src/lib/
```

这样 `frontend/src/lib/` 目录就不会被忽略了。

## 需要执行的操作

### 1. 添加 lib 目录到 Git

```bash
# 检查当前状态
git status frontend/src/lib/

# 添加 lib 目录
git add frontend/src/lib/

# 确认已添加
git status
```

### 2. 提交更改

```bash
# 提交 .gitignore 和 lib 目录
git add .gitignore frontend/src/lib/
git commit -m "fix: Add frontend/src/lib/ directory to git tracking"

# 推送到远程仓库
git push
```

### 3. 在服务器上拉取代码

```bash
# SSH 到服务器
ssh user@server

# 进入项目目录
cd /path/to/ThetaMind

# 拉取最新代码
git pull

# 确认 lib 目录存在
ls -la frontend/src/lib/
# 应该看到：
# - strategyTemplates.ts
# - utils.ts
# - constants/
```

### 4. 重新构建

```bash
# 在服务器上重新构建
docker compose build --no-cache frontend
docker compose up -d
```

## 验证

构建成功后，应该能看到：
- ✅ `✓ Critical files verified` 消息
- ✅ 前端构建成功
- ✅ 应用正常运行

