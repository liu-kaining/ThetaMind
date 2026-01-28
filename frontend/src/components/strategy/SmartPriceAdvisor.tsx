import * as React from "react"
import { Crown, Lock, RefreshCw } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { StrategyLeg } from "@/services/api/strategy"
import { useAuth } from "@/features/auth/AuthProvider"
import { useNavigate } from "react-router-dom"

interface SmartPriceAdvisorProps {
  symbol: string
  legs: StrategyLeg[]
  expirationDate: string
  optionChain?: {
    calls: Array<{
      strike: number
      bid?: number
      ask?: number
      bid_price?: number
      ask_price?: number
      [key: string]: any
    }>
    puts: Array<{
      strike: number
      bid?: number
      ask?: number
      bid_price?: number
      ask_price?: number
      [key: string]: any
    }>
    spot_price?: number
  } | null
  onRefresh?: () => void
  isRefreshing?: boolean
}

export const SmartPriceAdvisor: React.FC<SmartPriceAdvisorProps> = ({
  legs,
  optionChain,
  onRefresh,
  isRefreshing = false,
}) => {
  const { user } = useAuth()
  const navigate = useNavigate()
  const isPro = user?.is_pro || false

  if (!isPro) {
    return (
      <Card className="relative overflow-hidden">
        <div className="absolute inset-0 backdrop-blur-sm bg-background/80 z-10 flex items-center justify-center">
          <div className="text-center space-y-4 p-6">
            <Lock className="h-12 w-12 mx-auto text-muted-foreground" />
            <div>
              <h3 className="font-semibold text-lg mb-2">Smart Price Advisor</h3>
              <p className="text-sm text-muted-foreground mb-4">
                Upgrade to Pro to see real-time pricing recommendations
              </p>
              <Button onClick={() => navigate("/pricing")}>
                <Crown className="h-4 w-4 mr-2" />
                Upgrade to Pro
              </Button>
            </div>
          </div>
        </div>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Crown className="h-5 w-5 text-yellow-500" />
            Trade Execution
          </CardTitle>
          <CardDescription>Smart pricing recommendations</CardDescription>
        </CardHeader>
        <CardContent className="blur-sm pointer-events-none">
          <div className="space-y-4">
            <div className="p-4 border rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium">Conservative</span>
                <Badge variant="outline">$0.00</Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Crown className="h-5 w-5 text-yellow-500" />
              Trade Execution
            </CardTitle>
            <CardDescription>
              Smart pricing recommendations based on real-time market data
            </CardDescription>
          </div>
          {onRefresh && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              disabled={isRefreshing}
              className="ml-2 h-7 text-xs"
            >
              <RefreshCw className={`h-3 w-3 mr-1 ${isRefreshing ? "animate-spin" : ""}`} />
              {isRefreshing ? "Refreshing..." : "Refresh"}
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {legs.length === 0 ? (
          <div className="text-center py-2 text-muted-foreground text-xs">
            <p>Add option legs to see pricing recommendations</p>
          </div>
        ) : !optionChain ? (
          <div className="text-center py-2 text-muted-foreground text-xs">
            <p>Loading option chain data...</p>
          </div>
        ) : (
          <div className="space-y-1.5">
            {legs.map((leg, index) => {
              // Find option in chain
              const options = leg.type === "call" ? optionChain.calls : optionChain.puts
              
              // First try exact match (within 0.01 tolerance)
              let option = options.find((o) => {
                const optionStrike = o.strike
                return optionStrike !== undefined && Math.abs(optionStrike - leg.strike) < 0.01
              })

              // If exact match not found, find nearest adjacent strike
              if (!option) {
                let nearestOption: typeof options[0] | undefined = undefined
                let minDistance = Infinity

                options.forEach((o) => {
                  const optionStrike = o.strike
                  if (optionStrike === undefined) return

                  const distance = Math.abs(optionStrike - leg.strike)
                  if (distance < minDistance) {
                    minDistance = distance
                    nearestOption = o
                  }
                })

                // Use nearest option if found and within reasonable range (e.g., within $10)
                if (nearestOption && minDistance <= 10) {
                  option = nearestOption
                }
              }

              if (!option) {
                return (
                  <div key={index} className="p-4 border rounded-lg text-sm text-muted-foreground">
                    {leg.type.toUpperCase()} ${leg.strike} - Option not found in chain (no adjacent strike within $10)
                  </div>
                )
              }

              // Get bid/ask prices (support multiple field names)
              const bid = Number(option.bid ?? option.bid_price ?? 0)
              const ask = Number(option.ask ?? option.ask_price ?? 0)

              if (bid <= 0 || ask <= 0 || bid >= ask) {
                return (
                  <div key={index} className="p-4 border rounded-lg text-sm text-muted-foreground">
                    {leg.type.toUpperCase()} ${leg.strike} - Invalid bid/ask data
                  </div>
                )
              }

              const midPrice = (bid + ask) / 2
              const spread = ask - bid

              const conservative = midPrice
              const aggressive = ask
              const passive = Math.max(bid, bid + 0.05)

              return (
                <div key={index} className="p-1.5 border rounded-lg space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-xs">
                      {leg.action === "buy" ? "Buy" : "Sell"} {leg.quantity}x {leg.type.toUpperCase()} ${leg.strike}
                    </span>
                    <Badge variant="outline" className="text-xs px-1.5 py-0">
                      Mid: ${midPrice.toFixed(2)}
                    </Badge>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-1">
                    {/* Conservative */}
                    <div className="p-1 bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-800 rounded-lg">
                      <div className="flex items-center gap-1 mb-0.5">
                        <div className="w-2 h-2 rounded-full bg-green-500"></div>
                        <span className="text-xs font-medium text-green-700 dark:text-green-300">
                          Conservative
                        </span>
                      </div>
                      <div className="text-sm font-bold text-green-700 dark:text-green-300 leading-tight">
                        ${conservative.toFixed(2)}
                      </div>
                      <div className="text-[10px] text-green-600 dark:text-green-400 mt-0.5 leading-tight">
                        Limit Order
                      </div>
                    </div>

                    {/* Aggressive */}
                    <div className="p-1 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-lg">
                      <div className="flex items-center gap-1 mb-0.5">
                        <div className="w-2 h-2 rounded-full bg-red-500"></div>
                        <span className="text-xs font-medium text-red-700 dark:text-red-300">
                          Aggressive
                        </span>
                      </div>
                      <div className="text-sm font-bold text-red-700 dark:text-red-300 leading-tight">
                        ${aggressive.toFixed(2)}
                      </div>
                      <div className="text-[10px] text-red-600 dark:text-red-400 mt-0.5 leading-tight">
                        Instant Fill
                      </div>
                    </div>

                    {/* Passive */}
                    <div className="p-1 bg-yellow-50 dark:bg-yellow-950/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                      <div className="flex items-center gap-1 mb-0.5">
                        <div className="w-2 h-2 rounded-full bg-yellow-500"></div>
                        <span className="text-xs font-medium text-yellow-700 dark:text-yellow-300">
                          Passive
                        </span>
                      </div>
                      <div className="text-sm font-bold text-yellow-700 dark:text-yellow-300 leading-tight">
                        ${passive.toFixed(2)}
                      </div>
                      <div className="text-[10px] text-yellow-600 dark:text-yellow-400 mt-0.5 leading-tight">
                        Bid + $0.05
                      </div>
                    </div>
                  </div>

                  <div className="text-[10px] text-muted-foreground pt-0.5 border-t leading-tight">
                    Spread: ${spread.toFixed(2)} ({((spread / midPrice) * 100).toFixed(1)}%)
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

