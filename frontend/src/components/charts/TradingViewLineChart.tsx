/**
 * TradingView-style line chart using lightweight-charts.
 * Used for technical indicators, risk metrics, and time-series data.
 * Supports multiple series with on-demand rendering.
 */
import * as React from "react"
import { createChart, IChartApi, ISeriesApi, LineData } from "lightweight-charts"

const MAX_POINTS = 120 // Limit for performance

// yyyy-mm-dd or yyyy-mm-dd hh:mm:ss
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}([\sT]|$|\.)/
// Year-only (e.g. risk/performance metrics: "2013", "2014")
const YEAR_PATTERN = /^\d{4}$/

function isValidDateKey(s: string): boolean {
  const t = String(s).trim()
  return DATE_PATTERN.test(t) || YEAR_PATTERN.test(t)
}

function toLightweightTime(dateStr: string): string {
  const t = String(dateStr).trim()
  if (YEAR_PATTERN.test(t)) return `${t}-01-01`
  const d = t.slice(0, 10)
  if (/^\d{4}-\d{2}-\d{2}$/.test(d)) return d
  if (DATE_PATTERN.test(t)) return d || t.slice(0, 10)
  return ""
}

/**
 * Normalize data to { metric: { date: value } }.
 * API may return either { metric: { date: value } } or { date: { metric: value } }.
 */
function normalizeToMetricDateValue(
  data: Record<string, Record<string, unknown>>
): Record<string, Record<string, unknown>> {
  const entries = Object.entries(data).filter(([, v]) => v && typeof v === "object")
  if (entries.length === 0) return {}

  const firstKey = entries[0][0]
  const firstInnerKeys = Object.keys(entries[0][1] as Record<string, unknown>)

  const topLevelLooksLikeDates = isValidDateKey(firstKey)
  const innerLooksLikeDates = firstInnerKeys.some(isValidDateKey)

  if (topLevelLooksLikeDates && !innerLooksLikeDates) {
    // { date: { metric: value } } -> invert to { metric: { date: value } }
    const out: Record<string, Record<string, unknown>> = {}
    entries.forEach(([dateKey, inner]) => {
      if (!isValidDateKey(dateKey)) return
      Object.entries(inner as Record<string, unknown>).forEach(([metric, val]) => {
        if (val == null || typeof val !== "number" || !Number.isFinite(val)) return
        if (!out[metric]) out[metric] = {}
        out[metric][dateKey] = val
      })
    })
    return out
  }

  return data as Record<string, Record<string, unknown>>
}

function metricToSeries(
  data: Record<string, Record<string, unknown>>,
  maxPoints: number
): Array<{ name: string; lineData: LineData[] }> {
  const normalized = normalizeToMetricDateValue(data)
  const metrics = Object.entries(normalized).filter(([, v]) => v && typeof v === "object")
  if (metrics.length === 0) return []

  const allDates = new Set<string>()
  metrics.forEach(([, vals]) => {
    Object.keys(vals as Record<string, unknown>)
      .filter(isValidDateKey)
      .forEach((d) => allDates.add(d))
  })
  const sortedDates = Array.from(allDates).sort().slice(-maxPoints)

  return metrics
    .map(([name, vals]) => {
      const row = vals as Record<string, unknown>
      const lineData: LineData[] = []
      for (const d of sortedDates) {
        const v = row[d]
        if (v == null || typeof v !== "number" || !Number.isFinite(v)) continue
        const t = toLightweightTime(d)
        if (!t) continue
        lineData.push({ time: t, value: v })
      }
      return { name, lineData }
    })
    .filter((s) => s.lineData.length >= 2)
}

const SERIES_COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899"]

function formatPriceLabel(price: number): string {
  const abs = Math.abs(price)
  if (abs >= 1e12) return `${(price / 1e12).toFixed(2)}T`
  if (abs >= 1e9) return `${(price / 1e9).toFixed(2)}B`
  if (abs >= 1e6) return `${(price / 1e6).toFixed(2)}M`
  if (abs >= 1e3) return `${(price / 1e3).toFixed(2)}K`
  if (abs < 0.01 && price !== 0) return price.toExponential(2)
  if (abs >= 100) return price.toFixed(1)
  if (abs >= 1) return price.toFixed(2)
  return price.toFixed(2)
}

interface TradingViewLineChartProps {
  data: Record<string, Record<string, unknown>>
  height?: number
  colors?: string[]
  maxPoints?: number
}

export const TradingViewLineChart: React.FC<TradingViewLineChartProps> = ({
  data,
  height = 280,
  colors = SERIES_COLORS,
  maxPoints = MAX_POINTS,
}) => {
  const containerRef = React.useRef<HTMLDivElement>(null)
  const chartRef = React.useRef<IChartApi | null>(null)
  const seriesRef = React.useRef<ISeriesApi<"Line">[]>([])

  const seriesData = React.useMemo(() => metricToSeries(data, maxPoints), [data, maxPoints])

  const getResolvedColor = React.useCallback((cssVar: string, fallback: string) => {
    if (typeof document === "undefined") return fallback
    const value = getComputedStyle(document.documentElement).getPropertyValue(cssVar).trim()
    if (!value) return fallback
    const normalized = value.replace(/\s+/g, " ").trim()
    const hsl = normalized.includes(",") ? `hsl(${normalized})` : `hsl(${normalized.replace(/\s/g, ", ")})`
    const temp = document.createElement("span")
    temp.style.color = hsl
    document.body.appendChild(temp)
    const resolved = getComputedStyle(temp).color
    if (temp.parentNode === document.body) {
      document.body.removeChild(temp)
    }
    return resolved || fallback
  }, [])

  React.useEffect(() => {
    if (!containerRef.current || seriesData.length === 0) return

    const textColor = getResolvedColor("--foreground", "#0f172a")
    const gridColor = getResolvedColor("--border", "rgba(148, 163, 184, 0.3)")
    const backgroundColor = getResolvedColor("--card", "transparent")

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height,
      layout: {
        background: { color: backgroundColor },
        textColor,
        fontSize: 13,
        fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
      },
      localization: {
        priceFormatter: formatPriceLabel,
      },
      grid: { vertLines: { color: gridColor }, horzLines: { color: gridColor } },
      crosshair: {
        mode: 1,
        vertLine: { color: gridColor, width: 1, style: 2 },
        horzLine: { color: gridColor, width: 1, style: 2 },
      },
      rightPriceScale: {
        borderColor: gridColor,
        scaleMargins: { top: 0.08, bottom: 0.08 },
        borderVisible: true,
        entireTextOnly: false,
      },
      timeScale: {
        borderColor: gridColor,
        rightOffset: 12,
        barSpacing: 6,
        fixLeftEdge: true,
        fixRightEdge: true,
      },
    })

    const series: ISeriesApi<"Line">[] = []
    seriesData.forEach(({ lineData }, i) => {
      const lineSeries = chart.addLineSeries({
        color: colors[i % colors.length],
        lineWidth: 2,
        priceLineVisible: true,
        lastValueVisible: false,
        title: "",
      })
      lineSeries.setData(lineData)
      series.push(lineSeries)
    })

    chartRef.current = chart
    seriesRef.current = series

    const handleResize = () => {
      if (containerRef.current && chart) {
        chart.applyOptions({ width: containerRef.current.clientWidth })
      }
    }
    window.addEventListener("resize", handleResize)

    return () => {
      window.removeEventListener("resize", handleResize)
      chart.remove()
      chartRef.current = null
      seriesRef.current = []
    }
  }, [seriesData, height, colors, getResolvedColor])

  if (seriesData.length === 0) return null

  return (
    <div className="flex flex-col gap-2">
      <div ref={containerRef} style={{ width: "100%", height }} />
      <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs">
          {seriesData.map(({ name, lineData }, i) => {
            const last = lineData[lineData.length - 1]
            const val = last?.value ?? "—"
            const display = typeof val === "number" ? formatPriceLabel(val) : val
            return (
              <span key={name} className="flex items-center gap-1.5">
                <span
                  className="inline-block w-2.5 h-0.5 rounded-full shrink-0"
                  style={{ backgroundColor: colors[i % colors.length] }}
                />
                <span className="text-muted-foreground truncate max-w-[140px]" title={name}>
                  {name}
                </span>
                <span className="font-mono tabular-nums shrink-0">{display}</span>
              </span>
            )
          })}
        </div>
    </div>
  )
}
