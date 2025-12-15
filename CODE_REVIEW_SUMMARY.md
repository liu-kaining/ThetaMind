# ThetaMind 代码逻辑审查报告

## 📋 核心功能流程

### 1. 策略保存与状态管理 (`StrategyLab.tsx`)

#### 策略加载流程
```typescript
// 1. 从 URL 参数加载策略 ID
const strategyId = searchParams.get("strategy")

// 2. 查询策略数据
const { data: loadedStrategy } = useQuery({
  queryKey: ["strategy", strategyId],
  queryFn: () => strategyService.get(strategyId!),
  enabled: !!strategyId,
})

// 3. 加载策略后，标记为已保存
React.useEffect(() => {
  if (strategyId) {
    setIsStrategySaved(true)  // ✅ 从 URL 加载的策略视为已保存
  }
}, [strategyId])
```

#### 策略修改检测
以下操作会重置 `isStrategySaved = false`：
- ✅ 修改 Symbol (`handleSymbolSelect`)
- ✅ 修改 Expiration Date (`setExpirationDate`)
- ✅ 添加/删除/修改 Legs (`addLeg`, `removeLeg`, `updateLeg`)
- ✅ 修改 Strategy Name (`setStrategyName`)
- ✅ 从 Option Chain 添加 Option (`onSelectOption`)
- ✅ 加载模板 (`handleTemplateSelect`)

**关键逻辑**：无论是否有 `strategyId`，任何修改都会重置保存状态。

#### 策略保存流程
```typescript
const saveStrategyMutation = useMutation({
  mutationFn: async () => {
    return strategyService.create({
      name: strategyName,
      legs_json: {
        symbol,
        legs: legs.map(({ id, ...leg }) => leg),
      },
    })
  },
  onSuccess: (data) => {
    setIsStrategySaved(true)  // ✅ 保存成功后标记为已保存
    if (data?.id) {
      navigate(`/strategy-lab?strategy=${data.id}`, { replace: true })
    }
  },
})
```

---

### 2. AI 报告生成流程

#### 前端触发 (`StrategyLab.tsx`)
```typescript
const handleAnalyzeClick = () => {
  // ✅ 检查 1: 策略是否已保存
  if (!isStrategySaved) {
    toast.error("Please save your strategy first...")
    return
  }

  // ✅ 检查 2: 配额是否充足
  if (!hasAiQuota) {
    toast.error("Daily AI quota exceeded")
    return
  }

  // ✅ 显示确认对话框（Deep Research 模式）
  setDeepResearchConfirmOpen(true)
}
```

#### 配额计算
```typescript
// ✅ 页面加载时刷新用户数据
React.useEffect(() => {
  refreshUser()
}, [refreshUser])

// ✅ 计算剩余配额
const aiQuotaRemaining = user?.daily_ai_quota 
  ? Math.max(0, (user.daily_ai_quota || 0) - (user.daily_ai_usage || 0))
  : 0
const hasAiQuota = aiQuotaRemaining > 0
```

#### 后端任务创建 (`tasks.py`)
```python
@router.post("/tasks", response_model=TaskResponse)
async def create_task(
    request: TaskCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # ✅ 检查配额（在创建任务前）
    if request.task_type == "ai_report":
        await db.refresh(current_user)  # 刷新用户数据
        check_ai_quota(current_user)  # 如果配额不足，返回 429
    elif request.task_type == "generate_strategy_chart":
        await db.refresh(current_user)
        check_image_quota(current_user)
    
    # ✅ 创建任务
    task = await create_task_async(...)
    
    # ✅ 异步处理任务
    # 任务在后台处理，不阻塞响应
```

#### 任务处理流程 (`process_task_async`)
```python
async def process_task_async(task_id, task_type, metadata, db):
    # 1. 更新状态为 PROCESSING
    task.status = "PROCESSING"
    
    # 2. 保存完整 prompt（包含 strategy_summary JSON）
    full_prompt = await ai_provider._format_prompt(strategy_summary)
    task.prompt_used = full_prompt
    
    # 3. 生成报告（Deep Research 模式）
    report_content = await ai_service.generate_deep_research_report(
        strategy_summary=strategy_summary,
        progress_callback=progress_callback,
    )
    
    # 4. 保存报告并更新配额
    ai_report = AIReport(...)
    await increment_ai_usage(user, db)  # ✅ 递增使用量
    
    # 5. 更新任务状态为 SUCCESS
    task.status = "SUCCESS"
```

---

### 3. 配额系统

#### 配额限制定义 (`ai.py`)
```python
# 免费用户
FREE_AI_QUOTA = 1
FREE_IMAGE_QUOTA = 1

# Pro 月费用户 ($69/月)
PRO_MONTHLY_AI_QUOTA = 20
PRO_MONTHLY_IMAGE_QUOTA = 20

# Pro 年费用户 ($599/年)
PRO_YEARLY_AI_QUOTA = 30
PRO_YEARLY_IMAGE_QUOTA = 30
```

#### 配额检查函数
```python
def get_ai_quota_limit(user: User) -> int:
    if not user.is_pro:
        return FREE_AI_QUOTA
    if user.subscription_type == "yearly":
        return PRO_YEARLY_AI_QUOTA
    elif user.subscription_type == "monthly":
        return PRO_MONTHLY_AI_QUOTA
    else:
        return PRO_MONTHLY_AI_QUOTA  # 默认

def check_ai_quota(user: User) -> None:
    quota_limit = get_ai_quota_limit(user)
    if user.daily_ai_usage >= quota_limit:
        raise HTTPException(429, "Daily AI report quota exceeded")
```

#### 配额重置 (`scheduler.py`)
```python
async def reset_daily_ai_usage():
    """每天 UTC 午夜重置配额"""
    await db.execute(
        update(User)
        .values(
            daily_ai_usage=0,
            daily_image_usage=0  # ✅ 同时重置图片配额
        )
    )
```

---

### 4. Deep Research 模式

#### 强制使用 Deep Research
```python
# backend/app/api/endpoints/tasks.py
# ✅ 始终使用 Deep Research 模式（快速模式已移除）
use_deep_research = True
logger.info(f"Task {task_id} - Using Deep Research mode (only mode available)")

report_content = await ai_service.generate_deep_research_report(
    strategy_summary=strategy_summary,
    progress_callback=progress_callback,
)
```

#### Deep Research 流程 (`gemini_provider.py`)
```python
async def generate_deep_research_report(strategy_summary, progress_callback):
    # Phase 1: Planning（规划研究问题）
    planning_response = await self._call_gemini_with_search(...)
    questions = self._extract_questions(planning_response)
    
    # Phase 2: Research（逐个问题搜索研究）
    research_findings = []
    for question in questions:
        research_response = await self._call_gemini_with_search(...)
        research_findings.append(research_response)
    
    # Phase 3: Synthesis（综合所有研究结果生成报告）
    research_summary = "\n\n".join(research_findings)
    final_report = await self._call_gemini_with_search(...)
    
    return final_report
```

---

### 5. 实时数据限制

#### 免费用户限制 (`market.py`)
```python
@router.get("/option-chain")
async def get_option_chain(
    symbol: str,
    expiration_date: str,
    force_refresh: bool = False,
    current_user: User = Depends(get_current_user),
):
    # ✅ 免费用户不能使用实时数据
    if force_refresh and not current_user.is_pro:
        raise HTTPException(
            403,
            "Real-time data refresh is only available for Pro users"
        )
    
    # 返回数据（可能是缓存的）
```

---

### 6. 图片生成流程

#### 配额检查（双重检查）
```python
# 1. 创建任务时检查
@router.post("/tasks")
async def create_task(...):
    if request.task_type == "generate_strategy_chart":
        check_image_quota(current_user)  # ✅ 创建前检查
    
    task = await create_task_async(...)

# 2. 处理任务时再次检查（防止并发问题）
async def process_task_async(...):
    if task_type == "generate_strategy_chart":
        check_image_quota(user)  # ✅ 处理前再次检查
        
        # 生成图片
        image_base64 = await image_provider.generate_chart(prompt)
        
        # 保存图片
        generated_image = GeneratedImage(...)
        
        # ✅ 递增使用量
        await increment_image_usage(user, db)
```

---

## 🔍 关键检查点

### ✅ 策略保存检查
- [x] 加载模板后必须保存才能使用 AI
- [x] 修改策略后必须重新保存才能使用 AI
- [x] 从 URL 加载的策略视为已保存
- [x] 所有修改操作都会重置保存状态

### ✅ 配额检查
- [x] 页面加载时刷新用户数据
- [x] 前端显示配额信息（卡片、按钮、对话框）
- [x] 创建任务前检查配额（返回 429）
- [x] 处理任务时再次检查配额（防止并发）
- [x] 任务成功后递增使用量

### ✅ Deep Research 模式
- [x] 强制使用 Deep Research（快速模式已移除）
- [x] 显示确认对话框（3-5 分钟警告）
- [x] 显示配额信息在确认对话框中
- [x] 进度回调更新任务状态

### ✅ 数据完整性
- [x] Prompt 保存包含完整 `strategy_summary` JSON
- [x] 即使 prompt 格式化失败，也保存完整数据
- [x] Full Prompt 页面显示完整数据
- [x] 所有 None 检查和类型安全

---

## 📊 数据流

```
用户操作
  ↓
前端检查（策略保存 + 配额）
  ↓
创建任务（后端检查配额）
  ↓
异步处理任务
  ↓
生成报告/图片
  ↓
保存结果 + 递增配额
  ↓
更新任务状态
```

---

## 🎯 关键文件

1. **前端策略管理**: `frontend/src/pages/StrategyLab.tsx`
2. **任务创建**: `backend/app/api/endpoints/tasks.py`
3. **配额管理**: `backend/app/api/endpoints/ai.py`
4. **AI 服务**: `backend/app/services/ai/gemini_provider.py`
5. **用户认证**: `backend/app/api/endpoints/auth.py`
6. **市场数据**: `backend/app/api/endpoints/market.py`

---

## ⚠️ 注意事项

1. **配额检查时机**：创建任务前检查，处理任务时再次检查（防止并发）
2. **策略保存状态**：任何修改都会重置，必须重新保存
3. **Deep Research**：唯一可用模式，处理时间 3-5 分钟
4. **实时数据**：仅 Pro 用户可用，免费用户返回缓存数据
5. **Prompt 保存**：始终保存完整 `strategy_summary` JSON，即使格式化失败

---

### 7. 订阅管理流程

#### Webhook 处理 (`payment_service.py`)
```python
async def process_webhook_event(event_name, event_data, raw_payload, db):
    # 1. 幂等性检查（防止重复处理）
    existing_event = await db.execute(
        select(PaymentEvent).where(
            PaymentEvent.lemon_squeezy_id == lemon_squeezy_id
        )
    )
    if existing_event and existing_event.processed:
        return  # ✅ 已处理，跳过
    
    # 2. 记录审计日志
    payment_event = PaymentEvent(...)
    db.add(payment_event)
    
    # 3. 业务逻辑处理
    if event_name in ("subscription_created", "subscription_updated"):
        user.is_pro = True
        user.subscription_id = lemon_squeezy_id
        
        # ✅ 从 variant_id 确定订阅类型
        variant_id = attributes.get("variant_id")
        if variant_id == settings.lemon_squeezy_variant_id_yearly:
            user.subscription_type = "yearly"
        elif variant_id == settings.lemon_squeezy_variant_id:
            user.subscription_type = "monthly"
        else:
            user.subscription_type = "monthly"  # 默认
        
        # ✅ 设置过期时间
        renews_at = parse_date(attributes.get("renews_at"))
        user.plan_expiry_date = renews_at
        
    elif event_name == "subscription_expired":
        user.is_pro = False
        user.plan_expiry_date = None
        user.subscription_type = None  # ✅ 清除订阅类型
        
    elif event_name == "subscription_cancelled":
        # ✅ 不立即取消，等待自然过期
        pass
    
    # 4. 标记为已处理
    payment_event.processed = True
    await db.commit()
```

#### 用户信息端点 (`auth.py`)
```python
@router.get("/me")
async def get_current_user_info(current_user, db):
    # ✅ 动态计算配额（基于订阅类型）
    ai_quota = get_ai_quota_limit(current_user)
    image_quota = get_image_quota_limit(current_user)
    
    return UserMeResponse(
        is_pro=current_user.is_pro,
        subscription_type=current_user.subscription_type,
        plan_expiry_date=current_user.plan_expiry_date,
        daily_ai_quota=ai_quota,  # ✅ 动态配额
        daily_image_quota=image_quota,  # ✅ 动态配额
        daily_ai_usage=current_user.daily_ai_usage,
        daily_image_usage=current_user.daily_image_usage,
    )
```

---

## 🔄 待优化点

1. 可以考虑添加策略版本管理（保存历史版本）
2. 可以考虑添加配额使用历史记录
3. 可以考虑添加任务取消功能
4. 可以考虑添加批量策略分析功能

