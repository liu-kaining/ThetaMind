# 前端构建错误修复（服务器环境）

## 问题

在服务器上构建前端时，报错：
```
✗ Missing critical files!
ls: ./src/lib/: No such file or directory
```

但本地 `docker compose build` 构建正常。

## 可能的原因

1. **服务器上的代码未完全同步** - `frontend/src/lib/` 目录可能在服务器上不存在
2. **.dockerignore 配置问题** - 可能排除了某些文件（已检查，无此问题）
3. **构建上下文不同** - 虽然 `docker-compose.yml` 中构建上下文是 `./frontend`，但可能有问题

## 解决方案

### 1. 验证服务器上的文件结构

在服务器上运行：

```bash
cd /path/to/ThetaMind
ls -la frontend/src/lib/
# 应该看到：
# - strategyTemplates.ts
# - utils.ts
# - constants/
```

如果文件不存在，需要同步代码到服务器。

### 2. 检查构建日志

重新构建并查看详细的调试输出：

```bash
docker compose build --no-cache frontend 2>&1 | tee build.log
```

查找以下输出：
- `=== Checking src directory structure ===` - 显示复制的文件列表
- `=== Checking lib directory ===` - 显示 lib 目录内容
- `=== Full src directory tree ===` - 显示所有文件树

### 3. 如果文件确实存在但仍报错

可能是 Docker 构建缓存问题，尝试：

```bash
# 清理所有缓存
docker system prune -a

# 重新构建
docker compose build --no-cache frontend
```

### 4. 验证代码同步

确保服务器上的代码与本地一致：

```bash
# 在服务器上
cd /path/to/ThetaMind
git status  # 检查是否有未提交的更改
git pull    # 拉取最新代码（如果使用 git）

# 或者手动同步 frontend/src/lib/ 目录
```

## 当前修复

Dockerfile 已添加详细的调试信息，会在构建时显示：
1. `src` 目录结构
2. `lib` 目录内容
3. 完整的文件树
4. 如果文件缺失，会显示详细的错误信息

## 验证

重新构建后，应该能看到详细的调试输出。如果文件确实存在但构建仍然失败，请将完整的构建日志发送以便进一步诊断。

