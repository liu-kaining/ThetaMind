# **ThetaMind Technical Specification for Cursor**

Version: 2.0 (Golden Master \- CTO Approved)  
Target: AI Coding Assistant (Cursor/Copilot)  
Language: Python (Backend), TypeScript (Frontend)

## **1\. Project Overview (项目概述)**

**ThetaMind** is a US stock option strategy analysis platform. It serves as a "War Room" for traders to analyze strategies, visualize P\&L, and get AI-driven insights before executing trades on brokers (Tiger Brokers).

**Core Philosophy**:

* **No Execution**: We do not trade. We analyze.  
* **Freemium**: Free users get delayed data; Pro users get real-time data & smart pricing.  
* **AI-First**: **Gemini 3.0 Pro** drives recommendations, with architecture supporting **DeepSeek** & **Qwen**.  
* **Resilience**: The system must survive external API failures (Tiger/Gemini).

## **2\. System Architecture (系统架构)**

### **2.1 High-Level Component Diagram (Mermaid)**

graph TD  
    User\[User (Browser/Mobile)\] \--\>|HTTPS| Nginx\[Nginx Gateway\]  
      
    subgraph "Docker Host (HK VPS)"  
        Nginx \--\>|/api| API\[FastAPI Backend\]  
        Nginx \--\>|/| React\[React Frontend Static\]  
          
        API \--\>|Read/Write| DB\[(PostgreSQL)\]  
        API \--\>|Cache/RateLimit| Redis\[(Redis)\]  
          
        subgraph "Backend Services"  
            Auth\[Auth Service\]  
            Market\[Market Data Service\]  
            Strategy\[Strategy Engine\]  
            AI\[AI Service Adapter\]  
            Payment\[Payment Service\]  
            Scheduler\[APScheduler\]  
        end  
          
        API \--\> Auth  
        API \--\> Market  
        API \--\> Strategy  
        API \--\> AI  
        API \--\> Payment  
        Scheduler \--\>|Trigger Daily Picks| AI  
        Scheduler \--\>|Reset Quotas| DB  
    end  
      
    subgraph "External Cloud Services"  
        Auth \--\>|Verify Token| Google\[Google Identity\]  
        Market \--\>|Quote/OptionChain| Tiger\[Tiger Brokers OpenAPI\]  
        AI \--\>|Generate Report| Gemini\[Google Gemini API\]  
        Payment \--\>|Checkout/Webhook| LS\[Lemon Squeezy\]  
    end

### **2.2 Critical Data Flows**

1. **Market Data with Circuit Breaker**:  
   * App \-\> Redis Cache.  
   * (If Miss) \-\> **Circuit Breaker** \-\> Tiger API.  
   * (If Tiger Fails) \-\> Return "Service Degraded" or Stale Cache \-\> Frontend shows warning toast.  
2. **AI Analysis with Context Filtering**:  
   * User submits Strategy \-\> **Filter Logic** (Strip OTM options \> 20%) \-\> Send condensed JSON to Gemini.

## **3\. Tech Stack (技术栈)**

### **3.1 Backend (Python)**

* **Framework**: FastAPI (Async).  
* **Database**: PostgreSQL \+ SQLAlchemy (Async) \+ Alembic.  
  * *Config*: pool\_size=20, max\_overflow=10 to prevent connection exhaustion.  
* **Cache**: **Redis** (Official redis-py async).  
* **Resilience**: tenacity (Retry logic), circuitbreaker (Fail fast).  
* **Auth**: Google OAuth2 \+ JWT.  
* **Finance**: numpy, scipy.  
* **Timezone**: pytz (Server runs in UTC, converts for Tiger/US Markets).  
* **SDKs**: tigeropen, google-generativeai, httpx.  
* **Scheduler**: APScheduler.

### **3.2 Frontend (React)**

* **Core**: React 18, Vite, TypeScript.  
* **UI**: **Shadcn/UI** \+ Tailwind CSS.  
* **State**: **React Query**.  
* **Charts**: lightweight-charts, recharts.

## **4\. Database Schema (核心数据模型)**

**All Timestamps \= UTC.**

### **4.1 Users Table (users)**

* id: UUID (PK)  
* email: String (Unique, Index)  
* google\_sub: String (Unique, Index)  
* is\_pro: Boolean (Default: False)  
* subscription\_id: String (Nullable)  
* plan\_expiry\_date: DateTime (Nullable, UTC)  
* daily\_ai\_usage: Integer (Default: 0\)  
* created\_at: DateTime

### **4.2 Strategies Table (strategies)**

* id: UUID  
* user\_id: UUID (FK)  
* name: String  
* legs\_json: JSONB  
* created\_at: DateTime

### **4.3 AI Reports Table (ai\_reports)**

* id: UUID  
* user\_id: UUID (FK)  
* report\_content: Text  
* model\_used: String  
* created\_at: DateTime

### **4.4 Payment Events Table (payment\_events)**

* id: UUID (PK)  
* lemon\_squeezy\_id: String (Index)  
* event\_name: String  
* payload: JSONB  
* processed: Boolean (Default: False)  
* created\_at: DateTime

### **4.5 Daily Picks Table (daily\_picks) \- NEW**

* *Purpose: Cache the daily generated strategies to solve Cold Start problem.*  
* id: UUID  
* date: Date (Index, Unique)  
* content\_json: JSONB (List of strategy cards)  
* created\_at: DateTime

## **5\. Key Feature Implementation (核心实现细节)**

### **5.1 Resilience & Caching (The "Shield")**

* **Circuit Breaker**: Wrap tiger\_service.get\_option\_chain. If error rate \> 50%, open circuit for 60s. Raise 503 Service Unavailable immediately without waiting for timeout.  
* **Redis Strategy**:  
  * Keys: market:chain:{symbol}:{date}.  
  * **Pro**: TTL 5s.  
  * **Free**: TTL 15m.

### **5.2 Startup Logic (The "Warm Up")**

* **File**: app/main.py \-\> @asynccontextmanager  
* **Logic**:  
  1. Initialize DB / Redis connections.  
  2. Check Tiger API Connectivity (Ping).  
  3. **Check Daily Picks**:  
     * Query daily\_picks table for today().  
     * If missing \-\> Trigger ai\_service.generate\_daily\_picks() immediately in background task.

### **5.3 AI Service (Optimized)**

* **Context Optimization**:  
  * Before calling generate\_report, run filter\_option\_chain(chain\_data).  
  * **Rule**: Keep only Strikes within \+/- 15% of Spot Price. Discard deep OTM options to save Tokens and reduce noise.  
* **Grounding**: Enable tools='google\_search' for Gemini.  
* **Output**: Validate response is Markdown.

### **5.4 Payment (Audit Trail)**

* **Webhook**:  
  1. Verify Signature.  
  2. Idempotency Check (payment\_events).  
  3. Transaction:  
     * Insert payment\_event.  
     * Update user.  
     * Commit.

### **5.5 Scheduler**

* **Job 1: Daily Picks**: 08:30 AM EST. Write to daily\_picks table.  
* **Job 2: Quota Reset**: 00:00 UTC. UPDATE users SET daily\_ai\_usage \= 0\.

## **6\. API Interface Standards**

* **Security Headers**: X-Content-Type-Options: nosniff.  
* **Rate Limit Headers**: X-RateLimit-Limit, X-RateLimit-Remaining.  
* **Error Responses**:  
  {  
    "detail": "Market data service unavailable",  
    "code": "MARKET\_SERVICE\_DOWN",  
    "retry\_after": 60  
  }

## **7\. Frontend Guidelines**

### **7.1 Modern UI Architecture**

* **Error Boundaries**: Wrap Chart components. If Chart fails (data missing), show "Data Unavailable" placeholder, don't crash App.  
* **Timezone**: All displays use **New York Time (EST/EDT)**.

### **7.2 Charting**

* **Lightweight Charts**: Enable crosshair and timeScale.rightOffset.  
* **Recharts**: Add Gradient Fill (\<defs\>) to P\&L areas for professional look.

## **8\. Deployment (Docker)**

* **Health Check**: Add HEALTHCHECK instruction in Dockerfile calling GET /health.  
* **Secrets**: Use Docker Secrets or injected Env Vars.  
* **Env Vars**:  
  * DB\_POOL\_SIZE: 20  
  * AI\_MODEL\_TIMEOUT: 30