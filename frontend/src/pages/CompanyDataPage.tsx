import { useCallback, useEffect, useMemo, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import {
  BarChart3,
  Calendar,
  DollarSign,
  Loader2,
  MessageSquare,
  PieChart,
  TrendingUp,
  AlertCircle,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { SymbolSearch } from "@/components/market/SymbolSearch"
import { CandlestickChart } from "@/components/charts/CandlestickChart"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { FundamentalDataContent } from "@/components/market/ProfileDataDialog"
import { companyDataApi, CompanyDataFullResponse } from "@/services/api/companyData"
import { marketService } from "@/services/api/market"

const MODULES = "overview,valuation,ratios,analyst,charts"

const SYMBOL_PARAM = "symbol"

export default function CompanyDataPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const urlSymbol = searchParams.get(SYMBOL_PARAM)?.trim().toUpperCase() || null

  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null)
  const [loadingProgress, setLoadingProgress] = useState(0)

  // Restore symbol from URL on load / when URL changes (e.g. refresh or back)
  useEffect(() => {
    if (urlSymbol && urlSymbol !== selectedSymbol) {
      setSelectedSymbol(urlSymbol)
    }
  }, [urlSymbol])

  // Keep URL in sync when user selects a symbol (same behavior as Strategy Lab)
  const handleSelectSymbol = useCallback(
    (symbol: string) => {
      const sym = symbol.trim().toUpperCase()
      setSelectedSymbol(sym)
      setSearchParams({ [SYMBOL_PARAM]: sym }, { replace: true })
    },
    [setSearchParams]
  )

  const { data: quota, refetch: refetchQuota } = useQuery({
    queryKey: ["company-data-quota"],
    queryFn: () => companyDataApi.getQuota(),
  })

  const {
    data: fullData,
    isLoading: loadingData,
    error: dataError,
    refetch: refetchData,
  } = useQuery({
    queryKey: ["company-data-full", selectedSymbol],
    queryFn: () => companyDataApi.getFull(selectedSymbol!, MODULES),
    enabled: !!selectedSymbol?.trim(),
  })

  const { data: financialProfile, isLoading: isLoadingProfile } = useQuery({
    queryKey: ["financialProfile", selectedSymbol],
    queryFn: () => marketService.getFinancialProfile(selectedSymbol!),
    enabled: !!selectedSymbol?.trim(),
    staleTime: 5 * 60 * 1000, // 5 min — avoid refetch on tab switch / window focus
    refetchOnWindowFocus: false,
  })

  const { data: historicalData } = useQuery({
    queryKey: ["historicalData", selectedSymbol],
    queryFn: () => marketService.getHistoricalData(selectedSymbol!, 500, "day"),
    enabled: !!selectedSymbol?.trim(),
  })

  // Same candlestick format as Strategy Lab for CandlestickChart (lightweight-charts)
  type MarketCandle = { time: string; open: number; high: number; low: number; close: number; volume: number }
  const marketCandleData = useMemo(() => {
    if (!historicalData?.data?.length) return []
    return historicalData.data
      .map((d: { time?: string | number; open?: number; high?: number; low?: number; close?: number; volume?: number }) => {
        const timeValue =
          typeof d.time === "string"
            ? d.time
            : typeof d.time === "number"
              ? new Date(d.time * 1000).toISOString().split("T")[0]
              : null
        if (timeValue == null) return null
        const open = Number(d.open)
        const high = Number(d.high)
        const low = Number(d.low)
        const close = Number(d.close)
        if (![open, high, low, close].every(Number.isFinite)) return null
        const volume = Number.isFinite(Number(d.volume)) ? Number(d.volume) : 0
        return { time: timeValue, open, high, low, close, volume }
      })
      .filter((x): x is MarketCandle => !!x)
  }, [historicalData])

  // Simulated progress bar while loading (0 → 90% over ~2.5s; resets when done)
  useEffect(() => {
    if (!selectedSymbol || !loadingData) {
      if (!loadingData) {
        const t = setTimeout(() => setLoadingProgress(0), 200)
        return () => clearTimeout(t)
      }
      return
    }
    setLoadingProgress(0)
    const interval = setInterval(() => {
      setLoadingProgress((p) => Math.min(90, p + 4))
    }, 120)
    return () => clearInterval(interval)
  }, [loadingData, selectedSymbol])


  const formatNum = (v: unknown): string => {
    if (v == null) return "—"
    if (typeof v === "object") return "—"
    if (typeof v === "number") {
      if (Number.isInteger(v)) return v.toLocaleString()
      return v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    }
    return String(v)
  }

  const formatPct = (v: unknown): string => {
    if (v == null) return "—"
    const n = Number(v)
    if (Number.isNaN(n)) return "—"
    return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`
  }

  return (
    <div className="container mx-auto space-y-6 py-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Company Data</h1>
          <p className="text-muted-foreground">
            Fundamental and financial data. One lookup per symbol per day counts toward your quota.
          </p>
        </div>
        {quota != null && (
          <Card className="w-full sm:w-auto">
            <CardContent className="pt-4">
              <div className="flex items-center gap-2 text-sm">
                <BarChart3 className="h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">Today:</span>
                <span className="font-medium">
                  {quota.used} / {quota.limit}
                </span>
                {quota.is_pro && (
                  <span className="rounded bg-primary/10 px-1.5 py-0.5 text-xs text-primary">
                    Pro
                  </span>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Search: same style and behavior as Strategy Lab */}
      <div className="flex flex-col gap-6 min-w-0 overflow-x-hidden">
        {!selectedSymbol ? (
          <div className="flex flex-col items-center gap-6 py-8">
            <div className="w-full max-w-2xl">
              <SymbolSearch
                onSelect={(sym) => handleSelectSymbol(sym)}
                value={selectedSymbol ?? ""}
                placeholder="Search for a stock symbol (e.g., AAPL, TSLA, NVDA)..."
                size="large"
              />
            </div>
            <p className="text-sm text-muted-foreground">
              Enter a stock symbol to get started with option strategy analysis
            </p>
            <div className="flex flex-wrap items-center justify-center gap-2 text-xs">
              <span className="rounded-full bg-primary/10 px-3 py-1 text-primary font-medium">30+ Technical Indicators</span>
              <span className="rounded-full bg-primary/10 px-3 py-1 text-primary font-medium">Risk & Performance</span>
              <span className="rounded-full bg-primary/10 px-3 py-1 text-primary font-medium">Financial Statements</span>
              <span className="rounded-full bg-primary/10 px-3 py-1 text-primary font-medium">Valuation & Ratios</span>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center gap-4">
            <div className="w-full max-w-md rounded-lg ring-1 ring-border/50 hover:ring-primary/30 transition-all focus-within:ring-2 focus-within:ring-primary/20">
              <SymbolSearch
                onSelect={(sym) => handleSelectSymbol(sym)}
                value={selectedSymbol}
                placeholder="Switch symbol (e.g., AAPL, TSLA, NVDA)..."
              />
            </div>
          </div>
        )}
      </div>

      {selectedSymbol && (
        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="mb-4">
            <TabsTrigger value="overview">
              Overview — {(fullData?.overview?.profile as { companyName?: string } | undefined)?.companyName ?? selectedSymbol}
            </TabsTrigger>
            <TabsTrigger value="fundamentals">Full fundamentals</TabsTrigger>
          </TabsList>
          <TabsContent value="overview" className="mt-0">
            {loadingData && (
              <Card className="border-primary/20">
                <CardContent className="flex flex-col items-center justify-center gap-6 py-16 px-8 max-w-md mx-auto">
                  <Loader2 className="h-10 w-10 animate-spin text-primary shrink-0" />
                  <div className="text-center space-y-1 w-full">
                    <p className="font-medium">Loading company data for {selectedSymbol}</p>
                    <p className="text-sm text-muted-foreground">Fetching overview, valuation, ratios…</p>
                  </div>
                  <div className="w-full space-y-2">
                    <Progress value={loadingProgress} className="h-2" />
                    <p className="text-center text-xs text-muted-foreground tabular-nums">
                      {loadingProgress}%
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}
            {!loadingData && dataError != null && (
              <Card className="border-destructive/50">
                <CardContent className="flex items-center gap-2 pt-4 text-destructive">
                  <AlertCircle className="h-4 w-4" />
                  <span>
                    {(dataError as Error)?.message || "Failed to load data. Check your quota or try again."}
                  </span>
                </CardContent>
              </Card>
            )}
            {!loadingData && fullData && (
              <CompanyDataBlocks
                symbol={selectedSymbol}
                data={fullData}
                marketCandleData={marketCandleData}
                formatNum={formatNum}
                formatPct={formatPct}
                onSelectSymbol={handleSelectSymbol}
                onRefetch={() => {
                  refetchData()
                  refetchQuota()
                }}
              />
            )}
          </TabsContent>
          <TabsContent value="fundamentals" className="mt-0 data-[state=inactive]:hidden" forceMount>
            <Card className="overflow-hidden">
              <CardHeader className="pb-2">
                <CardTitle className="text-lg">Full fundamentals</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Ratios · Statements · Valuation · Analysis · Technical & Risk · Profile (same data as Strategy Lab)
                </p>
              </CardHeader>
              <CardContent className="p-0">
                <div className="min-h-[520px] flex flex-col">
                  <FundamentalDataContent
                    profile={financialProfile}
                    symbol={selectedSymbol}
                    isLoading={isLoadingProfile}
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}

function CompanyDataBlocks({
  symbol,
  data,
  marketCandleData = [],
  formatNum,
  formatPct,
  onSelectSymbol,
}: {
  symbol: string
  data: CompanyDataFullResponse
  marketCandleData?: Array<{ time: string; open: number; high: number; low: number; close: number; volume: number }>
  formatNum: (v: unknown) => string
  formatPct: (v: unknown) => string
  onSelectSymbol: (sym: string) => void
  onRefetch?: () => void
}) {
  const overview = data.overview
  const valuation = data.valuation
  const ratios = data.ratios
  const analyst = data.analyst

  const profile = overview?.profile as Record<string, unknown> | undefined
  const quote = overview?.quote as Record<string, unknown> | undefined
  const priceChange = overview?.stock_price_change as Record<string, unknown> | undefined
  const nextEarnings = overview?.next_earnings
  const peers = Array.isArray(overview?.peers) ? overview.peers : []

  const get = (o: Record<string, unknown> | undefined, ...keys: string[]) =>
    keys.reduce<unknown>((acc, k) => acc != null ? acc : o?.[k], null)

  const price = get(quote, "price", "Price") ?? get(profile, "price", "Price")
  const changePct = get(quote, "changesPercentage", "changesPercentage", "change", "Change")
  const mcap = get(profile, "mktCap", "mktCap", "marketCap", "MarketCapitalization") ?? get(quote, "marketCap", "MarketCapitalization")
  const beta = get(profile, "beta", "Beta")
  const companyName = (get(profile, "companyName", "Company Name", "name") as string) || symbol

  const priceChangeKeys: Record<string, string[]> = {
    "1D": ["1dPercentage", "1D", "1d"],
    "5D": ["5dPercentage", "5D", "5d"],
    "1M": ["1mPercentage", "1M", "1m"],
    "3M": ["3mPercentage", "3M", "3m"],
    "6M": ["6mPercentage", "6M", "6m"],
    "1Y": ["1yPercentage", "1Y", "1y"],
  }
  const hasAnyPriceChange = priceChange && typeof priceChange === "object" &&
    (["1D", "5D", "1M", "3M", "6M", "1Y"] as const).some(
      (period) => priceChangeKeys[period].reduce<unknown>((acc, k) => acc != null ? acc : (priceChange as Record<string, unknown>)[k], null) != null
    )

  const r = ratios?.ratios_ttm as Record<string, unknown> | undefined
  const m = ratios?.key_metrics_ttm as Record<string, unknown> | undefined
  const sc = ratios?.financial_scores as Record<string, unknown> | undefined
  const peRaw =
    get(r, "peRatioTTM", "peRatio", "pe") ?? get(m, "peRatioTTM", "priceToEarningsRatioTTM")
  const pe =
    peRaw != null
      ? peRaw
      : (price != null && (get(m, "netIncomePerShareTTM") ?? get(r, "eps") ?? get(profile, "eps")) != null
          ? (() => {
              const p = Number(price)
              const eps = Number(get(m, "netIncomePerShareTTM") ?? get(r, "eps") ?? get(profile, "eps"))
              return p > 0 && eps > 0 ? p / eps : undefined
            })()
          : undefined)
  const pb = get(r, "pbRatioTTM", "pbRatio", "pb") ?? get(m, "pbRatioTTM", "priceToBookRatioTTM")
  const roe = get(r, "roeTTM", "roe") ?? get(m, "roeTTM", "returnOnEquityTTM")
  const debtEq =
    get(r, "debtEquityRatioTTM", "debtEquityRatio") ??
    (sc && (() => {
      const tl = Number(sc.totalLiabilities)
      const ta = Number(sc.totalAssets)
      const eq = ta - tl
      return tl > 0 && eq > 0 ? tl / eq : undefined
    })())

  const dcfVal = valuation && get(valuation.dcf as Record<string, unknown>, "dcf", "DCF", "value")
  const leveredVal = valuation && get(valuation.levered_dcf as Record<string, unknown>, "leveredDcf", "levered_dcf", "dcf", "value")

  const pt = analyst?.price_target_consensus as Record<string, unknown> | undefined
  const target = get(pt, "median", "priceTargetMedian", "targetMedianPrice", "consensus")
  const grades = analyst?.grades_consensus as Record<string, unknown> | undefined
  const summary = analyst?.price_target_summary as Record<string, unknown> | undefined
  const recommendation = get(grades, "recommendation", "recommend", "rating") ?? get(summary, "recommendation")

  const hasOverview = overview && (
    price != null || changePct != null || mcap != null || beta != null ||
    hasAnyPriceChange || (nextEarnings && typeof nextEarnings === "object" && Object.keys(nextEarnings).length > 0)
  )
  const hasValuation = (typeof dcfVal === "number" && Number.isFinite(dcfVal)) || (typeof leveredVal === "number" && Number.isFinite(leveredVal))
  const hasRatios = (typeof pe === "number" && Number.isFinite(pe)) || (typeof pb === "number" && Number.isFinite(pb)) ||
    (typeof roe === "number" && Number.isFinite(roe)) || (typeof debtEq === "number" && Number.isFinite(debtEq)) ||
    (ratios?.financial_scores && Object.keys(ratios.financial_scores).length > 0)
  const hasAnalyst = target != null || (recommendation != null && String(recommendation).trim() !== "")

  const hasValidNum = (v: unknown) => v != null && typeof v === "number" && Number.isFinite(v)

  return (
    <div className="space-y-6">
      {/* Overview: snapshot + next earnings (core, FMP-only headline) — only when we have data */}
      {hasOverview && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Overview — {companyName}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {price != null && <KpiCard label="Price" value={price} formatter={formatNum} prefix="$" />}
              {changePct != null && <KpiCard label="Change %" value={changePct} formatter={(v) => formatPct(v)} greenRed />}
              {mcap != null && <KpiCard label="Market Cap" value={mcap} formatter={formatNum} />}
              {beta != null && <KpiCard label="Beta" value={beta} formatter={formatNum} />}
            </div>
            {nextEarnings && typeof nextEarnings === "object" && (nextEarnings.date != null || nextEarnings.earningsDate != null) && (
              <div className="flex items-center gap-2 rounded-md border p-3">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <div className="text-sm">
                  <span className="font-medium text-muted-foreground">Next earnings</span>
                  <span className="ml-2 font-medium">
                    {String(nextEarnings.date ?? nextEarnings.earningsDate ?? "")}
                    {(nextEarnings.epsEstimated ?? nextEarnings.epsEstimate) != null && (
                      <span className="ml-2 text-muted-foreground">
                        (EPS est. {formatNum(nextEarnings.epsEstimated ?? nextEarnings.epsEstimate)})
                      </span>
                    )}
                  </span>
                </div>
              </div>
            )}
            {hasAnyPriceChange && priceChange && typeof priceChange === "object" && (
              <div className="rounded-md border p-3">
                <p className="mb-2 text-sm font-medium text-muted-foreground">Price change</p>
                <div className="flex flex-wrap gap-4 text-sm">
                  {(["1D", "5D", "1M", "3M", "6M", "1Y"] as const).map((period) => {
                    const val = priceChangeKeys[period].reduce<unknown>((acc, k) => acc != null ? acc : (priceChange as Record<string, unknown>)[k], null)
                    if (val == null) return null
                    return (
                      <span key={period}>
                        {period}: {formatPct(val)}
                      </span>
                    )
                  })}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Valuation & DCF — only when we have at least one value */}
      {hasValuation && valuation && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              Valuation & DCF
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {hasValidNum(dcfVal) && <KpiCard label="DCF value" value={dcfVal} formatter={formatNum} />}
              {hasValidNum(leveredVal) && <KpiCard label="Levered DCF" value={leveredVal} formatter={formatNum} />}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Ratios (TTM) — only when we have at least one value */}
      {hasRatios && ratios && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <PieChart className="h-5 w-5" />
              Key ratios (TTM)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {hasValidNum(pe) && <KpiCard label="PE ratio" value={pe} formatter={formatNum} />}
              {hasValidNum(pb) && <KpiCard label="PB ratio" value={pb} formatter={formatNum} />}
              {hasValidNum(roe) && <KpiCard label="ROE" value={roe} formatter={formatPct} />}
              {hasValidNum(debtEq) && <KpiCard label="Debt/Equity" value={debtEq} formatter={formatNum} />}
            </div>
            {ratios.financial_scores && Object.keys(ratios.financial_scores).length > 0 && (
              <div className="mt-4 rounded-md border p-3">
                <p className="mb-2 text-sm font-medium text-muted-foreground">Financial scores</p>
                <div className="flex flex-wrap gap-4 text-sm">
                  {Object.entries(ratios.financial_scores).map(([k, v]) => (
                    <span key={k}>
                      {k}: {formatNum(v)}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Analyst consensus — only when we have target or recommendation */}
      {hasAnalyst && analyst && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              Analyst
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {target != null && <KpiCard label="Target (median)" value={target} formatter={formatNum} prefix="$" />}
              {recommendation != null && String(recommendation).trim() !== "" && (
                <KpiCard label="Recommendation" value={recommendation} formatter={(v) => (v != null ? String(v) : "—")} />
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Market Data: same CandlestickChart as Strategy Lab */}
      <Card className="flex flex-col min-h-[500px]">
        <CardHeader className="flex-shrink-0">
          <CardTitle>Market Data</CardTitle>
          <p className="text-sm text-muted-foreground">Real-time stock chart</p>
        </CardHeader>
        <CardContent className="flex-1 overflow-hidden flex flex-col">
          {marketCandleData.length > 0 ? (
            <div className="flex-1 min-h-[500px]">
              <CandlestickChart data={marketCandleData} height={600} />
            </div>
          ) : (
            <div className="flex h-full min-h-[400px] items-center justify-center text-muted-foreground text-sm">
              {symbol ? "Loading..." : "No chart data"}
            </div>
          )}
        </CardContent>
      </Card>

      {peers.length > 0 && (
        <Card className="border-muted/50">
          <CardContent className="pt-4">
            <p className="mb-2 text-sm font-medium text-muted-foreground">Related symbols (Peers)</p>
            <div className="flex flex-wrap gap-2">
              {peers.slice(0, 15).map((p: string | Record<string, unknown>) => {
                const sym = typeof p === "string" ? p : (p && typeof p === "object" && "symbol" in p ? String((p as { symbol?: string }).symbol) : null)
                if (!sym) return null
                return (
                  <Button
                    key={sym}
                    variant="outline"
                    size="sm"
                    onClick={() => onSelectSymbol(sym)}
                  >
                    {sym}
                  </Button>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      <p className="text-center text-xs text-muted-foreground">
        For informational use only.
      </p>
    </div>
  )
}

function KpiCard({
  label,
  value,
  formatter,
  prefix = "",
  suffix = "",
  greenRed = false,
}: {
  label: string
  value: unknown
  formatter: (v: unknown) => string
  prefix?: string
  suffix?: string
  greenRed?: boolean
}) {
  const num = typeof value === "number" ? value : value != null ? Number(value) : null
  const isNeg = num != null && num < 0
  const isPos = num != null && num > 0
  return (
    <div className="rounded-lg border p-3">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p
        className={
          greenRed
            ? isPos
              ? "text-green-600 dark:text-green-400"
              : isNeg
                ? "text-red-600 dark:text-red-400"
                : ""
            : "font-semibold"
        }
      >
        {prefix}
        {typeof value === "object" && value !== null ? "—" : formatter(value)}
        {suffix}
      </p>
    </div>
  )
}
