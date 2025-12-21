import { StrategyLeg } from "@/services/api/strategy"

export interface StrategyTemplate {
  id: string
  name: string
  description: string
  category: "directional" | "neutral" | "spread" | "complex"
  applyTemplate: (spotPrice: number, expirationDate: string) => StrategyLeg[]
}

/**
 * Apply a strategy template to generate legs based on current spot price.
 * 
 * Templates are designed to be beginner-friendly and automatically
 * calculate strikes relative to the current stock price.
 */

export const strategyTemplates: StrategyTemplate[] = [
  {
    id: "long_call",
    name: "Long Call",
    description: "Buy a call option. Bullish strategy with unlimited upside, limited risk.",
    category: "directional",
    applyTemplate: (spotPrice: number, expirationDate: string): StrategyLeg[] => {
      // Buy 1 Call at ATM + 1 strike (slightly OTM for better entry)
      const strike = Math.round(spotPrice * 1.02) // ~2% OTM
      return [
        {
          type: "call",
          action: "buy",
          strike,
          quantity: 1,
          expiry: expirationDate,
        },
      ]
    },
  },
  {
    id: "covered_call",
    name: "Covered Call",
    description: "Sell a call option against stock you own. Generate income, limit upside.",
    category: "neutral",
    applyTemplate: (spotPrice: number, expirationDate: string): StrategyLeg[] => {
      // Sell 1 Call at OTM (assumes stock is held)
      const strike = Math.round(spotPrice * 1.05) // ~5% OTM
      return [
        {
          type: "call",
          action: "sell",
          strike,
          quantity: 1,
          expiry: expirationDate,
        },
      ]
    },
  },
  {
    id: "bull_put_spread",
    name: "Bull Put Spread",
    description: "Sell a put at higher strike, buy a put at lower strike. Bullish, income strategy.",
    category: "spread",
    applyTemplate: (spotPrice: number, expirationDate: string): StrategyLeg[] => {
      // Sell Put at ~5% OTM, Buy Put at ~10% OTM
      const sellStrike = Math.round(spotPrice * 0.95) // 5% below spot
      const buyStrike = Math.round(spotPrice * 0.90) // 10% below spot
      return [
        {
          type: "put",
          action: "sell",
          strike: sellStrike,
          quantity: 1,
          expiry: expirationDate,
        },
        {
          type: "put",
          action: "buy",
          strike: buyStrike,
          quantity: 1,
          expiry: expirationDate,
        },
      ]
    },
  },
  {
    id: "iron_condor",
    name: "Iron Condor",
    description: "4-leg neutral strategy. Sell OTM call spread + sell OTM put spread. Max profit in range.",
    category: "complex",
    applyTemplate: (spotPrice: number, expirationDate: string): StrategyLeg[] => {
      // Iron Condor: Sell Call Spread (OTM) + Sell Put Spread (OTM)
      // Structure: Sell Call at +5%, Buy Call at +10%, Sell Put at -5%, Buy Put at -10%
      const callSellStrike = Math.round(spotPrice * 1.05) // 5% above spot
      const callBuyStrike = Math.round(spotPrice * 1.10) // 10% above spot
      const putSellStrike = Math.round(spotPrice * 0.95) // 5% below spot
      const putBuyStrike = Math.round(spotPrice * 0.90) // 10% below spot

      return [
        {
          type: "call",
          action: "sell",
          strike: callSellStrike,
          quantity: 1,
          expiry: expirationDate,
        },
        {
          type: "call",
          action: "buy",
          strike: callBuyStrike,
          quantity: 1,
          expiry: expirationDate,
        },
        {
          type: "put",
          action: "sell",
          strike: putSellStrike,
          quantity: 1,
          expiry: expirationDate,
        },
        {
          type: "put",
          action: "buy",
          strike: putBuyStrike,
          quantity: 1,
          expiry: expirationDate,
        },
      ]
    },
  },
  {
    id: "long_put",
    name: "Long Put",
    description: "Buy a put option. Bearish strategy with limited risk, high profit potential if stock falls.",
    category: "directional",
    applyTemplate: (spotPrice: number, expirationDate: string): StrategyLeg[] => {
      // Buy 1 Put at ATM - 1 strike (slightly OTM for better entry)
      const strike = Math.round(spotPrice * 0.98) // ~2% OTM
      return [
        {
          type: "put",
          action: "buy",
          strike,
          quantity: 1,
          expiry: expirationDate,
        },
      ]
    },
  },
  {
    id: "protective_put",
    name: "Protective Put",
    description: "Buy a put to protect stock position. Insurance against downside risk.",
    category: "directional",
    applyTemplate: (spotPrice: number, expirationDate: string): StrategyLeg[] => {
      // Buy 1 Put at ~5% OTM (insurance)
      const strike = Math.round(spotPrice * 0.95) // 5% below spot
      return [
        {
          type: "put",
          action: "buy",
          strike,
          quantity: 1,
          expiry: expirationDate,
        },
      ]
    },
  },
  {
    id: "bull_call_spread",
    name: "Bull Call Spread",
    description: "Buy call at lower strike, sell call at higher strike. Bullish with limited risk/reward.",
    category: "spread",
    applyTemplate: (spotPrice: number, expirationDate: string): StrategyLeg[] => {
      // Buy Call at ATM, Sell Call at ~5% OTM
      const buyStrike = Math.round(spotPrice * 1.00) // ATM
      const sellStrike = Math.round(spotPrice * 1.05) // 5% above
      return [
        {
          type: "call",
          action: "buy",
          strike: buyStrike,
          quantity: 1,
          expiry: expirationDate,
        },
        {
          type: "call",
          action: "sell",
          strike: sellStrike,
          quantity: 1,
          expiry: expirationDate,
        },
      ]
    },
  },
]

/**
 * Get template by ID
 */
export function getTemplateById(id: string): StrategyTemplate | undefined {
  return strategyTemplates.find((t) => t.id === id)
}

/**
 * Get templates by category
 */
export function getTemplatesByCategory(
  category: StrategyTemplate["category"]
): StrategyTemplate[] {
  return strategyTemplates.filter((t) => t.category === category)
}

