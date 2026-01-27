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
  onSelectOption?: (option: Option, type: "call" | "put") => void
  // New props for one-click actions
  onAddLeg?: (leg: Omit<import("@/services/api/strategy").StrategyLeg, "expiry">) => void
  expirationDate?: string
}

export const OptionChainVisualization: React.FC<OptionChainVisualizationProps> = ({
  calls,
  puts,
  spotPrice,
  onSelectOption,
  onAddLeg,
  expirationDate,
}) => {
  return (
    <div className="w-full h-full flex flex-col">
      {/* OptionChainTable has its own Card wrapper */}
      <OptionChainTable
        calls={calls}
        puts={puts}
        spotPrice={spotPrice}
        onSelectOption={onSelectOption}
        onAddLeg={onAddLeg}
        expirationDate={expirationDate}
      />
    </div>
  )
}

