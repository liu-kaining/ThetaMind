# ThetaMind

> **Professional US Stock Option Analysis — Five Specialists. Deep Research. One Report.**

**ThetaMind** is a production-grade option strategy analysis platform that delivers **desk-style research in one click**. Build strategies with real option chains and fundamentals, run a multi-agent AI pipeline powered by **Google Gemini 3.0 Pro**, and get a single long-form report with full audit trail—**analysis and research only; we do not execute trades.**

---

## Why ThetaMind?

| Traditional tools | ThetaMind |
|-------------------|-----------|
| Single generic AI summary | **5 specialist agents** (Greeks, IV, Market, Risk, Synthesis) + **Deep Research** with live web search |
| Placeholder or delayed data | **Real option chains** (Tiger) + **real fundamentals** (FMP); Pro gets **5s refresh** |
| Black-box output | **Full task history**: every agent memo, prompt, and synthesis stored and replayable |
| Manual copy-paste | **Strategy Lab → one click** → one coherent report; no re-typing |
| Execution risk | **Analysis only** — we never place orders; you decide in your broker |

---

## Core Capabilities

- **Strategy Lab** — Pick symbol and expiration; option chain (Tiger) and fundamentals (FMP) load automatically. Build iron condors, straddles, strangles, spreads, or custom combos. Real-time Greeks, IV, max loss, break-evens.
- **Multi-Agent + Deep Research** — Five specialists run in sequence (Greeks → IV → Market → Risk → Synthesis); then Deep Research answers four questions via **live Google search** and folds them into one long-form section. One report, not five fragments.
- **Reports & Audit Trail** — Every report is stored with full task history: stage-by-stage outputs, exact prompt, and final memo. Revisit, compare runs, or export.
- **Real-Time Charts** — Candlesticks (TradingView-style), interactive payoff diagrams, Greeks curves. Pro: 5s refresh; Free: delayed (15 min cache).
- **Risk & Greeks** — Per-leg and portfolio max loss, max gain, break-evens; delta, gamma, theta, vega. AI explains the numbers in plain language.
- **Nano Banana** — AI-generated option strategy images (payoff-style diagrams, strategy layout) for sharing or presentation.

---

## Data Sources & Tech Stack

**Data**

- **Tiger Brokers OpenAPI** — Real option chains (bids, asks, volume, OI, computed Greeks). Same numbers you’d see in a broker.
- **FMP (Financial Modeling Prep)** — Fundamentals, earnings, ratios, debt, profitability. AI references real financials in the report.
- **Google Search (Gemini)** — Deep Research uses live web search for grounded, up-to-date synthesis.

**Backend**

- **FastAPI** (async), **PostgreSQL** (SQLAlchemy async + Alembic), **Redis** (cache + rate limit).
- **Resilience**: circuit breakers for Tiger/Gemini; tenacity retries; stale cache fallback so the app stays up when external APIs fail.
- **Auth**: Google OAuth2 + JWT. **Payments**: Lemon Squeezy (checkout + webhooks, idempotent, audit-logged).
- **AI**: **Google Gemini 3.0 Pro** via a provider abstraction (swap to DeepSeek/Qwen if needed). Context filtering (e.g. ±15% strike) to keep token usage and noise under control.

**Frontend**

- **React 18**, **Vite**, **TypeScript**. **Shadcn/UI** + **Tailwind CSS**.
- **React Query** for server state; **lightweight-charts** (candlesticks), **recharts** (payoff/area).
- All times **UTC** in backend; **US/Eastern** on the UI.

**Deployment**

- **Docker Compose**: PostgreSQL, Redis, FastAPI backend, React (static), Nginx gateway. Health checks, env-based config, single-command run.

---

## Architecture (High Level)

```
User (Browser)
       │
       ▼ HTTPS
   Nginx Gateway
       │
       ├── /api  ──► FastAPI Backend ──► PostgreSQL, Redis
       │                  │
       │                  ├── Auth (Google OAuth2)
       │                  ├── Market Data (Tiger + cache; circuit breaker)
       │                  ├── Strategy Engine
       │                  ├── AI Service (Gemini 3.0 Pro, multi-agent + Deep Research)
       │                  ├── Payment (Lemon Squeezy)
       │                  └── Scheduler (daily picks, quota reset)
       │
       └── /     ──► React Frontend (static)
```

**Report pipeline**

1. **Strategy Lab** — User builds strategy (symbol, expiration, legs). Option chain (Tiger) + fundamentals (FMP) loaded automatically.
2. **Five specialist agents** — Greeks → IV → Market → Risk → Synthesis. Each writes a focused memo; results feed the next stage.
3. **Deep Research** — Four questions, live Google search; answers synthesized into one long-form section.
4. **Report & task history** — Stored with full prompt, stages, and audit trail. Replay any run.

---

## Usage

**End users**

1. Sign in with Google (or try the **Demo**).
2. Open **Strategy Lab**: pick symbol, expiration, add legs. Chain and fundamentals load automatically.
3. Click **Deep Research** (or equivalent “one-click report”). Wait for the pipeline (agents + Deep Research).
4. Read the report, check payoff charts and Greeks. Export or revisit via task history. **We never execute** — you trade (or not) in your broker.

**Developers (local)**

- **Prerequisites**: Docker & Docker Compose (or local Python 3.11+, Node 18+, PostgreSQL, Redis).
- Copy `.env.example` to `.env` and set at least: `DB_PASSWORD`, `GOOGLE_CLIENT_ID`, `VITE_GOOGLE_CLIENT_ID`, backend AI keys (e.g. Gemini/ZenMux), optional Tiger/FMP/Lemon Squeezy.
- **Run stack**: `docker-compose up -d` (db, redis, backend, frontend, nginx). Backend: `http://localhost:5300`, Frontend: `http://localhost:3000` (or via nginx on 80/443).
- **Backend only**: `cd backend && pip install -r requirements.txt` (or poetry), set `DATABASE_URL` and `REDIS_URL`, then `uvicorn app.main:app --reload`.
- **Frontend only**: `cd frontend && npm install && npm run dev`.

**Quota (daily, UTC reset)**

- **Free**: 5 units/day (1 Deep Research run; 1 run = 5 units).
- **Pro Monthly**: 40 units/day (8 runs).
- **Pro Yearly**: 100 units/day (20 runs). See in-app **Pricing** for details and to upgrade.

---

## Project Structure (Monorepo)

```
ThetaMind/
├── backend/          # FastAPI app (Python)
│   ├── app/
│   │   ├── api/      # Routes, deps, schemas
│   │   ├── core/     # Config, security
│   │   ├── db/       # SQLAlchemy, session
│   │   ├── services/ # Agents, AI, market, payment, storage, etc.
│   │   └── main.py
│   ├── alembic/      # Migrations
│   └── Dockerfile
├── frontend/         # React app (Vite + TypeScript)
│   ├── src/
│   │   ├── components/
│   │   ├── features/ # Auth, etc.
│   │   ├── pages/    # Dashboard, Strategy Lab, Pricing, etc.
│   │   └── services/
│   └── Dockerfile
├── nginx/            # Gateway config
├── docker-compose.yml
├── spec/             # PRD, tech spec, design docs
└── README.md         # This file
```

---

## Security & Compliance

- **No execution** — ThetaMind does not execute trades, place orders, or hold customer funds.
- **Secrets** — API keys and PII are not logged; webhook signatures (e.g. Lemon Squeezy) are verified.
- **Data** — Backend stores and processes times in UTC; frontend displays in US/Eastern.

---

## License & Disclaimer

ThetaMind is for **analysis and educational use only**. It is **not** a trading platform or investment advisor. Options involve substantial risk; past results do not guarantee future outcomes. Always do your own due diligence and consult a qualified financial advisor before any investment decision.

---

**ThetaMind** — *Option analysis that thinks like a research desk.*
