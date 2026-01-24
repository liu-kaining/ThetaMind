import * as React from "react"
import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useSearchParams } from "react-router-dom"
import { Plus, Trash2, Sparkles, Clock, AlertTriangle, Brain, CheckCircle, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { PayoffChart } from "@/components/charts/PayoffChart"
import { CandlestickChart } from "@/components/charts/CandlestickChart"
import { SymbolSearch } from "@/components/market/SymbolSearch"
import { OptionChainVisualization } from "@/components/market/OptionChainVisualization"
import { StrategyGreeks } from "@/components/strategy/StrategyGreeks"
import { StrategyTemplatesPagination } from "@/components/strategy/StrategyTemplatesPagination"
import { ScenarioSimulator } from "@/components/strategy/ScenarioSimulator"
import { SmartPriceAdvisor } from "@/components/strategy/SmartPriceAdvisor"
import { TradeCheatSheet } from "@/components/strategy/TradeCheatSheet"
import { AIChartTab } from "@/components/strategy/AIChartTab"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Switch } from "@/components/ui/switch"
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
  const { user, refreshUser } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const strategyId = searchParams.get("strategy")
  const initialSymbol = strategyId ? "" : searchParams.get("symbol") || "AAPL"
  
  // Refresh user data on mount to ensure quota info is up-to-date
  React.useEffect(() => {
    refreshUser()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Only run once on mount
  const [symbol, setSymbol] = useState(initialSymbol)
  const [spotPrice, setSpotPrice] = useState<number | null>(null)
  const [expirationDate, setExpirationDate] = useState("")
  const [strategyName, setStrategyName] = useState("")
  const [legs, setLegs] = useState<StrategyLegForm[]>([])
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  // Always use Deep Research mode (quick mode removed due to data accuracy issues)
  const useDeepResearch = true
  const [scenarioParams, setScenarioParams] = useState<{
    priceChangePercent: number
    volatilityChangePercent: number
    daysRemaining: number
  } | null>(null)
  const [cheatSheetOpen, setCheatSheetOpen] = useState(false)
  const [deepResearchConfirmOpen, setDeepResearchConfirmOpen] = useState(false)
  const [useMultiAgentReport, setUseMultiAgentReport] = useState(false)
  const [hoveredCandleTime, setHoveredCandleTime] = useState<string | null>(null)
  const [isStrategySaved, setIsStrategySaved] = useState(false) // Track if strategy has been saved
  
  const getLatestMetricByKeys = React.useCallback(
    (series: Record<string, Record<string, number | null>> | undefined, keys: string[]) => {
      if (!series || keys.length === 0) return null
      const sortedKeys = Object.keys(series).sort().reverse()
      for (const rowKey of sortedKeys) {
        const row = series[rowKey]
        for (const field of keys) {
          const value = row?.[field as keyof typeof row]
          if (value !== undefined && value !== null) {
            return value
          }
        }
      }
      return null
    },
    []
  )

  const formatMetric = React.useCallback((value: number | null, digits = 2) => {
    if (value === null || value === undefined) return "—"
    if (Number.isFinite(value)) return value.toFixed(digits)
    return "—"
  }, [])

  // Refs for PDF export
  const tradeExecutionRef = React.useRef<HTMLDivElement>(null)
  const portfolioGreeksRef = React.useRef<HTMLDivElement>(null)
  const payoffChartRef = React.useRef<HTMLDivElement>(null)
  
  // Ref to track if expirationDate has been set from loaded strategy/daily pick
  // This prevents default expiration date from overwriting the strategy's saved date
  const expirationDateSetFromStrategyRef = React.useRef(false)

  // Load strategy if strategyId is provided
  const { data: loadedStrategy } = useQuery({
    queryKey: ["strategy", strategyId],
    queryFn: () => strategyService.get(strategyId!),
    enabled: !!strategyId,
  })

  // Mark strategy as saved if loaded from URL
  React.useEffect(() => {
    if (strategyId) {
      setIsStrategySaved(true)
    }
  }, [strategyId])

  // Load strategy data when loaded
  // This must run BEFORE the default expiration date effect to ensure correct date is set
  React.useEffect(() => {
    if (loadedStrategy) {
      setStrategyName(loadedStrategy.name)
      if (loadedStrategy.legs_json?.symbol) {
        setSymbol(loadedStrategy.legs_json.symbol)
      }
      // Load expiration_date from top level first (preferred), fallback to first leg's expiry
      // Mark that we've set expiration date from strategy to prevent default date from overwriting
      if (loadedStrategy.legs_json?.expiration_date) {
        setExpirationDate(loadedStrategy.legs_json.expiration_date)
        expirationDateSetFromStrategyRef.current = true
      } else if (loadedStrategy.legs_json?.legs && loadedStrategy.legs_json.legs.length > 0 && loadedStrategy.legs_json.legs[0].expiry) {
        // Fallback: use first leg's expiry (for backward compatibility)
        setExpirationDate(loadedStrategy.legs_json.legs[0].expiry)
        expirationDateSetFromStrategyRef.current = true
      }
      if (loadedStrategy.legs_json?.legs) {
        const loadedLegs: StrategyLegForm[] = loadedStrategy.legs_json.legs.map(
          (leg: StrategyLeg, index: number) => ({
            ...leg,
            id: `loaded-${index}-${Date.now()}`,
          })
        )
        setLegs(loadedLegs)
      }
      toast.success(`Loaded strategy: ${loadedStrategy.name}`)
    }
  }, [loadedStrategy])

  // Load daily pick strategy from sessionStorage (when navigating from Daily Picks)
  // This must run BEFORE the default expiration date effect to ensure correct date is set
  React.useEffect(() => {
    // Skip if we're loading a strategy from URL (strategyId exists)
    if (strategyId) {
      return
    }
    
    try {
      const dailyPickData = sessionStorage.getItem("dailyPickStrategy")
      if (dailyPickData) {
        const pick = JSON.parse(dailyPickData)
        if (pick.symbol) {
          setSymbol(pick.symbol)
        }
        if (pick.strategyName) {
          setStrategyName(pick.strategyName)
        }
        if (pick.legs && Array.isArray(pick.legs) && pick.legs.length > 0) {
          const loadedLegs: StrategyLegForm[] = pick.legs.map(
            (leg: StrategyLeg, index: number) => ({
              ...leg,
              id: `daily-pick-${index}-${Date.now()}`,
            })
          )
          setLegs(loadedLegs)
          // Set expiration date from first leg - Mark that we've set it to prevent default date from overwriting
          if (loadedLegs.length > 0 && loadedLegs[0].expiry) {
            setExpirationDate(loadedLegs[0].expiry)
            expirationDateSetFromStrategyRef.current = true
          }
          toast.success(`Loaded daily pick strategy: ${pick.strategyName || pick.symbol}`)
        }
        // Clear sessionStorage after loading
        sessionStorage.removeItem("dailyPickStrategy")
      }
    } catch (error) {
      console.error("Error loading daily pick strategy:", error)
      sessionStorage.removeItem("dailyPickStrategy")
    }
  }, [strategyId])

  // Fetch available expiration dates when symbol changes
  const { data: availableExpirations, isLoading: isLoadingExpirations } = useQuery({
    queryKey: ["optionExpirations", symbol],
    queryFn: () => marketService.getOptionExpirations(symbol),
    enabled: !!symbol,
    staleTime: 24 * 60 * 60 * 1000, // Cache for 24 hours
  })

  const { data: financialProfile, isLoading: isLoadingProfile } = useQuery({
    queryKey: ["financialProfile", symbol],
    queryFn: () => marketService.getFinancialProfile(symbol),
    enabled: !!symbol,
    staleTime: 10 * 60 * 1000, // Cache for 10 minutes
  })

  // Set default expiration date from available expirations
  // IMPORTANT: Do NOT set default expiration date if expirationDate has been set from loaded strategy/daily pick
  // This prevents the default date from overwriting the strategy's saved expiration date
  React.useEffect(() => {
    // Skip setting default expiration date if:
    // 1. We have a strategyId (loading strategy from URL - wait for loadedStrategy to set it)
    // 2. Expiration date has already been set from strategy/daily pick
    if (strategyId || expirationDateSetFromStrategyRef.current) {
      return
    }
    
    if (availableExpirations && availableExpirations.length > 0 && !expirationDate) {
      // Use the first (earliest) available expiration date
      setExpirationDate(availableExpirations[0])
    } else if (!availableExpirations && !expirationDate) {
      // Fallback: Calculate next Friday if no expirations available yet
      const today = new Date()
      const daysUntilFriday = (5 - today.getDay() + 7) % 7 || 7
      const nextFriday = new Date(today)
      nextFriday.setDate(today.getDate() + daysUntilFriday)
      setExpirationDate(nextFriday.toISOString().split("T")[0])
    }
  }, [availableExpirations, expirationDate, strategyId])
  
  // Reset the ref when strategyId changes (when navigating to a new strategy or away from strategy)
  React.useEffect(() => {
    if (!strategyId) {
      expirationDateSetFromStrategyRef.current = false
    }
  }, [strategyId])

  // Fetch option chain (manual refresh only - no auto polling to save API quota)
  const { data: optionChain, isLoading: isLoadingChain } = useQuery({
    queryKey: ["optionChain", symbol, expirationDate],
    queryFn: () => marketService.getOptionChain(symbol, expirationDate, false), // Default: use cache
    enabled: !!symbol && !!expirationDate,
    staleTime: 0, // No caching for option chain (always treat as stale)
    gcTime: 0, // Drop cache immediately to avoid reuse
    refetchInterval: false, // Disabled auto-refresh to save API quota
  })

  // Sync leg premiums from option chain (ensures consistency across all components)
  // If exact strike not found, uses nearest adjacent strike
  const syncLegPremiumsFromChain = React.useCallback((legsToSync: StrategyLegForm[], chain?: typeof optionChain): StrategyLegForm[] => {
    if (!chain || !chain.calls || !chain.puts) {
      return legsToSync // Return unchanged if no chain data
    }

    return legsToSync.map((leg) => {
      // Find matching option in chain
      const options = leg.type === "call" ? chain.calls : chain.puts
      
      // First try exact match (within 0.01 tolerance)
      let option = options.find((o) => {
        if (!o) return false
        const optionStrike = o.strike ?? (o as any).strike_price
        return optionStrike !== undefined && Math.abs(optionStrike - leg.strike) < 0.01
      })

      // If exact match not found, find nearest adjacent strike
      if (!option) {
        let nearestOption: typeof options[0] | undefined = undefined
        let minDistance = Infinity

        options.forEach((o) => {
          if (!o) return
          const optionStrike = o.strike ?? (o as any).strike_price
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
        // No option found (even adjacent) - keep existing premium or set to 0
        return { ...leg, premium: leg.premium || 0 }
      }

      // Get bid/ask from option chain (support multiple field names)
      const bid = Number(option.bid ?? option.bid_price ?? 0)
      const ask = Number(option.ask ?? option.ask_price ?? 0)

      // Calculate mid price as premium (consistent with payoff calculation and SmartPriceAdvisor)
      let premium = leg.premium || 0
      if (!isNaN(bid) && !isNaN(ask) && isFinite(bid) && isFinite(ask) && bid > 0 && ask > 0) {
        premium = (bid + ask) / 2
      } else if (bid > 0) {
        premium = bid // Fallback to bid if ask unavailable
      } else if (ask > 0) {
        premium = ask // Fallback to ask if bid unavailable
      }

      return {
        ...leg,
        premium: premium > 0 ? premium : (leg.premium || 0), // Keep existing if calculation fails
      }
    })
  }, [])

  // Auto-sync leg premiums when option chain updates (ensures consistency)
  React.useEffect(() => {
    if (optionChain && legs.length > 0) {
      const syncedLegs = syncLegPremiumsFromChain(legs, optionChain)
      // Only update if premiums actually changed (avoid infinite loops)
      const hasChanges = syncedLegs.some((leg, index) => {
        const originalLeg = legs[index]
        return Math.abs((leg.premium || 0) - (originalLeg.premium || 0)) > 0.001
      })
      if (hasChanges) {
        setLegs(syncedLegs)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [optionChain, syncLegPremiumsFromChain]) // Note: legs is intentionally excluded to avoid loops
  
  // Manual refresh function that forces API call
  const handleRefreshOptionChain = async () => {
    if (!symbol || !expirationDate) return
    await queryClient.fetchQuery({
      queryKey: ["optionChain", symbol, expirationDate],
      queryFn: () => marketService.getOptionChain(symbol, expirationDate, true), // force_refresh=true
    })
  }

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
    queryFn: () => marketService.getHistoricalData(symbol, 500, "day"),
    enabled: !!symbol,
    staleTime: 24 * 60 * 60 * 1000, // Cache for 24 hours
    gcTime: 24 * 60 * 60 * 1000,
    refetchOnWindowFocus: false,
  })

  type MarketCandle = { time: any; open: number; high: number; low: number; close: number; volume: number }

  const marketCandleData = React.useMemo(() => {
    if (!historicalData?.data || historicalData.data.length === 0) {
      return []
    }
    return historicalData.data
      .map((d) => {
        let timeValue: string
        if (typeof d.time === "string") {
          timeValue = d.time
        } else if (typeof d.time === "number") {
          const date = new Date(d.time * 1000)
          timeValue = date.toISOString().split("T")[0]
        } else {
          return null
        }
        const open = Number(d.open)
        const high = Number(d.high)
        const low = Number(d.low)
        const close = Number(d.close)
        if (![open, high, low, close].every((value) => Number.isFinite(value))) {
          return null
        }
        const volume = Number(d.volume ?? 0)
        return {
          time: timeValue as any,
          open,
          high,
          low,
          close,
          volume: Number.isFinite(volume) ? volume : 0,
        }
      })
      .filter((entry): entry is MarketCandle => !!entry)
  }, [historicalData])

  const handleCandleHover = React.useCallback(
    (value: { time: any } | null) => {
      if (!value) {
        setHoveredCandleTime(null)
        return
      }
      const timeValue = typeof value.time === "string" ? value.time : String(value.time)
      setHoveredCandleTime(timeValue)
    },
    []
  )

  const latestClosePrice = React.useMemo(() => {
    if (marketCandleData.length === 0) return null
    return marketCandleData[marketCandleData.length - 1]?.close ?? null
  }, [marketCandleData])

  // Update spot price from quote if chain doesn't have it
  // Note: Quote now returns inferred price (cost-efficient)
  React.useEffect(() => {
    if (stockQuote?.data?.price && !spotPrice) {
      setSpotPrice(stockQuote.data.price)
    }
  }, [stockQuote, spotPrice])
  
  // Determine if price is estimated (from quote inference)

  // Handle symbol selection
  const handleSymbolSelect = async (selectedSymbol: string) => {
    setSymbol(selectedSymbol)
    // Reset saved status when symbol changes (unless it's the same symbol)
    // Even if we have a strategyId, changing symbol modifies the strategy, so reset saved status
    if (selectedSymbol !== symbol && isStrategySaved) {
      setIsStrategySaved(false)
    }
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
    
    const legsWithIds: StrategyLegForm[] = templateLegs.map((leg: { type: "call" | "put"; action: "buy" | "sell"; strike: number; quantity: number; expiry: string }, index: number) => ({
      ...leg,
      id: `template-${Date.now()}-${index}`,
      premium: 0, // Initialize to 0, will be synced from optionChain
    }))
    
    // Sync premiums from option chain to ensure consistency with Trade Execution and Option Chain
    const syncedLegs = syncLegPremiumsFromChain(legsWithIds, optionChain || undefined)
    setLegs(syncedLegs)
    setStrategyName(template.name)
    
    // IMPORTANT: Reset saved status when loading a template (user must save before using AI features)
    // Even if we have a strategyId, loading a template changes the strategy content, so reset saved status
    setIsStrategySaved(false)
    
    if (!optionChain) {
      toast.info(`Loaded "${template.name}" template. Prices will sync when option chain loads.`)
    } else {
      toast.success(`Loaded "${template.name}" template with current market prices`)
    }
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
        
        // First try exact match (within 0.01 tolerance)
        let option = options.find((o) => {
          if (!o) return false
          const optionStrike = o.strike ?? o.strike_price
          return optionStrike !== undefined && Math.abs(optionStrike - leg.strike) < 0.01
        })

        // If exact match not found, find nearest adjacent strike
        if (!option) {
          let nearestOption: typeof options[0] | undefined = undefined
          let minDistance = Infinity

          options.forEach((o) => {
            if (!o) return
            const optionStrike = o.strike ?? o.strike_price
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
    // Reset saved status when legs are modified
    // Even if we have a strategyId, modifying legs changes the strategy, so reset saved status
    if (isStrategySaved) {
      setIsStrategySaved(false)
    }
  }

  const removeLeg = (id: string) => {
    setLegs(legs.filter((leg) => leg.id !== id))
    // Reset saved status when legs are modified
    // Even if we have a strategyId, modifying legs changes the strategy, so reset saved status
    if (isStrategySaved) {
      setIsStrategySaved(false)
    }
  }

  const updateLeg = (id: string, updates: Partial<StrategyLegForm>) => {
    setLegs(legs.map((leg) => (leg.id === id ? { ...leg, ...updates } : leg)))
    // Reset saved status when legs are modified
    // Even if we have a strategyId, modifying legs changes the strategy, so reset saved status
    if (isStrategySaved) {
      setIsStrategySaved(false)
    }
  }

  // Check AI quota availability
  const aiQuotaRemaining = user?.daily_ai_quota 
    ? Math.max(0, (user.daily_ai_quota || 0) - (user.daily_ai_usage || 0))
    : 0
  const requiredAiQuota = useMultiAgentReport ? 5 : 1
  const hasAiQuota = aiQuotaRemaining >= requiredAiQuota

  const estimatedInputSizeKb = React.useMemo(() => {
    try {
      const estimatePayload = {
        option_chain: optionChain || undefined,
        historical_prices: historicalData?.data || undefined,
        legs,
      }
      const raw = JSON.stringify(estimatePayload)
      return Math.round(raw.length / 1024)
    } catch {
      return null
    }
  }, [optionChain, historicalData?.data, legs])

  const handleAnalyzeClick = () => {
    // Check if strategy is saved
    // Even if we have a strategyId, if isStrategySaved is false, the strategy has been modified and needs to be saved
    if (!isStrategySaved) {
      toast.error("Please save your strategy first before using AI analysis", {
        duration: 4000,
        description: "Click the 'Save' button to save your strategy, then you can use AI features.",
      })
      return
    }

    // Always show confirmation dialog (Deep Research is the only mode)
    setDeepResearchConfirmOpen(true)
  }

  const handleConfirmDeepResearch = () => {
    if (!hasAiQuota) {
      toast.error("Daily AI quota insufficient", {
        duration: 5000,
        description: `Need ${requiredAiQuota} credits. Remaining: ${aiQuotaRemaining}. Quota resets at midnight UTC.`,
      })
      return
    }
    setDeepResearchConfirmOpen(false)
    analyzeMutation.mutate()
  }

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      if (!optionChain || legs.length === 0) {
        throw new Error("Please add at least one leg and fetch option chain")
      }

      setIsAnalyzing(true)
      try {
        // Calculate portfolio Greeks (strategy-level Greeks)
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
          const direct = (option as any)[greekName]
          if (direct !== undefined && direct !== null) {
            const value = Number(direct)
            if (!isNaN(value) && isFinite(value)) return value
          }
          const greeks = (option as any).greeks
          if (greeks && typeof greeks === "object") {
            const nested = greeks[greekName]
            if (nested !== undefined && nested !== null) {
              const value = Number(nested)
              if (!isNaN(value) && isFinite(value)) return value
            }
          }
          return undefined
        }

        const calculatePortfolioGreeks = () => {
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

            // For puts, delta is negative; for sells, flip the sign
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

          return { delta: totalDelta, gamma: totalGamma, theta: totalTheta, vega: totalVega, rho: totalRho }
        }

        const portfolioGreeks = calculatePortfolioGreeks()

        // Calculate trade execution summary
        const calculateTradeExecution = () => {
          let netCost = 0
          let totalPremium = 0
          let totalQuantity = 0

          const executionDetails = legs.map((leg) => {
            const premium = leg.premium || 0
            const cost = leg.action === "buy" ? premium * leg.quantity : -premium * leg.quantity
            netCost += cost
            totalPremium += premium * leg.quantity
            totalQuantity += leg.quantity

            return {
              type: leg.type,
              action: leg.action,
              strike: leg.strike,
              quantity: leg.quantity,
              premium: premium,
              cost: cost,
              delta: leg.delta,
              gamma: leg.gamma,
              theta: leg.theta,
              vega: leg.vega,
              implied_volatility: leg.implied_volatility || leg.implied_vol,
            }
          })

          return {
            net_cost: netCost,
            total_premium: totalPremium,
            total_quantity: totalQuantity,
            legs: executionDetails,
          }
        }

        const tradeExecution = calculateTradeExecution()

        // Calculate strategy metrics from payoff data
        const calculateStrategyMetrics = () => {
          if (payoffData.length === 0) {
            return {
              max_profit: 0,
              max_loss: 0,
              breakeven_points: [],
              profit_zones: [],
            }
          }

          const profits = payoffData.map((p) => p.profit)
          const maxProfit = Math.max(...profits)
          const maxLoss = Math.min(...profits)

          // Find breakeven points (where profit crosses zero)
          const breakevenPoints: number[] = []
          for (let i = 0; i < payoffData.length - 1; i++) {
            if (
              (payoffData[i].profit <= 0 && payoffData[i + 1].profit >= 0) ||
              (payoffData[i].profit >= 0 && payoffData[i + 1].profit <= 0)
            ) {
              // Linear interpolation to find exact breakeven price
              const p1 = payoffData[i]
              const p2 = payoffData[i + 1]
              const breakevenPrice = p1.price + ((0 - p1.profit) / (p2.profit - p1.profit)) * (p2.price - p1.price)
              breakevenPoints.push(breakevenPrice)
            }
          }

          // Find profit zones (price ranges where profit > 0)
          const profitZones: Array<{ start: number; end: number }> = []
          let currentZoneStart: number | null = null
          for (const point of payoffData) {
            if (point.profit > 0) {
              if (currentZoneStart === null) {
                currentZoneStart = point.price
              }
            } else {
              if (currentZoneStart !== null) {
                profitZones.push({ start: currentZoneStart, end: point.price })
                currentZoneStart = null
              }
            }
          }
          if (currentZoneStart !== null && payoffData.length > 0) {
            profitZones.push({ start: currentZoneStart, end: payoffData[payoffData.length - 1].price })
          }

          return {
            max_profit: maxProfit,
            max_loss: maxLoss,
            breakeven_points: breakevenPoints,
            profit_zones: profitZones,
          }
        }

        const strategyMetrics = calculateStrategyMetrics()

        // Create a background task with strategy summary data (NOT the full option chain)
          const task = await taskService.createTask({
            task_type: useMultiAgentReport ? "multi_agent_report" : "ai_report",
          metadata: {
            use_deep_research: useDeepResearch,
              use_multi_agent: useMultiAgentReport,
            option_chain: optionChain || undefined,
            strategy_summary: {
              // Basic strategy info
              symbol,
              strategy_name: strategyName || "Custom Strategy",
              spot_price: optionChain?.spot_price || spotPrice,
              expiration_date: expirationDate,
              
              // Strategy legs with all details
              legs: legs.map(({ id, ...leg }) => {
                // Include all leg details (Greeks, IV, bid/ask already enriched from option chain)
                return {
                  type: leg.type,
                  action: leg.action,
                  strike: leg.strike,
                  quantity: leg.quantity,
                  premium: leg.premium,
                  expiry: leg.expiry,
                  delta: leg.delta,
                  gamma: leg.gamma,
                  theta: leg.theta,
                  vega: leg.vega,
                  rho: leg.rho,
                  implied_volatility: leg.implied_volatility || leg.implied_vol,
                  bid: leg.bid,
                  ask: leg.ask,
                  volume: leg.volume,
                  open_interest: leg.open_interest,
                }
              }),
              
              // Portfolio Greeks (combined strategy-level Greeks)
              portfolio_greeks: portfolioGreeks,
              
              // Trade execution summary
              trade_execution: tradeExecution,
              
              // Strategy metrics from payoff analysis
              strategy_metrics: strategyMetrics,
              
              // Historical price data (full series for agent analysis)
              historical_prices: historicalData?.data || [],
              historical_source: historicalData?._source,
              
              // Payoff diagram data (key points only, not full 200 points)
              payoff_summary: {
                max_profit_price: payoffData.find((p) => p.profit === strategyMetrics.max_profit)?.price,
                max_loss_price: payoffData.find((p) => p.profit === strategyMetrics.max_loss)?.price,
                // Include a sample of key payoff points (not all 200 points)
                key_points: payoffData.filter((_, index) => index % 20 === 0 || 
                  payoffData[index - 1]?.profit * payoffData[index]?.profit < 0), // Include points near zero crossings
              },
            },
          },
        })
        return task
      } finally {
        setIsAnalyzing(false)
      }
    },
    onSuccess: () => {
      // Invalidate tasks query to refresh the list
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
      
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

  // Export full strategy report as PDF functionality removed (not currently used)

  const saveStrategyMutation = useMutation({
    mutationFn: async () => {
      if (!strategyName || legs.length === 0) {
        throw new Error("Please provide a strategy name and add legs")
      }

      return strategyService.create({
        name: strategyName,
        legs_json: {
          symbol,
          expiration_date: expirationDate, // Save expiration date at top level for consistency
          legs: legs.map(({ id, ...leg }) => leg),
        },
      })
    },
    onSuccess: (data) => {
      toast.success("Strategy saved successfully!")
      setIsStrategySaved(true)
      // Update URL with strategy ID if returned
      if (data?.id) {
        navigate(`/strategy-lab?strategy=${data.id}`, { replace: true })
      }
      // Don't clear strategy name and legs - keep them for AI analysis
      queryClient.invalidateQueries({ queryKey: ["strategies"] })
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail || "Failed to save strategy"
      )
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Strategy Lab</h1>
          <p className="text-muted-foreground">
            Build and analyze option strategies with AI-powered insights
          </p>
        </div>
        <Card className="border-primary/40 bg-primary/5">
          <CardContent className="flex flex-wrap items-center justify-between gap-4 py-4">
            <div className="space-y-1">
              <div className="text-xs uppercase tracking-wide text-muted-foreground">
                Current Symbol
              </div>
              <div className="text-2xl font-semibold">{symbol || "—"}</div>
              <div className="text-sm text-muted-foreground">
                {financialProfile?.profile?.companyName ||
                  financialProfile?.profile?.name ||
                  "—"}
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-6 text-sm">
              <div className="space-y-1">
                <div className="text-xs uppercase tracking-wide text-muted-foreground">
                  Exchange
                </div>
                <div className="font-semibold">
                  {financialProfile?.profile?.exchangeShortName ||
                    financialProfile?.profile?.exchange ||
                    "—"}
                </div>
              </div>
              <div className="space-y-1">
                <div className="text-xs uppercase tracking-wide text-muted-foreground">
                  Price
                </div>
                <div className="font-semibold">
                  {latestClosePrice ? `$${latestClosePrice.toFixed(2)}` : "—"}
                </div>
              </div>
              <div className="space-y-1">
                <div className="text-xs uppercase tracking-wide text-muted-foreground">
                  Source
                </div>
                <div className="font-semibold">
                  {stockQuote?.price_source === "api"
                    ? "Real-time"
                    : stockQuote?.price_source === "inferred"
                      ? "Estimated"
                      : "Unavailable"}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* New Layout: Left-Right Split */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Left: Strategy Builder (1 column) */}
        <div className="lg:col-span-1 space-y-4">
          {/* Smart Price Advisor - Pro Feature */}
          {symbol && expirationDate && legs.length > 0 && (
            <div ref={tradeExecutionRef}>
              <SmartPriceAdvisor
                symbol={symbol}
                legs={legs}
                expirationDate={expirationDate}
                optionChain={optionChain || undefined}
                onRefresh={() => {
                  handleRefreshOptionChain()
                  toast.info("Refreshing market data...")
                }}
                isRefreshing={isLoadingChain}
              />
            </div>
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
                  {availableExpirations && availableExpirations.length > 0 ? (
                    <Select
                      value={expirationDate}
                      onValueChange={(newDate) => {
                        // Reset saved status when expiration date changes (unless it's the same date)
                        // Even if we have a strategyId, changing expiration date modifies the strategy, so reset saved status
                        if (newDate !== expirationDate && isStrategySaved) {
                          setIsStrategySaved(false)
                        }
                        setExpirationDate(newDate)
                      }}
                      disabled={isLoadingExpirations}
                    >
                      <SelectTrigger id="expiry" className="w-full">
                        <SelectValue placeholder="Select an expiration date" />
                      </SelectTrigger>
                      <SelectContent className="max-h-[300px]">
                        {availableExpirations.map((date) => {
                          const dateObj = new Date(date)
                          const isSelected = date === expirationDate
                          const daysUntilExpiry = Math.ceil((dateObj.getTime() - new Date().getTime()) / (1000 * 60 * 60 * 24))
                          
                          return (
                            <SelectItem 
                              key={date} 
                              value={date}
                              className={isSelected ? "bg-accent" : ""}
                            >
                              <div className="flex items-center justify-between w-full">
                                <div className="flex flex-col">
                                  <span className="font-medium">
                                    {dateObj.toLocaleDateString('en-US', { 
                                      weekday: 'short', 
                                      month: 'short', 
                                      day: 'numeric',
                                      year: 'numeric'
                                    })}
                                  </span>
                                  <span className="text-xs text-muted-foreground">
                                    {daysUntilExpiry > 0 ? `${daysUntilExpiry} days` : daysUntilExpiry === 0 ? 'Today' : 'Expired'}
                                  </span>
                                </div>
                              </div>
                            </SelectItem>
                          )
                        })}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Input
                      id="expiry"
                      type="date"
                      value={expirationDate}
                      onChange={(e) => {
                        const newDate = e.target.value
                        // Reset saved status when expiration date changes (unless it's the same date)
                        // Even if we have a strategyId, changing expiration date modifies the strategy, so reset saved status
                        if (newDate !== expirationDate && isStrategySaved) {
                          setIsStrategySaved(false)
                        }
                        setExpirationDate(newDate)
                      }}
                      min={new Date().toISOString().split("T")[0]}
                      max={new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().split("T")[0]}
                      placeholder="Loading available dates..."
                      disabled={isLoadingExpirations}
                    />
                  )}
                </div>
              </div>

              {isLoadingChain && (
                <div className="text-sm text-muted-foreground">
                  Loading option chain...
                </div>
              )}

              {optionChain && (
                <div className="text-sm text-muted-foreground">
                  <span>
                    Last Close: {latestClosePrice ? `$${latestClosePrice.toFixed(2)}` : "—"}
                    <span
                      className="ml-2 text-blue-600 cursor-help"
                      title="Price derived from latest historical close"
                    >
                      ℹ️
                    </span>
                  </span>
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
                        <Select
                          value={leg.type}
                          onValueChange={(value) =>
                            updateLeg(leg.id, {
                              type: value as "call" | "put",
                            })
                          }
                        >
                          <SelectTrigger className="w-full">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="call">Call</SelectItem>
                            <SelectItem value="put">Put</SelectItem>
                          </SelectContent>
                        </Select>
                        <Select
                          value={leg.action}
                          onValueChange={(value) =>
                            updateLeg(leg.id, {
                              action: value as "buy" | "sell",
                            })
                          }
                        >
                          <SelectTrigger className="w-full">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="buy">Buy</SelectItem>
                            <SelectItem value="sell">Sell</SelectItem>
                          </SelectContent>
                        </Select>
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

              {/* Deep Research Mode Info */}
              <div className={`flex items-center gap-3 p-3 rounded-lg border ${
                hasAiQuota 
                  ? "bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800"
                  : "bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800"
              }`}>
                <div className="flex items-center gap-2 flex-1">
                  <Sparkles className={`h-5 w-5 ${
                    hasAiQuota 
                      ? "text-blue-600 dark:text-blue-400"
                      : "text-red-600 dark:text-red-400"
                  }`} />
                  <div className="flex-1">
                    <Label className={`text-sm font-semibold ${
                      hasAiQuota 
                        ? "text-blue-900 dark:text-blue-100"
                        : "text-red-900 dark:text-red-100"
                    }`}>
                      Deep Research Analysis
                    </Label>
                    <p className={`text-xs mt-0.5 ${
                      hasAiQuota 
                        ? "text-blue-700 dark:text-blue-300"
                        : "text-red-700 dark:text-red-300"
                    }`}>
                      ⏱️ 3-5 minutes • Multi-step comprehensive analysis
                      {user?.daily_ai_quota !== undefined ? (
                        hasAiQuota ? (
                          <span className="ml-2 font-semibold">
                            • Quota: {aiQuotaRemaining}/{user.daily_ai_quota} remaining
                          </span>
                        ) : (
                          <span className="ml-2 font-semibold">
                            • Quota exceeded: {user.daily_ai_usage || 0}/{user.daily_ai_quota} used (resets at midnight UTC)
                          </span>
                        )
                      ) : null}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex gap-2">
                <Button
                  onClick={handleAnalyzeClick}
                  disabled={isAnalyzing || legs.length === 0 || !optionChain || !isStrategySaved || !hasAiQuota}
                  className="flex-1 font-semibold"
                  variant="default"
                  title={
                    !isStrategySaved 
                      ? "Please save your strategy first" 
                      : !hasAiQuota 
                        ? `Daily quota exceeded (${user?.daily_ai_usage || 0}/${user?.daily_ai_quota || 0}). Resets at midnight UTC.`
                        : undefined
                  }
                >
                  <Sparkles className="h-4 w-4 mr-2" />
                  {isAnalyzing ? "Analyzing..." : "Analyze with AI"}
                  {user?.daily_ai_quota !== undefined && (
                    <span className={`ml-2 text-xs ${hasAiQuota ? "opacity-75" : "text-red-600 dark:text-red-400 font-semibold"}`}>
                      ({aiQuotaRemaining}/{user.daily_ai_quota} left)
                    </span>
                  )}
                </Button>
                <Input
                  placeholder="Strategy name"
                  value={strategyName}
                  onChange={(e) => {
                    setStrategyName(e.target.value)
                    // Reset saved status when strategy name changes (user is editing)
                    // Even if we have a strategyId, changing name modifies the strategy, so reset saved status
                    if (isStrategySaved) {
                      setIsStrategySaved(false)
                    }
                  }}
                  className="flex-1"
                />
                <Button
                  onClick={() => saveStrategyMutation.mutate()}
                  disabled={!strategyName || legs.length === 0 || saveStrategyMutation.isPending}
                  variant="secondary"
                  className="font-semibold min-w-[80px]"
                  title={(!strategyName || legs.length === 0) ? "Please provide a strategy name and add legs" : "Save your strategy to enable AI features"}
                >
                  {saveStrategyMutation.isPending ? "Saving..." : "Save"}
                </Button>
              </div>
              {!isStrategySaved && (
                <div className="mt-2 text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1">
                  <span>⚠️</span>
                  <span>Please save your strategy first to use AI analysis and AI chart generation</span>
                </div>
              )}
            </CardContent>
          </Card>

        </div>

        {/* Right: Charts and Option Chain (2 columns) */}
        <div className="lg:col-span-2 space-y-4">
          {/* Portfolio Greeks - Compact at top */}
          {legs.length > 0 && (
            <div ref={portfolioGreeksRef}>
              <StrategyGreeks legs={legs} optionChain={optionChain} />
            </div>
          )}

          {/* Data Panel: Option Chain / Market / Fundamentals / Technicals */}
          <Card>
            <CardHeader>
              <CardTitle>Data Panel</CardTitle>
              <CardDescription>
                Option chain, fundamentals, and technical indicators
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="option-chain" className="w-full">
                <TabsList className="grid w-full grid-cols-4">
                  <TabsTrigger value="option-chain">Option Chain</TabsTrigger>
                  <TabsTrigger value="market">Market</TabsTrigger>
                  <TabsTrigger value="fundamentals">Fundamentals</TabsTrigger>
                  <TabsTrigger value="technicals">Technicals</TabsTrigger>
                </TabsList>
                <TabsContent value="option-chain" className="mt-4">
                  {optionChain && optionChain.calls.length > 0 ? (
                    <OptionChainVisualization
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
                        // Reset saved status when legs are modified (unless loaded from URL)
                        // Reset saved status when adding option from chain
                        // Even if we have a strategyId, adding options modifies the strategy, so reset saved status
                        if (isStrategySaved) {
                          setIsStrategySaved(false)
                        }
                        toast.success(`Added ${type} option at strike $${optionStrike.toFixed(2)}`)
                      }}
                    />
                  ) : (
                    <div className="flex h-[220px] items-center justify-center text-muted-foreground">
                      {symbol ? "Loading option chain..." : "Select a symbol to view option chain"}
                    </div>
                  )}
                </TabsContent>
                <TabsContent value="market" className="mt-4">
                  {marketCandleData.length > 0 ? (
                    <div className="space-y-4">
                      <div className="text-sm text-muted-foreground">
                        Historical candlestick chart (max available) for {symbol}
                        {historicalData?._source ? ` · ${historicalData._source}` : ""}
                      </div>
                      <CandlestickChart
                        data={marketCandleData}
                        height={360}
                        watermarkText={symbol}
                        onHover={handleCandleHover}
                      />
                      <div className="rounded-lg border border-border">
                        <div className="grid grid-cols-5 gap-2 border-b border-border px-4 py-2 text-xs font-semibold text-muted-foreground">
                          <div>Date</div>
                          <div>Open</div>
                          <div>High</div>
                          <div>Low</div>
                          <div>Close</div>
                        </div>
                        <div className="max-h-[240px] overflow-y-auto">
                          {marketCandleData
                            .slice()
                            .reverse()
                            .map((row) => (
                              <div
                                key={`${symbol}-${row.time}`}
                                className={`grid grid-cols-5 gap-2 border-b border-border/60 px-4 py-2 text-sm last:border-0 ${
                                  hoveredCandleTime === String(row.time)
                                    ? "bg-blue-50/70 dark:bg-blue-900/20"
                                    : row.close >= row.open
                                      ? "text-emerald-700 dark:text-emerald-300"
                                      : "text-rose-700 dark:text-rose-300"
                                }`}
                              >
                                <div>{String(row.time)}</div>
                                <div>${row.open.toFixed(2)}</div>
                                <div>${row.high.toFixed(2)}</div>
                                <div>${row.low.toFixed(2)}</div>
                                <div>${row.close.toFixed(2)}</div>
                              </div>
                            ))}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex h-[220px] items-center justify-center text-muted-foreground">
                      {symbol ? "Loading market data..." : "Select a symbol to view market data"}
                    </div>
                  )}
                </TabsContent>
                <TabsContent value="fundamentals" className="mt-4">
                  {isLoadingProfile ? (
                    <div className="flex h-[220px] items-center justify-center text-muted-foreground">
                      Loading fundamentals...
                    </div>
                  ) : (
                    <div className="grid gap-4 md:grid-cols-2">
                      {financialProfile?.error && (
                        <div className="md:col-span-2 text-sm text-amber-600 dark:text-amber-400">
                          Fundamentals data is limited: {String(financialProfile.error)}
                        </div>
                      )}
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-base">Valuation</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2 text-sm">
                          <div className="flex items-center justify-between">
                            <span>PE</span>
                            <span>
                              {formatMetric(
                                getLatestMetricByKeys(financialProfile?.ratios?.valuation, [
                                  "PE",
                                  "P/E",
                                  "Price to Earnings Ratio",
                                  "Price/Earnings",
                                ])
                              )}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>PB</span>
                            <span>
                              {formatMetric(
                                getLatestMetricByKeys(financialProfile?.ratios?.valuation, [
                                  "PB",
                                  "P/B",
                                  "Price to Book Ratio",
                                  "Price/Book",
                                ])
                              )}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>DCF</span>
                            <span>{formatMetric(financialProfile?.valuation?.dcf?.value ?? null)}</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>DDM</span>
                            <span>{formatMetric(financialProfile?.valuation?.ddm?.value ?? null)}</span>
                          </div>
                        </CardContent>
                      </Card>
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-base">Profitability</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2 text-sm">
                          <div className="flex items-center justify-between">
                            <span>ROE</span>
                            <span>
                              {formatMetric(
                                getLatestMetricByKeys(financialProfile?.ratios?.profitability, [
                                  "ROE",
                                  "Return on Equity",
                                  "Return on Equity Ratio",
                                ])
                              )}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>ROA</span>
                            <span>
                              {formatMetric(
                                getLatestMetricByKeys(financialProfile?.ratios?.profitability, [
                                  "ROA",
                                  "Return on Assets",
                                  "Return on Assets Ratio",
                                ])
                              )}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>Net Margin</span>
                            <span>
                              {formatMetric(
                                getLatestMetricByKeys(financialProfile?.ratios?.profitability, [
                                  "Net Profit Margin",
                                  "Net Margin",
                                ])
                              )}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>Health Score</span>
                            <span>{formatMetric(financialProfile?.analysis?.health_score?.overall ?? null, 0)}</span>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  )}
                </TabsContent>
                <TabsContent value="technicals" className="mt-4">
                  {isLoadingProfile ? (
                    <div className="flex h-[220px] items-center justify-center text-muted-foreground">
                      Loading technical indicators...
                    </div>
                  ) : (
                    <div className="grid gap-4 md:grid-cols-2">
                      {financialProfile?.error && (
                        <div className="md:col-span-2 text-sm text-amber-600 dark:text-amber-400">
                          Technical indicators are limited: {String(financialProfile.error)}
                        </div>
                      )}
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-base">Indicators</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2 text-sm">
                          <div className="flex items-center justify-between">
                            <span>RSI</span>
                            <span>
                              {formatMetric(
                                getLatestMetricByKeys(
                                  financialProfile?.technical_indicators?.rsi ||
                                    financialProfile?.technical_indicators?.momentum,
                                  ["RSI"]
                                )
                              )}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>MACD</span>
                            <span>
                              {formatMetric(
                                getLatestMetricByKeys(
                                  financialProfile?.technical_indicators?.macd ||
                                    financialProfile?.technical_indicators?.macd_line ||
                                    financialProfile?.technical_indicators?.momentum,
                                  ["MACD", "MACD Line"]
                                )
                              )}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>SMA 20</span>
                            <span>
                              {formatMetric(
                                getLatestMetricByKeys(
                                  financialProfile?.technical_indicators?.sma,
                                  ["SMA_20", "SMA 20"]
                                )
                              )}
                            </span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>ADX</span>
                            <span>
                              {formatMetric(
                                getLatestMetricByKeys(financialProfile?.technical_indicators?.adx, ["ADX"])
                              )}
                            </span>
                          </div>
                        </CardContent>
                      </Card>
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-base">Signals</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-2 text-sm">
                          <div className="flex items-center justify-between">
                            <span>RSI Signal</span>
                            <span>{financialProfile?.analysis?.technical_signals?.rsi ?? "—"}</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>MACD Signal</span>
                            <span>{financialProfile?.analysis?.technical_signals?.macd ?? "—"}</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span>Health Category</span>
                            <span>{financialProfile?.analysis?.health_score?.category ?? "—"}</span>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>

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
                  <TabsTrigger value="ai-chart">AI Chart</TabsTrigger>
                </TabsList>
                <TabsContent value="payoff" className="mt-4">
                  {payoffData.length > 0 ? (
                    <div ref={payoffChartRef}>
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
                <TabsContent value="ai-chart" className="mt-4">
                  {!isStrategySaved ? (
                    <Card>
                      <CardContent className="py-12 text-center">
                        <div className="flex flex-col items-center gap-4">
                          <div className="text-amber-600 dark:text-amber-400 text-4xl">⚠️</div>
                          <div>
                            <h3 className="text-lg font-semibold mb-2">Save Strategy First</h3>
                            <p className="text-sm text-muted-foreground mb-4">
                              Please save your strategy using the "Save" button above before generating AI charts.
                            </p>
                            <p className="text-xs text-muted-foreground">
                              This ensures your strategy is properly stored and can be used for AI analysis.
                            </p>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ) : (
                    <AIChartTab
                      isStrategySaved={isStrategySaved}
                      strategyId={strategyId}
                      strategySummary={
                        legs.length > 0 && optionChain
                          ? {
                              symbol,
                              strategy_name: strategyName || "Custom Strategy",
                              spot_price: optionChain?.spot_price || spotPrice || 0,
                              expiration_date: expirationDate,
                              legs: legs.map(({ id, ...leg }) => {
                                // Enrich leg with Greeks and IV from option chain
                                const options = leg.type === "call" ? optionChain?.calls : optionChain?.puts
                                const option = options?.find((o) => {
                                  const optionStrike = o.strike ?? (o as any).strike_price
                                  return optionStrike !== undefined && Math.abs(optionStrike - leg.strike) < 0.01
                                })
                                
                                const enrichedLeg: StrategyLeg & Record<string, any> = { ...leg }
                                if (option) {
                                  if (option.delta !== undefined) enrichedLeg.delta = option.delta
                                  if (option.gamma !== undefined) enrichedLeg.gamma = option.gamma
                                  if (option.theta !== undefined) enrichedLeg.theta = option.theta
                                  if (option.vega !== undefined) enrichedLeg.vega = option.vega
                                  if (option.rho !== undefined) enrichedLeg.rho = option.rho
                                  if (option.implied_volatility !== undefined) enrichedLeg.implied_volatility = option.implied_volatility
                                  if (option.implied_vol !== undefined) enrichedLeg.implied_vol = option.implied_vol
                                  if (option.bid !== undefined) enrichedLeg.bid = option.bid
                                  if (option.ask !== undefined) enrichedLeg.ask = option.ask
                                  if (option.volume !== undefined) enrichedLeg.volume = option.volume
                                  if (option.open_interest !== undefined) enrichedLeg.open_interest = option.open_interest
                                }
                                return enrichedLeg
                              }),
                              portfolio_greeks: (() => {
                                // Calculate portfolio Greeks
                                let totalDelta = 0, totalGamma = 0, totalTheta = 0, totalVega = 0, totalRho = 0
                                legs.forEach((leg) => {
                                  const delta = leg.delta ?? 0
                                  const gamma = leg.gamma ?? 0
                                  const theta = leg.theta ?? 0
                                  const vega = leg.vega ?? 0
                                  const rho = leg.rho ?? 0
                                  const sign = leg.action === "buy" ? 1 : -1
                                  const multiplier = leg.type === "put" ? -1 : 1
                                  totalDelta += delta * sign * multiplier * leg.quantity
                                  totalGamma += gamma * sign * leg.quantity
                                  totalTheta += theta * sign * leg.quantity
                                  totalVega += vega * sign * leg.quantity
                                  totalRho += rho * sign * multiplier * leg.quantity
                                })
                                return { delta: totalDelta, gamma: totalGamma, theta: totalTheta, vega: totalVega, rho: totalRho }
                              })(),
                              trade_execution: (() => {
                                // Calculate trade execution summary
                                let netCost = 0
                                return {
                                  net_cost: legs.reduce((sum, leg) => {
                                    const premium = leg.premium || 0
                                    const cost = leg.action === "buy" ? premium * leg.quantity : -premium * leg.quantity
                                    netCost += cost
                                    return sum
                                  }, 0),
                                  legs: legs.map((leg) => ({
                                    type: leg.type,
                                    action: leg.action,
                                    strike: leg.strike,
                                    quantity: leg.quantity,
                                    premium: leg.premium,
                                  })),
                                }
                              })(),
                              strategy_metrics: (() => {
                                // Calculate strategy metrics from payoff data
                                if (payoffData.length === 0) {
                                  return { max_profit: 0, max_loss: 0, breakeven_points: [], profit_zones: [] }
                                }
                                const profits = payoffData.map((p) => p.profit)
                                const maxProfit = Math.max(...profits)
                                const maxLoss = Math.min(...profits)
                                const breakevenPoints: number[] = []
                                for (let i = 0; i < payoffData.length - 1; i++) {
                                  if (
                                    (payoffData[i].profit <= 0 && payoffData[i + 1].profit >= 0) ||
                                    (payoffData[i].profit >= 0 && payoffData[i + 1].profit <= 0)
                                  ) {
                                    const p1 = payoffData[i]
                                    const p2 = payoffData[i + 1]
                                    const breakevenPrice = p1.price + ((0 - p1.profit) / (p2.profit - p1.profit)) * (p2.price - p1.price)
                                    breakevenPoints.push(breakevenPrice)
                                  }
                                }
                                return { max_profit: maxProfit, max_loss: maxLoss, breakeven_points: breakevenPoints }
                              })(),
                            }
                          : undefined
                      }
                    />
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

      {/* Deep Research Confirmation Dialog */}
      <Dialog open={deepResearchConfirmOpen} onOpenChange={setDeepResearchConfirmOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              AI Analysis Confirmation
            </DialogTitle>
            <DialogDescription className="text-base">
              This will start a comprehensive Deep Research analysis of your strategy. Please review the details below.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <div className="space-y-4">
              {/* Quota Status */}
              {user?.daily_ai_quota && (
                <div className={`flex items-start gap-3 p-3 rounded-lg border ${
                  hasAiQuota
                    ? "bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800"
                    : "bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800"
                }`}>
                  {hasAiQuota ? (
                    <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5 shrink-0" />
                  ) : (
                    <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5 shrink-0" />
                  )}
                  <div>
                    <p className={`font-semibold text-sm ${
                      hasAiQuota
                        ? "text-green-900 dark:text-green-100"
                        : "text-red-900 dark:text-red-100"
                    }`}>
                      {hasAiQuota
                        ? `✅ Quota Available: ${aiQuotaRemaining} of ${user.daily_ai_quota} remaining (need ${requiredAiQuota})`
                        : `❌ Quota Insufficient: ${aiQuotaRemaining} remaining (need ${requiredAiQuota})`
                      }
                    </p>
                    {!hasAiQuota && (
                      <p className="text-sm text-red-700 dark:text-red-300 mt-1">
                        Quota resets at midnight UTC
                      </p>
                    )}
                  </div>
                </div>
              )}
              <div className="flex items-start gap-3 p-3 bg-amber-50 dark:bg-amber-950/30 rounded-lg border border-amber-200 dark:border-amber-800">
                <AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
                <div>
                  <p className="font-semibold text-sm text-amber-900 dark:text-amber-100">
                    ⚠️ Important: Processing Time & AI Credits
                  </p>
                  <p className="text-sm text-amber-800 dark:text-amber-200 mt-1">
                    This analysis will take <strong>3-5 minutes</strong> and will consume <strong>AI credits</strong>. 
                    The process cannot be cancelled once started. Please ensure you have sufficient credits available.
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-between rounded-lg border border-border px-3 py-3">
                <div>
                  <p className="font-medium text-sm">Multi-Agent Report</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    Use 5 specialized agents for deeper analysis (costs 5 credits).
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-muted-foreground">Off</span>
                  <Switch
                    checked={useMultiAgentReport}
                    onCheckedChange={setUseMultiAgentReport}
                  />
                  <span className="text-xs text-muted-foreground">On</span>
                </div>
              </div>

              {estimatedInputSizeKb !== null && (
                <div className="text-xs text-muted-foreground">
                  Estimated input size: {estimatedInputSizeKb} KB
                  {estimatedInputSizeKb > 1200 ? " · Large input may hit model limits" : ""}
                </div>
              )}
              
              <div className="flex items-start gap-3">
                <div className="rounded-full bg-blue-100 dark:bg-blue-900 p-2 mt-0.5 shrink-0">
                  <Clock className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <p className="font-medium text-sm">⏱️ Estimated Time: 3-5 minutes</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    The analysis uses a multi-step agentic workflow (Plan → Research → Synthesize) to provide comprehensive insights.
                  </p>
                </div>
              </div>
              
              <div className="flex items-start gap-3">
                <div className="rounded-full bg-green-100 dark:bg-green-900 p-2 mt-0.5 shrink-0">
                  <Sparkles className="h-4 w-4 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <p className="font-medium text-sm">🔍 Enhanced Research Features</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Includes Google Search for latest news, IV analysis, catalyst research, analyst insights, and comprehensive market context.
                  </p>
                </div>
              </div>
              
              <div className="flex items-start gap-3">
                <div className="rounded-full bg-purple-100 dark:bg-purple-900 p-2 mt-0.5 shrink-0">
                  <Brain className="h-4 w-4 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <p className="font-medium text-sm">📊 Comprehensive Analysis</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    Provides detailed risk/reward analysis, scenario testing, Greeks analysis, and professional investment memo format.
                  </p>
                </div>
              </div>
            </div>
          </div>
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => setDeepResearchConfirmOpen(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleConfirmDeepResearch}
              variant="default"
              className="bg-blue-600 hover:bg-blue-700"
              disabled={!hasAiQuota}
            >
              <Sparkles className="h-4 w-4 mr-2" />
              Start Analysis
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

