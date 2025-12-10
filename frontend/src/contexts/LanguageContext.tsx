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

