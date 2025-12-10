import * as React from "react"
import { useState } from "react"
import { useQuery, useMutation } from "@tanstack/react-query"
import { useSearchParams } from "react-router-dom"
import { Plus, Trash2, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { PayoffChart } from "@/components/charts/PayoffChart"
import { SymbolSearch } from "@/components/market/SymbolSearch"
import { OptionChainTable } from "@/components/market/OptionChainTable"
import { StrategyGreeks } from "@/components/strategy/StrategyGreeks"
import { StrategyTemplatesPagination } from "@/components/strategy/StrategyTemplatesPagination"
import { useAuth } from "@/features/auth/AuthProvider"
import { marketService } from "@/services/api/market"
import { strategyService, StrategyLeg } from "@/services/api/strategy"
import { aiService } from "@/services/api/ai"
import { strategyTemplates, getTemplateById } from "@/lib/strategyTemplates"
import { toast } from "sonner"
import ReactMarkdown from "react-markdown"

interface StrategyLegForm extends StrategyLeg {
  id: string
}

export const StrategyLab: React.FC = () => {
  const { user } = useAuth()
  const [searchParams] = useSearchParams()
  const strategyId = searchParams.get("strategy")
  const initialSymbol = searchParams.get("symbol") || "AAPL"
  const [symbol, setSymbol] = useState(initialSymbol)
  const [spotPrice, setSpotPrice] = useState<number | null>(null)
  const [expirationDate, setExpirationDate] = useState("")
  const [strategyName, setStrategyName] = useState("")
  const [legs, setLegs] = useState<StrategyLegForm[]>([])
  const [aiReport, setAiReport] = useState<string | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

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
    
    // Check if template exceeds 4 legs limit
    if (templateLegs.length > 4) {
      toast.error(`This template has ${templateLegs.length} legs, exceeding the 4-leg limit. Please build the strategy manually.`)
      return
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
    if (legs.length >= 4) {
      toast.error("Maximum 4 legs allowed. Most brokers don't support strategies with more than 4 legs.")
      return
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
        const response = await aiService.generateReport({
          strategy_data: {
            symbol,
            legs: legs.map(({ id, ...leg }) => leg),
          },
          option_chain: optionChain,
        })
        return response.report_content
      } finally {
        setIsAnalyzing(false)
      }
    },
    onSuccess: (report) => {
      setAiReport(report)
      toast.success("AI analysis completed!")
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail || "Failed to generate AI report"
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
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Strategy Lab</h1>
        <p className="text-muted-foreground">
          Build and analyze option strategies with AI-powered insights
        </p>
      </div>

      {/* New Layout: Left-Right Split */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left: Strategy Builder (1 column) */}
        <div className="lg:col-span-1 space-y-4">
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
                      ({legs.length}/4)
                    </span>
                  </div>
                  <Button 
                    onClick={addLeg} 
                    size="sm" 
                    variant="default" 
                    className="font-medium"
                    disabled={legs.length >= 4}
                    title={legs.length >= 4 ? "Maximum 4 legs allowed" : "Add option leg"}
                  >
                    <Plus className="h-4 w-4 mr-1" />
                    Add Leg
                  </Button>
                </div>
                {legs.length >= 4 && (
                  <div className="mb-2 p-2 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md">
                    <p className="text-xs text-yellow-800 dark:text-yellow-200">
                      ⚠️ Maximum limit reached: Most brokers don't support option strategies with more than 4 legs
                    </p>
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

          {aiReport && (
            <Card>
              <CardHeader>
                <CardTitle>AI Analysis Report</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <ReactMarkdown>{aiReport}</ReactMarkdown>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right: Charts and Option Chain (2 columns) */}
        <div className="lg:col-span-2 space-y-4">
          {/* Portfolio Greeks - Compact at top */}
          {legs.length > 0 && (
            <StrategyGreeks legs={legs} optionChain={optionChain} />
          )}

          {/* Payoff Chart - Medium size */}
          {payoffData.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle>Payoff Diagram</CardTitle>
                <CardDescription>
                  Profit/Loss visualization across stock prices
                  {daysToExpiry && ` • ${daysToExpiry} days to expiration`}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <PayoffChart
                  data={payoffData}
                  breakEven={breakEven}
                  currentPrice={optionChain?.spot_price}
                  expirationDate={expirationDate}
                  timeToExpiry={daysToExpiry}
                />
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Payoff Diagram</CardTitle>
                <CardDescription>
                  Profit/Loss visualization across stock prices
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex h-[400px] items-center justify-center text-muted-foreground">
                  Add option legs to see payoff diagram
                </div>
              </CardContent>
            </Card>
          )}

          {/* Option Chain Table */}
          {optionChain && optionChain.calls.length > 0 && (
            <OptionChainTable
              calls={optionChain.calls}
              puts={optionChain.puts}
              spotPrice={optionChain.spot_price || 0}
              onSelectOption={(option, type) => {
                if (legs.length >= 4) {
                  toast.error("Maximum 4 legs allowed. Most brokers don't support strategies with more than 4 legs.")
                  return
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
    </div>
  )
}

