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
  const getGreekFromChain = (
    strike: number,
    type: "call" | "put",
    greekName: string
  ): number | undefined => {
    if (!optionChain) return undefined

    const options = type === "call" ? optionChain.calls : optionChain.puts
    const option = options.find((o) => Math.abs(o.strike - strike) < 0.01)

    if (!option) return undefined

    // Try direct field
    if (option[greekName] !== undefined) return option[greekName] as number
    // Try nested greeks
    if (option.greeks) {
      const greeks = option.greeks as Record<string, number | undefined>
      return greeks[greekName]
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
      <CardHeader>
        <CardTitle>Portfolio Greeks</CardTitle>
        <CardDescription>Combined Greeks for the entire strategy</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-5 gap-4">
          <div className="text-center">
            <div className="text-xs text-muted-foreground mb-1">Delta (Δ)</div>
            <div className={`text-lg font-bold ${getDeltaColor(portfolioGreeks.delta)}`}>
              {formatGreek(portfolioGreeks.delta)}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Price sensitivity
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-muted-foreground mb-1">Gamma (Γ)</div>
            <div className="text-lg font-bold">
              {formatGreek(portfolioGreeks.gamma)}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Delta sensitivity
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-muted-foreground mb-1">Theta (Θ)</div>
            <div className={`text-lg font-bold ${getThetaColor(portfolioGreeks.theta)}`}>
              {formatGreek(portfolioGreeks.theta)}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Time decay /day
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-muted-foreground mb-1">Vega (ν)</div>
            <div className="text-lg font-bold">
              {formatGreek(portfolioGreeks.vega)}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Volatility sensitivity
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-muted-foreground mb-1">Rho (ρ)</div>
            <div className="text-lg font-bold">
              {formatGreek(portfolioGreeks.rho)}
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Interest rate sensitivity
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

