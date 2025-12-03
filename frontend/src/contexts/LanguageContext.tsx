import * as React from "react"
import { createContext, useContext, useState, useEffect } from "react"

type Language = "en" | "zh"

interface LanguageContextType {
  language: Language
  setLanguage: (lang: Language) => void
  t: (key: string) => string
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined)

// Translations
const translations: Record<Language, Record<string, string>> = {
  en: {
    // Navigation
    "nav.signIn": "Sign In",
    "nav.getStarted": "Get Started",
    
    // Hero
    "hero.badge": "AI-Powered Options Strategy Analysis",
    "hero.title.part1": "Analyze Options Strategies",
    "hero.title.part2": "with AI Intelligence",
    "hero.subtitle": "Professional-grade option strategy analysis powered by advanced AI. Understand risk, calculate payoffs, and make informed decisions.",
    "hero.cta.primary": "Start Analyzing",
    "hero.cta.secondary": "View Demo",
    
    // Disclaimer
    "disclaimer.title": "Analysis Tool Only",
    "disclaimer.text": "ThetaMind is an **analysis and educational tool** for understanding option strategies. It does not provide investment advice, recommendations, or solicitations to buy or sell securities. All analysis is for informational purposes only. Always consult with a qualified financial advisor before making investment decisions.",
    
    // Features
    "features.title": "Powerful Features",
    "features.subtitle": "Everything you need for professional option strategy analysis",
    "features.ai.title": "AI-Powered Analysis",
    "features.ai.desc": "Get comprehensive strategy analysis powered by advanced AI models. Understand risk, reward, and market sentiment.",
    "features.charts.title": "Interactive Charts",
    "features.charts.desc": "Visualize option payoffs with interactive charts. See profit/loss scenarios across different stock prices.",
    "features.data.title": "Real-Time Market Data",
    "features.data.desc": "Access real-time option chain data for US stocks. Pro users get 5-second updates, free users get 15-minute delayed data.",
    "features.builder.title": "Strategy Builder",
    "features.builder.desc": "Build complex multi-leg option strategies with our intuitive builder. Add calls, puts, and customize strikes and expirations.",
    "features.picks.title": "Daily AI Picks",
    "features.picks.desc": "Discover AI-generated strategy recommendations daily. Learn from market analysis and strategy insights.",
    "features.risk.title": "Risk Analysis",
    "features.risk.desc": "Understand maximum loss, break-even points, and Greeks. Make informed decisions with comprehensive risk metrics.",
    
    // How It Works
    "how.title": "How It Works",
    "how.subtitle": "Simple, powerful, and designed for professionals",
    "how.step1.title": "Build Your Strategy",
    "how.step1.desc": "Use our Strategy Lab to construct multi-leg option strategies. Add calls and puts with custom strikes and expiration dates.",
    "how.step2.title": "Analyze with AI",
    "how.step2.desc": "Get comprehensive AI-powered analysis including risk assessment, break-even calculations, and market sentiment insights.",
    "how.step3.title": "Visualize & Learn",
    "how.step3.desc": "View interactive payoff charts and understand how your strategy performs across different market scenarios.",
    
    // CTA
    "cta.title": "Ready to Analyze Options Strategies?",
    "cta.subtitle": "Join professionals using AI to understand option strategies better.",
    "cta.button": "Get Started Free",
    "cta.free": "Free tier available",
    "cta.noCard": "No credit card required",
    "cta.toolOnly": "Analysis tool only",
    
    // Footer
    "footer.copyright": "© 2025 ThetaMind. Analysis tool for educational purposes only. Not investment advice.",
  },
  zh: {
    // Navigation
    "nav.signIn": "登录",
    "nav.getStarted": "开始使用",
    
    // Hero
    "hero.badge": "AI 驱动的期权策略分析",
    "hero.title.part1": "用 AI 智能",
    "hero.title.part2": "分析期权策略",
    "hero.subtitle": "专业级期权策略分析，由先进 AI 驱动。了解风险，计算盈亏，做出明智决策。",
    "hero.cta.primary": "开始分析",
    "hero.cta.secondary": "查看演示",
    
    // Disclaimer
    "disclaimer.title": "仅限分析工具",
    "disclaimer.text": "ThetaMind 是一个用于理解期权策略的**分析和教育工具**。它不提供投资建议、推荐或买卖证券的招揽。所有分析仅供信息参考。在做出投资决策前，请务必咨询合格的财务顾问。",
    
    // Features
    "features.title": "强大功能",
    "features.subtitle": "专业期权策略分析所需的一切",
    "features.ai.title": "AI 驱动分析",
    "features.ai.desc": "通过先进的 AI 模型获得全面的策略分析。了解风险、收益和市场情绪。",
    "features.charts.title": "交互式图表",
    "features.charts.desc": "通过交互式图表可视化期权盈亏。查看不同股价下的盈亏情况。",
    "features.data.title": "实时市场数据",
    "features.data.desc": "访问美股实时期权链数据。Pro 用户每 5 秒更新，免费用户延迟 15 分钟。",
    "features.builder.title": "策略构建器",
    "features.builder.desc": "使用直观的构建器构建复杂的多腿期权策略。添加看涨/看跌期权，自定义行权价和到期日。",
    "features.picks.title": "每日 AI 推荐",
    "features.picks.desc": "每日发现 AI 生成的策略推荐。从市场分析和策略洞察中学习。",
    "features.risk.title": "风险分析",
    "features.risk.desc": "了解最大亏损、盈亏平衡点和希腊字母。通过全面的风险指标做出明智决策。",
    
    // How It Works
    "how.title": "使用流程",
    "how.subtitle": "简单、强大，专为专业人士设计",
    "how.step1.title": "构建策略",
    "how.step1.desc": "使用策略实验室构建多腿期权策略。添加看涨和看跌期权，自定义行权价和到期日。",
    "how.step2.title": "AI 分析",
    "how.step2.desc": "获得全面的 AI 驱动分析，包括风险评估、盈亏平衡计算和市场情绪洞察。",
    "how.step3.title": "可视化学习",
    "how.step3.desc": "查看交互式盈亏图表，了解策略在不同市场情景下的表现。",
    
    // CTA
    "cta.title": "准备分析期权策略？",
    "cta.subtitle": "加入使用 AI 更好地理解期权策略的专业人士行列。",
    "cta.button": "免费开始",
    "cta.free": "提供免费版本",
    "cta.noCard": "无需信用卡",
    "cta.toolOnly": "仅限分析工具",
    
    // Footer
    "footer.copyright": "© 2025 ThetaMind。仅用于教育目的的分析工具。非投资建议。",
  },
}

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>(() => {
    // Get from localStorage or default to browser language
    const saved = localStorage.getItem("language") as Language
    if (saved && (saved === "en" || saved === "zh")) {
      return saved
    }
    // Detect browser language
    const browserLang = navigator.language.toLowerCase()
    return browserLang.startsWith("zh") ? "zh" : "en"
  })

  useEffect(() => {
    localStorage.setItem("language", language)
  }, [language])

  const setLanguage = (lang: Language) => {
    setLanguageState(lang)
  }

  const t = (key: string): string => {
    return translations[language][key] || key
  }

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
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

