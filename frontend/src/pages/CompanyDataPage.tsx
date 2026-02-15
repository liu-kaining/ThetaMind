import { useCallback, useEffect, useMemo, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import {
  BarChart3,
  Calendar,
  DollarSign,
  FileText,
  HelpCircle,
  Loader2,
  MessageSquare,
  Newspaper,
  PieChart,
  Shield,
  TrendingUp,
  Users,
  AlertCircle,
  ExternalLink,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { SymbolSearch } from "@/components/market/SymbolSearch"
import { CandlestickChart } from "@/components/charts/CandlestickChart"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { FundamentalDataContent } from "@/components/market/ProfileDataDialog"
import {
  companyDataApi,
  CompanyDataFullResponse,
  CompanyDataNewsItem,
  CompanyDataSecFilingItem,
  CompanyDataInsiderItem,
  CompanyDataGovernanceResponse,
  CompanyDataStatementsResponse,
} from "@/services/api/companyData"
import { marketService } from "@/services/api/market"

const MODULES = "overview,valuation,ratios,analyst,charts"

const SYMBOL_PARAM = "symbol"

const DCF_FORMULA_HINT = "DCF = Equity Value / Weighted Avg Shares Diluted. Equity Value = EV − Net Debt. EV = Market Cap + Long Term Debt + Short Term Debt. See FMP docs for details."
const LEVERED_DCF_HINT = "Levered DCF adjusts for debt. See FMP DCF formula docs."
const RATING_METHODOLOGY_HINT = "Rating based on DCF, ROE, ROA, Debt/Equity, P/E, P/B. Scores map to Strong Buy → Strong Sell. Total score maps to S+/A+/B+/C+/D. See FMP recommendations formula."
const RATIO_FORMULAS: Record<string, string> = {
  "PE ratio": "P/E = price / (netIncome / shareNumber)",
  "PB ratio": "P/B = price / (totalStockHolderEquity / shareNumber)",
  "ROE": "ROE = netIncome / totalStockHolderEquity",
  "Debt/Equity": "Debt/Equity = totalLiabilities / totalStockHolderEquity",
}

function FormulaHint({ hint, className }: { hint: string; className?: string }) {
  return (
    <span
      title={hint}
      className={className ?? "inline-flex cursor-help text-muted-foreground hover:text-foreground"}
    >
      <HelpCircle className="h-3.5 w-3.5 shrink-0" />
    </span>
  )
}

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

  const { data: newsData } = useQuery({
    queryKey: ["company-data-news", selectedSymbol],
    queryFn: () => companyDataApi.getNews(selectedSymbol!, 5),
    enabled: !!selectedSymbol?.trim(),
    staleTime: 5 * 60 * 1000,
  })

  const { data: calendarData } = useQuery({
    queryKey: ["company-data-calendar", selectedSymbol],
    queryFn: () => companyDataApi.getCalendar(selectedSymbol!),
    enabled: !!selectedSymbol?.trim(),
    staleTime: 60 * 60 * 1000,
  })

  const { data: newsFull } = useQuery({
    queryKey: ["company-data-news-full", selectedSymbol],
    queryFn: () => companyDataApi.getNews(selectedSymbol!, 20),
    enabled: !!selectedSymbol?.trim(),
    staleTime: 5 * 60 * 1000,
  })

  const { data: calendarFull } = useQuery({
    queryKey: ["company-data-calendar-full", selectedSymbol],
    queryFn: () => companyDataApi.getCalendar(selectedSymbol!),
    enabled: !!selectedSymbol?.trim(),
    staleTime: 60 * 60 * 1000,
  })

  const { data: statements } = useQuery({
    queryKey: ["company-data-statements", selectedSymbol],
    queryFn: () => companyDataApi.getStatements(selectedSymbol!, "annual", 5),
    enabled: !!selectedSymbol?.trim(),
    staleTime: 60 * 60 * 1000,
  })

  const { data: secFilings } = useQuery({
    queryKey: ["company-data-sec", selectedSymbol],
    queryFn: () => companyDataApi.getSecFilings(selectedSymbol!, 20),
    enabled: !!selectedSymbol?.trim(),
    staleTime: 60 * 60 * 1000,
  })

  const { data: insider } = useQuery({
    queryKey: ["company-data-insider", selectedSymbol],
    queryFn: () => companyDataApi.getInsider(selectedSymbol!, 20),
    enabled: !!selectedSymbol?.trim(),
    staleTime: 60 * 60 * 1000,
  })

  const { data: governance } = useQuery({
    queryKey: ["company-data-governance", selectedSymbol],
    queryFn: () => companyDataApi.getGovernance(selectedSymbol!),
    enabled: !!selectedSymbol?.trim(),
    staleTime: 60 * 60 * 1000,
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
          <TabsList className="mb-4 flex-wrap h-auto gap-1">
            <TabsTrigger value="overview">
              Overview — {(fullData?.overview?.profile as { companyName?: string } | undefined)?.companyName ?? selectedSymbol}
            </TabsTrigger>
            <TabsTrigger value="news-calendar">News & Calendar</TabsTrigger>
            <TabsTrigger value="financials-sec">Financials & SEC</TabsTrigger>
            <TabsTrigger value="insider-governance">Insider & Governance</TabsTrigger>
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
                newsItems={newsData ?? []}
                calendarEvents={calendarData?.events ?? []}
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
          <TabsContent value="news-calendar" className="mt-0 data-[state=inactive]:hidden" forceMount>
            <CompanyDataNewsCalendarTab
              symbol={selectedSymbol}
              newsItems={newsFull ?? []}
              calendarEvents={calendarFull?.events ?? []}
            />
          </TabsContent>
          <TabsContent value="financials-sec" className="mt-0 data-[state=inactive]:hidden" forceMount>
            <CompanyDataFinancialsSecTab
              symbol={selectedSymbol}
              statements={statements}
              secFilings={secFilings ?? []}
            />
          </TabsContent>
          <TabsContent value="insider-governance" className="mt-0 data-[state=inactive]:hidden" forceMount>
            <CompanyDataInsiderGovernanceTab
              symbol={selectedSymbol}
              insider={insider ?? []}
              governance={governance}
            />
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
  newsItems = [],
  calendarEvents = [],
  formatNum,
  formatPct,
  onSelectSymbol,
}: {
  symbol: string
  data: CompanyDataFullResponse
  marketCandleData?: Array<{ time: string; open: number; high: number; low: number; close: number; volume: number }>
  newsItems?: CompanyDataNewsItem[]
  calendarEvents?: Array<{ type?: string; date?: string; [key: string]: unknown }>
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

      {/* Recent News — no quota; only when we have items */}
      {newsItems.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Newspaper className="h-5 w-5" />
              Recent News
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-3">
              {newsItems.slice(0, 5).map((item, i) => {
                const title = (item.title || item.text || "").trim() || "—"
                const url = item.url
                const pubDate = item.publishedDate
                const site = item.site
                return (
                  <li key={i} className="text-sm">
                    {url ? (
                      <a
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-primary hover:underline inline-flex items-center gap-1"
                      >
                        {title}
                        <ExternalLink className="h-3 w-3 shrink-0" />
                      </a>
                    ) : (
                      <span className="font-medium">{title}</span>
                    )}
                    {(pubDate || site) && (
                      <span className="ml-2 text-xs text-muted-foreground">
                        {pubDate ? new Date(pubDate).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : ""}
                        {pubDate && site ? " · " : ""}
                        {site || ""}
                      </span>
                    )}
                  </li>
                )
              })}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Upcoming Events (Calendar) — no quota; only when we have items */}
      {calendarEvents.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Upcoming Events
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2 text-sm">
              {calendarEvents.slice(0, 10).map((evt, i) => {
                const type = (evt.type || "event") as string
                const date = evt.date
                const label = type === "earnings" ? "Earnings" : type === "dividend" ? "Dividend" : type === "split" ? "Stock Split" : "Event"
                const extra = type === "earnings" && evt.epsEstimated != null ? ` (EPS est. ${formatNum(evt.epsEstimated)})` : ""
                return (
                  <li key={i} className="flex items-center gap-3">
                    <span className="text-muted-foreground min-w-[80px]">
                      {date ? new Date(date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—"}
                    </span>
                    <span className="font-medium">{label}</span>
                    {extra && <span className="text-muted-foreground">{extra}</span>}
                  </li>
                )
              })}
            </ul>
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
              <a
                href="https://site.financialmodelingprep.com/developer/docs/dcf-formula"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-muted-foreground hover:text-primary"
              >
                How we calculate
              </a>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {hasValidNum(dcfVal) && (
                <div className="flex items-start gap-1">
                  <div className="flex-1">
                    <KpiCard label="DCF value" value={dcfVal} formatter={formatNum} />
                  </div>
                  <FormulaHint hint={DCF_FORMULA_HINT} className="mt-3 cursor-help text-muted-foreground hover:text-foreground" />
                </div>
              )}
              {hasValidNum(leveredVal) && (
                <div className="flex items-start gap-1">
                  <div className="flex-1">
                    <KpiCard label="Levered DCF" value={leveredVal} formatter={formatNum} />
                  </div>
                  <FormulaHint hint={LEVERED_DCF_HINT} className="mt-3 cursor-help text-muted-foreground hover:text-foreground" />
                </div>
              )}
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
              <a
                href="https://site.financialmodelingprep.com/developer/docs/formula"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-muted-foreground hover:text-primary"
              >
                Formulas
              </a>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {hasValidNum(pe) && (
                <div className="flex items-start gap-1">
                  <div className="flex-1">
                    <KpiCard label="PE ratio" value={pe} formatter={formatNum} />
                  </div>
                  <FormulaHint hint={RATIO_FORMULAS["PE ratio"]} className="mt-3 cursor-help text-muted-foreground hover:text-foreground" />
                </div>
              )}
              {hasValidNum(pb) && (
                <div className="flex items-start gap-1">
                  <div className="flex-1">
                    <KpiCard label="PB ratio" value={pb} formatter={formatNum} />
                  </div>
                  <FormulaHint hint={RATIO_FORMULAS["PB ratio"]} className="mt-3 cursor-help text-muted-foreground hover:text-foreground" />
                </div>
              )}
              {hasValidNum(roe) && (
                <div className="flex items-start gap-1">
                  <div className="flex-1">
                    <KpiCard label="ROE" value={roe} formatter={formatPct} />
                  </div>
                  <FormulaHint hint={RATIO_FORMULAS["ROE"]} className="mt-3 cursor-help text-muted-foreground hover:text-foreground" />
                </div>
              )}
              {hasValidNum(debtEq) && (
                <div className="flex items-start gap-1">
                  <div className="flex-1">
                    <KpiCard label="Debt/Equity" value={debtEq} formatter={formatNum} />
                  </div>
                  <FormulaHint hint={RATIO_FORMULAS["Debt/Equity"]} className="mt-3 cursor-help text-muted-foreground hover:text-foreground" />
                </div>
              )}
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
              <FormulaHint hint={RATING_METHODOLOGY_HINT} />
              <a
                href="https://site.financialmodelingprep.com/developer/docs/recommendations-formula"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-muted-foreground hover:text-primary"
              >
                Rating methodology
              </a>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {target != null && <KpiCard label="Target (median)" value={target} formatter={formatNum} prefix="$" />}
              {recommendation != null && String(recommendation).trim() !== "" && (
                <div className="flex items-start gap-1">
                  <div className="flex-1">
                    <KpiCard label="Recommendation" value={recommendation} formatter={(v) => (v != null ? String(v) : "—")} />
                  </div>
                  <FormulaHint hint={RATING_METHODOLOGY_HINT} className="mt-3 cursor-help text-muted-foreground hover:text-foreground" />
                </div>
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

function CompanyDataNewsCalendarTab({
  symbol,
  newsItems,
  calendarEvents,
}: {
  symbol: string
  newsItems: CompanyDataNewsItem[]
  calendarEvents: Array<{ type?: string; date?: string; [key: string]: unknown }>
}) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Newspaper className="h-5 w-5" />
            News — {symbol}
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Latest stock news and press releases.
          </p>
        </CardHeader>
        <CardContent>
          {newsItems.length === 0 ? (
            <p className="text-sm text-muted-foreground">No news available.</p>
          ) : (
            <ul className="space-y-3">
              {newsItems.map((item, i) => {
                const title = (item.title || item.text || "").trim() || "—"
                const url = item.url
                const pubDate = item.publishedDate
                const site = item.site
                return (
                  <li key={i} className="text-sm">
                    {url ? (
                      <a
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-primary hover:underline inline-flex items-center gap-1"
                      >
                        {title}
                        <ExternalLink className="h-3 w-3 shrink-0" />
                      </a>
                    ) : (
                      <span className="font-medium">{title}</span>
                    )}
                    {(pubDate || site) && (
                      <span className="ml-2 text-xs text-muted-foreground">
                        {pubDate ? new Date(pubDate).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : ""}
                        {pubDate && site ? " · " : ""}
                        {site || ""}
                      </span>
                    )}
                  </li>
                )
              })}
            </ul>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Calendar — {symbol}
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Earnings, dividends, and stock splits.
          </p>
        </CardHeader>
        <CardContent>
          {calendarEvents.length === 0 ? (
            <p className="text-sm text-muted-foreground">No upcoming events.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {calendarEvents.map((evt, i) => {
                const type = (evt.type || "event") as string
                const date = evt.date
                const label = type === "earnings" ? "Earnings" : type === "dividend" ? "Dividend" : type === "split" ? "Stock Split" : "Event"
                return (
                  <li key={i} className="flex items-center gap-3">
                    <span className="text-muted-foreground min-w-[100px]">
                      {date ? new Date(date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—"}
                    </span>
                    <span className="font-medium">{label}</span>
                  </li>
                )
              })}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function CompanyDataFinancialsSecTab({
  symbol,
  statements,
  secFilings,
}: {
  symbol: string
  statements: CompanyDataStatementsResponse | undefined
  secFilings: CompanyDataSecFilingItem[]
}) {
  const income = statements?.income ?? []
  const balance = statements?.balance ?? []
  const cashflow = statements?.cashflow ?? []

  const formatCurrency = (v: unknown): string => {
    if (v == null) return "—"
    const n = Number(v)
    if (!Number.isFinite(n)) return "—"
    if (Math.abs(n) >= 1e12) return `$${(n / 1e12).toFixed(2)}T`
    if (Math.abs(n) >= 1e9) return `$${(n / 1e9).toFixed(2)}B`
    if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(2)}M`
    return `$${n.toLocaleString()}`
  }

  const renderStatementTable = (rows: Record<string, unknown>[], title: string) => {
    if (rows.length === 0) return null
    const first = rows[0] as Record<string, unknown>
    const keys = Object.keys(first).filter((k) => k !== "date" && k !== "calendarYear" && k !== "period" && typeof first[k] === "number")
    if (keys.length === 0) return null
    return (
      <div className="overflow-x-auto">
        <p className="mb-2 text-sm font-medium text-muted-foreground">{title}</p>
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b">
              <th className="text-left py-2 pr-4">Date</th>
              {keys.slice(0, 8).map((k) => (
                <th key={k} className="text-right py-2 px-2">{k.replace(/([A-Z])/g, " $1").trim()}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 5).map((row, i) => (
              <tr key={i} className="border-b border-border/50">
                <td className="py-2 pr-4">{String(row.date ?? row.calendarYear ?? "—")}</td>
                {keys.slice(0, 8).map((k) => (
                  <td key={k} className="text-right py-2 px-2">{formatCurrency(row[k])}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Financial Statements — {symbol}
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Income statement, balance sheet, cash flow. One load per symbol per day counts toward quota.
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          {income.length === 0 && balance.length === 0 && cashflow.length === 0 ? (
            <p className="text-sm text-muted-foreground">No statement data available.</p>
          ) : (
            <>
              {renderStatementTable(income as Record<string, unknown>[], "Income Statement")}
              {renderStatementTable(balance as Record<string, unknown>[], "Balance Sheet")}
              {renderStatementTable(cashflow as Record<string, unknown>[], "Cash Flow")}
            </>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            SEC Filings — {symbol}
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            10-K, 10-Q, 8-K filings with links to SEC EDGAR.
          </p>
        </CardHeader>
        <CardContent>
          {secFilings.length === 0 ? (
            <p className="text-sm text-muted-foreground">No SEC filings available.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {secFilings.map((f, i) => {
                const type = String(f.type ?? f.filingType ?? "Filing")
                const dateVal = f.fillingDate ?? f.date ?? f.filingDate
                const date = typeof dateVal === "string" || typeof dateVal === "number" || dateVal instanceof Date ? dateVal : null
                const link = typeof f.finalLink === "string" ? f.finalLink : typeof f.link === "string" ? f.link : typeof f.url === "string" ? f.url : null
                return (
                  <li key={i} className="flex items-center gap-3">
                    <span className="text-muted-foreground min-w-[80px]">
                      {date ? new Date(date).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "—"}
                    </span>
                    <span className="font-medium">{type}</span>
                    {link && (
                      <a
                        href={link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline inline-flex items-center gap-1"
                      >
                        View <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </li>
                )
              })}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function CompanyDataInsiderGovernanceTab({
  symbol,
  insider,
  governance,
}: {
  symbol: string
  insider: CompanyDataInsiderItem[]
  governance: CompanyDataGovernanceResponse | undefined
}) {
  const execs = governance?.executives ?? []
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Insider Trading — {symbol}
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Recent insider transactions.
          </p>
        </CardHeader>
        <CardContent>
          {insider.length === 0 ? (
            <p className="text-sm text-muted-foreground">No insider transactions available.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b">
                    <th className="text-left py-2">Date</th>
                    <th className="text-left py-2">Name</th>
                    <th className="text-left py-2">Type</th>
                    <th className="text-right py-2">Shares</th>
                    <th className="text-right py-2">Price</th>
                  </tr>
                </thead>
                <tbody>
                  {insider.map((t, i) => (
                    <tr key={i} className="border-b border-border/50">
                      <td className="py-2">{t.transactionDate ? new Date(t.transactionDate).toLocaleDateString() : "—"}</td>
                      <td className="py-2">{t.reportingName ?? "—"}</td>
                      <td className="py-2">{t.transactionType ?? "—"}</td>
                      <td className="text-right py-2">{(t.securitiesTransacted ?? t.acquisition ?? 0).toLocaleString()}</td>
                      <td className="text-right py-2">${Number(t.price ?? 0).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Key Executives — {symbol}
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            Company leadership and compensation.
          </p>
        </CardHeader>
        <CardContent>
          {execs.length === 0 ? (
            <p className="text-sm text-muted-foreground">No executive data available.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {execs.map((e: Record<string, unknown>, i: number) => (
                <li key={i} className="flex items-center justify-between">
                  <div>
                    <span className="font-medium">{String(e.name ?? e.reportingName ?? "—")}</span>
                    <span className="ml-2 text-muted-foreground">{String(e.title ?? e.relation ?? "—")}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
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
