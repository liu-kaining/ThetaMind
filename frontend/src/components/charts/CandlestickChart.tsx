import * as React from "react"
import { createChart, IChartApi, ISeriesApi, CandlestickData } from "lightweight-charts"

interface CandlestickChartProps {
  data: CandlestickData[]
  height?: number
  className?: string
}

export const CandlestickChart: React.FC<CandlestickChartProps> = ({
  data,
  height = 400,
  className,
}) => {
  const chartContainerRef = React.useRef<HTMLDivElement>(null)
  const chartRef = React.useRef<IChartApi | null>(null)
  const seriesRef = React.useRef<ISeriesApi<"Candlestick"> | null>(null)

  React.useEffect(() => {
    if (!chartContainerRef.current) return

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height,
      layout: {
        background: { color: "transparent" },
        textColor: "hsl(var(--foreground))",
      },
      grid: {
        vertLines: { color: "hsl(var(--border))" },
        horzLines: { color: "hsl(var(--border))" },
      },
      crosshair: {
        mode: 1, // Normal crosshair
      },
      rightPriceScale: {
        borderColor: "hsl(var(--border))",
      },
      timeScale: {
        borderColor: "hsl(var(--border))",
        rightOffset: 12,
      },
    })

    // Create candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: "#26a69a",
      downColor: "#ef5350",
      borderVisible: false,
      wickUpColor: "#26a69a",
      wickDownColor: "#ef5350",
    })

    chartRef.current = chart
    seriesRef.current = candlestickSeries

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chart) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        })
      }
    }

    window.addEventListener("resize", handleResize)

    return () => {
      window.removeEventListener("resize", handleResize)
      chart.remove()
    }
  }, [height])

  // Update data when it changes
  React.useEffect(() => {
    if (seriesRef.current && data.length > 0) {
      seriesRef.current.setData(data)
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

