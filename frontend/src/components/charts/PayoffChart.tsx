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
import { Slider } from "@/components/ui/slider"
import { Label } from "@/components/ui/label"
import { Download, Clock, TrendingUp } from "lucide-react"
import html2canvas from "html2canvas"
import { StrategyLeg } from "@/services/api/strategy"
import { OptionChainResponse } from "@/services/api/market"

interface PayoffDataPoint {
  price: number
  profit: number
}

interface ScenarioParams {
  priceChangePercent: number
  volatilityChangePercent: number
  daysRemaining: number
}

interface PayoffChartProps {
  data: PayoffDataPoint[]
  breakEven?: number
  currentPrice?: number
  expirationDate?: string
  timeToExpiry?: number // Days to expiration
  scenarioParams?: ScenarioParams // Scenario simulation parameters
  className?: string
  // New props for enhanced visualization
  legs?: StrategyLeg[]
  optionChain?: OptionChainResponse
  portfolioGreeks?: {
    delta?: number
    theta?: number
    gamma?: number
    vega?: number
    rho?: number
  }
}

export const PayoffChart: React.FC<PayoffChartProps> = ({
  data,
  breakEven,
  currentPrice,
  timeToExpiry,
  scenarioParams,
  className,
  legs: _legs, // Reserved for future use
  optionChain,
  portfolioGreeks,
}) => {
  const chartRef = React.useRef<HTMLDivElement>(null)
  
  // Interactive sliders state
  const [timeSliderValue, setTimeSliderValue] = React.useState<number[]>(
    timeToExpiry ? [timeToExpiry] : [0]
  )
  const [ivSliderValue, setIvSliderValue] = React.useState<number[]>(
    [100] // 100% = current IV
  )
  
  // Calculate current IV from option chain (average of ATM options)
  const currentIV = React.useMemo(() => {
    if (!optionChain || !currentPrice) return 0.3 // Default 30%
    
    const calls = optionChain.calls || []
    const puts = optionChain.puts || []
    
    // Find ATM options (closest to spot price)
    const allOptions = [...calls, ...puts]
    const atmOptions = allOptions
      .filter((opt) => {
        const strike = opt.strike || 0
        const percentDiff = Math.abs((strike - currentPrice) / currentPrice)
        return percentDiff < 0.05 // Within 5% of spot
      })
      .map((opt) => {
        const iv = opt.implied_volatility || opt.implied_vol || 0
        return iv
      })
      .filter((iv) => iv > 0)
    
    if (atmOptions.length === 0) return 0.3
    return atmOptions.reduce((a, b) => a + b, 0) / atmOptions.length
  }, [optionChain, currentPrice])

  // Calculate P&L at T+n (with time decay and IV adjustment)
  const calculateCurrentPnl = React.useCallback(
    (price: number, daysRemaining: number, ivMultiplier: number): number => {
      // Base P&L at expiration (intrinsic value)
      const expirationPnl = data.find((d) => Math.abs(d.price - price) < 0.01)?.profit || 0
      
      if (!timeToExpiry || timeToExpiry <= 0 || daysRemaining >= timeToExpiry) {
        return expirationPnl
      }
      
      // Calculate time decay factor (Theta effect)
      // Time value decays proportionally to sqrt(time remaining)
      const timeDecayFactor = Math.sqrt(Math.max(0, daysRemaining) / timeToExpiry)
      
      // Estimate time value component
      // Time value is highest at ATM and decreases as we move away
      const spotPrice = currentPrice || price
      const atmDistance = Math.abs(price - spotPrice) / spotPrice
      const timeValueDecay = Math.exp(-Math.pow(atmDistance * 10, 2))
      
      // Adjust time value based on IV (Vega effect)
      const maxTimeValuePercent = 0.03 * ivMultiplier
      const estimatedTimeValue = spotPrice * maxTimeValuePercent * timeValueDecay * timeDecayFactor
      
      // Apply time value and IV adjustment
      if (expirationPnl >= 0) {
        return expirationPnl + estimatedTimeValue
      } else {
        return expirationPnl - estimatedTimeValue * 0.6
      }
    },
    [data, timeToExpiry, currentPrice]
  )

  // Calculate current P&L data (Line 2 - dashed)
  const currentPnlData = React.useMemo(() => {
    if (!timeToExpiry || timeToExpiry <= 0) return []
    
    const daysRemaining = timeSliderValue[0]
    const ivMultiplier = ivSliderValue[0] / 100 // Convert percentage to multiplier
    
    return data.map((point) => ({
      price: point.price,
      profit: calculateCurrentPnl(point.price, daysRemaining, ivMultiplier),
    }))
  }, [data, timeSliderValue, ivSliderValue, calculateCurrentPnl, timeToExpiry])

  // Apply scenario simulation to data (if active)
  const simulatedData = React.useMemo(() => {
    if (!scenarioParams || !currentPrice) return data

    const { priceChangePercent, volatilityChangePercent, daysRemaining } = scenarioParams
    
    return data.map((point) => {
      const adjustedPointPrice = point.price * (1 + priceChangePercent / 100)
      const volatilityMultiplier = 1 + (volatilityChangePercent / 100) * 0.3
      
      let adjustedProfit = point.profit
      if (timeToExpiry && timeToExpiry > 0 && daysRemaining >= 0) {
        const timeDecayFactor = Math.sqrt(Math.max(0, daysRemaining) / timeToExpiry)
        const spotPrice = currentPrice || adjustedPointPrice
        const atmDistance = Math.abs(adjustedPointPrice - spotPrice) / spotPrice
        const timeValueDecay = Math.exp(-Math.pow(atmDistance * 10, 2))
        const maxTimeValuePercent = 0.03 * volatilityMultiplier
        const estimatedTimeValue = spotPrice * maxTimeValuePercent * timeValueDecay * timeDecayFactor
        
        if (point.profit >= 0) {
          adjustedProfit = point.profit + estimatedTimeValue
        } else {
          adjustedProfit = point.profit - estimatedTimeValue * 0.6
        }
      } else {
        adjustedProfit = point.profit * volatilityMultiplier
      }

      return {
        price: adjustedPointPrice,
        profit: adjustedProfit,
      }
    })
  }, [data, scenarioParams, currentPrice, timeToExpiry])

  // Export chart as image
  const exportChart = React.useCallback(async () => {
    try {
      if (!chartRef.current) {
        alert("Chart not available")
        return
      }

      const chartContainer = chartRef.current.querySelector(".recharts-wrapper")
      if (!chartContainer) {
        alert("Chart container not found")
        return
      }

      const canvas = await html2canvas(chartContainer as HTMLElement, {
        backgroundColor: "#ffffff",
        scale: 2,
        logging: false,
        useCORS: true,
        allowTaint: false,
      })

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
            
            setTimeout(() => {
              document.body.removeChild(link)
              URL.revokeObjectURL(url)
            }, 100)
          } else {
            alert("Failed to create image file")
          }
        },
        "image/png",
        1.0
      )
    } catch (error) {
      console.error("Export error:", error)
      alert("Export failed: " + (error instanceof Error ? error.message : "Unknown error"))
    }
  }, [])

  // Format numbers
  const formatPrice = (value: number): string => {
    if (value >= 1000) return `$${value.toFixed(0)}`
    if (value >= 100) return `$${value.toFixed(1)}`
    return `$${value.toFixed(2)}`
  }

  const formatPnl = (value: number): string => {
    const absValue = Math.abs(value)
    if (absValue >= 1000) return `${value >= 0 ? "+" : ""}$${value.toFixed(0)}`
    if (absValue >= 100) return `${value >= 0 ? "+" : ""}$${value.toFixed(1)}`
    return `${value >= 0 ? "+" : ""}$${value.toFixed(2)}`
  }

  // Enhanced custom tooltip with Delta and Theta
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      const isProfit = data.profit >= 0
      const currentPnl = data.currentProfit !== undefined ? data.currentProfit : data.profit
      
      return (
        <div className="bg-card border-2 border-primary/20 rounded-lg shadow-xl p-4 backdrop-blur-sm min-w-[200px]">
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-4">
              <span className="text-sm font-medium text-muted-foreground">Stock Price:</span>
              <span className="text-base font-bold">{formatPrice(data.price)}</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <span className="text-sm font-medium text-muted-foreground">P&L (Expiration):</span>
              <span
                className={`text-lg font-bold ${isProfit ? "text-emerald-500" : "text-rose-500"}`}
              >
                {formatPnl(data.profit)}
              </span>
            </div>
            {currentPnlData.length > 0 && data.currentProfit !== undefined && (
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm font-medium text-muted-foreground">P&L (Current):</span>
                <span
                  className={`text-lg font-bold ${currentPnl >= 0 ? "text-emerald-500" : "text-rose-500"}`}
                >
                  {formatPnl(currentPnl)}
                </span>
              </div>
            )}
            {portfolioGreeks && (
              <div className="pt-2 border-t border-border space-y-1">
                {portfolioGreeks.delta !== undefined && (
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-xs text-muted-foreground">Delta:</span>
                    <span className="text-xs font-medium">{portfolioGreeks.delta.toFixed(4)}</span>
                  </div>
                )}
                {portfolioGreeks.theta !== undefined && (
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-xs text-muted-foreground">Theta:</span>
                    <span className={`text-xs font-medium ${portfolioGreeks.theta < 0 ? "text-rose-500" : "text-emerald-500"}`}>
                      {portfolioGreeks.theta.toFixed(4)}
                    </span>
                  </div>
                )}
              </div>
            )}
            {breakEven !== undefined && (
              <div className="pt-2 border-t border-border">
                <div className="text-xs text-muted-foreground">
                  Break-even: {formatPrice(breakEven)}
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

  // Use simulated data if scenario is active, otherwise use original data
  const displayData = scenarioParams ? simulatedData : data

  // Prepare chart data with both expiration and current P&L
  const chartData = React.useMemo(() => {
    return displayData.map((d, index) => {
      const currentProfit = currentPnlData[index]?.profit
      return {
        ...d,
        profit: d.profit >= 0 ? d.profit : 0,
        loss: d.profit < 0 ? d.profit : 0,
        currentProfit: currentProfit !== undefined ? (currentProfit >= 0 ? currentProfit : 0) : undefined,
        currentLoss: currentProfit !== undefined ? (currentProfit < 0 ? currentProfit : 0) : undefined,
      }
    })
  }, [displayData, currentPnlData])

  // Update time slider when timeToExpiry changes
  React.useEffect(() => {
    if (timeToExpiry && timeToExpiry > 0) {
      setTimeSliderValue([timeToExpiry])
    }
  }, [timeToExpiry])

  return (
    <div className="space-y-3">
      {/* Control Panel: Time and IV Sliders */}
      {timeToExpiry && timeToExpiry > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-3 bg-muted/20 rounded-lg border border-border/50">
          {/* Time Slider */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <Label htmlFor="time-slider" className="flex items-center gap-1.5 text-xs font-medium">
                <Clock className="h-3.5 w-3.5" />
                Days to Expiration
              </Label>
              <span className="text-xs font-semibold text-primary">
                {timeSliderValue[0].toFixed(0)} days
              </span>
            </div>
            <Slider
              id="time-slider"
              value={timeSliderValue}
              onValueChange={setTimeSliderValue}
              min={0}
              max={timeToExpiry}
              step={1}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-muted-foreground/70">
              <span>Today (0)</span>
              <span>Expiration ({timeToExpiry})</span>
            </div>
          </div>

          {/* IV Slider */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <Label htmlFor="iv-slider" className="flex items-center gap-1.5 text-xs font-medium">
                <TrendingUp className="h-3.5 w-3.5" />
                Implied Volatility
              </Label>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-primary">
                  {(currentIV * (ivSliderValue[0] / 100) * 100).toFixed(1)}%
                </span>
                <Button
                  onClick={exportChart}
                  size="sm"
                  variant="ghost"
                  className="h-7 w-7 p-0"
                  title="Export chart"
                >
                  <Download className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
            <Slider
              id="iv-slider"
              value={ivSliderValue}
              onValueChange={setIvSliderValue}
              min={50}
              max={150}
              step={1}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-muted-foreground/70">
              <span>-50%</span>
              <span>Current (100%)</span>
              <span>+50%</span>
            </div>
          </div>
        </div>
      )}

      <div ref={chartRef} className="relative" id="payoff-chart-container">
        <ResponsiveContainer width="100%" height={500} className={className}>
          <ComposedChart
            data={chartData}
            margin={{ top: 20, right: 30, left: 50, bottom: 60 }}
          >
            <defs>
              <linearGradient id="colorProfit" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10b981" stopOpacity={0.8} />
                <stop offset="100%" stopColor="#10b981" stopOpacity={0.1} />
              </linearGradient>
              <linearGradient id="colorLoss" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f43f5e" stopOpacity={0.8} />
                <stop offset="100%" stopColor="#f43f5e" stopOpacity={0.1} />
              </linearGradient>
              <linearGradient id="colorCurrentProfit" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.6} />
                <stop offset="100%" stopColor="#22d3ee" stopOpacity={0.1} />
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
              tickFormatter={(value) => {
                if (value >= 1000) return `$${value.toFixed(0)}`
                if (value >= 100) return `$${value.toFixed(1)}`
                return `$${value.toFixed(2)}`
              }}
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
              tickFormatter={(value) => {
                const absValue = Math.abs(value)
                if (absValue >= 1000) return `$${value.toFixed(0)}`
                if (absValue >= 100) return `$${value.toFixed(1)}`
                return `$${value.toFixed(2)}`
              }}
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
              wrapperStyle={{ paddingTop: "8px", paddingBottom: "8px" }}
              iconType="line"
              layout="horizontal"
              verticalAlign="bottom"
              align="center"
              iconSize={14}
              fontSize={12}
              fontWeight={500}
              formatter={(value) => {
                if (value === "profit") return "Profit @ Exp"
                if (value === "loss") return "Loss @ Exp"
                if (value === "currentProfit") return "Current P&L"
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
                strokeWidth={2}
                strokeDasharray="5 3"
                label={{
                  value: `BE: ${formatPrice(breakEven)}`,
                  position: "insideTop",
                  fill: "#3b82f6",
                  fontSize: 11,
                  fontWeight: 600,
                  offset: 5,
                  angle: 0,
                }}
              />
            )}
            {/* Current price line */}
            {currentPrice !== undefined && (() => {
              const simulatedPrice = scenarioParams 
                ? currentPrice * (1 + scenarioParams.priceChangePercent / 100)
                : currentPrice
              return (
                <ReferenceLine
                  x={simulatedPrice}
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  strokeDasharray="4 3"
                  label={{
                    value: scenarioParams 
                      ? `Sim: ${formatPrice(simulatedPrice)}`
                      : `Cur: ${formatPrice(currentPrice)}`,
                    position: breakEven !== undefined && Math.abs(simulatedPrice - (breakEven || 0)) < 10
                      ? (simulatedPrice < breakEven ? "insideBottom" : "insideTop")
                      : "insideTop",
                    fill: "#8b5cf6",
                    fontSize: 11,
                    fontWeight: 600,
                    offset: breakEven !== undefined && Math.abs(simulatedPrice - (breakEven || 0)) < 10 ? 20 : 5,
                    angle: 0,
                  }}
                />
              )
            })()}
            {/* Loss area (below zero) - Expiration */}
            <Area
              type="monotone"
              dataKey="loss"
              stroke="#f43f5e"
              strokeWidth={3}
              fill="url(#colorLoss)"
              fillOpacity={0.7}
              activeDot={{ r: 6, fill: "#f43f5e", stroke: "#fff", strokeWidth: 2 }}
              animationDuration={300}
            />
            {/* Profit area (above zero) - Expiration (Line 1 - Solid) */}
            <Area
              type="monotone"
              dataKey="profit"
              stroke="#10b981"
              strokeWidth={3.5}
              fill="url(#colorProfit)"
              fillOpacity={0.7}
              activeDot={{ r: 6, fill: "#10b981", stroke: "#fff", strokeWidth: 2 }}
              animationDuration={300}
              name="profit"
            />
            {/* Current P&L Line (Line 2 - Dashed) */}
            {currentPnlData.length > 0 && (
              <>
                <Line
                  type="monotone"
                  dataKey="currentProfit"
                  stroke="#22d3ee"
                  strokeWidth={3}
                  strokeDasharray="8 4"
                  strokeOpacity={0.9}
                  dot={false}
                  activeDot={{ r: 5, fill: "#22d3ee", stroke: "#fff", strokeWidth: 2 }}
                  name="currentProfit"
                  connectNulls={false}
                  animationDuration={300}
                />
                <Line
                  type="monotone"
                  dataKey="currentLoss"
                  stroke="#22d3ee"
                  strokeWidth={3}
                  strokeDasharray="8 4"
                  strokeOpacity={0.9}
                  dot={false}
                  activeDot={{ r: 5, fill: "#22d3ee", stroke: "#fff", strokeWidth: 2 }}
                  name="currentLoss"
                  connectNulls={false}
                  animationDuration={300}
                />
              </>
            )}
          </ComposedChart>
        </ResponsiveContainer>
        
        {/* Compact Legend explanation */}
        <div className="mt-2 p-2 bg-muted/20 rounded-lg border border-border/50">
          <div className="flex items-center gap-4 flex-wrap text-xs">
            <div className="flex items-center gap-1.5">
              <div className="w-4 h-1 bg-emerald-500 rounded"></div>
              <span className="font-medium">Profit @ Exp</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-4 h-1 bg-rose-500 rounded"></div>
              <span className="font-medium">Loss @ Exp</span>
            </div>
            {currentPnlData.length > 0 && (
              <div className="flex items-center gap-1.5">
                <div className="w-4 h-1 bg-cyan-400 rounded border border-dashed border-cyan-400"></div>
                <span className="font-medium">Current P&L</span>
              </div>
            )}
            {timeToExpiry && timeToExpiry > 0 && currentPnlData.length > 0 && (
              <span className="text-muted-foreground/70 italic ml-auto">
                💡 Time decay & IV effects shown
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
