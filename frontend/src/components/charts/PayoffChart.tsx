import * as React from "react"
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  defs,
  linearGradient,
  stop,
} from "recharts"

interface PayoffDataPoint {
  price: number
  profit: number
}

interface PayoffChartProps {
  data: PayoffDataPoint[]
  breakEven?: number
  currentPrice?: number
  className?: string
}

export const PayoffChart: React.FC<PayoffChartProps> = ({
  data,
  breakEven,
  currentPrice,
  className,
}) => {
  // Format tooltip
  const formatTooltip = (value: number, name: string) => {
    if (name === "profit") {
      return [`$${value.toFixed(2)}`, "Profit/Loss"]
    }
    return [value, name]
  }

  return (
    <ResponsiveContainer width="100%" height={400} className={className}>
      <AreaChart
        data={data}
        margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
      >
        <defs>
          <linearGradient id="colorProfit" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#26a69a" stopOpacity={0.8} />
            <stop offset="95%" stopColor="#26a69a" stopOpacity={0.1} />
          </linearGradient>
          <linearGradient id="colorLoss" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#ef5350" stopOpacity={0.8} />
            <stop offset="95%" stopColor="#ef5350" stopOpacity={0.1} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
        <XAxis
          dataKey="price"
          label={{ value: "Stock Price", position: "insideBottom", offset: -5 }}
          stroke="hsl(var(--muted-foreground))"
        />
        <YAxis
          label={{ value: "Profit/Loss ($)", angle: -90, position: "insideLeft" }}
          stroke="hsl(var(--muted-foreground))"
        />
        <Tooltip
          formatter={formatTooltip}
          contentStyle={{
            backgroundColor: "hsl(var(--card))",
            border: "1px solid hsl(var(--border))",
            borderRadius: "4px",
          }}
        />
        {breakEven !== undefined && (
          <ReferenceLine
            x={breakEven}
            stroke="hsl(var(--primary))"
            strokeDasharray="5 5"
            label={{ value: "Break-even", position: "top" }}
          />
        )}
        {currentPrice !== undefined && (
          <ReferenceLine
            x={currentPrice}
            stroke="hsl(var(--accent))"
            strokeDasharray="3 3"
            label={{ value: "Current Price", position: "top" }}
          />
        )}
        <Area
          type="monotone"
          dataKey="profit"
          stroke="#26a69a"
          fill="url(#colorProfit)"
          fillOpacity={1}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}

