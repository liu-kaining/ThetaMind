# **ThetaMind 产品需求文档 (PRD)**

| 版本 | 日期 | 修改人 | 备注 |
| :---- | :---- | :---- | :---- |
| v2.0 | 2025-05-20 | ThetaMind Team | **Golden Master**: 同步 Tech Spec v2.0，确立 Gemini 3.0 Pro 核心与多模型架构 |

## **1\. 项目愿景与设计哲学 (Vision & Philosophy)**

### **1.1 项目背景**

**ThetaMind** 旨在解决美股期权交易中的“分析与执行断层”问题。我们不试图替代券商 App，而是成为交易者的**第二屏 (Second Screen)**——一个冷静的**战前指挥室 (The War Room)**。

**Motto**: Plan on ThetaMind, Execute on Tiger. (在 ThetaMind 策划，在老虎证券执行。)

### **1.2 核心定位**

* **纯粹分析**：严格**不涉及**实盘交易执行，规避牌照风险。  
* **数据韧性**：即使上游数据源波动，系统也能提供降级服务，不让用户“瞎眼”。  
* **AI 驱动**：利用 **Gemini 3.0 Pro** 的推理能力进行机会发现，并具备切换至 DeepSeek/Qwen 的战略灵活性。

## **2\. 核心用户画像 (Target Audience)**

1. **进阶期权玩家**：熟悉 Greeks，需要专业的损益推演工具，对券商简陋的图表不满。  
2. **量化初学者**：希望验证策略逻辑，需要 AI 辅助解释复杂的风险敞口。  
3. **财经大 V**：需要导出极具设计感（Lightweight Charts 渲染）的损益图用于社交分享。

## **3\. 功能需求详解 (Functional Requirements)**

### **3.1 市场洞察与发现 (Discovery Module)**

* **AI 每日精选 (AI Daily Picks)**  
  * **机制**：每日 08:30 AM (EST) 自动生成。  
  * **逻辑**：扫描高 IV 异动个股，结合宏观新闻（Google Search Grounding），生成 3-5 个策略思路。  
  * **冷启动优化**：系统启动时自动检测，若今日未生成则立即补生成，确保首页不留白。  
* **智能筛选器**：支持自然语言（如“找 IV Rank \> 80 的科技股 Put”）转 SQL/API 查询。

### **3.2 策略实验室 (Strategy Lab)**

* **专业构建器**：支持 4 腿以上策略（Iron Condor, Butterfly 等）。  
* **实时风控推演 (Scenario Simulator)**：  
  * 拖动滑块模拟：股价波动、时间流逝 (Theta Decay)、波动率改变 (Vega Risk)。  
  * **可视化**：使用 **Lightweight Charts** 和 **Recharts** 渲染，提供类似 TradingView 的专业交互体验。

### **3.3 交易交接助手 (Execution Handoff)**

* **智能定价顾问 (Smart Price Advisor)** *\[Pro\]*  
  * 基于实时 Bid/Ask Spread，计算保守/激进/捡漏三个价位。  
  * *数据源*：Tiger Brokers 实时行情（经 Redis 5s 缓存）。  
* **交易小抄 (Cheat Sheet)**  
  * 手机端核心功能：全屏展示大字号参数（代码、方向、限价），方便用户手持手机对照下单。

### **3.4 AI 投顾与深度报告 (AI Copilot)**

* **核心模型**：**Gemini 3.0 Pro**。  
* **备用模型**：DeepSeek-V3 / Qwen (当 Google API 异常或需要特定推理能力时切换)。  
* **上下文优化**：自动过滤深度虚值/实值期权，只将 ATM 上下 15% 的核心数据喂给 AI，避免 Token 浪费和幻觉。  
* **输出控制**：强制结构化 Markdown 输出，防止前端渲染崩溃。

### **3.5 视觉导出引擎 (Visual Engine)**

* **社交战报**：一键生成适配 Twitter/Instagram 的高清图片（4K 分辨率）。  
* **品牌化**：Pro 用户可去除水印或上传个人 Logo。

## **4\. 平台差异化设计 (Platform Specifics)**

| 功能模块 | 🖥️ Desktop Web (桌面端) | 📱 Mobile Web (移动端) |
| :---- | :---- | :---- |
| **时区显示** | **强制 US/Eastern (纽交所时间)** | **强制 US/Eastern** |
| **策略构建** | ✅ 完整拖拽构建 | ❌ 仅查看已保存策略 |
| **图表交互** | ✅ 完整鼠标交互、十字光标 | ✅ 手势缩放、长按查价 |
| **交易交接** | ✅ 侧边栏小抄 | ✅ **全屏大字模式** |

## **5\. 商业模式与配额 (Business Model)**

### **5.1 会员权益 (Freemium)**

| 权益 | 🌱 Free (免费版) | 💎 Pro (专业版 / $29/mo) |
| :---- | :---- | :---- |
| **期权数据** | **延迟 15 分钟** (Redis 缓存) | **实时流式** (5s 刷新) |
| **智能定价** | ❌ 不可用 | ✅ **基于实时盘口** |
| **AI 报告** | 1 次/天 | **50 次/天** |
| **AI 模型** | Gemini Flash (快速) | **Gemini 3.0 Pro (深度)** |
| **服务韧性** | 基础优先级 | **高优先级 (独立限流池)** |

### **5.2 支付与审计**

* **平台**：Lemon Squeezy (MoR)。  
* **审计**：所有 Webhook 事件必须记录在 payment\_events 表中，确保每一分钱的权益变动都有据可查（Idempotency）。

## **6\. 非功能需求 (Non-functional Requirements)**

1. **服务韧性 (Resilience)**：  
   * **熔断机制**：当 Tiger API 错误率 \> 50% 时，自动开启熔断，返回缓存数据并提示“服务降级中”，防止后端雪崩。  
2. **数据准确性**：  
   * Greeks 计算误差 \< 0.01%。  
   * **时区安全**：后端统一 UTC 存储，前端统一美东时间 (EST) 展示，杜绝“期权提前过期”的显示 Bug。  
3. **隐私**：用户策略组合视为核心隐私，严禁第三方共享。  
4. **合规**：全站显著位置悬挂免责声明。

## **7\. 开发里程碑**

* **Phase 1 (Foundation)**: 架构搭建 (FastAPI+Redis+Postgres)，接入延迟数据，Lightweight Charts 集成。  
* **Phase 2 (Intelligence)**: 接入 Gemini 3.0 Pro，实现“每日精选”与“AI 报告”。  
* **Phase 3 (Monetization)**: 接入 Lemon Squeezy，上线 Pro 实时数据流与审计系统。