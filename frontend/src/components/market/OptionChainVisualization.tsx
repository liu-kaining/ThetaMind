import * as React from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { OptionChainTable } from "./OptionChainTable"
import { OptionChainPriceView } from "./OptionChainPriceView"

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
    <Card>
      <CardHeader>
        <CardTitle>Option Chain</CardTitle>
        <CardDescription>
          View option chain data in table or visual format
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="table" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="table">Table View</TabsTrigger>
            <TabsTrigger value="visual">Visual View</TabsTrigger>
          </TabsList>
          
          <TabsContent value="table" className="mt-4">
            {/* Remove outer Card wrapper from OptionChainTable when inside Tabs */}
            <OptionChainTable
              calls={calls}
              puts={puts}
              spotPrice={spotPrice}
              onSelectOption={onSelectOption}
              onAddLeg={onAddLeg}
              expirationDate={expirationDate}
            />
          </TabsContent>
          
          <TabsContent value="visual" className="mt-4">
            <OptionChainPriceView
              calls={calls}
              puts={puts}
              spotPrice={spotPrice}
              onSelectOption={onSelectOption}
            />
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}

