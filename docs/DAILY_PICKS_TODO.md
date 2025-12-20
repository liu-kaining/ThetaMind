# Daily Picks 功能待办事项

**状态**: ⏸️ 暂时关闭（前端入口已隐藏）

**最后更新**: 2025-12-20

## 📋 当前状态

### ✅ 已实现的功能

1. **Pipeline 架构** (`backend/app/services/daily_picks_service.py`)
   - 3步流程：市场扫描 → 策略生成 → AI 分析
   - 通过任务系统运行（`task_type="daily_picks"`）

2. **市场扫描** (`backend/app/services/market_scanner.py`)
   - 使用 Tiger Market Scanner API
   - 基本筛选：Volume > 1M, 价格变化 > 3%
   - 备选机制：API 失败时使用静态蓝筹股列表

3. **策略生成** (`backend/app/services/strategy_engine.py`)
   - 支持 3 种策略类型：
     - **Iron Condor** (NEUTRAL)
     - **Long Straddle** (VOLATILE)
     - **Bull Call Spread** (BULLISH)
   - 基于 Greeks (Delta, Gamma, Theta, Vega) 的量化逻辑
   - 为每个股票尝试 6 种组合（3 outlook × 2 risk_profile）

4. **评分系统**
   - 公式：`score = risk_reward_ratio * 0.7 + (max_profit / 1000) * 0.3`
   - 选择每个股票的最佳策略，然后选择 Top 3

5. **AI 分析**
   - 使用 `ai_service.generate_report()` 生成评论
   - 提取 headline, analysis, risks, target_price, timeframe

6. **存储和 API**
   - 数据库模型：`DailyPick` (按日期存储)
   - API 端点：`GET /api/v1/ai/daily-picks`
   - 调度：每天 08:30 EST 自动生成

### ⚠️ 已知问题和限制

1. **选股逻辑不够智能**
   - ❌ 没有考虑 IV Rank / IV Percentile（高 IV 更适合期权）
   - ❌ 没有过滤低流动性期权
   - ⚠️ 依赖 Tiger Market Scanner API，失败时使用静态列表

2. **期权到期日选择过于简单**
   - ❌ 固定为下一个周五（每周到期）
   - ❌ 没有考虑：
     - IV Rank（高 IV 时选择更远的到期日）
     - 特定事件（财报、美联储会议等）
     - 不同策略对 DTE 的偏好

3. **策略评分公式不够完善**
   - ⚠️ 权重固定（70% risk/reward, 30% profit magnitude）
   - ❌ 没有考虑：
     - POP (Probability of Profit)
     - Theta decay
     - IV Rank（是否在高 IV 时卖权）
     - 流动性评分
     - 市场条件（trending vs ranging）

4. **AI 分析没有任务化**
   - ❌ 直接在 pipeline 中调用，没有创建任务
   - ❌ 无法追踪进度、重试失败的分析
   - ❌ 如果 AI 失败，整个 pipeline 可能失败

5. **两种生成方式不一致**
   - ⚠️ Pipeline 方式（推荐）：`generate_daily_picks_pipeline()`
   - ⚠️ Cold Start 方式（旧）：`ai_service.generate_daily_picks()`
   - ⚠️ Cold Start 应该统一使用 Pipeline 方式

## 🎯 待办事项

### 高优先级

#### 1. 优化选股逻辑
**文件**: `backend/app/services/market_scanner.py`

**需求**:
- [ ] 增加 IV Rank / IV Percentile 筛选（优先选择高 IV 股票）
- [ ] 增加期权流动性检查（bid/ask spread, open interest）
- [ ] 考虑市场条件（trending vs ranging）
- [ ] 增加财报日历检查（避免在财报前选择）

**实现建议**:
```python
# 筛选条件优先级
1. Volume > 1M
2. IV Percentile > 50% (高 IV，适合期权)
3. Option liquidity: bid/ask spread < 5%, open interest > 1000
4. 价格变化 > 3% 或 在趋势中
5. 没有即将到来的财报（7天内）
```

#### 2. 动态选择期权到期日
**文件**: `backend/app/services/daily_picks_service.py`

**需求**:
- [ ] 根据 IV Rank 选择到期日
  - 高 IV (>70%): 选择更远的到期日（30-45 DTE）
  - 低 IV (<30%): 选择较近的到期日（7-14 DTE）
- [ ] 考虑策略类型偏好
  - Iron Condor: 30-45 DTE（Theta 衰减的最佳区间）
  - Long Straddle: 0-30 DTE（Gamma 敏感）
  - Bull Call Spread: 灵活
- [ ] 检查财报日历，避免在财报日期前后选择

**实现建议**:
```python
def select_optimal_expiration_date(
    symbol: str,
    iv_rank: float,
    strategy_type: str,
    available_expirations: list[str]
) -> str:
    # 1. 获取 IV Rank
    # 2. 根据策略类型和 IV Rank 选择 DTE 范围
    # 3. 过滤财报日期
    # 4. 从可用到期日中选择最接近目标 DTE 的日期
```

#### 3. 改进策略评分系统
**文件**: `backend/app/services/daily_picks_service.py`

**需求**:
- [ ] 增加多因子评分模型
  - POP (Probability of Profit)
  - Theta decay per day
  - IV Rank（高 IV 时卖权策略加分）
  - 流动性评分
  - Risk/Reward ratio
- [ ] 根据市场条件调整权重
  - Trending market: 增加 directional strategy 权重
  - Ranging market: 增加 neutral strategy 权重

**实现建议**:
```python
def calculate_strategy_score(
    strategy: CalculatedStrategy,
    iv_rank: float,
    market_condition: str,
    liquidity_score: float
) -> float:
    # 多因子评分
    score = (
        risk_reward_ratio * 0.35 +
        pop * 0.25 +
        (theta_decay_per_day / 10) * 0.15 +
        (iv_rank / 100 if selling_premium else (1 - iv_rank / 100)) * 0.15 +
        (liquidity_score / 10) * 0.10
    )
    # 根据市场条件调整
    if market_condition == "trending" and strategy.is_directional:
        score *= 1.1
    return score
```

#### 4. AI 分析任务化
**文件**: `backend/app/services/daily_picks_service.py`, `backend/app/api/endpoints/tasks.py`

**需求**:
- [ ] 为每个 pick 的 AI 分析创建独立任务
- [ ] 任务类型：`daily_pick_ai_analysis`
- [ ] 支持并行处理（提高速度）
- [ ] 支持失败重试
- [ ] 在 Task Center 中可以查看进度

**实现建议**:
```python
# 在 generate_daily_picks_pipeline() 中
# Step 3: 为 Top 3 策略创建 AI 分析任务
analysis_tasks = []
for pick_data in top_3_strategies:
    task = await create_task_async(
        db=session,
        user_id=None,  # System task
        task_type="daily_pick_ai_analysis",
        metadata={
            "pick_index": idx,
            "symbol": symbol,
            "strategy_data": strategy_data,
        }
    )
    analysis_tasks.append(task)

# 等待所有任务完成（或设置超时）
# 收集结果并合并到 picks
```

### 中优先级

#### 5. 统一生成方式
**文件**: `backend/app/main.py`

**需求**:
- [ ] Cold Start 时使用 Pipeline 方式（通过任务系统）
- [ ] 移除 `ai_service.generate_daily_picks()` 的直接调用

#### 6. 增加策略类型
**文件**: `backend/app/services/strategy_engine.py`

**需求**:
- [ ] 实现 Bear Put Spread（BEARISH outlook）
- [ ] 考虑增加其他策略类型：
  - Butterfly Spread
  - Calendar Spread
  - Diagonal Spread

#### 7. 改进 AI 分析 Prompt
**文件**: `backend/app/services/daily_picks_service.py`

**需求**:
- [ ] 为 Daily Picks 创建专门的 prompt（不要复用 `generate_report`）
- [ ] 要求返回结构化 JSON（headline, analysis, risks, target_price, timeframe）
- [ ] 增加市场背景信息（IV Rank, 近期新闻）

### 低优先级

#### 8. 增加回测和历史分析
- [ ] 记录每日 picks 的表现
- [ ] 分析哪些策略类型/股票表现最好
- [ ] 用于优化选股和评分逻辑

#### 9. 用户个性化
- [ ] 允许用户设置偏好（策略类型、风险等级）
- [ ] 根据用户历史表现推荐

#### 10. 前端优化
- [ ] 增加筛选和排序功能
- [ ] 显示更详细的分析（Greeks, POP, 等）
- [ ] 增加图表可视化

## 📁 相关文件

### 后端
- `backend/app/services/daily_picks_service.py` - Pipeline 主逻辑
- `backend/app/services/market_scanner.py` - 市场扫描
- `backend/app/services/strategy_engine.py` - 策略生成引擎
- `backend/app/api/endpoints/ai.py` - Daily Picks API
- `backend/app/api/endpoints/tasks.py` - 任务处理（需要增加 AI 分析任务）
- `backend/app/services/scheduler.py` - 定时任务
- `backend/app/main.py` - Cold Start 逻辑
- `backend/app/db/models.py` - DailyPick 模型

### 前端
- `frontend/src/pages/DailyPicks.tsx` - Daily Picks 页面（已隐藏）
- `frontend/src/components/layout/MainLayout.tsx` - 导航菜单（已注释 Daily Picks）
- `frontend/src/services/api/ai.ts` - API 客户端

## 🔧 重新启用步骤

1. 完成高优先级任务（至少完成 AI 分析任务化）
2. 在 `MainLayout.tsx` 中取消注释 Daily Picks 菜单项
3. 测试完整流程
4. 逐步启用功能

## 📝 备注

- 当前 Daily Picks 功能在技术上可以运行，但质量可能不够稳定
- 建议在完成高优先级优化后再启用
- 所有后端代码保持不变，只是隐藏前端入口

