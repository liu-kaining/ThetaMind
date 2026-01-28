import * as React from "react"
import { OptionChainTable } from "./OptionChainTable"

interface Option {
  strike: number
  bid: number
  ask: number
  volume: number
  open_interest: number
  delta?: number
  gamma?: number
  theta?: number
  vega?: number
  rho?: number
  implied_volatility?: number
  implied_vol?: number
  greeks?: {
    delta?: number
    gamma?: number
    theta?: number
    vega?: number
    rho?: number
  }
  [key: string]: any
}

interface OptionChainVisualizationProps {
  calls: Option[]
  puts: Option[]
  spotPrice: number
  // New props for one-click actions
  onAddLeg?: (leg: Omit<import("@/services/api/strategy").StrategyLeg, "expiry">) => void
  expirationDate?: string
  onRefresh?: () => void
  isRefreshing?: boolean
}

export const OptionChainVisualization: React.FC<OptionChainVisualizationProps> = ({
  calls,
  puts,
  spotPrice,
  onAddLeg,
  expirationDate,
  onRefresh,
  isRefreshing,
}) => {
  return (
    <div className="w-full h-full flex flex-col">
      {/* OptionChainTable has its own Card wrapper */}
      <OptionChainTable
        calls={calls}
        puts={puts}
        spotPrice={spotPrice}
        onAddLeg={onAddLeg}
        expirationDate={expirationDate}
        onRefresh={onRefresh}
        isRefreshing={isRefreshing}
      />
    </div>
  )
}

