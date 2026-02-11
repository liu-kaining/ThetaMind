import * as React from "react"
import { createChart, IChartApi, ISeriesApi, CandlestickData, HistogramData } from "lightweight-charts"

interface CandlestickChartProps {
  data: Array<CandlestickData & { volume?: number }>
  height?: number
  className?: string
  watermarkText?: string
  onHover?: (value: (CandlestickData & { volume?: number }) | null) => void
}

export const CandlestickChart: React.FC<CandlestickChartProps> = ({
  data,
  height = 400,
  className,
  watermarkText,
  onHover,
}) => {
  const chartContainerRef = React.useRef<HTMLDivElement>(null)
  const chartRef = React.useRef<IChartApi | null>(null)
  const seriesRef = React.useRef<ISeriesApi<"Candlestick"> | null>(null)
  const volumeSeriesRef = React.useRef<ISeriesApi<"Histogram"> | null>(null)
  const lastPriceLineRef = React.useRef<ReturnType<ISeriesApi<"Candlestick">["createPriceLine"]> | null>(null)
  const tooltipRef = React.useRef<HTMLDivElement | null>(null)

  const getResolvedColor = React.useCallback((cssVar: string, fallback: string) => {
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
    if (!chartContainerRef.current) return

    const textColor = getResolvedColor("--foreground", "#0f172a")
    const gridColor = getResolvedColor("--border", "rgba(148, 163, 184, 0.3)")
    const backgroundColor = getResolvedColor("--card", "transparent")
    const accentColor = getResolvedColor("--primary", "#2563eb")
    const volumeUpColor = getResolvedColor("--primary", "rgba(37, 99, 235, 0.35)")

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height,
      layout: {
        background: { color: backgroundColor },
        textColor,
      },
      grid: {
        vertLines: { color: gridColor },
        horzLines: { color: gridColor },
      },
      crosshair: {
        mode: 1, // Normal crosshair
        vertLine: { color: gridColor, width: 1, style: 2 },
        horzLine: { color: gridColor, width: 1, style: 2 },
      },
      rightPriceScale: {
        borderColor: gridColor,
        scaleMargins: { top: 0.1, bottom: 0.2 },
      },
      timeScale: {
        borderColor: gridColor,
        rightOffset: 12,
        barSpacing: 8,
        fixLeftEdge: true,
        fixRightEdge: true,
      },
      watermark: watermarkText
        ? {
            color: `${accentColor}33`,
            visible: true,
            text: watermarkText,
            fontSize: 28,
            horzAlign: "left",
            vertAlign: "top",
          }
        : undefined,
    })

    // Create candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: "#26a69a",
      downColor: "#ef5350",
      borderVisible: false,
      wickUpColor: "#26a69a",
      wickDownColor: "#ef5350",
      priceLineVisible: true,
      lastValueVisible: true,
    })

    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
      color: volumeUpColor,
    })
    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
      visible: false,
      borderVisible: false,
    })

    chartRef.current = chart
    seriesRef.current = candlestickSeries
    volumeSeriesRef.current = volumeSeries

    if (!tooltipRef.current && chartContainerRef.current) {
      const tooltip = document.createElement("div")
      tooltip.style.position = "absolute"
      tooltip.style.display = "none"
      tooltip.style.pointerEvents = "none"
      tooltip.style.zIndex = "10"
      tooltip.style.padding = "10px 12px"
      tooltip.style.borderRadius = "10px"
      tooltip.style.fontSize = "12px"
      tooltip.style.lineHeight = "1.4"
      tooltip.style.boxShadow = "0 10px 30px rgba(15, 23, 42, 0.18)"
      tooltip.style.background = getResolvedColor("--background", "#ffffff")
      tooltip.style.color = textColor
      tooltip.style.border = `1px solid ${gridColor}`
      tooltip.style.backdropFilter = "blur(6px)"
      tooltip.style.minWidth = "160px"
      tooltipRef.current = tooltip
      chartContainerRef.current.style.position = "relative"
      chartContainerRef.current.appendChild(tooltip)
    }

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chart) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
    }

    window.addEventListener("resize", handleResize)

    const updateColors = () => {
      const nextTextColor = getResolvedColor("--foreground", "#0f172a")
      const nextGridColor = getResolvedColor("--border", "rgba(148, 163, 184, 0.3)")
      const nextBackgroundColor = getResolvedColor("--card", "transparent")
      const nextAccentColor = getResolvedColor("--primary", "#2563eb")
      const nextVolumeUpColor = getResolvedColor("--primary", "rgba(37, 99, 235, 0.35)")
      chart.applyOptions({
        layout: { background: { color: nextBackgroundColor }, textColor: nextTextColor },
        grid: {
          vertLines: { color: nextGridColor },
          horzLines: { color: nextGridColor },
        },
        rightPriceScale: { borderColor: nextGridColor },
        timeScale: { borderColor: nextGridColor },
        watermark: watermarkText
          ? {
              color: `${nextAccentColor}33`,
              visible: true,
              text: watermarkText,
              fontSize: 28,
              horzAlign: "left",
              vertAlign: "top",
            }
          : undefined,
      })
      if (volumeSeriesRef.current) {
        volumeSeriesRef.current.applyOptions({ color: nextVolumeUpColor })
      }
      if (tooltipRef.current) {
        tooltipRef.current.style.color = nextTextColor
        tooltipRef.current.style.border = `1px solid ${nextGridColor}`
        tooltipRef.current.style.background = getResolvedColor("--background", "#ffffff")
      }
    }

    const themeObserver = new MutationObserver(() => updateColors())
    themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] })

    const formatPrice = (value: number) => value.toFixed(2)
    const formatVolume = (value?: number) => {
      if (!value || !Number.isFinite(value)) return "—"
      if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`
      if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`
      return value.toFixed(0)
    }

    const handleCrosshairMove = (param: any) => {
      if (!param || !seriesRef.current) {
        if (tooltipRef.current) tooltipRef.current.style.display = "none"
        onHover?.(null)
        return
      }
      const price = param.seriesData.get(seriesRef.current)
      if (!price) {
        if (tooltipRef.current) tooltipRef.current.style.display = "none"
        onHover?.(null)
        return
      }
      const candle = price as CandlestickData & { volume?: number }
      if (tooltipRef.current) {
        const timeLabel = typeof candle.time === "string" ? candle.time : String(candle.time)
        const closeColor = candle.close >= candle.open ? "#10b981" : "#ef4444"
        tooltipRef.current.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <div style="font-weight:600;">${timeLabel}</div>
            <div style="font-weight:600;color:${closeColor};">${formatPrice(candle.close)}</div>
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px 10px;">
            <div style="color:#64748b;">Open</div><div>${formatPrice(candle.open)}</div>
            <div style="color:#64748b;">High</div><div>${formatPrice(candle.high)}</div>
            <div style="color:#64748b;">Low</div><div>${formatPrice(candle.low)}</div>
            <div style="color:#64748b;">Vol</div><div>${formatVolume(candle.volume)}</div>
          </div>
        `
        const container = chartContainerRef.current
        if (container && param.point) {
          const boxWidth = tooltipRef.current.offsetWidth
          const boxHeight = tooltipRef.current.offsetHeight
          const x = Math.min(container.clientWidth - boxWidth - 12, Math.max(12, param.point.x + 12))
          const y = Math.min(container.clientHeight - boxHeight - 12, Math.max(12, param.point.y - boxHeight - 12))
          tooltipRef.current.style.left = `${x}px`
          tooltipRef.current.style.top = `${y}px`
        }
        tooltipRef.current.style.display = "block"
      }
      onHover?.(candle)
    }

    chart.subscribeCrosshairMove(handleCrosshairMove)

    return () => {
      window.removeEventListener("resize", handleResize)
      themeObserver.disconnect()
      chart.unsubscribeCrosshairMove(handleCrosshairMove)
      chart.remove()
    }
  }, [getResolvedColor, height, watermarkText, onHover])

  // Update data when it changes
  React.useEffect(() => {
    if (seriesRef.current && data.length > 0) {
      seriesRef.current.setData(data)
      const last = data[data.length - 1]
      if (last?.close && seriesRef.current) {
        if (lastPriceLineRef.current) {
          seriesRef.current.removePriceLine(lastPriceLineRef.current)
        }
        lastPriceLineRef.current = seriesRef.current.createPriceLine({
          price: last.close,
          color: "#94a3b8",
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: "Last",
        })
      }
    }
    if (volumeSeriesRef.current && data.length > 0) {
      const volumeData: HistogramData[] = data.map((bar, index) => {
        const prev = data[Math.max(0, index - 1)]
        const isUp = bar.close >= (prev?.close ?? bar.open)
        return {
          time: bar.time,
          value: bar.volume ?? 0,
          color: isUp ? "rgba(37, 99, 235, 0.35)" : "rgba(239, 83, 80, 0.35)",
        }
      })
      volumeSeriesRef.current.setData(volumeData)
    }
  }, [data])

  return (
    <div
      ref={chartContainerRef}
      className={className}
      style={{ width: "100%", height }}
    />
  )
}

