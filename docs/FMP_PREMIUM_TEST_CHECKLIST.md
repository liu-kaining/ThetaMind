# FMP Premium 测试验证清单

已订阅 FMP Premium 后，请按本清单逐项验证，确保数据与 AI 报告流程正常运行。

---

## 一、环境配置

### 1.1 `.env` 必填项

```bash
# FMP Premium API Key（必填）
FINANCIAL_MODELING_PREP_KEY=your_premium_api_key_here
```

- 从 [FMP Developer](https://site.financialmodelingprep.com/developer/docs/) 获取 API Key
- Premium 使用与 Free 相同的 Key，仅配额与数据范围不同
- 启动前后端后，检查日志应出现：`MarketDataService: Using Financial Modeling Prep API (Primary data source)`

### 1.2 其他相关配置（可选）

- **Tiger**：若测试期权链、option_chain 拉取，需配置 `TIGER_*` 相关环境变量
- **Gemini**：需配置 `GOOGLE_API_KEY` 或 Vertex 相关配置以运行 AI 报告

---

## 二、Data Enrichment 使用的 FMP 接口

| 数据项 | 实现位置 | FMP 调用 | 说明 |
|--------|----------|----------|------|
| fundamental_profile | tasks.py `_run_data_enrichment` | MarketDataService.get_financial_profile (FinanceToolkit) | 财务、估值、波动率等 |
| analyst_data | 同上 | get_analyst_estimates + get_price_target_summary | 分析师预估与目标价 |
| iv_context | 同上 | 从 fundamental_profile.volatility 解析 | 历史波动率 |
| upcoming_events / catalyst | 同上 | `v3/earning_calendar` (from, to) | 财报日历 |
| historical_prices | 同上 | get_historical_data (FinanceToolkit) | 近 60 日日线 |
| sentiment / market_sentiment | 同上 | `v3/stock_news` (tickers, limit) | 个股新闻 |

---

## 三、测试步骤建议

### 3.1 快速验证 FMP 连通性

```bash
cd backend
python -c "
from app.services.market_data_service import MarketDataService
svc = MarketDataService()
# 测试 analyst estimates（Data Enrichment 使用）
import asyncio
r = asyncio.run(svc.get_analyst_estimates('AAPL', period='quarter', limit=5))
print('analyst_estimates:', 'OK' if isinstance(r, dict) and 'error' not in r else r)
"
```

### 3.2 端到端：Strategy Lab → 生成 AI 分析

1. 登录前端，进入 **Strategy Lab**
2. 选择标的（如 AAPL）、到期日，添加至少 1 条腿
3. 勾选「使用多智能体报告」（multi_agent_report）
4. 点击「生成 AI 分析」
5. 在 **Task Center** 查看任务进度
6. 任务成功后，点击「View Report」查看报告

**检查点**：
- 任务阶段依次为：Data Enrichment → Phase A → Phase A+ → Phase B
- 报告包含：标的基本面、用户策略点评、系统推荐策略
- 若某阶段失败，查看 `task_metadata.stages` 中对应阶段的 `message`

### 3.3 一键加载推荐策略

1. 打开一份 multi_agent_report 成功生成的报告
2. 若存在「System-Recommended Strategies」，应显示「Load to Strategy Lab」
3. 点击后应跳转到 Strategy Lab，并自动填入标的、到期、腿信息

---

## 四、常见问题排查

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| `FMP API key is required` | `.env` 未配置或未加载 | 确认 `FINANCIAL_MODELING_PREP_KEY` 已设置且后端已重启 |
| upcoming_events 为空 | `v3/earning_calendar` 404 或参数错误 | 查看后端日志中 `Data enrichment (upcoming_events) failed` |
| sentiment 为空 | `v3/stock_news` 404 或参数错误 | 同上，查看 `Data enrichment (sentiment) failed` |
| Phase A/B 超时 | 模型或网络较慢 | 设计超时为 Phase A 5 分钟、Phase B 8 分钟，可适当调大 |
| Load to Strategy Lab 按钮禁用 | strategy_summary 中无 symbol 或推荐策略无 legs | 确认任务元数据中 strategy_summary 与 recommended_strategies 结构正确 |

---

## 五、FMP 接口说明（Premium）

- **Base URL**：`https://financialmodelingprep.com/stable`
- **Earnings Calendar**：`v3/earning_calendar`，参数 `from`、`to`（YYYY-MM-DD），最大间隔约 3 个月
- **Stock News**：`v3/stock_news`，参数 `tickers`（单标或逗号分隔）、`limit`
- FinanceToolkit 使用同一 FMP Key，负责 get_financial_profile、get_historical_data 等

若 FMP 文档或 API 版本更新导致接口变更，请对照 [FMP Developer Docs](https://site.financialmodelingprep.com/developer/docs/) 调整 `tasks.py` 与 `market_data_service.py` 中的 endpoint 与参数。
