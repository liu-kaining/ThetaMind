import * as React from "react"
import { useState } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import { useSearchParams } from "react-router-dom"
import { Plus, Trash2, Sparkles, Smartphone } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { PayoffChart } from "@/components/charts/PayoffChart"
import { AdvancedPayoffChart } from "@/components/charts/AdvancedPayoffChart"
import { CandlestickChart } from "@/components/charts/CandlestickChart"
import { SymbolSearch } from "@/components/market/SymbolSearch"
import { OptionChainTable } from "@/components/market/OptionChainTable"
import { StrategyGreeks } from "@/components/strategy/StrategyGreeks"
import { StrategyTemplatesPagination } from "@/components/strategy/StrategyTemplatesPagination"
import { ScenarioSimulator } from "@/components/strategy/ScenarioSimulator"
import { SmartPriceAdvisor } from "@/components/strategy/SmartPriceAdvisor"
import { TradeCheatSheet } from "@/components/strategy/TradeCheatSheet"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useAuth } from "@/features/auth/AuthProvider"
import { marketService } from "@/services/api/market"
import { strategyService, StrategyLeg } from "@/services/api/strategy"
import { taskService } from "@/services/api/task"
import { strategyTemplates, getTemplateById } from "@/lib/strategyTemplates"
import { toast } from "sonner"
import { useNavigate } from "react-router-dom"

interface StrategyLegForm extends StrategyLeg {
  id: string
}

export const StrategyLab: React.FC = () => {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const strategyId = searchParams.get("strategy")
  const initialSymbol = searchParams.get("symbol") || "AAPL"
  const [symbol, setSymbol] = useState(initialSymbol)
  const [spotPrice, setSpotPrice] = useState<number | null>(null)
  const [expirationDate, setExpirationDate] = useState("")
  const [strategyName, setStrategyName] = useState("")
  const [legs, setLegs] = useState<StrategyLegForm[]>([])
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [scenarioParams, setScenarioParams] = useState<{
    priceChangePercent: number
    volatilityChangePercent: number
    daysRemaining: number
  } | null>(null)
  const [cheatSheetOpen, setCheatSheetOpen] = useState(false)

  // Load strategy if strategyId is provided
  const { data: loadedStrategy } = useQuery({
    queryKey: ["strategy", strategyId],
    queryFn: () => strategyService.get(strategyId!),
    enabled: !!strategyId,
  })

  // Load strategy data when loaded
  React.useEffect(() => {
    if (loadedStrategy) {
      setStrategyName(loadedStrategy.name)
      if (loadedStrategy.legs_json?.symbol) {
        setSymbol(loadedStrategy.legs_json.symbol)
      }
      if (loadedStrategy.legs_json?.legs) {
        const loadedLegs: StrategyLegForm[] = loadedStrategy.legs_json.legs.map(
          (leg: StrategyLeg, index: number) => ({
            ...leg,
            id: `loaded-${index}-${Date.now()}`,
          })
        )
        setLegs(loadedLegs)
        // Set expiration date from first leg
        if (loadedLegs.length > 0 && loadedLegs[0].expiry) {
          setExpirationDate(loadedLegs[0].expiry)
        }
      }
      toast.success(`Loaded strategy: ${loadedStrategy.name}`)
    }
  }, [loadedStrategy])

  // Calculate expiration date (next Friday as default)
  React.useEffect(() => {
    if (!expirationDate) {
      const today = new Date()
      const daysUntilFriday = (5 - today.getDay() + 7) % 7 || 7
      const nextFriday = new Date(today)
      nextFriday.setDate(today.getDate() + daysUntilFriday)
      setExpirationDate(nextFriday.toISOString().split("T")[0])
    }
  }, [expirationDate])

  // Fetch option chain with polling for Pro users
  const { data: optionChain, isLoading: isLoadingChain } = useQuery({
    queryKey: ["optionChain", symbol, expirationDate],
    queryFn: () => marketService.getOptionChain(symbol, expirationDate),
    enabled: !!symbol && !!expirationDate,
    refetchInterval: user?.is_pro ? 5000 : false, // 5s for Pro, no polling for Free
  })

  // Update spot price when option chain loads
  React.useEffect(() => {
    if (optionChain?.spot_price) {
      setSpotPrice(optionChain.spot_price)
    }
  }, [optionChain])

  // Fetch stock quote when symbol changes (to get initial spot price)
  const { data: stockQuote } = useQuery({
    queryKey: ["stockQuote", symbol],
    queryFn: () => marketService.getStockQuote(symbol),
    enabled: !!symbol,
  })

  // Fetch historical candlestick data
  const { data: historicalData } = useQuery({
    queryKey: ["historicalData", symbol],
    queryFn: () => marketService.getHistoricalData(symbol, 30),
    enabled: !!symbol,
  })

  // Update spot price from quote if chain doesn't have it
  React.useEffect(() => {
    if (stockQuote?.data?.price && !spotPrice) {
      setSpotPrice(stockQuote.data.price)
    }
  }, [stockQuote, spotPrice])

  // Handle symbol selection
  const handleSymbolSelect = async (selectedSymbol: string) => {
    setSymbol(selectedSymbol)
    // Fetch quote to get spot price
    try {
      const quote = await marketService.getStockQuote(selectedSymbol)
      if (quote.data?.price) {
        setSpotPrice(quote.data.price)
      }
    } catch (error) {
      console.error("Failed to fetch quote:", error)
    }
  }

  // Handle template selection
  const handleTemplateSelect = (templateId: string) => {
    if (!spotPrice || !expirationDate) {
      toast.error("Please select a symbol and expiration date first")
      return
    }
    const template = getTemplateById(templateId)
    if (!template) {
      toast.error("Template not found")
      return
    }
    const templateLegs = template.apply(spotPrice, expirationDate)
    
    // Allow templates with any number of legs (for research and learning)
    // Show warning if template has more than 4 legs
    if (templateLegs.length > 4) {
      toast.warning(
        `⚠️ Advanced Strategy Alert: This template contains ${templateLegs.length} legs. This is an advanced strategy - please exercise caution in live trading. Most brokers cannot execute orders with more than 4 legs simultaneously.`,
        { duration: 6000 }
      )
    }
    
    const legsWithIds: StrategyLegForm[] = templateLegs.map((leg, index) => ({
      ...leg,
      id: `template-${Date.now()}-${index}`,
    }))
    setLegs(legsWithIds)
    setStrategyName(template.name)
    toast.success(`Loaded "${template.name}" template`)
  }

  // Calculate days to expiration
  const daysToExpiry = React.useMemo(() => {
    if (!expirationDate) return undefined
    const expDate = new Date(expirationDate)
    const today = new Date()
    const diffTime = expDate.getTime() - today.getTime()
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    return diffDays > 0 ? diffDays : undefined
  }, [expirationDate])

  // Calculate payoff diagram
  const payoffData = React.useMemo(() => {
    if (!optionChain || legs.length === 0) return []

    const spotPrice = optionChain.spot_price
    if (!spotPrice || isNaN(spotPrice) || !isFinite(spotPrice) || spotPrice <= 0) {
      return []
    }

    const minPrice = spotPrice * 0.7
    const maxPrice = spotPrice * 1.3
    const step = (maxPrice - minPrice) / 200 // More data points for smoother curve

    const data: Array<{ price: number; profit: number }> = []

    for (let price = minPrice; price <= maxPrice; price += step) {
      let totalProfit = 0

      legs.forEach((leg) => {
        if (!leg || !leg.strike || isNaN(leg.strike) || !isFinite(leg.strike)) {
          return
        }

        // Find option in chain to get premium
        // Support both strike and strike_price field names
        const options = leg.type === "call" ? optionChain.calls : optionChain.puts
        const option = options.find((o) => {
          if (!o) return false
          const optionStrike = o.strike ?? o.strike_price
          return optionStrike !== undefined && Math.abs(optionStrike - leg.strike) < 0.01
        })
        
        let premium = leg.premium || 0
        if (option) {
          // Support both bid/ask and bid_price/ask_price field names
          const bid = Number(option.bid ?? option.bid_price ?? 0)
          const ask = Number(option.ask ?? option.ask_price ?? 0)
          if (!isNaN(bid) && !isNaN(ask) && isFinite(bid) && isFinite(ask) && bid > 0 && ask > 0) {
            premium = (bid + ask) / 2
          }
        }
        if (isNaN(premium) || !isFinite(premium) || premium < 0) {
          premium = 0
        }

        const isInTheMoney =
          leg.type === "call" ? price > leg.strike : price < leg.strike
        const intrinsicValue = isInTheMoney
          ? leg.type === "call"
            ? price - leg.strike
            : leg.strike - price
          : 0

        const profit =
          leg.action === "buy"
            ? intrinsicValue - premium
            : premium - intrinsicValue

        const quantity = leg.quantity || 1
        const contribution = profit * quantity
        if (!isNaN(contribution) && isFinite(contribution)) {
          totalProfit += contribution
        }
      })

      const priceValue = Number(price.toFixed(2))
      const profitValue = Number(totalProfit.toFixed(2))
      if (!isNaN(priceValue) && !isNaN(profitValue) && isFinite(priceValue) && isFinite(profitValue)) {
        data.push({ price: priceValue, profit: profitValue })
      }
    }

    return data
  }, [optionChain, legs])

  // Calculate break-even
  const breakEven = React.useMemo(() => {
    if (payoffData.length === 0) return undefined

    // Find the price where profit crosses zero
    for (let i = 0; i < payoffData.length - 1; i++) {
      if (
        (payoffData[i].profit <= 0 && payoffData[i + 1].profit >= 0) ||
        (payoffData[i].profit >= 0 && payoffData[i + 1].profit <= 0)
      ) {
        return payoffData[i].price
      }
    }
    return undefined
  }, [payoffData])

  const addLeg = () => {
    // Allow adding legs beyond 4 (for research and learning)
    // Show warning when exceeding 4 legs
    if (legs.length >= 4) {
      toast.warning(
        "⚠️ Advanced Strategy Alert: Strategies with more than 4 legs are advanced strategies - please exercise caution in live trading. Most brokers cannot execute orders with more than 4 legs simultaneously.",
        { duration: 6000 }
      )
    }
    const newLeg: StrategyLegForm = {
      id: Date.now().toString(),
      type: "call",
      action: "buy",
      strike: optionChain?.spot_price || 100,
      quantity: 1,
      expiry: expirationDate,
    }
    setLegs([...legs, newLeg])
  }

  const removeLeg = (id: string) => {
    setLegs(legs.filter((leg) => leg.id !== id))
  }

  const updateLeg = (id: string, updates: Partial<StrategyLegForm>) => {
    setLegs(legs.map((leg) => (leg.id === id ? { ...leg, ...updates } : leg)))
  }

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      if (!optionChain || legs.length === 0) {
        throw new Error("Please add at least one leg and fetch option chain")
      }

      setIsAnalyzing(true)
      try {
        // Create a background task instead of generating report directly
        const task = await taskService.createTask({
          task_type: "ai_report",
          metadata: {
            strategy_data: {
              symbol,
              legs: legs.map(({ id, ...leg }) => leg),
            },
            option_chain: optionChain,
          },
        })
        return task
      } finally {
        setIsAnalyzing(false)
      }
    },
    onSuccess: () => {
      toast.success("Task started! Redirecting to Task Center...", {
        action: {
          label: "View Task",
          onClick: () => navigate(`/dashboard/tasks`),
        },
      })
      // Redirect to Task Center after a short delay
      setTimeout(() => {
        navigate("/dashboard/tasks")
      }, 1500)
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail || "Failed to start AI analysis task"
      )
    },
  })

  const saveStrategyMutation = useMutation({
    mutationFn: async () => {
      if (!strategyName || legs.length === 0) {
        throw new Error("Please provide a strategy name and add legs")
      }

      return strategyService.create({
        name: strategyName,
        legs_json: {
          symbol,
          legs: legs.map(({ id, ...leg }) => leg),
        },
      })
    },
    onSuccess: () => {
      toast.success("Strategy saved successfully!")
      setStrategyName("")
      setLegs([])
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail || "Failed to save strategy"
      )
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Strategy Lab</h1>
          <p className="text-muted-foreground">
            Build and analyze option strategies with AI-powered insights
          </p>
        </div>
        {legs.length > 0 && (
          <Button
            variant="outline"
            size="lg"
            onClick={() => setCheatSheetOpen(true)}
            className="gap-2"
          >
            <Smartphone className="h-5 w-5" />
            Phone View
          </Button>
        )}
      </div>

      {/* New Layout: Left-Right Split */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left: Strategy Builder (1 column) */}
        <div className="lg:col-span-1 space-y-4">
          {/* Smart Price Advisor - Pro Feature */}
          {symbol && expirationDate && legs.length > 0 && (
            <SmartPriceAdvisor
              symbol={symbol}
              legs={legs}
              expirationDate={expirationDate}
              optionChain={optionChain || undefined}
            />
          )}

            <Card>
            <CardHeader>
              <CardTitle>Strategy Builder</CardTitle>
              <CardDescription>Configure your option strategy</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <Label htmlFor="symbol">Symbol</Label>
                  <SymbolSearch
                    onSelect={handleSymbolSelect}
                    value={symbol}
                  />
                </div>
                <div>
                  <Label htmlFor="expiry">Expiration Date</Label>
                  <Input
                    id="expiry"
                    type="date"
                    value={expirationDate}
                    onChange={(e) => setExpirationDate(e.target.value)}
                    min={new Date().toISOString().split("T")[0]} // Today as minimum
                    max={new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().split("T")[0]} // 1 year from now
                  />
                </div>
              </div>

              {isLoadingChain && (
                <div className="text-sm text-muted-foreground">
                  Loading option chain...
                </div>
              )}

              {optionChain && (
                <div className="text-sm text-muted-foreground">
                  Spot Price: ${optionChain.spot_price?.toFixed(2)}
                  {user?.is_pro && (
                    <span className="ml-2 text-green-600">● Real-time</span>
                  )}
                </div>
              )}

              {/* Strategy Templates */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <Label>Strategy Templates ({strategyTemplates.length} total)</Label>
                </div>
                <StrategyTemplatesPagination
                  templates={strategyTemplates}
                  onSelect={handleTemplateSelect}
                  disabled={!spotPrice || !expirationDate}
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Label>Option Legs</Label>
                    <span className="text-xs text-muted-foreground">
                      ({legs.length} {legs.length === 1 ? "leg" : "legs"})
                    </span>
                  </div>
                  <Button 
                    onClick={addLeg} 
                    size="sm" 
                    variant="default" 
                    className="font-medium"
                    title="Add option leg"
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Add Leg
                  </Button>
                </div>
                {legs.length > 4 && (
                  <div className="mb-2 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-300 dark:border-amber-700 rounded-md">
                    <div className="flex items-start gap-2">
                      <span className="text-amber-600 dark:text-amber-400 text-sm font-semibold">⚠️</span>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-amber-800 dark:text-amber-200 mb-1">
                          Advanced Strategy Alert
                        </p>
                        <p className="text-xs text-amber-700 dark:text-amber-300">
                          Current strategy contains <strong>{legs.length} legs</strong>. This is an advanced strategy - please exercise caution in live trading. Most brokers cannot execute orders with more than 4 legs simultaneously.
                        </p>
                      </div>
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  {legs.map((leg) => (
                    <Card key={leg.id} className="p-3">
                      <div className="grid gap-2 md:grid-cols-5">
                        <select
                          value={leg.type}
                          onChange={(e) =>
                            updateLeg(leg.id, {
                              type: e.target.value as "call" | "put",
                            })
                          }
                          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                        >
                          <option value="call">Call</option>
                          <option value="put">Put</option>
                        </select>
                        <select
                          value={leg.action}
                          onChange={(e) =>
                            updateLeg(leg.id, {
                              action: e.target.value as "buy" | "sell",
                            })
                          }
                          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
                        >
                          <option value="buy">Buy</option>
                          <option value="sell">Sell</option>
                        </select>
                        <Input
                          type="number"
                          placeholder="Strike"
                          value={leg.strike}
                          onChange={(e) =>
                            updateLeg(leg.id, {
                              strike: parseFloat(e.target.value) || 0,
                            })
                          }
                        />
                        <Input
                          type="number"
                          placeholder="Qty"
                          value={leg.quantity}
                          onChange={(e) =>
                            updateLeg(leg.id, {
                              quantity: parseInt(e.target.value) || 1,
                            })
                          }
                        />
                        <Button
                          onClick={() => removeLeg(leg.id)}
                          size="sm"
                          variant="ghost"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  onClick={() => analyzeMutation.mutate()}
                  disabled={isAnalyzing || legs.length === 0 || !optionChain}
                  className="flex-1 font-semibold"
                  variant="default"
                >
                  <Sparkles className="h-4 w-4 mr-2" />
                  {isAnalyzing ? "Analyzing..." : "Analyze with AI"}
                </Button>
                <Input
                  placeholder="Strategy name"
                  value={strategyName}
                  onChange={(e) => setStrategyName(e.target.value)}
                  className="flex-1"
                />
                <Button
                  onClick={() => saveStrategyMutation.mutate()}
                  disabled={!strategyName || legs.length === 0}
                  variant="secondary"
                  className="font-semibold min-w-[80px]"
                >
                  Save
                </Button>
              </div>
            </CardContent>
          </Card>

        </div>

        {/* Right: Charts and Option Chain (2 columns) */}
        <div className="lg:col-span-2 space-y-4">
          {/* Portfolio Greeks - Compact at top */}
          {legs.length > 0 && (
            <StrategyGreeks legs={legs} optionChain={optionChain} />
          )}

          {/* Charts with Tabs */}
          <Card>
            <CardHeader>
              <CardTitle>Charts</CardTitle>
              <CardDescription>
                Visualize strategy payoff and market data
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="payoff" className="w-full">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="payoff">Payoff Diagram</TabsTrigger>
                  <TabsTrigger value="advanced">Advanced Payoff</TabsTrigger>
                  {/* Market Chart temporarily hidden */}
                </TabsList>
                <TabsContent value="payoff" className="mt-4">
                  {payoffData.length > 0 ? (
                    <div>
                      <div className="mb-2 text-sm text-muted-foreground">
                        Profit/Loss visualization across stock prices
                        {daysToExpiry && ` • ${daysToExpiry} days to expiration`}
                        {scenarioParams && (
                          <span className="ml-2 text-primary font-semibold">
                            • Scenario Active
                          </span>
                        )}
                      </div>
                      <PayoffChart
                        data={payoffData}
                        breakEven={breakEven}
                        currentPrice={optionChain?.spot_price}
                        expirationDate={expirationDate}
                        timeToExpiry={daysToExpiry}
                        scenarioParams={scenarioParams || undefined}
                      />
                    </div>
                  ) : (
                    <div className="flex h-[400px] items-center justify-center text-muted-foreground">
                      Add option legs to see payoff diagram
                    </div>
                  )}
                </TabsContent>
                <TabsContent value="advanced" className="mt-4">
                  {payoffData.length > 0 ? (
                    <div>
                      <div className="mb-2 text-sm text-muted-foreground">
                        Professional payoff visualization with detailed annotations
                        {daysToExpiry && ` • ${daysToExpiry} days to expiration`}
                      </div>
                      <AdvancedPayoffChart
                        data={payoffData}
                        legs={legs}
                        symbol={symbol}
                        strategyName={strategyName || "Custom Strategy"}
                        currentPrice={optionChain?.spot_price}
                        breakEven={breakEven}
                      />
                    </div>
                  ) : (
                    <div className="flex h-[400px] items-center justify-center text-muted-foreground">
                      Add option legs to see advanced payoff diagram
                    </div>
                  )}
                </TabsContent>
                <TabsContent value="market" className="mt-4">
                  {historicalData && historicalData.data && historicalData.data.length > 0 ? (
                    <div>
                      <div className="mb-2 text-sm text-muted-foreground">
                        30-day candlestick chart for {symbol}
                      </div>
                      <CandlestickChart
                        data={historicalData.data.map((d) => {
                          // Convert time string to format expected by lightweight-charts
                          // lightweight-charts accepts YYYY-MM-DD string format
                          let timeValue: string
                          if (typeof d.time === 'string') {
                            timeValue = d.time
                          } else if (typeof d.time === 'number') {
                            // Convert Unix timestamp to YYYY-MM-DD
                            const date = new Date(d.time * 1000)
                            timeValue = date.toISOString().split('T')[0]
                          } else {
                            // Fallback: use current date
                            timeValue = new Date().toISOString().split('T')[0]
                          }
                          return {
                            time: timeValue as any, // lightweight-charts accepts string dates
                            open: Number(d.open),
                            high: Number(d.high),
                            low: Number(d.low),
                            close: Number(d.close),
                          }
                        })}
                        height={450}
                      />
                    </div>
                  ) : (
                    <div className="flex h-[400px] items-center justify-center text-muted-foreground">
                      {symbol ? "Loading market data..." : "Select a symbol to view market chart"}
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

          {/* Scenario Simulator */}
          {payoffData.length > 0 && optionChain?.spot_price && daysToExpiry && (
            <ScenarioSimulator
              currentPrice={optionChain.spot_price}
              daysToExpiry={daysToExpiry}
              onScenarioChange={setScenarioParams}
            />
          )}

          {/* Option Chain Table */}
          {optionChain && optionChain.calls.length > 0 && (
            <OptionChainTable
              calls={optionChain.calls}
              puts={optionChain.puts}
              spotPrice={optionChain.spot_price || 0}
              onSelectOption={(option, type) => {
                // Allow selecting options beyond 4 legs (for research and learning)
                // Show warning when exceeding 4 legs
                if (legs.length >= 4) {
                  toast.warning(
                    "⚠️ Advanced Strategy Alert: Strategies with more than 4 legs are advanced strategies - please exercise caution in live trading. Most brokers cannot execute orders with more than 4 legs simultaneously.",
                    { duration: 6000 }
                  )
                }
                // Support multiple field name formats for compatibility
                const optionStrike = option.strike ?? (option as any).strike_price ?? 0
                const optionBid = option.bid ?? (option as any).bid_price ?? 0
                const optionAsk = option.ask ?? (option as any).ask_price ?? 0
                const premium = optionBid > 0 && optionAsk > 0 ? (optionBid + optionAsk) / 2 : 0
                
                const newLeg: StrategyLegForm = {
                  id: Date.now().toString(),
                  type: type,
                  action: "buy",
                  strike: optionStrike,
                  quantity: 1,
                  expiry: expirationDate,
                  premium: premium,
                }
                setLegs([...legs, newLeg])
                toast.success(`Added ${type} option at strike $${optionStrike.toFixed(2)}`)
              }}
            />
          )}
        </div>
      </div>

      {/* Trade Cheat Sheet Modal */}
      <TradeCheatSheet
        open={cheatSheetOpen}
        onOpenChange={setCheatSheetOpen}
        symbol={symbol}
        expirationDate={expirationDate}
        legs={legs}
      />
    </div>
  )
}

