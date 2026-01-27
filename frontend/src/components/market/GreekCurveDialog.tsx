import * as React from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogClose,
} from "@/components/ui/dialog"
import {
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts"

interface Option {
  strike: number
  bid: number
  ask: number
  delta?: number
  gamma?: number
  theta?: number
  vega?: number
  rho?: number
  implied_volatility?: number
  implied_vol?: number
  greeks?: {
    delta?: number
    gamma?: number
    theta?: number
    vega?: number
    rho?: number
  }
  [key: string]: any
}

interface GreekCurveDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  calls: Option[]
  puts: Option[]
  spotPrice: number
  greekName: "delta" | "gamma" | "theta" | "vega" | "rho" | "iv"
  strike?: number // Optional: highlight a specific strike
}

const getGreek = (option: Option | undefined, greekName: string): number | undefined => {
  if (!option) return undefined
  if (option[greekName] !== undefined) return option[greekName] as number
  if (option.greeks) {
    const greeks = option.greeks as Record<string, number | undefined>
    if (greeks[greekName] !== undefined) {
      return greeks[greekName]
    }
  }
  return undefined
}

const getIV = (option: Option | undefined): number | undefined => {
  if (!option) return undefined
  const iv = option.implied_volatility ?? option.implied_vol
  if (iv !== undefined && iv !== null && typeof iv === 'number' && !isNaN(iv) && isFinite(iv)) {
    return iv > 1 ? iv / 100 : iv
  }
  return undefined
}

const greekLabels: Record<string, { name: string; symbol: string; unit: string }> = {
  delta: { name: "Delta", symbol: "Δ", unit: "" },
  gamma: { name: "Gamma", symbol: "Γ", unit: "" },
  theta: { name: "Theta", symbol: "Θ", unit: " /day" },
  vega: { name: "Vega", symbol: "ν", unit: "" },
  rho: { name: "Rho", symbol: "ρ", unit: "" },
  iv: { name: "Implied Volatility", symbol: "IV", unit: "%" },
}

export const GreekCurveDialog: React.FC<GreekCurveDialogProps> = ({
  open,
  onOpenChange,
  calls,
  puts,
  spotPrice,
  greekName,
  strike,
}) => {
  const chartData = React.useMemo(() => {
    const strikes = new Set<number>()
    calls.forEach((c) => c?.strike && strikes.add(c.strike))
    puts.forEach((p) => p?.strike && strikes.add(p.strike))
    
    const sortedStrikes = Array.from(strikes).sort((a, b) => a - b)
    
    return sortedStrikes.map((s) => {
      const call = calls.find((c) => c && Math.abs((c.strike ?? 0) - s) < 0.01)
      const put = puts.find((p) => p && Math.abs((p.strike ?? 0) - s) < 0.01)
      
      let callValue: number | null = null
      let putValue: number | null = null
      
      if (greekName === "iv") {
        callValue = getIV(call) !== undefined ? (getIV(call)! * 100) : null
        putValue = getIV(put) !== undefined ? (getIV(put)! * 100) : null
      } else {
        callValue = getGreek(call, greekName) ?? null
        putValue = getGreek(put, greekName) ?? null
      }
      
      return {
        strike: s,
        callValue,
        putValue,
        isATM: spotPrice > 0 && Math.abs(s - spotPrice) / spotPrice < 0.02,
        isHighlighted: strike !== undefined && Math.abs(s - strike) < 0.01,
      }
    })
  }, [calls, puts, spotPrice, greekName, strike])

  const greekInfo = greekLabels[greekName] || { name: greekName, symbol: greekName, unit: "" }

  const formatValue = (value: number | null): string => {
    if (value === null) return "-"
    if (greekName === "iv") {
      return `${value.toFixed(2)}%`
    }
    return value.toFixed(4)
  }

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-card border-2 border-primary/20 rounded-lg shadow-xl p-3 backdrop-blur-sm">
          <div className="space-y-1.5">
            <div className="text-sm font-semibold">Strike: ${data.strike.toFixed(2)}</div>
            {data.callValue !== null && (
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                <span className="text-sm">Call {greekInfo.symbol}: {formatValue(data.callValue)}</span>
              </div>
            )}
            {data.putValue !== null && (
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-purple-500"></div>
                <span className="text-sm">Put {greekInfo.symbol}: {formatValue(data.putValue)}</span>
              </div>
            )}
            {data.isATM && (
              <div className="text-xs text-cyan-400 mt-1">📍 At The Money</div>
            )}
          </div>
        </div>
      )
    }
    return null
  }

  // Handle ESC key to close
  React.useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && open) {
        onOpenChange(false)
      }
    }
    document.addEventListener("keydown", handleEscape)
    return () => document.removeEventListener("keydown", handleEscape)
  }, [open, onOpenChange])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[95vw] max-h-[90vh] overflow-y-auto">
        <DialogClose onClose={() => onOpenChange(false)} />
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 pr-8">
            <span className="text-2xl">{greekInfo.symbol}</span>
            <span>{greekInfo.name} Curve{greekInfo.unit}</span>
          </DialogTitle>
          <DialogDescription>
            {greekInfo.name} values across strike prices. Blue line = Calls, Purple line = Puts.
          </DialogDescription>
        </DialogHeader>
        
        <div className="mt-4 h-[500px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
              <XAxis
                dataKey="strike"
                type="number"
                scale="linear"
                domain={["dataMin", "dataMax"]}
                tick={{ fill: "hsl(var(--foreground))", fontSize: 12 }}
                tickFormatter={(value) => `$${value.toFixed(0)}`}
                label={{ 
                  value: "Strike Price ($)", 
                  position: "insideBottom", 
                  offset: -5,
                  style: { fill: "hsl(var(--foreground))", fontSize: 13, fontWeight: 600 }
                }}
              />
              <YAxis
                tick={{ fill: "hsl(var(--foreground))", fontSize: 12 }}
                tickFormatter={(value) => {
                  if (greekName === "iv") return `${value.toFixed(0)}%`
                  return value.toFixed(2)
                }}
                label={{ 
                  value: `${greekInfo.name}${greekInfo.unit}`, 
                  angle: -90, 
                  position: "insideLeft",
                  style: { fill: "hsl(var(--foreground))", fontSize: 13, fontWeight: 600 }
                }}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend 
                wrapperStyle={{ paddingTop: "10px" }}
                formatter={(value) => {
                  if (value === "callValue") return `Call ${greekInfo.symbol}`
                  if (value === "putValue") return `Put ${greekInfo.symbol}`
                  return value
                }}
              />
              {/* Spot price reference line */}
              {spotPrice > 0 && (
                <ReferenceLine
                  x={spotPrice}
                  stroke="#fbbf24"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  label={{ 
                    value: "Spot Price", 
                    position: "insideTopRight",
                    fill: "#fbbf24",
                    fontSize: 11,
                    fontWeight: 600
                  }}
                />
              )}
              {/* Highlighted strike reference line */}
              {strike !== undefined && (
                <ReferenceLine
                  x={strike}
                  stroke="#3b82f6"
                  strokeWidth={2}
                  strokeDasharray="3 3"
                  label={{ 
                    value: `Strike: $${strike.toFixed(2)}`, 
                    position: "insideTop",
                    fill: "#3b82f6",
                    fontSize: 11,
                    fontWeight: 600
                  }}
                />
              )}
              {/* Call line */}
              <Line
                type="monotone"
                dataKey="callValue"
                stroke="#3b82f6"
                strokeWidth={2.5}
                dot={{ r: 3, fill: "#3b82f6" }}
                activeDot={{ r: 5 }}
                name="callValue"
                connectNulls={false}
              />
              {/* Put line */}
              <Line
                type="monotone"
                dataKey="putValue"
                stroke="#a855f7"
                strokeWidth={2.5}
                dot={{ r: 3, fill: "#a855f7" }}
                activeDot={{ r: 5 }}
                name="putValue"
                connectNulls={false}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </DialogContent>
    </Dialog>
  )
}
