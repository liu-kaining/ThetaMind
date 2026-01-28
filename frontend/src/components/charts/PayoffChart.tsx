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
  
  // Use scenarioParams if available, otherwise use defaults
  const effectiveDaysRemaining = scenarioParams?.daysRemaining ?? (timeToExpiry || 0)
  const effectiveIVMultiplier = scenarioParams 
    ? (1 + scenarioParams.volatilityChangePercent / 100)
    : 1.0 // 100% = current IV

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
    
    return data.map((point) => ({
      price: point.price,
      profit: calculateCurrentPnl(point.price, effectiveDaysRemaining, effectiveIVMultiplier),
    }))
  }, [data, effectiveDaysRemaining, effectiveIVMultiplier, calculateCurrentPnl, timeToExpiry])

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

  // Enhanced custom tooltip with better styling and animations
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      const isProfit = data.profit >= 0
      const currentPnl = data.currentProfit !== undefined ? data.currentProfit : data.profit
      const hasCurrentPnl = currentPnlData.length > 0 && data.currentProfit !== undefined
      
      return (
        <div className="bg-card/95 backdrop-blur-md border border-primary/30 rounded-xl shadow-2xl p-4 min-w-[240px] animate-in fade-in-0 zoom-in-95 duration-200">
          <div className="space-y-3">
            {/* Stock Price - Prominent */}
            <div className="pb-2 border-b border-border/50">
              <div className="text-xs font-medium text-muted-foreground mb-1">Stock Price</div>
              <div className="text-xl font-bold tracking-tight">{formatPrice(data.price)}</div>
            </div>
            
            {/* P&L Values */}
            <div className="space-y-2.5">
              <div className="flex items-center justify-between gap-4">
                <span className="text-sm font-medium text-muted-foreground">P&L @ Expiration:</span>
                <span
                  className={`text-lg font-bold tracking-tight ${isProfit ? "text-emerald-500" : "text-rose-500"}`}
                >
                  {formatPnl(data.profit)}
                </span>
              </div>
              {hasCurrentPnl && (
                <div className="flex items-center justify-between gap-4">
                  <span className="text-sm font-medium text-muted-foreground">P&L @ Current:</span>
                  <span
                    className={`text-lg font-bold tracking-tight ${currentPnl >= 0 ? "text-cyan-500" : "text-rose-500"}`}
                  >
                    {formatPnl(currentPnl)}
                  </span>
                </div>
              )}
            </div>
            
            {/* Greeks */}
            {portfolioGreeks && (
              <div className="pt-2 border-t border-border/50 space-y-1.5">
                <div className="text-xs font-semibold text-muted-foreground mb-1.5">Portfolio Greeks</div>
                {portfolioGreeks.delta !== undefined && (
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-xs text-muted-foreground">Δ Delta:</span>
                    <span className="text-xs font-semibold">{portfolioGreeks.delta.toFixed(4)}</span>
                  </div>
                )}
                {portfolioGreeks.theta !== undefined && (
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-xs text-muted-foreground">Θ Theta:</span>
                    <span className={`text-xs font-semibold ${portfolioGreeks.theta < 0 ? "text-rose-500" : "text-emerald-500"}`}>
                      {portfolioGreeks.theta.toFixed(4)}
                    </span>
                  </div>
                )}
                {portfolioGreeks.gamma !== undefined && (
                  <div className="flex items-center justify-between gap-4">
                    <span className="text-xs text-muted-foreground">Γ Gamma:</span>
                    <span className="text-xs font-semibold">{portfolioGreeks.gamma.toFixed(4)}</span>
                  </div>
                )}
              </div>
            )}
            
            {/* Break-even info */}
            {breakEven !== undefined && (
              <div className="pt-2 border-t border-border/50">
                <div className="flex items-center justify-between gap-4 mb-1">
                  <span className="text-xs text-muted-foreground">Break-even:</span>
                  <span className="text-xs font-semibold text-blue-500">{formatPrice(breakEven)}</span>
                </div>
                <div className="text-xs text-muted-foreground">
                  Distance: <span className={`font-medium ${Math.abs((data.price - breakEven) / breakEven * 100) < 5 ? "text-amber-500" : ""}`}>
                    {((data.price - breakEven) / breakEven * 100).toFixed(1)}%
                  </span>
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

  return (
    <div className="space-y-3">
      {/* Export button */}
      <div className="flex justify-end">
        <Button
          onClick={exportChart}
          size="sm"
          variant="ghost"
          className="h-8 gap-2"
          title="Export chart"
        >
          <Download className="h-4 w-4" />
          Export Chart
        </Button>
      </div>

      <div ref={chartRef} className="relative" id="payoff-chart-container">
        <ResponsiveContainer width="100%" height={550} className={className}>
          <ComposedChart
            data={chartData}
            margin={{ top: 20, right: 30, left: 50, bottom: 60 }}
          >
            <defs>
              <linearGradient id="colorProfit" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10b981" stopOpacity={0.9} />
                <stop offset="50%" stopColor="#10b981" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#10b981" stopOpacity={0.05} />
              </linearGradient>
              <linearGradient id="colorLoss" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f43f5e" stopOpacity={0.9} />
                <stop offset="50%" stopColor="#f43f5e" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#f43f5e" stopOpacity={0.05} />
              </linearGradient>
              <linearGradient id="colorCurrentProfit" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.7} />
                <stop offset="100%" stopColor="#22d3ee" stopOpacity={0.1} />
              </linearGradient>
              {/* Glow effects for better visual appeal */}
              <filter id="glow">
                <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                <feMerge>
                  <feMergeNode in="coloredBlur"/>
                  <feMergeNode in="SourceGraphic"/>
                </feMerge>
              </filter>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="hsl(var(--border))"
              opacity={0.2}
              strokeWidth={0.5}
              vertical={true}
              horizontal={true}
            />
            <XAxis
              dataKey="price"
              type="number"
              scale="linear"
              domain={["dataMin", "dataMax"]}
              tick={{ fill: "hsl(var(--foreground))", fontSize: 12, fontWeight: 500 }}
              tickFormatter={(value) => {
                if (value >= 1000) return `$${value.toFixed(0)}`
                if (value >= 100) return `$${value.toFixed(1)}`
                return `$${value.toFixed(2)}`
              }}
              angle={0}
              textAnchor="middle"
              height={60}
              interval="preserveStartEnd"
              tickLine={{ stroke: "hsl(var(--border))", strokeWidth: 1, opacity: 0.5 }}
              label={{
                value: "Stock Price ($)",
                position: "insideBottom",
                offset: -8,
                style: { fill: "hsl(var(--foreground))", fontSize: 14, fontWeight: 600, letterSpacing: "0.5px" },
              }}
              stroke="hsl(var(--border))"
              strokeWidth={1.5}
              opacity={0.6}
            />
            <YAxis
              tick={{ fill: "hsl(var(--foreground))", fontSize: 12, fontWeight: 500 }}
              tickFormatter={(value) => {
                const absValue = Math.abs(value)
                if (absValue >= 1000) return `$${value.toFixed(0)}`
                if (absValue >= 100) return `$${value.toFixed(1)}`
                return `$${value.toFixed(2)}`
              }}
              width={75}
              tickLine={{ stroke: "hsl(var(--border))", strokeWidth: 1, opacity: 0.5 }}
              label={{
                value: "Profit / Loss ($)",
                angle: -90,
                position: "insideLeft",
                offset: 12,
                style: { fill: "hsl(var(--foreground))", fontSize: 14, fontWeight: 600, letterSpacing: "0.5px" },
              }}
              stroke="hsl(var(--border))"
              strokeWidth={1.5}
              opacity={0.6}
            />
            <Tooltip 
              content={<CustomTooltip />}
              cursor={{ 
                stroke: "hsl(var(--primary))", 
                strokeWidth: 2, 
                strokeDasharray: "5 5",
                strokeOpacity: 0.6,
                pointerEvents: "none"
              }}
              animationDuration={150}
              animationEasing="ease-out"
              allowEscapeViewBox={{ x: false, y: false }}
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
              strokeWidth={2}
              strokeDasharray="6 4"
              opacity={0.5}
            />
            {/* Break-even line */}
            {breakEven !== undefined && (
              <ReferenceLine
                x={breakEven}
                stroke="#3b82f6"
                strokeWidth={2.5}
                strokeDasharray="6 4"
                strokeOpacity={0.8}
                label={{
                  value: `BE: ${formatPrice(breakEven)}`,
                  position: "insideTop",
                  fill: "#3b82f6",
                  fontSize: 12,
                  fontWeight: 700,
                  offset: 8,
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
                  strokeWidth={2.5}
                  strokeDasharray="6 4"
                  strokeOpacity={0.8}
                  label={{
                    value: scenarioParams 
                      ? `Sim: ${formatPrice(simulatedPrice)}`
                      : `Cur: ${formatPrice(currentPrice)}`,
                    position: breakEven !== undefined && Math.abs(simulatedPrice - (breakEven || 0)) < 10
                      ? (simulatedPrice < breakEven ? "insideBottom" : "insideTop")
                      : "insideTop",
                    fill: "#8b5cf6",
                    fontSize: 12,
                    fontWeight: 700,
                    offset: breakEven !== undefined && Math.abs(simulatedPrice - (breakEven || 0)) < 10 ? 20 : 8,
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
              fillOpacity={0.6}
              activeDot={{ r: 7, fill: "#f43f5e", stroke: "#fff", strokeWidth: 2.5, filter: "url(#glow)" }}
              animationDuration={400}
              animationEasing="ease-out"
              dot={false}
            />
            {/* Profit area (above zero) - Expiration (Line 1 - Solid) */}
            <Area
              type="monotone"
              dataKey="profit"
              stroke="#10b981"
              strokeWidth={3.5}
              fill="url(#colorProfit)"
              fillOpacity={0.6}
              activeDot={{ r: 7, fill: "#10b981", stroke: "#fff", strokeWidth: 2.5, filter: "url(#glow)" }}
              animationDuration={400}
              animationEasing="ease-out"
              name="profit"
              dot={false}
            />
            {/* Current P&L Line (Line 2 - Dashed) */}
            {currentPnlData.length > 0 && (
              <>
                <Line
                  type="monotone"
                  dataKey="currentProfit"
                  stroke="#22d3ee"
                  strokeWidth={3}
                  strokeDasharray="10 5"
                  strokeOpacity={0.95}
                  dot={false}
                  activeDot={{ r: 6, fill: "#22d3ee", stroke: "#fff", strokeWidth: 2.5, filter: "url(#glow)" }}
                  name="currentProfit"
                  connectNulls={false}
                  animationDuration={400}
                  animationEasing="ease-out"
                />
                <Line
                  type="monotone"
                  dataKey="currentLoss"
                  stroke="#22d3ee"
                  strokeWidth={3}
                  strokeDasharray="10 5"
                  strokeOpacity={0.95}
                  dot={false}
                  activeDot={{ r: 6, fill: "#22d3ee", stroke: "#fff", strokeWidth: 2.5, filter: "url(#glow)" }}
                  name="currentLoss"
                  connectNulls={false}
                  animationDuration={400}
                  animationEasing="ease-out"
                />
              </>
            )}
          </ComposedChart>
        </ResponsiveContainer>
        
        {/* Enhanced Legend */}
        <div className="mt-3 p-3 bg-gradient-to-r from-muted/30 to-muted/10 rounded-xl border border-border/50 backdrop-blur-sm">
          <div className="flex items-center gap-6 flex-wrap text-xs">
            <div className="flex items-center gap-2">
              <div className="w-5 h-1.5 bg-emerald-500 rounded-sm shadow-sm"></div>
              <span className="font-semibold text-foreground">Profit @ Expiration</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-5 h-1.5 bg-rose-500 rounded-sm shadow-sm"></div>
              <span className="font-semibold text-foreground">Loss @ Expiration</span>
            </div>
            {currentPnlData.length > 0 && (
              <div className="flex items-center gap-2">
                <div className="w-5 h-1.5 bg-cyan-400 rounded-sm border-2 border-dashed border-cyan-400/80"></div>
                <span className="font-semibold text-foreground">Current P&L</span>
              </div>
            )}
            {timeToExpiry && timeToExpiry > 0 && currentPnlData.length > 0 && (
              <div className="ml-auto flex items-center gap-1.5 text-muted-foreground">
                <span className="text-xs">💡</span>
                <span className="text-xs italic">Time decay & IV effects shown</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
