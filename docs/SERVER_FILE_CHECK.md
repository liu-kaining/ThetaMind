# 服务器文件检查指南

## 问题诊断

根据构建日志：
- `src directory exists: YES` ✅
- `lib directory exists: NO` ❌

这说明 `COPY src ./src` 复制了 `src` 目录，但没有复制 `lib` 子目录。

## 在服务器上检查文件

请在服务器上运行以下命令：

```bash
# 1. 进入项目目录
cd /path/to/ThetaMind

# 2. 检查 frontend/src/lib/ 目录是否存在
ls -la frontend/src/lib/

# 3. 如果不存在，检查整个 src 目录结构
find frontend/src -type d

# 4. 检查是否有 strategyTemplates.ts 文件
find frontend/src -name "strategyTemplates.ts"

# 5. 检查 git 状态（如果使用 git）
cd frontend
git status
git ls-files src/lib/

# 6. 如果使用 git，检查是否有未提交的文件
git diff --name-only
```

## 可能的原因

1. **代码未完全同步到服务器** - `frontend/src/lib/` 目录可能在服务器上不存在
2. **Git 忽略规则** - `.gitignore` 可能排除了某些文件（但 `src/lib/` 通常不会被忽略）
3. **文件权限问题** - 虽然不太可能，但可以检查文件权限

## 解决方案

### 方案 1：同步代码到服务器

如果服务器上的代码不完整，需要同步：

```bash
# 如果使用 git
cd /path/to/ThetaMind
git pull

# 或者手动同步 frontend/src/lib/ 目录
# 从本地复制到服务器
scp -r local/path/to/frontend/src/lib user@server:/path/to/ThetaMind/frontend/src/
```

### 方案 2：检查 .gitignore

检查是否有 `.gitignore` 排除了 `src/lib/`：

```bash
cd /path/to/ThetaMind
cat .gitignore | grep -i lib
cat frontend/.gitignore 2>/dev/null | grep -i lib
```

### 方案 3：临时修复（不推荐）

如果急需部署，可以临时创建一个空的 `lib` 目录，但这不是长久之计：

```bash
mkdir -p frontend/src/lib
touch frontend/src/lib/utils.ts
touch frontend/src/lib/strategyTemplates.ts
```

## 推荐操作

1. **首先检查**服务器上的 `frontend/src/lib/` 是否存在
2. **如果不存在**，从本地同步完整代码
3. **重新构建**后应该就能成功了

