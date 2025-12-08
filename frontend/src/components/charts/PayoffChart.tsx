import * as React from "react"
import {
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  ComposedChart,
  Line,
  Legend,
} from "recharts"
import { Button } from "@/components/ui/button"
import { Download } from "lucide-react"
import html2canvas from "html2canvas"

interface PayoffDataPoint {
  price: number
  profit: number
}

interface PayoffChartProps {
  data: PayoffDataPoint[]
  breakEven?: number
  currentPrice?: number
  expirationDate?: string
  timeToExpiry?: number // Days to expiration
  className?: string
}

export const PayoffChart: React.FC<PayoffChartProps> = ({
  data,
  breakEven,
  currentPrice,
  timeToExpiry,
  className,
}) => {
  const chartRef = React.useRef<HTMLDivElement>(null)

  // Calculate payoff at different time points (if timeToExpiry is provided)
  // Only show meaningful intermediate time points (not Today which overlaps with expiration)
  const timePoints = React.useMemo(() => {
    if (!timeToExpiry || timeToExpiry <= 0) return []
    
    // Only show 50% time remaining as it's the most meaningful intermediate point
    // Today (100%) overlaps with expiration, so we skip it
    const timePoints = [
      { label: "50% Time Left", daysRemaining: Math.floor(timeToExpiry * 0.5), factor: 0.65 },
    ]
    
    return timePoints.map((tp) => ({
      ...tp,
      data: data.map((point) => {
        // Better time decay calculation: preserve intrinsic value, decay time value
        const intrinsicValue = point.profit >= 0 
          ? Math.max(0, point.profit) 
          : 0 // Loss has no intrinsic value
        const timeValue = point.profit - intrinsicValue
        return {
          ...point,
          profit: intrinsicValue + timeValue * tp.factor,
        }
      }),
    }))
  }, [data, timeToExpiry])

  // Export chart as image using html2canvas - More reliable
  const exportChart = React.useCallback(async () => {
    try {
      if (!chartRef.current) {
        alert("图表不可用")
        return
      }

      // Find the chart container (ResponsiveContainer)
      const chartContainer = chartRef.current.querySelector(".recharts-wrapper")
      if (!chartContainer) {
        alert("找不到图表容器")
        return
      }

      // Use html2canvas to capture the chart
      const canvas = await html2canvas(chartContainer as HTMLElement, {
        backgroundColor: "#ffffff",
        scale: 2, // Higher quality
        logging: false,
        useCORS: true,
        allowTaint: false,
      })

      // Convert to blob and download
      canvas.toBlob(
        (blob) => {
          if (blob) {
            const url = URL.createObjectURL(blob)
            const link = document.createElement("a")
            link.style.display = "none"
            link.href = url
            link.download = `payoff-diagram-${new Date().toISOString().split("T")[0]}.png`
            
            document.body.appendChild(link)
            link.click()
            
            // Clean up
            setTimeout(() => {
              document.body.removeChild(link)
              URL.revokeObjectURL(url)
            }, 100)
          } else {
            alert("无法创建图片文件")
          }
        },
        "image/png",
        1.0
      )
    } catch (error) {
      console.error("导出错误:", error)
      alert("导出失败: " + (error instanceof Error ? error.message : "未知错误"))
    }
  }, [])

  // Enhanced custom tooltip component
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      const isProfit = data.profit >= 0
      return (
        <div className="bg-card border-2 border-primary/20 rounded-lg shadow-xl p-4 backdrop-blur-sm">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-4">
              <span className="text-sm font-medium text-muted-foreground">Stock Price:</span>
              <span className="text-base font-bold">${data.price.toFixed(2)}</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <span className="text-sm font-medium text-muted-foreground">P&L:</span>
              <span
                className={`text-xl font-bold ${isProfit ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"}`}
              >
                {isProfit ? "+" : ""}${data.profit.toFixed(2)}
              </span>
            </div>
            {breakEven !== undefined && (
              <div className="pt-2 border-t border-border">
                <div className="text-xs text-muted-foreground">
                  Break-even: ${breakEven.toFixed(2)}
                </div>
                <div className="text-xs text-muted-foreground">
                  Distance: {((data.price - breakEven) / breakEven * 100).toFixed(1)}%
                </div>
              </div>
            )}
          </div>
        </div>
      )
    }
    return null
  }

  // Split data into profit and loss areas
  const profitData = data.map((d) => ({
    ...d,
    profit: d.profit >= 0 ? d.profit : 0,
    loss: d.profit < 0 ? d.profit : 0,
  }))

  return (
    <div ref={chartRef} className="relative" id="payoff-chart-container">
      <div className="absolute top-2 right-2 z-10">
        <Button
          onClick={exportChart}
          size="sm"
          variant="secondary"
          className="bg-background/90 backdrop-blur-sm shadow-md hover:shadow-lg font-medium"
        >
          <Download className="h-4 w-4 mr-1" />
          Export
        </Button>
      </div>
      <ResponsiveContainer width="100%" height={450} className={className}>
        <ComposedChart
          data={profitData}
          margin={{ top: 70, right: 50, left: 50, bottom: 80 }}
        >
        <defs>
          <linearGradient id="colorProfit" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10b981" stopOpacity={0.8} />
            <stop offset="100%" stopColor="#10b981" stopOpacity={0.1} />
          </linearGradient>
          <linearGradient id="colorLoss" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#ef4444" stopOpacity={0.8} />
            <stop offset="100%" stopColor="#ef4444" stopOpacity={0.1} />
          </linearGradient>
        </defs>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="hsl(var(--border))"
          opacity={0.4}
          strokeWidth={1}
        />
        <XAxis
          dataKey="price"
          type="number"
          scale="linear"
          domain={["dataMin", "dataMax"]}
          tick={{ fill: "hsl(var(--foreground))", fontSize: 13, fontWeight: 500 }}
          angle={-45}
          textAnchor="end"
          height={70}
          tickLine={{ stroke: "hsl(var(--foreground))", strokeWidth: 1 }}
          label={{
            value: "Stock Price ($)",
            position: "insideBottom",
            offset: -5,
            style: { fill: "hsl(var(--foreground))", fontSize: 15, fontWeight: 600 },
          }}
          stroke="hsl(var(--border))"
          strokeWidth={2}
        />
        <YAxis
          tick={{ fill: "hsl(var(--foreground))", fontSize: 13, fontWeight: 500 }}
          width={70}
          tickLine={{ stroke: "hsl(var(--foreground))", strokeWidth: 1 }}
          label={{
            value: "Profit / Loss ($)",
            angle: -90,
            position: "insideLeft",
            offset: 15,
            style: { fill: "hsl(var(--foreground))", fontSize: 15, fontWeight: 600 },
          }}
          stroke="hsl(var(--border))"
          strokeWidth={2}
        />
        <Tooltip 
          content={<CustomTooltip />}
          cursor={{ stroke: "hsl(var(--primary))", strokeWidth: 2, strokeDasharray: "5 5" }}
          animationDuration={200}
        />
        <Legend
          wrapperStyle={{ paddingTop: "15px", paddingBottom: "15px" }}
          iconType="line"
          layout="horizontal"
          verticalAlign="bottom"
          align="center"
          iconSize={16}
          fontSize={14}
          fontWeight={500}
          formatter={(value) => {
            if (value === "profit") return "Profit at Expiration"
            if (value === "loss") return "Loss at Expiration"
            if (value?.includes("Time")) return value
            return value
          }}
        />
        {/* Zero line */}
        <ReferenceLine
          y={0}
          stroke="hsl(var(--foreground))"
          strokeWidth={2.5}
          strokeDasharray="5 5"
          opacity={0.6}
          label={{ 
            value: "Break-even Line", 
            position: "right",
            offset: 20,
            fontSize: 12,
            fontWeight: 600,
            fill: "hsl(var(--foreground))"
          }}
        />
        {/* Break-even line */}
        {breakEven !== undefined && (
          <ReferenceLine
            x={breakEven}
            stroke="#3b82f6"
            strokeWidth={2.5}
            strokeDasharray="6 4"
            label={{
              value: `Break-even: $${breakEven.toFixed(2)}`,
              position: "insideTop",
              fill: "#3b82f6",
              fontSize: 13,
              fontWeight: 700,
              offset: 8,
              angle: 0,
            }}
          />
        )}
        {/* Current price line */}
        {currentPrice !== undefined && (
          <ReferenceLine
            x={currentPrice}
            stroke="#8b5cf6"
            strokeWidth={2.5}
            strokeDasharray="4 4"
            label={{
              value: `Current: $${currentPrice.toFixed(2)}`,
              position: breakEven !== undefined && Math.abs(currentPrice - breakEven) < 10
                ? (currentPrice < breakEven ? "insideBottom" : "insideTop")
                : "insideTop",
              fill: "#8b5cf6",
              fontSize: 13,
              fontWeight: 700,
              offset: breakEven !== undefined && Math.abs(currentPrice - breakEven) < 10 ? 25 : 8,
              angle: 0,
            }}
          />
        )}
        {/* Loss area (below zero) */}
        <Area
          type="monotone"
          dataKey="loss"
          stroke="#ef4444"
          strokeWidth={3}
          fill="url(#colorLoss)"
          fillOpacity={0.7}
          activeDot={{ r: 6, fill: "#ef4444", stroke: "#fff", strokeWidth: 2 }}
          animationDuration={300}
        />
        {/* Profit area (above zero) - current expiration */}
        <Area
          type="monotone"
          dataKey="profit"
          stroke="#10b981"
          strokeWidth={3.5}
          fill="url(#colorProfit)"
          fillOpacity={0.7}
          activeDot={{ r: 6, fill: "#10b981", stroke: "#fff", strokeWidth: 2 }}
          animationDuration={300}
        />
        {/* Time decay lines (if timeToExpiry provided) - Only show 50% time left */}
        {timePoints.length > 0 && timePoints.map((tp, index) => (
          <Line
            key={`time-${index}`}
            type="monotone"
            data={tp.data}
            dataKey="profit"
            stroke="#8b5cf6"
            strokeWidth={3}
            strokeDasharray="8 4"
            strokeOpacity={0.85}
            dot={false}
            activeDot={{ r: 5, fill: "#8b5cf6", stroke: "#fff", strokeWidth: 2 }}
            name={tp.label}
            connectNulls={false}
            animationDuration={300}
          />
        ))}
      </ComposedChart>
      </ResponsiveContainer>
      
      {/* Legend explanation */}
      <div className="mt-4 p-3 bg-muted/30 rounded-lg border border-border">
        <div className="flex items-center gap-6 flex-wrap">
          <div className="flex items-center gap-2">
            <div className="w-6 h-1.5 bg-green-600 rounded shadow-sm"></div>
            <span className="text-sm font-semibold">Solid Green: Profit at Expiration</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-6 h-1.5 bg-red-600 rounded shadow-sm"></div>
            <span className="text-sm font-semibold">Solid Red: Loss at Expiration</span>
          </div>
          {timeToExpiry && timeToExpiry > 0 && (
            <div className="flex items-center gap-2">
              <div className="w-6 h-1.5 bg-purple-600 rounded shadow-sm border-2 border-dashed border-purple-600"></div>
              <span className="text-sm font-semibold">Dashed Purple: 50% Time Remaining</span>
            </div>
          )}
        </div>
        {timeToExpiry && timeToExpiry > 0 && (
          <div className="mt-2 text-sm text-muted-foreground italic">
            💡 The dashed line shows how time decay (Theta) affects your position value when 50% of time remains
          </div>
        )}
      </div>
    </div>
  )
}

