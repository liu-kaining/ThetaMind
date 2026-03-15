# 中英文切换与报告语言设计 (I18n & Report Language)

**日期**: 2026-02-21

## 总开关

- 应用内提供 **一个总开关**（语言切换器），在布局头部与主题切换并列。
- 开关选项：**中文** / **English**。
- 切换后同时影响：
  1. **界面文案**：导航、按钮、功能模块名、提示等（通过 `LanguageContext` 的 `t()` 与 `reportLocale`）。
  2. **报告语言**：发起 AI 分析任务时，将当前 `reportLocale` 作为 `language` 参数传给后端（`zh-CN` 或 `en-US`），报告全文按该语言生成。

## 翻译原则

- **可翻译**：按钮、功能模块名、说明文案、表单标签、Toast 等，均通过翻译 key 输出中文或英文。
- **不翻译**：Call、Put、Delta、Strike、Greeks、IV 等专有名词保持英文，便于与行情/报告一致。

## 报告语言策略（当前 v1）

- **仅支持整份报告单一语言**：要么全文中文（`zh-CN`），要么全文英文（`en-US`），由用户选择的语言决定。
- **不做「一段中文一段英文」的混排**：混排模式留作后续可选增强（如 v2），当前不实现。
- 后端报告生成接口已支持 `language` 参数；前端在发起任务时传入 `reportLocale` 即可。

## 实现要点

- `frontend/src/contexts/LanguageContext.tsx`：`ReportLocale`、`translationsEn` / `translationsZh`、`t(key)`、持久化到 `localStorage.reportLocale`。
- `frontend/src/components/common/LanguageSwitcher.tsx`：总开关组件。
- 布局与 Strategy Lab 等页面使用 `useLanguage()` 取得 `reportLocale` 与 `t()`，将硬编码文案改为 `t("key")`。
