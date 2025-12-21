# 前端构建错误修复

## 问题

在 Docker 构建时遇到 TypeScript 错误：
1. `Cannot find module '@/lib/utils'`
2. `Cannot find module '@/lib/strategyTemplates'`
3. 隐式 `any` 类型错误

## 修复

### 1. 修复 TypeScript 模块解析

将 `tsconfig.json` 中的 `moduleResolution` 从 `"bundler"` 改为 `"node"`，以兼容 Docker 构建环境。

### 2. 修复类型错误

在 `StrategyLab.tsx` 中为 `map` 回调函数的参数添加显式类型：

```typescript
const legsWithIds: StrategyLegForm[] = templateLegs.map(
  (leg: { type: "call" | "put"; action: "buy" | "sell"; strike: number; quantity: number; expiry: string }, 
   index: number) => ({
    ...leg,
    id: `template-${Date.now()}-${index}`,
    premium: 0,
  })
)
```

### 3. 构建命令优化

将构建命令从 `tsc && vite build` 改为 `tsc --noEmit && vite build`，只进行类型检查，不生成文件（Vite 会处理编译）。

## 验证

重新构建前端：

```bash
# 在 VM 上
cd /path/to/ThetaMind
docker compose build frontend
docker compose up -d frontend
```

## 如果问题仍然存在

### 检查文件是否存在

```bash
# 在 Docker 容器中检查
docker compose exec frontend sh
ls -la /app/src/lib/
# 应该看到 utils.ts 和 strategyTemplates.ts
```

### 检查路径别名配置

确保 `vite.config.ts` 和 `tsconfig.json` 中的路径别名配置一致：

```typescript
// vite.config.ts
resolve: {
  alias: {
    '@': path.resolve(__dirname, './src'),
  },
}
```

```json
// tsconfig.json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### 清理并重新构建

```bash
# 清理 Docker 缓存
docker compose down
docker system prune -a

# 重新构建
docker compose build --no-cache frontend
docker compose up -d
```

