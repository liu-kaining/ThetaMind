import * as React from "react"
import { useState } from "react"
import { Link } from "react-router-dom"
import { ArrowRight, Lock, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { PayoffChart } from "@/components/charts/PayoffChart"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

// Demo data - a sample Iron Condor strategy
const DEMO_STRATEGY = {
  symbol: "AAPL",
  expirationDate: "2024-02-16",
  legs: [
    {
      id: "1",
      type: "call",
      action: "sell",
      strike: 200,
      quantity: 1,
      premium: 2.5,
    },
    {
      id: "2",
      type: "call",
      action: "buy",
      strike: 205,
      quantity: 1,
      premium: 1.0,
    },
    {
      id: "3",
      type: "put",
      action: "sell",
      strike: 190,
      quantity: 1,
      premium: 2.0,
    },
    {
      id: "4",
      type: "put",
      action: "buy",
      strike: 185,
      quantity: 1,
      premium: 0.8,
    },
  ],
}

export const DemoPage: React.FC = () => {
  const [selectedTab, setSelectedTab] = useState<"payoff" | "market">("payoff")

  // Calculate demo payoff data
  const payoffData = React.useMemo(() => {
    const data: Array<{ price: number; profit: number }> = []
    const priceRange = [170, 220]
    const step = 1

    for (let price = priceRange[0]; price <= priceRange[1]; price += step) {
      let totalProfit = 0

      DEMO_STRATEGY.legs.forEach((leg) => {
        let legProfit = 0
        const intrinsicValue = Math.max(
          0,
          leg.type === "call" ? price - leg.strike : leg.strike - price
        )

        if (leg.action === "sell") {
          legProfit = leg.premium - intrinsicValue
        } else {
          legProfit = intrinsicValue - leg.premium
        }

        totalProfit += legProfit * leg.quantity
      })

      data.push({ price, profit: totalProfit })
    }

    return data
  }, [])

  const breakEven = React.useMemo(() => {
    // Calculate break-even points for Iron Condor
    const netCredit = DEMO_STRATEGY.legs.reduce((sum, leg) => {
      return sum + (leg.action === "sell" ? leg.premium : -leg.premium) * leg.quantity
    }, 0)

    // Upper break-even: short call strike + net credit
    const upperBE = 200 + netCredit
    // Lower break-even: short put strike - net credit
    const lowerBE = 190 - netCredit

    // Return the average for display (PayoffChart expects a single number)
    return (upperBE + lowerBE) / 2
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900">
      {/* Header */}
      <div className="border-b border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 backdrop-blur">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-6 w-6 text-primary" />
              <span className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                ThetaMind Demo
              </span>
            </div>
            <Button asChild className="bg-gradient-to-r from-blue-600 to-indigo-600">
              <Link to="/login">
                Sign In to Use
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </div>

      {/* Demo Content */}
      <div className="container mx-auto px-6 py-8">
        <div className="max-w-7xl mx-auto space-y-6">
          {/* Info Banner */}
          <Card className="border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <Lock className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5" />
                <div>
                  <p className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
                    Interactive Demo Mode
                  </p>
                  <p className="text-sm text-blue-800 dark:text-blue-200">
                    This is a read-only demonstration of ThetaMind's Strategy Lab. Sign in to create
                    your own strategies, access real-time data, and use AI-powered analysis.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Strategy Info */}
          <Card>
            <CardHeader>
              <CardTitle>Demo Strategy: Iron Condor on AAPL</CardTitle>
              <CardDescription>
                A neutral strategy with limited risk and limited profit potential
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Symbol</p>
                  <p className="font-semibold">{DEMO_STRATEGY.symbol}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Expiration</p>
                  <p className="font-semibold">{DEMO_STRATEGY.expirationDate}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Strategy Type</p>
                  <p className="font-semibold">Iron Condor</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Net Credit</p>
                  <p className="font-semibold text-green-600">
                    $
                    {DEMO_STRATEGY.legs
                      .reduce(
                        (sum, leg) =>
                          sum + (leg.action === "sell" ? leg.premium : -leg.premium) * leg.quantity,
                        0
                      )
                      .toFixed(2)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Charts */}
          <Card>
            <CardHeader>
              <CardTitle>Charts</CardTitle>
              <CardDescription>
                Visualize strategy payoff and market data
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs value={selectedTab} onValueChange={(v) => setSelectedTab(v as any)} className="w-full">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="payoff">Payoff Diagram</TabsTrigger>
                  <TabsTrigger value="market">Market Chart</TabsTrigger>
                </TabsList>
                <TabsContent value="payoff" className="mt-4">
                  <div className="mb-2 text-sm text-muted-foreground">
                    Profit/Loss visualization across stock prices
                  </div>
                  <PayoffChart
                    data={payoffData}
                    breakEven={breakEven}
                    currentPrice={195}
                    expirationDate={DEMO_STRATEGY.expirationDate}
                    timeToExpiry={30}
                  />
                </TabsContent>
                <TabsContent value="market" className="mt-4">
                  <div className="mb-2 text-sm text-muted-foreground">
                    30-day candlestick chart for {DEMO_STRATEGY.symbol}
                  </div>
                  <div className="flex h-[400px] items-center justify-center text-muted-foreground border rounded-lg bg-slate-50 dark:bg-slate-900">
                    <div className="text-center">
                      <Lock className="h-12 w-12 mx-auto mb-2 opacity-50" />
                      <p>Market chart available after sign in</p>
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          {/* Strategy Legs */}
          <Card>
            <CardHeader>
              <CardTitle>Strategy Legs</CardTitle>
              <CardDescription>Four-leg Iron Condor structure</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {DEMO_STRATEGY.legs.map((leg, index) => (
                  <div
                    key={leg.id}
                    className="flex items-center justify-between p-3 rounded-lg border bg-slate-50 dark:bg-slate-900"
                  >
                    <div className="flex items-center gap-4">
                      <span className="text-sm font-medium text-muted-foreground">
                        Leg {index + 1}
                      </span>
                      <span className="font-semibold">
                        {leg.action.toUpperCase()} {leg.strike} {leg.type.toUpperCase()}
                      </span>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-muted-foreground">Premium</p>
                      <p className="font-semibold">${leg.premium.toFixed(2)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* CTA */}
          <Card className="border-primary bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950">
            <CardContent className="pt-6">
              <div className="text-center space-y-4">
                <h3 className="text-2xl font-bold">Ready to Build Your Own Strategies?</h3>
                <p className="text-muted-foreground">
                  Sign in to access real-time market data, AI analysis, and unlimited strategy
                  building.
                </p>
                <Button size="lg" asChild className="bg-gradient-to-r from-blue-600 to-indigo-600">
                  <Link to="/login">
                    Get Started Free
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

