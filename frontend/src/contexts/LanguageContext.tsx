import * as React from "react"
import { createContext, useContext } from "react"

interface LanguageContextType {
  t: (key: string) => string
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined)

// English translations only
const translations: Record<string, string> = {
  // Navigation
  "nav.signIn": "Sign In",
  "nav.getStarted": "Get Started",
  
  // Hero (first screen — value-first)
  "hero.badge": "Analysis & research only · Not for trading",
  "hero.title.part1": "Option Analysis",
  "hero.title.part2": "Five Specialists. Deep Research. One Report.",
  "hero.subline": "Build in Strategy Lab with real chains (Tiger) and fundamentals (FMP). One click runs five AI agents plus live-web research—you get one long-form memo and full audit. No black box.",
  "hero.bullet1": "5 specialist agents",
  "hero.bullet2": "Deep Research with live Google search",
  "hero.bullet3": "Real option chains & FMP fundamentals",
  "hero.bullet4": "One report, full task audit trail",
  "hero.cta.primary": "Start Analyzing",
  "hero.cta.secondary": "View Demo",
  "hero.pipeline.label": "One pipeline",
  "hero.pipeline.step1": "Strategy Lab",
  "hero.pipeline.step2": "5 Agents",
  "hero.pipeline.step3": "Deep Research",
  "hero.pipeline.step4": "Report",
  
  // Disclaimer
  "disclaimer.title": "Analysis & Research Tool Only — Not for Trading",
  "disclaimer.text": "ThetaMind is an **analysis and educational tool** for research and learning. It is **not a trading platform**: we do not execute trades, place orders, or provide buy/sell recommendations. All content is for **informational and educational purposes only**. Options involve substantial risk; past results do not guarantee future outcomes. **Always do your own due diligence and consult a qualified financial advisor** before any investment decision.",
  
  // Features (short for cards)
  "features.title": "Core Capabilities",
  "features.subtitle": "Each capability in detail—what it is and what you can do",
  "features.ai.title": "Multi-Agent + Deep Research",
  "features.ai.desc": "Five specialist agents plus Deep Research with live search. One report, full audit.",
  "features.charts.title": "Real-Time Charts",
  "features.charts.desc": "Candlesticks, payoff curves, scenario sims. P&L and Greeks at a glance.",
  "features.data.title": "FMP + Tiger Data",
  "features.data.desc": "Real option chains (Tiger) and fundamentals (FMP). No fake data.",
  "features.builder.title": "Strategy Lab",
  "features.builder.desc": "Build spreads with real chain and fundamentals. One click to AI report.",
  "features.reports.title": "Reports & Full Audit Trail",
  "features.reports.desc": "Every report stored with full task history. Revisit and export.",
  "features.risk.title": "Risk & Greeks",
  "features.risk.desc": "Max loss, break-evens, delta/theta/vega. AI explains the numbers.",
  "features.tasks.title": "Task System",
  "features.tasks.desc": "Pipeline from Strategy Lab to Report. Track every run, full traceability.",
  "features.nano.title": "Nano Banana",
  "features.nano.desc": "AI-generated option strategy images for your strategy or report.",
  "features.nano.full": "Nano Banana generates AI option images: given your strategy (or a report), it produces visual illustrations of the option structure—e.g. payoff-style diagrams, strategy layout, or explanatory figures—using AI so you can share or present the idea clearly. The images are generated on demand and tied to the same strategy data you build in Strategy Lab or see in the report, making it easy to explain complex option positions without drawing by hand.",

  // Features full (what each capability does — shown in expanded section)
  "features.ai.full": "Five specialist AI agents run in sequence, each writing a focused memo: Greeks (delta, gamma, theta, vega and what they mean for your strategy), IV (implied volatility context and term structure), Market (underlying trend and key levels), Risk (max loss, break-evens, tail risk), and Synthesis (tie-together and caveats). Then Deep Research runs: four questions are answered using live Google search, and the answers are synthesized into a long-form section. You get one coherent report—not a single generic summary—with clear reasoning and sources. Every agent output and the full prompt are stored for audit.",
  "features.charts.full": "Real-time candlestick charts for the underlying (TradingView-style), so you see price action and key levels before choosing strikes. Interactive payoff diagrams show P&L at expiration and at any date; you can drag price or time to run what-if scenarios. Greeks curves (delta, gamma, theta, vega vs. strike or time) help you see where risk is concentrated. All charts use the same strategy and data as the report—no re-entering. Pro plans get higher refresh; free tier uses delayed data.",
  "features.data.full": "Option chain data comes from Tiger Brokers: live or delayed by plan, with bids, asks, volume, open interest, and computed Greeks so your Strategy Lab and reports use the same numbers you’d see in a broker. Fundamentals and ratios (earnings, revenue, multiples, debt, profitability) come from FMP (Financial Modeling Prep), so the AI can reference real financials in the Fundamentals section. No placeholder or fake data—what you build and what the report analyzes are tied to real chains and real financials.",
  "features.builder.full": "Strategy Lab is where you design the trade: pick a symbol and expiration, and the app loads the option chain (Tiger) and fundamentals (FMP) automatically. Add legs (calls/puts, strikes, quantity) with a clear layout; the builder computes combined Greeks, implied volatility, max loss, max gain, and break-evens in real time. You can build iron condors, straddles, strangles, spreads, or custom combos. When you’re ready, one click sends the strategy to the multi-agent pipeline and you get a full report. No retyping—the report uses the exact structure and numbers from the lab.",
  "features.risk.full": "Risk is shown at every step: per-leg and portfolio max loss, max gain, and break-even prices (and dates for multi-period). Delta, gamma, theta, and vega are displayed for each leg and aggregated, so you see where direction and volatility risk sit. The Risk agent in the report explains what those numbers mean in plain language—e.g. high theta decay, sensitivity to a move before expiry—and the payoff chart lets you stress-test price and time. We never execute; you use this to understand risk before deciding in your own broker.",
  "features.tasks.full": "Every report run is a task: it has a clear pipeline (Strategy Lab input → Multi-Agent stages → Deep Research → final report) and you can open any past task to see status, stage-by-stage outputs, the exact prompt sent, and the final report. Tasks are listed in a central list with symbol, time, and status; from a task you can re-read each agent’s memo and the Deep Research synthesis. This gives full traceability and replay—no black box. You can use it to compare runs, debug reasoning, or export for your own records.",
  "features.reports.full": "Every generated report is saved and linked to its task. You get a report list (filterable by symbol, date) and a report detail view with the full memo: Fundamentals, Strategy Review, and synthesis. The prompt used and the task that produced the report are one click away, so you always have the full audit trail. Reports can be copied or exported for your own use. Analysis only—reports are for research and learning; we do not execute trades.",
  "stack.title": "Powered by",
  "stack.gemini": "Google Gemini",
  "stack.cloud": "Google Cloud",
  "stack.fmp": "FMP",
  "stack.tiger": "Tiger",
  "stack.realtimeCharts": "Real-time charts",
  "stack.nanoBanana": "Nano Banana",
  "stack.taskSystem": "Task system",
  
  // How It Works
  "how.title": "How It Works",
  "how.subtitle": "Build once, get a desk-style report in one click",
  "how.step1.title": "Build in Strategy Lab",
  "how.step1.desc": "Pick a symbol, expiration, and legs. Option chain and fundamentals load automatically. Build iron condors, straddles, or custom spreads.",
  "how.step2.title": "One-Click Multi-Agent Report",
  "how.step2.desc": "AI runs five specialists (Greeks, IV, Market, Risk, Synthesis), then Deep Research with 4 Google-backed questions. You get one long-form memo—Fundamentals, Strategy Review, and synthesis.",
  "how.step3.title": "Read, Visualize, Decide",
  "how.step3.desc": "Read the report, check payoff charts and Greeks. We never execute—you take the trade (or not) in your broker. Analysis only.",
  
  // CTA
  "cta.title": "Option Analysis That Thinks Like a Research Desk",
  "cta.subtitle": "Google Cloud + Gemini, FMP & Tiger data, real-time charts, task system. Analysis only—no execution.",
  "cta.button": "Get Started Free",
  "cta.free": "Free tier available",
  "cta.noCard": "No credit card required",
  "cta.toolOnly": "Analysis & research only — we do not execute trades",
  
  // Footer
  "footer.copyright": "© 2026 ThetaMind. Analysis and research tool for educational use only. Not a trading platform. Not investment advice.",

  // Technical Architecture
  "arch.title": "Technical Architecture",
  "arch.subtitle": "From strategy input to desk-style report—one pipeline, full traceability",
  "arch.step1": "Strategy Lab",
  "arch.step1.desc": "Symbol, expiration, legs. Option chain (Tiger) + fundamentals (FMP) load automatically.",
  "arch.step2": "Five Specialist Agents",
  "arch.step2.desc": "Greeks · IV · Market · Risk · Synthesis. Each writes a focused memo.",
  "arch.step3": "Deep Research",
  "arch.step3.desc": "4 questions, live Google search. Long-form synthesis into one report.",
  "arch.step4": "Report & Task History",
  "arch.step4.desc": "Stored with full prompt, stages, and audit trail. Replay any run.",

  // Tech highlights (short labels for list)
  "tech.cloud": "Google Cloud",
  "tech.cloud.desc": "Infrastructure & scale",
  "tech.gemini": "Google Gemini 3.0 Pro",
  "tech.gemini.desc": "Multi-agent + Deep Research",
  "tech.fmp": "FMP",
  "tech.fmp.desc": "Fundamentals & ratios",
  "tech.tiger": "Tiger",
  "tech.tiger.desc": "Real option chains",
  "tech.charts": "Real-time charts",
  "tech.charts.desc": "Candlestick, payoff, Greeks",
  "tech.nano": "Nano Banana",
  "tech.nano.desc": "AI-generated option strategy images",
  "tech.tasks": "Task system",
  "tech.tasks.desc": "Full pipeline audit",
  "techHighlights.title": "Tech Stack & Highlights",
  "techHighlights.subtitle": "Production-grade stack; every component chosen for reliability and clarity",
}

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const t = (key: string): string => {
    return translations[key] || key
  }

  return (
    <LanguageContext.Provider value={{ t }}>
      {children}
    </LanguageContext.Provider>
  )
}

export const useLanguage = () => {
  const context = useContext(LanguageContext)
  if (!context) {
    throw new Error("useLanguage must be used within LanguageProvider")
  }
  return context
}

