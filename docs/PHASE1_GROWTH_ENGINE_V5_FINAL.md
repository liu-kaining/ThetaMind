# ThetaMind Phase 1: 增长引擎开发方案 (v5.0 最终落地版)

**状态**: Ready for Code  
**目标**: 构建每日流量入口 (Daily Picks) 和盘中留存工具 (Anomaly Radar)  
**周期**: 3 天 + 1-2 天缓冲

---

## 核心约束与调整

### 技术栈确认
- **AI 模型**: Gemini 3.0 Pro（不改为 1.5 Flash）
- **Tiger API**: 专注实时期权数据获取（Greeks、期权链）
- **FMP API**: 专注基本面数据（Earnings Calendar、Unusual Activity、批量报价）
- **成本控制**: 暂不考虑 AI 调用成本（后续优化）

### 关键约束
1. **Tiger API**: 严禁在循环中调用，仅用于 Top 3 数据的获取
2. **错误处理**: 必须完善，降级方案（显示数据，不显示 AI 点评）
3. **监控**: 记录 FMP API 调用次数到 Redis
4. **数据源验证**: Day 1 第一件事就是验证接口可用性

---

## 📅 Day 1: 核心后端与数据源验证

### 任务 1.1: 数据源验证脚本（必须最先做）

**文件**: `scripts/verify_datasources.py`

**验证内容**:
1. FMP Earnings Calendar: `/v3/earning_calendar`（未来 5 天数据）
2. FMP Unusual Activity: `/stock/option-unusual-activity`（检查是否返回数据）
3. FinanceToolkit: IV 计算能力测试
4. Tiger API: 连通性检查

**输出**: 
- ✅ PASS / ❌ FAIL / ⚠️ FALLBACK
- 如果关键数据源不可用，脚本退出码 1

---

### 任务 1.2: 重构 DailyPicksService

**文件**: `backend/app/services/daily_picks_service.py`

**逻辑流程**:

#### Step 1: 基础池构建
- **FinanceDatabase**: 读取 SP500 列表（本地库，0 IO）
- **流动性清洗**: 调用 FMP `get_batch_quotes`，剔除 Volume < 1.5M 的标的
- **事件驱动**: 调用 FMP `/v3/earning_calendar`，筛选未来 3-5 天内有财报的股票

#### Step 2: IV Rank 计算（核心难点）
- **尝试 A**: 使用 FinanceToolkit 计算 IV Rank
  - 公式: `(Current IV - Min52W) / (Max52W - Min52W) * 100`
- **尝试 B（兜底）**: 使用 HV（历史波动率）替代 IV 进行排名
- **筛选条件**: IV Rank > 60（高波，适合卖方策略）或 < 20（低波，适合买方策略）

#### Step 3: 策略构建（Tiger API）
- 仅对 **Top 3** 候选股调用 Tiger API `get_option_chain`
- 获取实时 Greeks，构建具体策略腿：
  - **高 IV (Rank > 60)**: Iron Condor
  - **低 IV (Rank < 20) + 财报前**: Long Straddle

#### Step 4: AI 分析（Gemini 3.0 Pro）
- **模型**: Gemini 3.0 Pro（通过 AIService）
- **Prompt**: JSON Mode，输出结构化数据
  ```json
  {
    "strategy_name": "Iron Condor",
    "risk_level": "Medium",
    "expected_return_pct": 15,
    "reasoning": "IV is overheated ahead of earnings. Expect volatility crush.",
    "confidence_score": 8.5
  }
  ```
- **缓存**: 写入 Redis `daily_picks:{date}`，TTL 24 小时

---

### 任务 1.3: FMP API 调用监控

**位置**: `backend/app/services/market_data_service.py`

**实现**:
- 在 `_call_fmp_api` 方法中添加调用次数记录
- Redis Key: `fmp_usage:{date}:{endpoint}`
- 使用 `INCR` 操作，TTL 24 小时

---

## 📅 Day 2: 异动雷达 (Anomaly Radar)

### 任务 2.1: 异动扫描器

**文件**: `backend/app/services/anomaly_service.py`

**扫描逻辑**:
- **频率**: 每 5 分钟一次（Cron Job）
- **策略 A（首选）**: 如果验证通过，直接调用 FMP `/stock/option-unusual-activity`
- **策略 B（兜底）**: 
  - 获取 Most Active 股票 Top 20（FMP）
  - 拉取期权链（Tiger，使用缓存）
  - 计算: `Vol/OI > 3.0` 且 `Volume > 2000`

**异动判定规则**:
- Vol/OI 爆破: `Volume / Open Interest > 3.0` 且 `Volume > 2000`
- IV 异动: 隐含波动率较昨日上涨 > 10%（如果可用）

---

### 任务 2.2: AI 解读与缓存

**触发机制**:
- **自动**: 每小时仅对 Top 1 最显著异动生成点评（存 Redis，TTL 1 小时）
- **手动**: 其他异动用户点击“AI 解读”按钮时生成（消耗用户配额）

**Prompt**:
```
Detected {anomaly_type} on {symbol}.
Details: Volume={volume}, OI={open_interest}, Vol/OI={ratio}
Interpret this move in 10 words.
```

**模型**: Gemini 3.0 Pro（通过 AIService）

---

### 任务 2.3: 数据库模型

**文件**: `backend/app/db/models.py`

**新增模型**: `Anomaly`
```python
class Anomaly(Base):
    __tablename__ = "anomalies"
    
    id: UUID
    symbol: str
    anomaly_type: str  # "volume_surge", "iv_spike", etc.
    score: float
    details: dict  # JSONB
    ai_insight: str | None
    detected_at: datetime
```

---

### 任务 2.4: 定时任务配置

**文件**: `backend/app/services/scheduler.py`

**新增任务**:
```python
@scheduler.scheduled_job('interval', minutes=5)
async def scan_anomalies():
    """每 5 分钟扫描异动"""
    # 调用 AnomalyService.detect_anomalies()
    # 存储到数据库（清理 1 小时前的旧数据）
```

---

## 📅 Day 3: 前端与联调

### 任务 3.1: 组件开发

#### DailyPickCard 组件
**位置**: `frontend/src/components/daily-picks/DailyPickCard.tsx`

**功能**:
- 展示 AI Score（confidence_score）
- 展示策略类型（strategy_name）
- 展示风险等级（risk_level）
- "Analyze in Lab" 按钮（跳转到 Strategy Lab，传递策略参数）

#### AnomalyRadar 组件
**位置**: `frontend/src/components/anomaly/AnomalyRadar.tsx`

**功能**:
- 侧边栏滚动展示异动列表
- 实时更新（每 5 分钟轮询）
- 点击异动项显示 AI 解读（如果可用）
- 颜色编码：🔴 高优先级，🟡 中优先级，🟢 低优先级

---

### 任务 3.2: 路由跳转

**实现**: 从 DailyPickCard 跳转到 `/strategy-lab`

**参数传递**:
- 使用 `location.state` 传递策略腿参数
- 自动填充 Strategy Lab 表单

---

## 关键风控 (Code Constraints)

### 1. Tiger API 调用约束
```python
# ❌ 错误：在循环中调用 Tiger API
for symbol in symbols:
    chain = await tiger_service.get_option_chain(...)  # 禁止！

# ✅ 正确：只对 Top 3 调用
top_3 = candidates[:3]
for candidate in top_3:
    chain = await tiger_service.get_option_chain(...)  # 允许
```

### 2. 错误处理
```python
try:
    ai_analysis = await self._analyze_with_ai(strategy)
except Exception as e:
    logger.error(f"AI analysis failed: {e}")
    # 降级：返回基础数据，不显示 AI 点评
    return {
        'strategy_name': strategy['strategy_name'],
        'reasoning': 'AI analysis unavailable',
        'confidence_score': 0.0
    }
```

### 3. FMP API 监控
```python
async def _call_fmp_api(self, endpoint: str, params: dict = None):
    # 记录调用次数
    today = datetime.now(EST).date().isoformat()
    usage_key = f"fmp_usage:{today}:{endpoint}"
    await cache_service.redis.incr(usage_key)
    await cache_service.redis.expire(usage_key, 86400)
    
    # 原有逻辑...
```

---

## 实施检查清单

### Day 1: 后端核心
- [ ] 编写 `scripts/verify_datasources.py` 并运行验证
- [ ] 重构 `DailyPicksService`（按照新逻辑）
- [ ] 实现 IV Rank 计算（FinanceToolkit + HV 兜底）
- [ ] 添加 FMP API 调用监控
- [ ] 单元测试：确保筛选逻辑能吐出数据

### Day 2: 异动雷达
- [ ] 创建 `AnomalyService`
- [ ] 实现异动扫描逻辑（FMP + 兜底方案）
- [ ] 实现 AI 解读（自动 Top 1 + 手动触发）
- [ ] 创建 `Anomaly` 数据库模型
- [ ] 配置定时任务（每 5 分钟扫描）

### Day 3: 前端与联调
- [ ] 开发 `DailyPickCard` 组件
- [ ] 开发 `AnomalyRadar` 组件
- [ ] 实现路由跳转（Strategy Lab 参数传递）
- [ ] 跑通 "生成 -> 数据库 -> 前端展示" 链路
- [ ] 设置 Redis 缓存规则
- [ ] 部署生产环境并监控 FMP API 用量

---

## 技术细节补充

### 1. IV Rank 计算实现
```python
async def _calculate_iv_rank(self, symbol: str) -> Optional[float]:
    """计算 IV Rank"""
    try:
        # 尝试 A: FinanceToolkit
        toolkit = self.market_data_service._get_toolkit([symbol])
        iv_data = toolkit.options.get_implied_volatility()
        
        if iv_data is not None and not iv_data.empty:
            current_iv = float(iv_data.iloc[-1])
            min_52w = float(iv_data.min())
            max_52w = float(iv_data.max())
            
            if max_52w > min_52w:
                return ((current_iv - min_52w) / (max_52w - min_52w)) * 100
    except Exception:
        pass
    
    # 尝试 B: HV 作为代理
    try:
        hv_data = toolkit.risk.get_volatility()
        # 同样的计算逻辑...
    except Exception:
        return None
```

### 2. 缓存键设计
- `daily_picks:{date}`: 每日精选（TTL 24 小时）
- `anomaly_insight:{symbol}:{type}`: 异动 AI 解读（TTL 1 小时）
- `fmp_usage:{date}:{endpoint}`: FMP API 调用次数（TTL 24 小时）

### 3. 数据库迁移
需要创建 `Anomaly` 表的 Alembic migration：
```bash
alembic revision --autogenerate -m "add_anomaly_table"
alembic upgrade head
```

---

## 风险评估与应对

### 风险 1: 数据源验证失败
- **应对**: Day 1 第一件事就是验证，准备兜底方案

### 风险 2: Tiger API 限流
- **应对**: 严禁在循环中调用，只对 Top 3 调用，使用缓存

### 风险 3: AI 生成失败
- **应对**: 完善的错误处理，降级方案（显示数据，不显示 AI 点评）

### 风险 4: FMP API 不可用
- **应对**: 兜底方案（手动计算 Vol/OI，使用 FinanceToolkit HV）

---

## 总结

本方案基于 Gemini v5.0 规格，结合 Cursor 技术调整，形成最终落地版本。

**核心原则**:
1. **数据源验证优先**: Day 1 第一件事
2. **Tiger API 约束**: 严禁循环调用
3. **错误处理完善**: 降级方案，不崩溃
4. **监控到位**: FMP API 调用次数监控

**技术栈确认**:
- AI: Gemini 3.0 Pro
- Tiger: 实时期权数据
- FMP: 基本面数据

**时间安排**: 3 天 + 1-2 天缓冲

---

**文档版本**: v5.0 Final  
**创建时间**: 2026-01-24  
**状态**: Ready for Implementation
