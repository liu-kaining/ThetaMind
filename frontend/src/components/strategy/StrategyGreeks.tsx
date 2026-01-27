import * as React from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

interface StrategyGreeksProps {
  legs: Array<{
    type: "call" | "put"
    action: "buy" | "sell"
    strike: number
    quantity: number
    premium?: number
    delta?: number
    gamma?: number
    theta?: number
    vega?: number
    rho?: number
  }>
  optionChain?: {
    calls: Array<{
      strike: number
      delta?: number
      gamma?: number
      theta?: number
      vega?: number
      rho?: number
      greeks?: {
        delta?: number
        gamma?: number
        theta?: number
        vega?: number
        rho?: number
      }
      [key: string]: any
    }>
    puts: Array<{
      strike: number
      delta?: number
      gamma?: number
      theta?: number
      vega?: number
      rho?: number
      greeks?: {
        delta?: number
        gamma?: number
        theta?: number
        vega?: number
        rho?: number
      }
      [key: string]: any
    }>
  }
}

export const StrategyGreeks: React.FC<StrategyGreeksProps> = ({ legs, optionChain }) => {
  // Get Greek from option chain
  // Supports multiple field name formats for compatibility
  const getGreekFromChain = (
    strike: number,
    type: "call" | "put",
    greekName: string
  ): number | undefined => {
    if (!optionChain) return undefined

    const options = type === "call" ? optionChain.calls : optionChain.puts
    const option = options.find((o) => {
      if (!o) return false
      const optionStrike = o.strike ?? (o as any).strike_price
      return optionStrike !== undefined && Math.abs(optionStrike - strike) < 0.01
    })

    if (!option) return undefined

    // Try direct field first
    if (option[greekName] !== undefined && option[greekName] !== null) {
      const value = Number(option[greekName])
      if (!isNaN(value) && isFinite(value)) return value
    }
    
    // Try nested greeks object
    if (option.greeks && typeof option.greeks === 'object') {
      const greeks = option.greeks as Record<string, number | undefined>
      if (greeks[greekName] !== undefined && greeks[greekName] !== null) {
        const value = Number(greeks[greekName])
        if (!isNaN(value) && isFinite(value)) return value
      }
    }
    
    return undefined
  }

  // Calculate portfolio Greeks
  const portfolioGreeks = React.useMemo(() => {
    let totalDelta = 0
    let totalGamma = 0
    let totalTheta = 0
    let totalVega = 0
    let totalRho = 0

    legs.forEach((leg) => {
      const delta = leg.delta ?? getGreekFromChain(leg.strike, leg.type, "delta")
      const gamma = leg.gamma ?? getGreekFromChain(leg.strike, leg.type, "gamma")
      const theta = leg.theta ?? getGreekFromChain(leg.strike, leg.type, "theta")
      const vega = leg.vega ?? getGreekFromChain(leg.strike, leg.type, "vega")
      const rho = leg.rho ?? getGreekFromChain(leg.strike, leg.type, "rho")

      // For puts, delta is negative
      const sign = leg.action === "buy" ? 1 : -1
      const multiplier = leg.type === "put" ? -1 : 1

      if (delta !== undefined) {
        totalDelta += delta * sign * multiplier * leg.quantity
      }
      if (gamma !== undefined) {
        totalGamma += gamma * sign * leg.quantity
      }
      if (theta !== undefined) {
        totalTheta += theta * sign * leg.quantity
      }
      if (vega !== undefined) {
        totalVega += vega * sign * leg.quantity
      }
      if (rho !== undefined) {
        totalRho += rho * sign * multiplier * leg.quantity
      }
    })

    return {
      delta: totalDelta,
      gamma: totalGamma,
      theta: totalTheta,
      vega: totalVega,
      rho: totalRho,
    }
  }, [legs, optionChain])

  if (legs.length === 0) {
    return null
  }

  const formatGreek = (value: number | undefined): string => {
    if (value === undefined || value === null || isNaN(value)) return "-"
    return value.toFixed(4)
  }

  const getDeltaColor = (delta: number): string => {
    if (Math.abs(delta) < 0.1) return "text-muted-foreground"
    return delta > 0 ? "text-green-600" : "text-red-600"
  }

  const getThetaColor = (theta: number): string => {
    return theta < 0 ? "text-red-600" : "text-green-600"
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Portfolio Greeks</CardTitle>
        <CardDescription className="text-xs">Combined Greeks for the entire strategy</CardDescription>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="grid grid-cols-5 gap-1.5">
          <div className="text-center">
            <div className="text-xs text-muted-foreground mb-0.5">Delta (Δ)</div>
            <div className={`text-sm font-bold leading-tight ${getDeltaColor(portfolioGreeks.delta)}`}>
              {formatGreek(portfolioGreeks.delta)}
            </div>
            <div className="text-[10px] text-muted-foreground mt-0.5 leading-tight">
              Price sensitivity
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-muted-foreground mb-0.5">Gamma (Γ)</div>
            <div className="text-sm font-bold leading-tight">
              {formatGreek(portfolioGreeks.gamma)}
            </div>
            <div className="text-[10px] text-muted-foreground mt-0.5 leading-tight">
              Delta sensitivity
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-muted-foreground mb-0.5">Theta (Θ)</div>
            <div className={`text-sm font-bold leading-tight ${getThetaColor(portfolioGreeks.theta)}`}>
              {formatGreek(portfolioGreeks.theta)}
            </div>
            <div className="text-[10px] text-muted-foreground mt-0.5 leading-tight">
              Time decay /day
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-muted-foreground mb-0.5">Vega (ν)</div>
            <div className="text-sm font-bold leading-tight">
              {formatGreek(portfolioGreeks.vega)}
            </div>
            <div className="text-[10px] text-muted-foreground mt-0.5 leading-tight">
              Volatility sensitivity
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-muted-foreground mb-0.5">Rho (ρ)</div>
            <div className="text-sm font-bold leading-tight">
              {formatGreek(portfolioGreeks.rho)}
            </div>
            <div className="text-[10px] text-muted-foreground mt-0.5 leading-tight">
              Interest rate sensitivity
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

