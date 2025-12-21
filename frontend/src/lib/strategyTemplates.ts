/**
 * Option Strategy Templates
 * Pre-defined professional option strategies
 */

export interface StrategyTemplate {
  id: string
  name: string
  description: string
  category: "bullish" | "bearish" | "neutral" | "volatile"
  apply: (spotPrice: number, expirationDate: string) => Array<{
    type: "call" | "put"
    action: "buy" | "sell"
    strike: number
    quantity: number
    expiry: string
  }>
}

export const strategyTemplates: StrategyTemplate[] = [
  {
    id: "bull-call-spread",
    name: "Bull Call Spread",
    description: "Buy lower strike call, sell higher strike call. Limited profit, limited risk.",
    category: "bullish",
    apply: (spotPrice, expirationDate) => {
      const lowerStrike = Math.round(spotPrice * 0.95 / 5) * 5
      const upperStrike = Math.round(spotPrice * 1.10 / 5) * 5
      return [
        { type: "call", action: "buy", strike: lowerStrike, quantity: 1, expiry: expirationDate },
        { type: "call", action: "sell", strike: upperStrike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "bear-put-spread",
    name: "Bear Put Spread",
    description: "Buy higher strike put, sell lower strike put. Profits when stock falls.",
    category: "bearish",
    apply: (spotPrice, expirationDate) => {
      const upperStrike = Math.round(spotPrice * 1.05 / 5) * 5
      const lowerStrike = Math.round(spotPrice * 0.90 / 5) * 5
      return [
        { type: "put", action: "buy", strike: upperStrike, quantity: 1, expiry: expirationDate },
        { type: "put", action: "sell", strike: lowerStrike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "iron-condor",
    name: "Iron Condor",
    description: "Sell OTM call spread + sell OTM put spread. Profits in range-bound market.",
    category: "neutral",
    apply: (spotPrice, expirationDate) => {
      const callSellStrike = Math.round(spotPrice * 1.05 / 5) * 5
      const callBuyStrike = Math.round(spotPrice * 1.15 / 5) * 5
      const putSellStrike = Math.round(spotPrice * 0.95 / 5) * 5
      const putBuyStrike = Math.round(spotPrice * 0.85 / 5) * 5
      return [
        { type: "call", action: "sell", strike: callSellStrike, quantity: 1, expiry: expirationDate },
        { type: "call", action: "buy", strike: callBuyStrike, quantity: 1, expiry: expirationDate },
        { type: "put", action: "sell", strike: putSellStrike, quantity: 1, expiry: expirationDate },
        { type: "put", action: "buy", strike: putBuyStrike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "long-straddle",
    name: "Long Straddle",
    description: "Buy ATM call + buy ATM put. Profits from large price moves in either direction.",
    category: "volatile",
    apply: (spotPrice, expirationDate) => {
      const strike = Math.round(spotPrice / 5) * 5
      return [
        { type: "call", action: "buy", strike, quantity: 1, expiry: expirationDate },
        { type: "put", action: "buy", strike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "long-strangle",
    name: "Long Strangle",
    description: "Buy OTM call + buy OTM put. Lower cost than straddle, needs bigger move.",
    category: "volatile",
    apply: (spotPrice, expirationDate) => {
      const callStrike = Math.round(spotPrice * 1.05 / 5) * 5
      const putStrike = Math.round(spotPrice * 0.95 / 5) * 5
      return [
        { type: "call", action: "buy", strike: callStrike, quantity: 1, expiry: expirationDate },
        { type: "put", action: "buy", strike: putStrike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "protective-collar",
    name: "Protective Collar",
    description: "Own stock + buy OTM put + sell OTM call. Limits downside, caps upside.",
    category: "neutral",
    apply: (spotPrice, expirationDate) => {
      const putStrike = Math.round(spotPrice * 0.95 / 5) * 5
      const callStrike = Math.round(spotPrice * 1.05 / 5) * 5
      return [
        { type: "put", action: "buy", strike: putStrike, quantity: 1, expiry: expirationDate },
        { type: "call", action: "sell", strike: callStrike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "butterfly-spread",
    name: "Butterfly Spread (Call)",
    description: "Buy lower, sell 2 middle, buy higher. Maximum profit at middle strike.",
    category: "neutral",
    apply: (spotPrice, expirationDate) => {
      const lowerStrike = Math.round(spotPrice * 0.90 / 5) * 5
      const middleStrike = Math.round(spotPrice / 5) * 5
      const upperStrike = Math.round(spotPrice * 1.10 / 5) * 5
      return [
        { type: "call", action: "buy", strike: lowerStrike, quantity: 1, expiry: expirationDate },
        { type: "call", action: "sell", strike: middleStrike, quantity: 2, expiry: expirationDate },
        { type: "call", action: "buy", strike: upperStrike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "covered-call",
    name: "Covered Call",
    description: "Own stock + sell OTM call. Generates income, limits upside.",
    category: "bullish",
    apply: (spotPrice, expirationDate) => {
      const strike = Math.round(spotPrice * 1.05 / 5) * 5
      return [
        { type: "call", action: "sell", strike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "short-straddle",
    name: "Short Straddle",
    description: "Sell ATM call + sell ATM put. Profits from low volatility, range-bound price.",
    category: "neutral",
    apply: (spotPrice, expirationDate) => {
      const strike = Math.round(spotPrice / 5) * 5
      return [
        { type: "call", action: "sell", strike, quantity: 1, expiry: expirationDate },
        { type: "put", action: "sell", strike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "short-strangle",
    name: "Short Strangle",
    description: "Sell OTM call + sell OTM put. Lower risk than short straddle, needs range-bound market.",
    category: "neutral",
    apply: (spotPrice, expirationDate) => {
      const callStrike = Math.round(spotPrice * 1.05 / 5) * 5
      const putStrike = Math.round(spotPrice * 0.95 / 5) * 5
      return [
        { type: "call", action: "sell", strike: callStrike, quantity: 1, expiry: expirationDate },
        { type: "put", action: "sell", strike: putStrike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "butterfly-put",
    name: "Butterfly Spread (Put)",
    description: "Buy higher put, sell 2 middle puts, buy lower put. Maximum profit at middle strike.",
    category: "neutral",
    apply: (spotPrice, expirationDate) => {
      const upperStrike = Math.round(spotPrice * 1.10 / 5) * 5
      const middleStrike = Math.round(spotPrice / 5) * 5
      const lowerStrike = Math.round(spotPrice * 0.90 / 5) * 5
      return [
        { type: "put", action: "buy", strike: upperStrike, quantity: 1, expiry: expirationDate },
        { type: "put", action: "sell", strike: middleStrike, quantity: 2, expiry: expirationDate },
        { type: "put", action: "buy", strike: lowerStrike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "iron-butterfly",
    name: "Iron Butterfly",
    description: "Sell ATM call & put, buy OTM call & put. Maximum profit at ATM, limited risk.",
    category: "neutral",
    apply: (spotPrice, expirationDate) => {
      const atmStrike = Math.round(spotPrice / 5) * 5
      const callBuyStrike = Math.round(spotPrice * 1.10 / 5) * 5
      const putBuyStrike = Math.round(spotPrice * 0.90 / 5) * 5
      return [
        { type: "call", action: "sell", strike: atmStrike, quantity: 1, expiry: expirationDate },
        { type: "call", action: "buy", strike: callBuyStrike, quantity: 1, expiry: expirationDate },
        { type: "put", action: "sell", strike: atmStrike, quantity: 1, expiry: expirationDate },
        { type: "put", action: "buy", strike: putBuyStrike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "calendar-spread",
    name: "Calendar Spread (Call)",
    description: "Sell near-term call, buy longer-term call. Profits from time decay of short option.",
    category: "neutral",
    apply: (spotPrice, expirationDate) => {
      const strike = Math.round(spotPrice / 5) * 5
      return [
        { type: "call", action: "sell", strike, quantity: 1, expiry: expirationDate },
        { type: "call", action: "buy", strike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "protective-put",
    name: "Protective Put",
    description: "Own stock + buy OTM put. Limits downside risk while maintaining upside potential.",
    category: "bullish",
    apply: (spotPrice, expirationDate) => {
      const strike = Math.round(spotPrice * 0.95 / 5) * 5
      return [
        { type: "put", action: "buy", strike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "collar-spread",
    name: "Collar",
    description: "Own stock + buy OTM put + sell OTM call. Zero-cost protection with capped upside.",
    category: "neutral",
    apply: (spotPrice, expirationDate) => {
      const putStrike = Math.round(spotPrice * 0.95 / 5) * 5
      const callStrike = Math.round(spotPrice * 1.05 / 5) * 5
      return [
        { type: "put", action: "buy", strike: putStrike, quantity: 1, expiry: expirationDate },
        { type: "call", action: "sell", strike: callStrike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "ratio-spread-call",
    name: "Ratio Call Spread",
    description: "Buy 1 lower strike call, sell 2 higher strike calls. Profits from moderate rise.",
    category: "bullish",
    apply: (spotPrice, expirationDate) => {
      const lowerStrike = Math.round(spotPrice * 0.95 / 5) * 5
      const upperStrike = Math.round(spotPrice * 1.10 / 5) * 5
      return [
        { type: "call", action: "buy", strike: lowerStrike, quantity: 1, expiry: expirationDate },
        { type: "call", action: "sell", strike: upperStrike, quantity: 2, expiry: expirationDate },
      ]
    },
  },
  {
    id: "ratio-spread-put",
    name: "Ratio Put Spread",
    description: "Buy 1 higher strike put, sell 2 lower strike puts. Profits from moderate fall.",
    category: "bearish",
    apply: (spotPrice, expirationDate) => {
      const upperStrike = Math.round(spotPrice * 1.05 / 5) * 5
      const lowerStrike = Math.round(spotPrice * 0.90 / 5) * 5
      return [
        { type: "put", action: "buy", strike: upperStrike, quantity: 1, expiry: expirationDate },
        { type: "put", action: "sell", strike: lowerStrike, quantity: 2, expiry: expirationDate },
      ]
    },
  },
  {
    id: "long-call",
    name: "Long Call",
    description: "Buy call option. Unlimited profit potential, limited risk. Bullish strategy.",
    category: "bullish",
    apply: (spotPrice, expirationDate) => {
      const strike = Math.round(spotPrice * 1.05 / 5) * 5
      return [
        { type: "call", action: "buy", strike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "long-put",
    name: "Long Put",
    description: "Buy put option. Profits from stock decline. Limited risk, high profit potential.",
    category: "bearish",
    apply: (spotPrice, expirationDate) => {
      const strike = Math.round(spotPrice * 0.95 / 5) * 5
      return [
        { type: "put", action: "buy", strike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "naked-call",
    name: "Naked Call (Short Call)",
    description: "Sell call option. Profits from stock staying below strike. High risk, limited profit.",
    category: "bearish",
    apply: (spotPrice, expirationDate) => {
      const strike = Math.round(spotPrice * 1.05 / 5) * 5
      return [
        { type: "call", action: "sell", strike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "naked-put",
    name: "Naked Put (Short Put)",
    description: "Sell put option. Profits from stock staying above strike. Bullish, limited profit.",
    category: "bullish",
    apply: (spotPrice, expirationDate) => {
      const strike = Math.round(spotPrice * 0.95 / 5) * 5
      return [
        { type: "put", action: "sell", strike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "diagonal-spread",
    name: "Diagonal Spread",
    description: "Sell near-term OTM call, buy longer-term ITM call. Combines time decay and direction.",
    category: "bullish",
    apply: (spotPrice, expirationDate) => {
      const shortStrike = Math.round(spotPrice * 1.05 / 5) * 5
      const longStrike = Math.round(spotPrice * 0.95 / 5) * 5
      return [
        { type: "call", action: "sell", strike: shortStrike, quantity: 1, expiry: expirationDate },
        { type: "call", action: "buy", strike: longStrike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "box-spread",
    name: "Box Spread",
    description: "Bull call spread + bear put spread. Risk-free arbitrage if priced correctly.",
    category: "neutral",
    apply: (spotPrice, expirationDate) => {
      const lowerStrike = Math.round(spotPrice * 0.95 / 5) * 5
      const upperStrike = Math.round(spotPrice * 1.05 / 5) * 5
      return [
        { type: "call", action: "buy", strike: lowerStrike, quantity: 1, expiry: expirationDate },
        { type: "call", action: "sell", strike: upperStrike, quantity: 1, expiry: expirationDate },
        { type: "put", action: "buy", strike: upperStrike, quantity: 1, expiry: expirationDate },
        { type: "put", action: "sell", strike: lowerStrike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "jade-lizard",
    name: "Jade Lizard",
    description: "Sell OTM call spread + sell OTM put. Profits from range-bound or upward movement.",
    category: "neutral",
    apply: (spotPrice, expirationDate) => {
      const callSellStrike = Math.round(spotPrice * 1.05 / 5) * 5
      const callBuyStrike = Math.round(spotPrice * 1.15 / 5) * 5
      const putStrike = Math.round(spotPrice * 0.95 / 5) * 5
      return [
        { type: "call", action: "sell", strike: callSellStrike, quantity: 1, expiry: expirationDate },
        { type: "call", action: "buy", strike: callBuyStrike, quantity: 1, expiry: expirationDate },
        { type: "put", action: "sell", strike: putStrike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "collar-with-stock",
    name: "Zero-Cost Collar",
    description: "Own stock + buy put + sell call. Premiums offset for zero-cost downside protection.",
    category: "neutral",
    apply: (spotPrice, expirationDate) => {
      const putStrike = Math.round(spotPrice * 0.95 / 5) * 5
      const callStrike = Math.round(spotPrice * 1.05 / 5) * 5
      return [
        { type: "put", action: "buy", strike: putStrike, quantity: 1, expiry: expirationDate },
        { type: "call", action: "sell", strike: callStrike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
  {
    id: "reverse-iron-condor",
    name: "Reverse Iron Condor",
    description: "Buy OTM call spread + buy OTM put spread. Profits from large price moves either way.",
    category: "volatile",
    apply: (spotPrice, expirationDate) => {
      const callBuyStrike = Math.round(spotPrice * 1.05 / 5) * 5
      const callSellStrike = Math.round(spotPrice * 1.15 / 5) * 5
      const putBuyStrike = Math.round(spotPrice * 0.95 / 5) * 5
      const putSellStrike = Math.round(spotPrice * 0.85 / 5) * 5
      return [
        { type: "call", action: "buy", strike: callBuyStrike, quantity: 1, expiry: expirationDate },
        { type: "call", action: "sell", strike: callSellStrike, quantity: 1, expiry: expirationDate },
        { type: "put", action: "buy", strike: putBuyStrike, quantity: 1, expiry: expirationDate },
        { type: "put", action: "sell", strike: putSellStrike, quantity: 1, expiry: expirationDate },
      ]
    },
  },
]

export const getTemplateById = (id: string): StrategyTemplate | undefined => {
  return strategyTemplates.find((t) => t.id === id)
}

export const getTemplatesByCategory = (category: string): StrategyTemplate[] => {
  return strategyTemplates.filter((t) => t.category === category)
}

