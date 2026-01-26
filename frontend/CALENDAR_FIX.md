# Calendar 组件导入错误修复

## 问题

前端报错：`ReferenceError: Calendar is not defined`

## 原因

在 `frontend/src/components/layout/MainLayout.tsx` 中：
- `Calendar` 图标被注释掉了（第6行）
- 但代码中仍在使用它（第39行）

## 修复

已取消注释 `Calendar` 的导入：

```typescript
import {
  LayoutDashboard,
  FlaskConical,
  Calendar,  // ✅ 已取消注释
  FileText,
  Settings,
  // ...
} from "lucide-react"
```

## 验证

修复后，请：
1. 刷新浏览器页面
2. 如果错误仍然存在，可能需要重启前端容器：
   ```bash
   docker-compose restart frontend
   ```
3. 或者重新构建前端：
   ```bash
   docker-compose up -d --build frontend
   ```

## 状态

✅ 已修复 - `Calendar` 图标已正确导入
