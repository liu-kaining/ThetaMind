import * as React from "react"
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogClose,
} from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import {
  ChevronDown,
  ChevronRight,
  Building2,
  TrendingUp,
  FileText,
  BarChart2,
  Shield,
  Zap,
  Loader2,
} from "lucide-react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  BarChart,
  Bar,
} from "recharts"
import { TradingViewLineChart } from "@/components/charts/TradingViewLineChart"
import { Progress } from "@/components/ui/progress"
import type { FinancialProfileResponse } from "@/services/api/market"

const LOADING_EST_SECONDS = 60
const PROGRESS_UPDATE_INTERVAL_MS = 500

// ——— Formatters ———
function formatNum(val: unknown, hint?: "pct" | "currency" | "ratio"): string {
  if (val === null || val === undefined) return "—"
  if (typeof val !== "number" || !Number.isFinite(val)) return "—"
  if (hint === "pct") {
    const asPct = Math.abs(val) <= 2 && val !== 0 ? val * 100 : val
    return `${Number(asPct).toFixed(2)}%`
  }
  if (hint === "currency" || val >= 1e6)
    return val >= 1e12 ? `$${(val / 1e12).toFixed(2)}T` : val >= 1e9 ? `$${(val / 1e9).toFixed(2)}B` : val >= 1e6 ? `$${(val / 1e6).toFixed(2)}M` : `$${val.toLocaleString("en-US", { minimumFractionDigits: 2 })}`
  if (Math.abs(val) < 0.0001 && val !== 0) return val.toExponential(2)
  return val.toLocaleString("en-US", { maximumFractionDigits: 2 })
}

function metricHint(name: string): "pct" | "currency" | "ratio" | undefined {
  const n = name.toLowerCase()
  if (n.includes("return on") || n.includes("margin") || n.includes("yield"))
    return "pct"
  if (n.includes("ratio") && !n.includes("price")) return "ratio"
  if (n.includes("revenue") || n.includes("income") || n.includes("cap") || n.includes("price") || n.includes("value"))
    return "currency"
  return undefined
}

// ——— Data structure helpers ———
function isMetricToYears(obj: unknown): obj is Record<string, Record<string, unknown>> {
  if (!obj || typeof obj !== "object") return false
  const entries = Object.entries(obj as Record<string, unknown>)
  if (entries.length === 0) return false
  const [, v] = entries[0]
  return v !== null && typeof v === "object" && !Array.isArray(v)
}

function getLatestFromMetricYears(data: Record<string, Record<string, unknown>>, metricKeys: string[]): number | null {
  for (const key of metricKeys) {
    const row = data[key]
    if (!row || typeof row !== "object") continue
    const years = Object.entries(row)
      .filter(([, v]) => v != null && typeof v === "number")
      .sort(([a], [b]) => b.localeCompare(a))
    if (years.length > 0) return years[0][1] as number
  }
  return null
}

const STATEMENT_CHART_KEYS = [
  "Revenue",
  "Net Income",
  "Gross Profit",
  "Operating Income",
  "Total Assets",
  "Total Equity",
  "Operating Cash Flow",
  "Free Cash Flow",
]

const CHARTABLE_RATIO_KEYS = [
  "Price-Earnings Ratio",
  "PE",
  "P/E",
  "Return on Equity",
  "ROE",
  "Return on Assets",
  "ROA",
  "Gross Margin",
  "Gross Profit Margin",
  "Operating Margin",
]

function extractChartableStatements(statementData: Record<string, Record<string, unknown>>): Record<string, Record<string, unknown>> {
  const out: Record<string, Record<string, unknown>> = {}
  STATEMENT_CHART_KEYS.forEach((key) => {
    const row = statementData[key]
    if (!row || typeof row !== "object") return
    const hasAny = Object.values(row).some((v) => v != null && typeof v === "number")
    if (hasAny) out[key] = row
  })
  return out
}

function extractChartableRatios(ratiosAll: Record<string, Record<string, unknown>>): Record<string, Record<string, unknown>> {
  const out: Record<string, Record<string, unknown>> = {}
  const seen = new Set<string>()
  CHARTABLE_RATIO_KEYS.forEach((key) => {
    const row = ratiosAll[key]
    if (!row || typeof row !== "object") return
    const label = key === "Price-Earnings Ratio" || key === "PE" || key === "P/E" ? "P/E" : key === "Gross Profit Margin" ? "Gross Margin" : key
    if (seen.has(label)) return
    seen.add(label)
    const hasAny = Object.values(row).some((v) => v != null && typeof v === "number")
    if (hasAny) out[label] = row
  })
  return out
}

/** Pick metrics from ratios.all by exact names (for chart from table selection) */
function pickMetricsForChart(
  ratiosAll: Record<string, Record<string, unknown>>,
  metricNames: string[]
): Record<string, Record<string, unknown>> {
  if (metricNames.length === 0) return {}
  const out: Record<string, Record<string, unknown>> = {}
  metricNames.forEach((name) => {
    const row = ratiosAll[name]
    if (row && typeof row === "object") {
      const hasAny = Object.values(row).some((v) => v != null && typeof v === "number")
      if (hasAny) out[name] = row
    }
  })
  return out
}

function extractKeyRatiosSnapshot(ratiosAll: Record<string, Record<string, unknown>>): Record<string, unknown> {
  const snapshot: Record<string, unknown> = {}
  const metrics: Array<{ keys: string[]; label: string; hint?: "pct" | "currency" | "ratio" }> = [
    { keys: ["Price-Earnings Ratio", "PE", "P/E", "Price Earnings Ratio"], label: "P/E" },
    { keys: ["Price to Book Ratio", "PB", "P/B"], label: "P/B" },
    { keys: ["Return on Equity", "ROE"], label: "ROE", hint: "pct" },
    { keys: ["Return on Assets", "ROA"], label: "ROA", hint: "pct" },
    { keys: ["Gross Margin", "Gross Profit Margin"], label: "Gross Margin", hint: "pct" },
    { keys: ["Operating Margin", "Operating Profit Margin"], label: "Operating Margin", hint: "pct" },
  ]
  metrics.forEach(({ keys, label, hint }) => {
    const val = getLatestFromMetricYears(ratiosAll, keys)
    if (val != null) snapshot[label] = hint === "pct" ? `${formatNum(val, "pct")}` : val
  })
  return snapshot
}

// ——— Year-over-year table (supports row selection for chart linkage) ———
function YearOverYearTable({
  data,
  title,
  description,
  maxYears = 8,
  selectedMetrics,
  onMetricClick,
}: {
  data: Record<string, Record<string, unknown>>
  title: string
  description?: string
  maxYears?: number
  selectedMetrics?: Set<string>
  onMetricClick?: (metric: string) => void
}) {
  const metrics = Object.entries(data).filter(([, v]) => v && typeof v === "object")
  if (metrics.length === 0) return null

  const allYears = new Set<string>()
  metrics.forEach(([, years]) => {
    Object.keys(years as Record<string, unknown>).forEach((y) => allYears.add(y))
  })
  const years = Array.from(allYears)
    .sort()
    .reverse()
    .slice(0, maxYears)

  const isSelectable = !!onMetricClick

  return (
    <div className="rounded-lg border bg-card overflow-hidden w-full">
      {(title || description) && (
        <div className="px-4 py-3 border-b bg-muted/30">
          {title && <h4 className="font-semibold text-sm">{title}</h4>}
          {description && <p className="text-xs text-muted-foreground mt-0.5">{description}</p>}
          {isSelectable && (
            <p className="text-xs text-primary/80 mt-1">Click a row to show its curve in the chart above.</p>
          )}
        </div>
      )}
      <div className="overflow-x-auto w-full min-w-0">
        <table className="w-full text-sm" style={{ minWidth: "100%", tableLayout: "auto" }}>
          <thead>
            <tr className="border-b bg-primary/5">
              <th className="px-4 py-2.5 text-left font-medium text-foreground sticky left-0 bg-primary/5 min-w-[200px]">
                Metric
              </th>
              {years.map((y) => (
                <th key={y} className="px-4 py-2.5 text-right font-medium text-foreground whitespace-nowrap min-w-[100px]">
                  {y}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {metrics.map(([metric, vals], i) => {
              const row = vals as Record<string, unknown>
              const hasAny = years.some((y) => row[y] != null)
              if (!hasAny) return null
              const isSelected = selectedMetrics?.has(metric)
              return (
                <tr
                  key={metric}
                  role={isSelectable ? "button" : undefined}
                  tabIndex={isSelectable ? 0 : undefined}
                  onClick={isSelectable ? () => onMetricClick?.(metric) : undefined}
                  onKeyDown={
                    isSelectable
                      ? (e) => {
                          if (e.key === "Enter" || e.key === " ") onMetricClick?.(metric)
                        }
                      : undefined
                  }
                  className={`border-b last:border-0 transition-colors ${
                    isSelectable ? "cursor-pointer hover:bg-primary/10" : "hover:bg-muted/20"
                  } ${isSelected ? "bg-primary/15 ring-1 ring-primary/30" : ""} ${i % 2 === 1 && !isSelected ? "bg-muted/5" : ""}`}
                >
                  <td className="px-4 py-2 text-muted-foreground sticky left-0 bg-inherit min-w-[200px]">
                    {metric}
                  </td>
                  {years.map((y) => {
                    const v = row[y]
                    const hint = metricHint(metric)
                    return (
                      <td key={y} className="px-4 py-2 text-right font-mono tabular-nums whitespace-nowrap min-w-[100px]">
                        {formatNum(v, hint)}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ——— Collapsible section ———
function CollapsibleSection({
  title,
  icon: Icon,
  children,
  defaultOpen = true,
}: {
  title: string
  icon?: React.ComponentType<{ className?: string }>
  children: React.ReactNode
  defaultOpen?: boolean
}) {
  const [open, setOpen] = React.useState(defaultOpen)
  return (
    <div className="rounded-lg border overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full px-4 py-3 flex items-center gap-2 text-left font-medium hover:bg-muted/20 transition-colors"
      >
        {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
        <span>{title}</span>
        {open ? <ChevronDown className="h-4 w-4 ml-auto" /> : <ChevronRight className="h-4 w-4 ml-auto" />}
      </button>
      {open && <div className="border-t p-4">{children}</div>}
    </div>
  )
}

// ——— Key-value grid (full display, no truncation) ———
function formatValue(v: unknown): React.ReactNode {
  if (v === null || v === undefined) return "—"
  if (typeof v === "number" && Number.isFinite(v)) return v.toLocaleString("en-US", { maximumFractionDigits: 4 })
  if (typeof v === "boolean") return v ? "Yes" : "No"
  if (typeof v === "string") return v || "—"
  if (Array.isArray(v)) {
    if (v.length === 0) return "—"
    const first = v[0]
    if (typeof first === "object" && first !== null) return `[${v.length} items]`
    return v.join(", ")
  }
  if (typeof v === "object") {
    const entries = Object.entries(v as Record<string, unknown>).filter(
      ([, val]) => val !== null && val !== undefined
    )
    if (entries.length === 0) return "—"
    return entries.map(([ek, ev]) => `${ek}: ${formatValue(ev)}`).join("; ")
  }
  return String(v)
}

function KeyValueGrid({
  data,
  columns = 2,
  flattenNested = false,
}: {
  data: Record<string, unknown>
  columns?: number
  flattenNested?: boolean
}) {
  const entries = React.useMemo(() => {
    const result: Array<[string, unknown]> = []
    const walk = (obj: Record<string, unknown>, prefix = "") => {
      Object.entries(obj).forEach(([k, v]) => {
        if (flattenNested && typeof v === "object" && !Array.isArray(v) && v !== null && Object.keys(v).length > 0) {
          walk(v as Record<string, unknown>, prefix ? `${prefix}.${k}` : k)
        } else {
          result.push([prefix ? `${prefix}.${k}` : k, v])
        }
      })
    }
    walk(data)
    return result
  }, [data, flattenNested])

  const DESCRIPTION_KEYS = ["description", "companydescription", "company description"]
  const isLongDescription = (key: string, val: unknown) =>
    DESCRIPTION_KEYS.some((d) => key.toLowerCase().replace(/_/g, " ").includes(d)) &&
    typeof val === "string" &&
    (val as string).length > 200

  if (entries.length === 0) return <p className="text-sm text-muted-foreground">No data available</p>
  return (
    <dl
      className="grid gap-x-6 gap-y-2 text-sm"
      style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
    >
      {entries.map(([k, v]) => {
        const isDesc = isLongDescription(k, v)
        return (
          <div key={k} className={`flex gap-4 py-1.5 min-w-0 items-start ${isDesc ? "col-span-full flex-col" : ""}`}>
            <dt className="text-muted-foreground capitalize shrink-0">{k.replace(/_/g, " ")}</dt>
            <dd
              className={`font-mono tabular-nums break-words min-w-0 ${isDesc ? "text-left w-full" : "text-right"}`}
            >
              {isDesc ? (
                <div className="max-h-28 overflow-y-auto rounded border bg-muted/20 px-3 py-2 text-xs">
                  {formatValue(v)}
                </div>
              ) : (
                formatValue(v)
              )}
            </dd>
          </div>
        )
      })}
    </dl>
  )
}

function formatChartValue(v: number): string {
  if (v >= 1e12) return `${(v / 1e12).toFixed(2)}T`
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)}B`
  if (v >= 1e6) return `${(v / 1e6).toFixed(2)}M`
  if (Math.abs(v) < 0.01 && v !== 0) return v.toExponential(2)
  return v.toLocaleString("en-US", { maximumFractionDigits: 2 })
}

// ——— Recharts line chart (for yearly ratios, valuation, supports selectedMetrics) ———
function RatioLineChart({
  data,
  title,
  description,
  colors = ["#3b82f6", "#22c55e", "#f59e0b", "#8b5cf6"],
  valueFormat = "auto",
  selectedMetrics,
  maxYears = 10,
}: {
  data: Record<string, Record<string, unknown>>
  title: string
  description?: string
  colors?: string[]
  valueFormat?: "auto" | "currency"
  selectedMetrics?: Set<string>
  maxYears?: number
}) {
  const chartData = React.useMemo(() => {
    const source = selectedMetrics && selectedMetrics.size > 0
      ? pickMetricsForChart(data, Array.from(selectedMetrics))
      : data
    const metrics = Object.entries(source).filter(([, v]) => v && typeof v === "object")
    if (metrics.length === 0) return []
    const allDates = new Set<string>()
    metrics.forEach(([, vals]) => Object.keys(vals as Record<string, unknown>).forEach((d) => allDates.add(d)))
    const sortedDates = Array.from(allDates).sort().slice(-maxYears)
    return sortedDates.map((date) => {
      const point: Record<string, string | number> = { date }
      metrics.forEach(([metric, vals]) => {
        const v = (vals as Record<string, unknown>)[date]
        if (v != null && typeof v === "number" && Number.isFinite(v)) point[metric] = v
      })
      return point
    })
  }, [data, selectedMetrics, maxYears])
  const source = selectedMetrics && selectedMetrics.size > 0
    ? pickMetricsForChart(data, Array.from(selectedMetrics))
    : data
  const series = Object.entries(source).filter(([, v]) => v && typeof v === "object").map(([n]) => n)
  const fmt = valueFormat === "currency" ? (v: number) => (v >= 1e9 ? `$${formatChartValue(v)}` : `$${Number(v).toLocaleString()}`) : formatChartValue
  if (chartData.length < 2 || series.length === 0) return null
  return (
    <div className="rounded-lg border overflow-hidden w-full">
      {(title || description) && (
        <div className="px-4 py-3 border-b bg-muted/30">
          {title && <h4 className="font-semibold text-sm">{title}</h4>}
          {description && <p className="text-xs text-muted-foreground mt-0.5">{description}</p>}
        </div>
      )}
      <div className="p-4 h-[360px] w-full min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(v) => String(v).slice(0, 7)} />
            <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => formatChartValue(Number(v))} />
            <Tooltip
              contentStyle={{
                fontSize: 12,
                backgroundColor: "hsl(var(--card))",
                color: "hsl(var(--foreground))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "var(--radius)",
              }}
              cursor={{ fill: "transparent" }}
              formatter={(val: number) => [fmt(Number(val)), ""]}
            />
            <Legend />
            {series.map((s, i) => (
              <Line key={s} type="monotone" dataKey={s} stroke={colors[i % colors.length]} strokeWidth={2} dot={false} connectNulls />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// ——— Statements bar chart (supports selectedMetrics for linkage) ———
function StatementBarChart({
  data,
  title,
  description,
  maxYears = 6,
  selectedMetrics,
}: {
  data: Record<string, Record<string, unknown>>
  title: string
  description?: string
  maxYears?: number
  selectedMetrics?: Set<string>
}) {
  const chartData = React.useMemo(() => {
    const source = selectedMetrics && selectedMetrics.size > 0
      ? pickMetricsForChart(data, Array.from(selectedMetrics))
      : extractChartableStatements(data)
    const metrics = Object.entries(source).filter(([, v]) => v && typeof v === "object")
    if (metrics.length === 0) return []
    const allYears = new Set<string>()
    metrics.forEach(([, vals]) => Object.keys(vals as Record<string, unknown>).forEach((y) => allYears.add(y)))
    const years = Array.from(allYears).sort().reverse().slice(0, maxYears)
    return years.map((year) => {
      const point: Record<string, string | number> = { year }
      metrics.forEach(([name, vals]) => {
        const v = (vals as Record<string, unknown>)[year]
        if (v != null && typeof v === "number" && Number.isFinite(v)) point[name] = v
      })
      return point
    }).reverse()
  }, [data, maxYears, selectedMetrics])
  const source = selectedMetrics && selectedMetrics.size > 0
    ? pickMetricsForChart(data, Array.from(selectedMetrics))
    : extractChartableStatements(data)
  const series = Object.keys(source)
  const colors = ["#3b82f6", "#22c55e", "#f59e0b", "#8b5cf6", "#ec4899", "#14b8a6"]
  if (chartData.length === 0 || series.length === 0) return null
  return (
    <div className="rounded-lg border overflow-hidden w-full">
      <div className="px-4 py-3 border-b bg-muted/30">
        <h4 className="font-semibold text-sm">{title}</h4>
        {description && <p className="text-xs text-muted-foreground mt-0.5">{description}</p>}
      </div>
      <div className="p-4 h-[360px] w-full min-w-0">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis dataKey="year" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => (v >= 1e9 ? `${(v / 1e9).toFixed(1)}B` : v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : String(v))} />
            <Tooltip
              contentStyle={{
                fontSize: 11,
                backgroundColor: "hsl(var(--card))",
                color: "hsl(var(--foreground))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "var(--radius)",
              }}
              cursor={{ fill: "transparent" }}
              formatter={(val: number) => [val >= 1e9 ? `$${(val / 1e9).toFixed(2)}B` : val >= 1e6 ? `$${(val / 1e6).toFixed(2)}M` : `$${Number(val).toLocaleString()}`, ""]}
            />
            <Legend />
            {series.slice(0, 6).map((s, i) => (
              <Bar key={s} dataKey={s} fill={colors[i % colors.length]} radius={[2, 2, 0, 0]} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

// Normalize { date: { metric: value } } -> { metric: { date: value } } for tables/charts
function normalizeToMetricDates(data: Record<string, Record<string, unknown>>): Record<string, Record<string, unknown>> {
  const entries = Object.entries(data).filter(([, v]) => v && typeof v === "object")
  if (entries.length === 0) return {}
  const firstKey = entries[0][0]
  const firstInner = entries[0][1] as Record<string, unknown>
  const topLooksLikeDate = /^\d{4}(-\d{2}-\d{2})?([\sT]|$|\.)?/.test(String(firstKey).trim()) || /^\d{4}$/.test(String(firstKey).trim())
  const innerLooksLikeDate = Object.keys(firstInner).some((k) => /^\d{4}(-\d{2}-\d{2})?([\sT]|$|\.)?/.test(String(k).trim()) || /^\d{4}$/.test(String(k).trim()))
  if (topLooksLikeDate && !innerLooksLikeDate) {
    const out: Record<string, Record<string, unknown>> = {}
    entries.forEach(([dateKey, inner]) => {
      Object.entries(inner as Record<string, unknown>).forEach(([metric, val]) => {
        if (val == null || (typeof val !== "number" && typeof val !== "string")) return
        if (typeof val === "number" && !Number.isFinite(val)) return
        if (!out[metric]) out[metric] = {}
        out[metric][dateKey] = val
      })
    })
    return out
  }
  return data
}

// ——— Lazy Technical/Risk chart (TradingView lightweight-charts) ———
function LazyTechnicalChart({
  data,
  colors,
}: {
  data: Record<string, Record<string, unknown>>
  colors?: string[]
}) {
  const chart = <TradingViewLineChart data={data} height={360} colors={colors} maxPoints={120} />
  const normalized = normalizeToMetricDates(data)
  const hasTableData = Object.keys(normalized).length > 0
  return (
    <div className="rounded overflow-hidden space-y-4">
      <p className="text-xs text-muted-foreground mb-2">Last 120 data points. Professional TradingView-style chart.</p>
      {chart}
      {hasTableData && (
        <YearOverYearTable data={normalized} title="" description="Data table (chart above when chartable)." maxYears={15} />
      )}
    </div>
  )
}

// ——— Key metrics strip ———
function KeyMetricsStrip({
  profile,
  ratios,
}: {
  profile: Record<string, unknown> | undefined
  ratios: Record<string, Record<string, Record<string, unknown>>> | undefined
}) {
  const metrics: { label: string; value: string }[] = []

  if (profile) {
    const price = profile.Price ?? profile.price
    if (typeof price === "number") metrics.push({ label: "Price", value: `$${Number(price).toFixed(2)}` })
    const mc = profile["Market Capitalization"] ?? profile.marketCap ?? profile.MarketCapitalization
    if (typeof mc === "number") metrics.push({ label: "Market Cap", value: formatNum(mc, "currency") })
    const beta = profile.Beta ?? profile.beta
    if (typeof beta === "number") metrics.push({ label: "Beta", value: Number(beta).toFixed(2) })
  }

  if (ratios?.all && isMetricToYears(ratios.all)) {
    const pe = getLatestFromMetricYears(ratios.all as Record<string, Record<string, unknown>>, [
      "Price-Earnings Ratio",
      "PE",
      "P/E",
      "Price Earnings Ratio",
    ])
    if (pe != null) metrics.push({ label: "P/E", value: formatNum(pe) })
    const pb = getLatestFromMetricYears(ratios.all as Record<string, Record<string, unknown>>, [
      "Price to Book Ratio",
      "PB",
      "P/B",
      "Price-Book Ratio",
    ])
    if (pb != null) metrics.push({ label: "P/B", value: formatNum(pb) })
    const roe = getLatestFromMetricYears(ratios.all as Record<string, Record<string, unknown>>, [
      "Return on Equity",
      "ROE",
    ])
    if (roe != null) metrics.push({ label: "ROE", value: formatNum(roe, "pct") })
    const roa = getLatestFromMetricYears(ratios.all as Record<string, Record<string, unknown>>, [
      "Return on Assets",
      "ROA",
    ])
    if (roa != null) metrics.push({ label: "ROA", value: formatNum(roa, "pct") })
  }

  if (metrics.length === 0) return null
  return (
    <div className="flex flex-wrap gap-4 py-3 px-4 rounded-lg bg-muted/20 border">
      {metrics.map(({ label, value }) => (
        <div key={label} className="flex flex-col">
          <span className="text-xs text-muted-foreground uppercase tracking-wide">{label}</span>
          <span className="font-semibold font-mono tabular-nums">{value}</span>
        </div>
      ))}
    </div>
  )
}

interface ProfileDataDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  profile: FinancialProfileResponse | undefined
  symbol: string
  isLoading?: boolean
}

export const ProfileDataDialog: React.FC<ProfileDataDialogProps> = ({
  open,
  onOpenChange,
  profile,
  symbol,
  isLoading = false,
}) => {
  const [selectedRatioMetrics, setSelectedRatioMetrics] = React.useState<Set<string>>(new Set())
  const [selectedStatementMetrics, setSelectedStatementMetrics] = React.useState<Record<string, Set<string>>>({})
  const [selectedValuationMetrics, setSelectedValuationMetrics] = React.useState<Record<string, Set<string>>>({})

  const toggleRatioMetric = React.useCallback((metric: string) => {
    setSelectedRatioMetrics((prev) => {
      const next = new Set(prev)
      if (next.has(metric)) {
        next.delete(metric)
      } else {
        if (next.size >= 6) {
          const first = next.values().next().value
          if (first) next.delete(first)
        }
        next.add(metric)
      }
      return next
    })
  }, [])

  const toggleStatementMetric = React.useCallback((stmtKey: string, metric: string) => {
    setSelectedStatementMetrics((prev) => {
      const next = { ...prev }
      const set = new Set(next[stmtKey] ?? [])
      if (set.has(metric)) set.delete(metric)
      else {
        if (set.size >= 6) set.delete([...set][0])
        set.add(metric)
      }
      next[stmtKey] = set
      return next
    })
  }, [])

  const toggleValuationMetric = React.useCallback((blockKey: string, metric: string) => {
    setSelectedValuationMetrics((prev) => {
      const next = { ...prev }
      const set = new Set(next[blockKey] ?? [])
      if (set.has(metric)) set.delete(metric)
      else {
        if (set.size >= 6) set.delete([...set][0])
        set.add(metric)
      }
      next[blockKey] = set
      return next
    })
  }, [])

  const chartDataForRatios = React.useMemo(() => {
    if (!profile?.ratios?.all || !isMetricToYears(profile.ratios.all)) return {}
    const all = profile.ratios.all as Record<string, Record<string, unknown>>
    if (selectedRatioMetrics.size > 0) {
      return pickMetricsForChart(all, Array.from(selectedRatioMetrics))
    }
    return extractChartableRatios(all)
  }, [profile?.ratios?.all, selectedRatioMetrics])

  const companyName =
    (profile?.profile as Record<string, unknown>)?.companyName ??
    (profile?.profile as Record<string, unknown>)?.["Company Name"] ??
    (profile?.profile as Record<string, unknown>)?.name ??
    ""
  const exchange =
    (profile?.profile as Record<string, unknown>)?.exchangeShortName ??
    (profile?.profile as Record<string, unknown>)?.["Exchange Short Name"] ??
    (profile?.profile as Record<string, unknown>)?.exchange ??
    ""
  const sector = (profile?.profile as Record<string, unknown>)?.sector ?? ""
  const industry = (profile?.profile as Record<string, unknown>)?.industry ?? ""

  const hasData = profile && !profile.error && (profile.profile || profile.ratios || profile.technical_indicators)
  const showLoadingHint = isLoading && !hasData
  const showEmptyHint = !isLoading && !hasData && open

  const [loadingProgress, setLoadingProgress] = React.useState(0)
  const [elapsedSeconds, setElapsedSeconds] = React.useState(0)

  React.useEffect(() => {
    if (!showLoadingHint) {
      setLoadingProgress(0)
      setElapsedSeconds(0)
      return
    }
    const startTime = Date.now()
    const interval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - startTime) / 1000)
      setElapsedSeconds(elapsed)
      const progress = Math.min(95, (elapsed / LOADING_EST_SECONDS) * 95)
      setLoadingProgress(progress)
    }, PROGRESS_UPDATE_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [showLoadingHint])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="h-[90vh] min-h-[600px] overflow-hidden flex flex-col p-0"
        style={{ width: '85vw', minWidth: '85vw', maxWidth: '85vw' }}
      >
        <DialogClose onClose={() => onOpenChange(false)} />
        <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
          {/* Hero header */}
          <div className="flex-shrink-0 px-6 py-5 border-b bg-gradient-to-b from-primary/5 to-background">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <DialogTitle className="text-2xl font-bold">{symbol || "—"}</DialogTitle>
                  <Badge variant="secondary" className="text-xs bg-primary/15 text-primary border-primary/30">
                    FMP Premium
                  </Badge>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">
                  {companyName ? (
                    <span className="font-medium text-foreground">{String(companyName)}</span>
                  ) : null}
                  {exchange || sector || industry ? (
                    <span className="ml-2">
                      {String(exchange || "")}
                      {sector ? ` · ${String(sector)}` : ""}
                      {industry ? ` · ${String(industry)}` : ""}
                    </span>
                  ) : null}
                </p>
              </div>
            </div>
            {profile?.error && (
              <p className="mt-3 text-sm text-destructive rounded border border-destructive/30 p-3 bg-destructive/5">
                {profile.error}
              </p>
            )}
            {showLoadingHint && (
              <div className="mt-4 p-4 rounded-lg border bg-muted/20 space-y-3">
                <div className="flex items-center gap-3 text-muted-foreground">
                  <Loader2 className="h-5 w-5 animate-spin shrink-0" />
                  <div>
                    <p className="text-sm font-medium">Fetching comprehensive fundamental data...</p>
                    <p className="text-xs mt-0.5">
                      Typically 30–60 seconds · Elapsed: {elapsedSeconds}s
                    </p>
                  </div>
                </div>
                <Progress value={loadingProgress} className="h-2" />
              </div>
            )}
            {showEmptyHint && !profile?.error && (
              <div className="mt-4 flex items-center gap-3 p-4 rounded-lg border bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-400">
                <Zap className="h-5 w-5 shrink-0" />
                <p className="text-sm">No data yet. Data will be available shortly after loading. Please wait a moment and try again.</p>
              </div>
            )}
            {!profile?.error && profile && !showLoadingHint && (
              <div className="mt-4">
                <KeyMetricsStrip
                  profile={profile.profile as Record<string, unknown>}
                  ratios={profile.ratios as Record<string, Record<string, Record<string, unknown>>>}
                />
              </div>
            )}
          </div>

          {/* Tabs */}
          <Tabs defaultValue="ratios" className="flex-1 min-h-0 flex flex-col overflow-hidden">
            <TabsList className="flex-shrink-0 mx-6 mt-4 h-10 bg-muted/80 border border-border">
              <TabsTrigger value="ratios" className="gap-1.5 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-sm">
                <BarChart2 className="h-4 w-4" />
                Financial Ratios
              </TabsTrigger>
              <TabsTrigger value="statements" className="gap-1.5 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-sm">
                <FileText className="h-4 w-4" />
                Statements
              </TabsTrigger>
              <TabsTrigger value="valuation" className="gap-1.5 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-sm">
                <TrendingUp className="h-4 w-4" />
                Valuation
              </TabsTrigger>
              <TabsTrigger value="analysis" className="gap-1.5 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-sm">
                <Shield className="h-4 w-4" />
                Analysis
              </TabsTrigger>
              <TabsTrigger value="technicals" className="gap-1.5 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-sm">
                <Zap className="h-4 w-4" />
                Technical & Risk
              </TabsTrigger>
              <TabsTrigger value="profile" className="gap-1.5 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground data-[state=active]:shadow-sm">
                <Building2 className="h-4 w-4" />
                Profile
              </TabsTrigger>
            </TabsList>

            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6 min-h-[520px] w-full min-w-0">
              <TabsContent value="ratios" className="mt-0 space-y-6 w-full min-w-0">
                {profile?.ratios?.all && isMetricToYears(profile.ratios.all) && (
                  <>
                    <RatioLineChart
                      data={chartDataForRatios}
                      title="Key Ratios Over Time"
                      description={
                        selectedRatioMetrics.size > 0
                          ? `Showing selected: ${Array.from(selectedRatioMetrics).join(", ")}`
                          : "Default: P/E, ROE, ROA, Gross Margin. Click table rows below to show in chart."
                      }
                      colors={["#3b82f6", "#22c55e", "#f59e0b", "#8b5cf6", "#ec4899", "#14b8a6"]}
                    />
                    <YearOverYearTable
                      data={profile.ratios.all as Record<string, Record<string, unknown>>}
                      title="All Financial Ratios"
                      description="Comprehensive ratio history. Scroll horizontally for more years."
                      maxYears={10}
                      selectedMetrics={selectedRatioMetrics}
                      onMetricClick={toggleRatioMetric}
                    />
                  </>
                )}
                {profile?.ratios?.valuation && isMetricToYears(profile.ratios.valuation) && (
                  <CollapsibleSection title="Valuation Ratios" icon={TrendingUp} defaultOpen={false}>
                    <YearOverYearTable
                      data={profile.ratios.valuation as Record<string, Record<string, unknown>>}
                      title=""
                      maxYears={8}
                    />
                  </CollapsibleSection>
                )}
                {profile?.ratios?.profitability && isMetricToYears(profile.ratios.profitability) && (
                  <CollapsibleSection title="Profitability Ratios" icon={TrendingUp} defaultOpen={false}>
                    <YearOverYearTable
                      data={profile.ratios.profitability as Record<string, Record<string, unknown>>}
                      title=""
                      maxYears={8}
                    />
                  </CollapsibleSection>
                )}
                {profile?.ratios?.liquidity && isMetricToYears(profile.ratios.liquidity) && (
                  <CollapsibleSection title="Liquidity Ratios" defaultOpen={false}>
                    <YearOverYearTable
                      data={profile.ratios.liquidity as Record<string, Record<string, unknown>>}
                      title=""
                      maxYears={8}
                    />
                  </CollapsibleSection>
                )}
                {profile?.ratios?.solvency && isMetricToYears(profile.ratios.solvency) && (
                  <CollapsibleSection title="Solvency Ratios" defaultOpen={false}>
                    <YearOverYearTable
                      data={profile.ratios.solvency as Record<string, Record<string, unknown>>}
                      title=""
                      maxYears={8}
                    />
                  </CollapsibleSection>
                )}
                {(!profile?.ratios || Object.keys(profile.ratios).length === 0) && (
                  <p className="text-sm text-muted-foreground py-8 text-center">No ratios data available</p>
                )}
              </TabsContent>

              <TabsContent value="statements" className="mt-0 space-y-6 w-full min-w-0">
                {profile?.financial_statements &&
                  Object.entries(profile.financial_statements).map(([key, val]) =>
                    val && typeof val === "object" && isMetricToYears(val) ? (
                      <CollapsibleSection
                        key={key}
                        title={`${key.charAt(0).toUpperCase() + key.slice(1)} Statement`}
                        icon={FileText}
                        defaultOpen={key === "income"}
                      >
                        <StatementBarChart
                          data={val as Record<string, Record<string, unknown>>}
                          title={`${key.charAt(0).toUpperCase() + key.slice(1)} — Key Metrics`}
                          description={
                            (selectedStatementMetrics[key]?.size ?? 0) > 0
                              ? `Showing selected: ${Array.from(selectedStatementMetrics[key] ?? []).join(", ")}`
                              : "Click table rows below to show in chart. Multi-select supported."
                          }
                          maxYears={6}
                          selectedMetrics={selectedStatementMetrics[key]}
                        />
                        <YearOverYearTable
                          data={val as Record<string, Record<string, unknown>>}
                          title=""
                          description="Full data. Scroll horizontally for more years."
                          maxYears={6}
                          selectedMetrics={selectedStatementMetrics[key]}
                          onMetricClick={(m) => toggleStatementMetric(key, m)}
                        />
                      </CollapsibleSection>
                    ) : null
                  )}
                {(!profile?.financial_statements || Object.keys(profile.financial_statements).length === 0) && (
                  <p className="text-sm text-muted-foreground py-8 text-center">No financial statements available</p>
                )}
              </TabsContent>

              <TabsContent value="valuation" className="mt-0 space-y-6 w-full min-w-0">
                <p className="text-sm text-muted-foreground mb-2">Click table rows to show in chart. Multi-select supported.</p>
                {profile?.valuation &&
                  Object.entries(profile.valuation).map(([key, val]) =>
                    val && typeof val === "object" && isMetricToYears(val) ? (
                      <CollapsibleSection
                        key={key}
                        title={`Valuation: ${key.replace(/_/g, " ")}`}
                        icon={TrendingUp}
                        defaultOpen={key === "enterprise_value"}
                      >
                        <RatioLineChart
                          data={val as Record<string, Record<string, unknown>>}
                          title={`Valuation: ${key.replace(/_/g, " ")}`}
                          description={
                            (selectedValuationMetrics[`valuation.${key}`]?.size ?? 0) > 0
                              ? `Showing: ${Array.from(selectedValuationMetrics[`valuation.${key}`] ?? []).join(", ")}`
                              : "Click table rows below to show in chart."
                          }
                          maxYears={8}
                          valueFormat="currency"
                          selectedMetrics={selectedValuationMetrics[`valuation.${key}`]}
                          colors={["#3b82f6", "#22c55e", "#f59e0b", "#8b5cf6", "#ec4899", "#14b8a6"]}
                        />
                        <YearOverYearTable
                          data={val as Record<string, Record<string, unknown>>}
                          title=""
                          maxYears={8}
                          selectedMetrics={selectedValuationMetrics[`valuation.${key}`]}
                          onMetricClick={(m) => toggleValuationMetric(`valuation.${key}`, m)}
                        />
                      </CollapsibleSection>
                    ) : null
                  )}
                {profile?.dupont_analysis?.standard && isMetricToYears(profile.dupont_analysis.standard) && (
                  <CollapsibleSection title="DuPont Analysis (Standard)" icon={TrendingUp} defaultOpen={true}>
                    <RatioLineChart
                      data={profile.dupont_analysis.standard as Record<string, Record<string, unknown>>}
                      title="DuPont Analysis (Standard)"
                      description={
                        (selectedValuationMetrics["dupont_standard"]?.size ?? 0) > 0
                          ? `Showing: ${Array.from(selectedValuationMetrics["dupont_standard"] ?? []).join(", ")}`
                          : "Click table rows below to show in chart."
                      }
                      maxYears={8}
                      selectedMetrics={selectedValuationMetrics["dupont_standard"]}
                      colors={["#8b5cf6", "#ec4899", "#14b8a6", "#f59e0b", "#3b82f6"]}
                    />
                    <YearOverYearTable
                      data={profile.dupont_analysis.standard as Record<string, Record<string, unknown>>}
                      title=""
                      maxYears={8}
                      selectedMetrics={selectedValuationMetrics["dupont_standard"]}
                      onMetricClick={(m) => toggleValuationMetric("dupont_standard", m)}
                    />
                  </CollapsibleSection>
                )}
                {profile?.dupont_analysis?.extended && isMetricToYears(profile.dupont_analysis.extended) && (
                  <CollapsibleSection title="DuPont Analysis (Extended)" icon={TrendingUp} defaultOpen={false}>
                    <RatioLineChart
                      data={profile.dupont_analysis.extended as Record<string, Record<string, unknown>>}
                      title="DuPont Analysis (Extended)"
                      description={
                        (selectedValuationMetrics["dupont_extended"]?.size ?? 0) > 0
                          ? `Showing: ${Array.from(selectedValuationMetrics["dupont_extended"] ?? []).join(", ")}`
                          : "Click table rows below to show in chart."
                      }
                      maxYears={8}
                      selectedMetrics={selectedValuationMetrics["dupont_extended"]}
                      colors={["#14b8a6", "#f59e0b", "#ef4444", "#3b82f6", "#8b5cf6"]}
                    />
                    <YearOverYearTable
                      data={profile.dupont_analysis.extended as Record<string, Record<string, unknown>>}
                      title=""
                      maxYears={8}
                      selectedMetrics={selectedValuationMetrics["dupont_extended"]}
                      onMetricClick={(m) => toggleValuationMetric("dupont_extended", m)}
                    />
                  </CollapsibleSection>
                )}
                {(!profile?.valuation || Object.keys(profile.valuation).length === 0) &&
                  !profile?.dupont_analysis && (
                  <p className="text-sm text-muted-foreground py-8 text-center">No valuation data available</p>
                )}
              </TabsContent>

              <TabsContent value="analysis" className="mt-0 space-y-6 w-full min-w-0">
                {profile?.analysis?.health_score && Object.keys(profile.analysis.health_score).length > 0 && (
                  <CollapsibleSection title="Health Score" icon={Shield} defaultOpen={true}>
                    <KeyValueGrid
                      data={profile.analysis.health_score as Record<string, unknown>}
                      columns={2}
                      flattenNested
                    />
                  </CollapsibleSection>
                )}
                {profile?.analysis?.risk_score && Object.keys(profile.analysis.risk_score).length > 0 && (
                  <CollapsibleSection title="Risk Score" icon={Shield} defaultOpen={true}>
                    <KeyValueGrid
                      data={profile.analysis.risk_score as Record<string, unknown>}
                      columns={2}
                      flattenNested
                    />
                  </CollapsibleSection>
                )}
                {profile?.analysis?.technical_signals &&
                  Object.keys(profile.analysis.technical_signals).length > 0 && (
                  <CollapsibleSection title="Technical Signals" icon={Zap} defaultOpen={true}>
                    <KeyValueGrid
                      data={profile.analysis.technical_signals as unknown as Record<string, unknown>}
                      columns={2}
                    />
                  </CollapsibleSection>
                )}
                {profile?.analysis?.warnings && profile.analysis.warnings.length > 0 && (
                  <CollapsibleSection title="Warnings" defaultOpen={true}>
                    <ul className="list-disc list-inside text-sm text-amber-600 dark:text-amber-400">
                      {profile.analysis.warnings.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  </CollapsibleSection>
                )}
                {profile?.ratios?.all && isMetricToYears(profile.ratios.all) && (
                  <CollapsibleSection title="Key Ratios Snapshot" icon={BarChart2} defaultOpen={false}>
                    <KeyValueGrid
                      data={extractKeyRatiosSnapshot(profile.ratios.all as Record<string, Record<string, unknown>>)}
                      columns={3}
                    />
                  </CollapsibleSection>
                )}
                {(!profile?.analysis || Object.keys(profile.analysis).length === 0) &&
                  !profile?.ratios?.all && (
                  <p className="text-sm text-muted-foreground py-8 text-center">No analysis data available</p>
                )}
              </TabsContent>

              <TabsContent value="technicals" className="mt-0 space-y-4 w-full min-w-0">
                <p className="text-sm text-muted-foreground mb-2">
                  Click to expand — charts load on demand (TradingView lightweight-charts).
                </p>
                {profile?.technical_indicators &&
                  Object.entries(profile.technical_indicators).map(([key, val]) =>
                    val && typeof val === "object" && isMetricToYears(val) ? (
                      <CollapsibleSection
                        key={key}
                        title={`Technical: ${key}`}
                        icon={Zap}
                        defaultOpen={false}
                      >
                        <LazyTechnicalChart
                          data={val as Record<string, Record<string, unknown>>}
                          colors={["#3b82f6", "#22c55e", "#f59e0b", "#ef4444"]}
                        />
                      </CollapsibleSection>
                    ) : null
                  )}
                {profile?.risk_metrics &&
                  Object.entries(profile.risk_metrics).map(([key, val]) =>
                    val && typeof val === "object" && isMetricToYears(val) ? (
                      <CollapsibleSection key={key} title={`Risk: ${key}`} icon={Shield} defaultOpen={false}>
                        <LazyTechnicalChart
                          data={val as Record<string, Record<string, unknown>>}
                          colors={["#8b5cf6", "#ec4899", "#14b8a6"]}
                        />
                      </CollapsibleSection>
                    ) : null
                  )}
                {profile?.performance_metrics &&
                  Object.entries(profile.performance_metrics).map(([key, val]) =>
                    val && typeof val === "object" && isMetricToYears(val) ? (
                      <CollapsibleSection key={key} title={`Performance: ${key}`} icon={TrendingUp} defaultOpen={false}>
                        <LazyTechnicalChart
                          data={val as Record<string, Record<string, unknown>>}
                          colors={["#f59e0b", "#10b981", "#6366f1"]}
                        />
                      </CollapsibleSection>
                    ) : null
                  )}
                {(!profile?.technical_indicators || Object.keys(profile.technical_indicators).length === 0) &&
                  (!profile?.risk_metrics || Object.keys(profile.risk_metrics).length === 0) &&
                  (!profile?.performance_metrics || Object.keys(profile.performance_metrics).length === 0) && (
                  <p className="text-sm text-muted-foreground py-8 text-center">
                    No technical, risk, or performance data available
                  </p>
                )}
              </TabsContent>

              <TabsContent value="profile" className="mt-0">
                {profile?.profile && Object.keys(profile.profile).length > 0 ? (
                  <div className="rounded-lg border p-4">
                    <h4 className="font-semibold mb-3">Company Profile</h4>
                    <KeyValueGrid
                      data={profile.profile as Record<string, unknown>}
                      columns={3}
                      flattenNested
                    />
                  </div>
                ) : profile?.ratios?.all && isMetricToYears(profile.ratios.all) ? (
                  <div className="rounded-lg border p-4">
                    <p className="text-sm text-muted-foreground mb-3">
                      Full company profile not available. Showing key ratios from available data.
                    </p>
                    <KeyValueGrid
                      data={{
                        symbol: profile?.ticker || symbol,
                        ...extractKeyRatiosSnapshot(profile.ratios.all as Record<string, Record<string, unknown>>),
                      }}
                      columns={3}
                    />
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground py-8 text-center">No profile data available</p>
                )}
              </TabsContent>
            </div>
          </Tabs>
        </div>
      </DialogContent>
    </Dialog>
  )
}
