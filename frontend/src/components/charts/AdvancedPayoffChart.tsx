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
} from "recharts"
import { Card } from "@/components/ui/card"
import { StrategyLeg } from "@/services/api/strategy"

interface PayoffDataPoint {
  price: number
  profit: number
}

interface AdvancedPayoffChartProps {
  data: PayoffDataPoint[]
  legs: StrategyLeg[]
  symbol: string
  strategyName: string
  currentPrice?: number
  breakEven?: number
  className?: string
}

interface KeyPoint {
  price: number
  profit: number
  label: string
  type: "max-profit" | "moon-profit" | "credit-zone" | "breakeven"
}

export const AdvancedPayoffChart: React.FC<AdvancedPayoffChartProps> = ({
  data,
  legs,
  symbol,
  strategyName,
  currentPrice,
  breakEven,
  className,
}) => {
  // Calculate net cash flow
  const netCashFlow = React.useMemo(() => {
    let total = 0
    legs.forEach((leg) => {
      const premium = leg.premium || 0
      if (leg.action === "buy") {
        total -= premium * leg.quantity
      } else {
        total += premium * leg.quantity
      }
    })
    return total
  }, [legs])

  // Calculate key points from payoff data
  const keyPoints = React.useMemo(() => {
    if (data.length === 0) return []

    const points: KeyPoint[] = []

    // Find max profit point
    const maxProfitPoint = data.reduce((max, point) =>
      point.profit > max.profit ? point : max
    )
    if (maxProfitPoint.profit > 0) {
      points.push({
        price: maxProfitPoint.price,
        profit: maxProfitPoint.profit,
        label: `Max Profit: $${maxProfitPoint.profit.toFixed(0)}`,
        type: "max-profit",
      })
    }

    // Find moon profit (right side plateau - last 10% of data)
    const rightSideStart = Math.floor(data.length * 0.9)
    const rightSideData = data.slice(rightSideStart)
    if (rightSideData.length > 0) {
      const avgRightProfit =
        rightSideData.reduce((sum, p) => sum + p.profit, 0) /
        rightSideData.length
      if (avgRightProfit > 0) {
        const moonPrice = rightSideData[Math.floor(rightSideData.length / 2)].price
        points.push({
          price: moonPrice,
          profit: avgRightProfit,
          label: `Moon Profit: $${avgRightProfit.toFixed(0)}`,
          type: "moon-profit",
        })
      }
    }

    // Find credit zone (middle plateau - 40-60% of data range)
    const middleStart = Math.floor(data.length * 0.4)
    const middleEnd = Math.floor(data.length * 0.6)
    const middleData = data.slice(middleStart, middleEnd)
    if (middleData.length > 0) {
      const avgMiddleProfit =
        middleData.reduce((sum, p) => sum + p.profit, 0) / middleData.length
      if (avgMiddleProfit > 0 && Math.abs(avgMiddleProfit - netCashFlow) < 50) {
        const creditPrice = middleData[Math.floor(middleData.length / 2)].price
        points.push({
          price: creditPrice,
          profit: avgMiddleProfit,
          label: `Credit: $${avgMiddleProfit.toFixed(0)}`,
          type: "credit-zone",
        })
      }
    }

    // Add breakeven if available
    if (breakEven !== undefined) {
      const breakevenPoint = data.find(
        (p) => Math.abs(p.price - breakEven) < 1
      )
      if (breakevenPoint) {
        points.push({
          price: breakEven,
          profit: 0,
          label: `Breakeven: $${breakEven.toFixed(1)}`,
          type: "breakeven",
        })
      }
    }

    return points
  }, [data, breakEven, netCashFlow])

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

  // Split data into profit and loss areas
  const chartData = data.map((d) => ({
    ...d,
    profit: d.profit >= 0 ? d.profit : 0,
    loss: d.profit < 0 ? d.profit : 0,
  }))

  // Group legs by type for display
  const groupedLegs = React.useMemo(() => {
    const groups: { [key: string]: StrategyLeg[] } = {}
    legs.forEach((leg) => {
      // Simple grouping: can be enhanced later
      const groupKey = leg.action === "buy" ? "Long Legs" : "Short Legs"
      if (!groups[groupKey]) {
        groups[groupKey] = []
      }
      groups[groupKey].push(leg)
    })
    return groups
  }, [legs])

  // Calculate estimated margin (simplified)
  const estimatedMargin = React.useMemo(() => {
    // For credit spreads: (high strike - low strike) * 100
    // This is a simplified calculation
    if (legs.length >= 2) {
      const strikes = legs.map((l) => l.strike).sort((a, b) => a - b)
      const maxStrike = strikes[strikes.length - 1]
      const minStrike = strikes[0]
      return (maxStrike - minStrike) * 100
    }
    return 0
  }, [legs])

  // Chart title
  const chartTitle = `${symbol} '${strategyName}' Strategy Payoff at Expiration`

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Chart Container with Strategy Info Box */}
      <div className="relative">
        <ResponsiveContainer width="100%" height={600}>
          <ComposedChart
            data={chartData}
            margin={{ top: 80, right: 200, left: 60, bottom: 80 }}
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

            {/* Title */}
            <text
              x="50%"
              y={20}
              textAnchor="middle"
              className="text-lg font-bold fill-foreground"
            >
              {chartTitle}
            </text>

            <CartesianGrid
              strokeDasharray="3 3"
              stroke="hsl(var(--border))"
              opacity={0.4}
            />

            <XAxis
              dataKey="price"
              type="number"
              scale="linear"
              domain={["dataMin", "dataMax"]}
              tick={{ fill: "hsl(var(--foreground))", fontSize: 12 }}
              tickFormatter={formatPrice}
              label={{
                value: "Stock Price",
                position: "insideBottom",
                offset: -5,
                style: { fill: "hsl(var(--foreground))", fontSize: 14, fontWeight: 600 },
              }}
            />

            <YAxis
              tick={{ fill: "hsl(var(--foreground))", fontSize: 12 }}
              tickFormatter={(value) => formatPnl(value)}
              label={{
                value: "Strategy P/L",
                angle: -90,
                position: "insideLeft",
                style: { fill: "hsl(var(--foreground))", fontSize: 14, fontWeight: 600 },
              }}
            />

            <Tooltip
              content={({ active, payload }) => {
                if (active && payload && payload.length) {
                  const data = payload[0].payload
                  return (
                    <div className="bg-card border-2 border-primary/20 rounded-lg shadow-xl p-3">
                      <div className="space-y-1">
                        <div className="font-semibold">
                          Price: {formatPrice(data.price)}
                        </div>
                        <div
                          className={`font-bold ${
                            data.profit >= 0
                              ? "text-green-600 dark:text-green-400"
                              : "text-red-600 dark:text-red-400"
                          }`}
                        >
                          P/L: {formatPnl(data.profit)}
                        </div>
                      </div>
                    </div>
                  )
                }
                return null
              }}
            />

            {/* Zero line */}
            <ReferenceLine
              y={0}
              stroke="hsl(var(--foreground))"
              strokeWidth={2}
              strokeDasharray="5 5"
              opacity={0.6}
            />

            {/* Current price line */}
            {currentPrice !== undefined && (
              <ReferenceLine
                x={currentPrice}
                stroke="#8b5cf6"
                strokeWidth={2}
                strokeDasharray="4 4"
                label={{
                  value: `Current: ${formatPrice(currentPrice)}`,
                  position: "insideTop",
                  fill: "#8b5cf6",
                  fontSize: 11,
                  fontWeight: 600,
                }}
              />
            )}

            {/* Breakeven line */}
            {breakEven !== undefined && (
              <ReferenceLine
                x={breakEven}
                stroke="#3b82f6"
                strokeWidth={2}
                strokeDasharray="6 4"
                label={{
                  value: `Breakeven: ${formatPrice(breakEven)}`,
                  position: "insideTop",
                  fill: "#3b82f6",
                  fontSize: 11,
                  fontWeight: 600,
                  offset: breakEven && currentPrice && Math.abs(breakEven - currentPrice) < 10 ? 20 : 5,
                }}
              />
            )}

            {/* Key points with labels */}
            {keyPoints.map((point, index) => (
              <ReferenceLine
                key={`keypoint-${index}`}
                x={point.price}
                stroke={
                  point.type === "max-profit"
                    ? "#10b981"
                    : point.type === "moon-profit"
                    ? "#10b981"
                    : point.type === "credit-zone"
                    ? "#f59e0b"
                    : "#3b82f6"
                }
                strokeWidth={1.5}
                strokeDasharray="3 3"
                strokeOpacity={0.6}
                label={{
                  value: point.label,
                  position: "top",
                  offset: 10,
                  fill:
                    point.type === "max-profit" || point.type === "moon-profit"
                      ? "#10b981"
                      : point.type === "credit-zone"
                      ? "#f59e0b"
                      : "#3b82f6",
                  fontSize: 10,
                  fontWeight: 600,
                }}
              />
            ))}

            {/* Loss area */}
            <Area
              type="monotone"
              dataKey="loss"
              stroke="#ef4444"
              strokeWidth={3}
              fill="url(#colorLoss)"
              fillOpacity={0.6}
            />

            {/* Profit area */}
            <Area
              type="monotone"
              dataKey="profit"
              stroke="#10b981"
              strokeWidth={3}
              fill="url(#colorProfit)"
              fillOpacity={0.6}
            />
          </ComposedChart>
        </ResponsiveContainer>

        {/* Strategy Info Box - Positioned absolutely in top right */}
        <Card className="absolute top-4 right-4 w-64 p-4 bg-card/95 backdrop-blur-sm border-2 shadow-lg z-10">
          <div className="space-y-3">
            <div className="font-bold text-sm border-b pb-2">Strategy Components</div>
            
            {/* Legs grouped by type */}
            {Object.entries(groupedLegs).map(([groupName, groupLegs]) => (
              <div key={groupName} className="space-y-1">
                <div className="text-xs font-semibold text-muted-foreground uppercase">
                  {groupName}
                </div>
                {groupLegs.map((leg, idx) => {
                  const actionText = leg.action === "buy" ? "Buy" : "Sell"
                  const typeText = leg.type === "call" ? "Call" : "Put"
                  const otmText =
                    currentPrice &&
                    ((leg.type === "call" && leg.strike > currentPrice) ||
                      (leg.type === "put" && leg.strike < currentPrice))
                      ? " (OTM)"
                      : leg.strike === currentPrice
                      ? " (ATM)"
                      : " (ITM)"
                  const premium = leg.premium || 0
                  
                  return (
                    <div key={idx} className="text-xs pl-2">
                      <span className="font-medium">
                        {actionText} {leg.quantity}x {leg.strike} {typeText}
                        {otmText}
                      </span>
                      <span className="text-muted-foreground ml-1">
                        @ ${premium.toFixed(2)}
                      </span>
                    </div>
                  )
                })}
              </div>
            ))}

            <div className="border-t pt-2 space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-muted-foreground">Net Cash Flow:</span>
                <span
                  className={`font-semibold ${
                    netCashFlow >= 0
                      ? "text-green-600 dark:text-green-400"
                      : "text-red-600 dark:text-red-400"
                  }`}
                >
                  {formatPnl(netCashFlow)}
                  {Math.abs(netCashFlow) < 1 && " (Free Trade)"}
                </span>
              </div>
              {estimatedMargin > 0 && (
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Margin:</span>
                  <span className="font-semibold">${estimatedMargin.toLocaleString()}</span>
                </div>
              )}
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}

