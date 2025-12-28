import * as React from "react"
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
import { Badge } from "@/components/ui/badge"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

interface Option {
  strike: number
  bid: number
  ask: number
  volume: number
  open_interest: number
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

interface OptionChainPriceViewProps {
  calls: Option[]
  puts: Option[]
  spotPrice: number
  onSelectOption?: (option: Option, type: "call" | "put") => void
}

type ViewType = "price" | "delta" | "gamma" | "theta" | "vega" | "rho" | "iv"

interface ChartDataPoint {
  strike: number
  callValue: number | null
  putValue: number | null
  isATM: boolean
  callOption?: Option
  putOption?: Option
}


// Helper function to validate and clean numeric values
const validateNumber = (value: number | null | undefined): number | null => {
  if (value === null || value === undefined) return null
  if (typeof value !== 'number') return null
  if (isNaN(value) || !isFinite(value)) return null
  return value
}

// Get Greek value from option (supports both flat and nested format)
const getGreek = (option: Option | undefined, greekName: "delta" | "gamma" | "theta" | "vega" | "rho"): number | undefined => {
  if (!option) return undefined
  let value: number | undefined
  // Try direct field first
  if (option[greekName] !== undefined) {
    value = option[greekName] as number
  }
  // Try nested greeks object
  else if (option.greeks && option.greeks[greekName] !== undefined) {
    value = option.greeks[greekName]
  }
  
  // Validate the value
  if (value !== undefined) {
    const validated = validateNumber(value)
    return validated !== null ? validated : undefined
  }
  return undefined
}

// Get IV value from option
const getIV = (option: Option | undefined): number | undefined => {
  if (!option) return undefined
  const iv = option.implied_volatility ?? option.implied_vol
  // Ensure IV is a valid number (not NaN, Infinity, or null)
  const validated = validateNumber(iv)
  if (validated !== null) {
    // If IV is already in decimal format (0-1), return as is
    // If IV is in percentage format (0-100), convert to decimal
    return validated > 1 ? validated / 100 : validated
  }
  return undefined
}

// Custom tooltip component
const CustomTooltip = ({ active, payload, label, viewType }: any) => {
  if (active && payload && payload.length > 0 && typeof label === 'number') {
    const data = payload[0].payload as ChartDataPoint
    
    const formatValue = (value: number | null, type: ViewType): string => {
      if (value === null || value === undefined) return "N/A"
      switch (type) {
        case "price":
          return `$${value.toFixed(2)}`
        case "iv":
          return `${(value * 100).toFixed(2)}%`
        case "delta":
        case "gamma":
        case "theta":
        case "vega":
        case "rho":
          return value.toFixed(4)
        default:
          return value.toFixed(2)
      }
    }
    
    const getLabel = (type: ViewType): string => {
      switch (type) {
        case "price": return "Price"
        case "delta": return "Delta (Δ)"
        case "gamma": return "Gamma (Γ)"
        case "theta": return "Theta (Θ)"
        case "vega": return "Vega (ν)"
        case "rho": return "Rho (ρ)"
        case "iv": return "Implied Volatility"
        default: return "Value"
      }
    }
    
    return (
      <div className="bg-background border rounded-lg shadow-lg p-4 space-y-2">
        <p className="font-semibold">Strike: ${label.toFixed(2)}</p>
        {data.isATM && (
          <Badge variant="outline" className="mb-2">ATM</Badge>
        )}
        
        {data.callValue !== null && (
          <div className="space-y-1 border-l-2 border-blue-500 pl-2">
            <p className="font-medium text-blue-600 dark:text-blue-400">Call {getLabel(viewType)}</p>
            <p className="text-sm">{getLabel(viewType)}: {formatValue(data.callValue, viewType)}</p>
          </div>
        )}
        
        {data.putValue !== null && (
          <div className="space-y-1 border-l-2 border-red-500 pl-2 mt-2">
            <p className="font-medium text-red-600 dark:text-red-400">Put {getLabel(viewType)}</p>
            <p className="text-sm">{getLabel(viewType)}: {formatValue(data.putValue, viewType)}</p>
          </div>
        )}
      </div>
    )
  }
  return null
}

export const OptionChainPriceView: React.FC<OptionChainPriceViewProps> = ({
  calls,
  puts,
  spotPrice,
  onSelectOption,
}) => {
  const [viewType, setViewType] = React.useState<ViewType>("price")
  
  // Transform data for chart based on view type (single metric view)
  const chartData = React.useMemo<ChartDataPoint[]>(() => {
    // Validate spotPrice
    if (!spotPrice || spotPrice <= 0) {
      return []
    }
    
    // Get all unique strikes
    const strikes = new Set<number>()
    
    calls.forEach((call) => {
      if (call && call.strike && call.strike > 0) strikes.add(call.strike)
    })
    puts.forEach((put) => {
      if (put && put.strike && put.strike > 0) strikes.add(put.strike)
    })
    
    if (strikes.size === 0) {
      return []
    }
    
    // Filter strikes around spot price (±30%)
    const minStrike = spotPrice * 0.7
    const maxStrike = spotPrice * 1.3
    const filteredStrikes = Array.from(strikes)
      .filter((s) => s >= minStrike && s <= maxStrike)
      .sort((a, b) => a - b)
    
    // Create data points based on view type
    return filteredStrikes.map((strike) => {
      const call = calls.find(
        (c) => c && c.strike !== undefined && Math.abs(c.strike - strike) < 0.01
      )
      const put = puts.find(
        (p) => p && p.strike !== undefined && Math.abs(p.strike - strike) < 0.01
      )
      
      // Calculate isATM (avoid division by zero)
      const isATM = spotPrice > 0 && Math.abs(strike - spotPrice) / spotPrice < 0.02
      
      let callValue: number | null = null
      let putValue: number | null = null
      
      switch (viewType) {
        case "price":
          // Mid price
          callValue = call && typeof call.bid === 'number' && call.bid > 0 && typeof call.ask === 'number' && call.ask > 0
            ? (call.bid + call.ask) / 2
            : null
          putValue = put && typeof put.bid === 'number' && put.bid > 0 && typeof put.ask === 'number' && put.ask > 0
            ? (put.bid + put.ask) / 2
            : null
          break
        case "delta":
          callValue = getGreek(call, "delta") ?? null
          putValue = getGreek(put, "delta") ?? null
          break
        case "gamma":
          callValue = getGreek(call, "gamma") ?? null
          putValue = getGreek(put, "gamma") ?? null
          break
        case "theta":
          callValue = getGreek(call, "theta") ?? null
          putValue = getGreek(put, "theta") ?? null
          break
        case "vega":
          callValue = getGreek(call, "vega") ?? null
          putValue = getGreek(put, "vega") ?? null
          break
        case "rho":
          callValue = getGreek(call, "rho") ?? null
          putValue = getGreek(put, "rho") ?? null
          break
        case "iv":
          callValue = getIV(call) ?? null
          putValue = getIV(put) ?? null
          break
      }
      
      return {
        strike,
        callValue,
        putValue,
        isATM,
        callOption: call,
        putOption: put,
      }
    })
  }, [calls, puts, spotPrice, viewType])
  
  // Get Y-axis label and formatter based on view type
  const getYAxisConfig = (type: ViewType) => {
    switch (type) {
      case "price":
        return {
          label: "Option Price ($)",
          formatter: (value: number) => `$${value.toFixed(2)}`,
        }
      case "iv":
        return {
          label: "Implied Volatility (%)",
          formatter: (value: number) => `${(value * 100).toFixed(1)}%`,
        }
      case "delta":
        return {
          label: "Delta (Δ)",
          formatter: (value: number) => value.toFixed(3),
        }
      case "gamma":
        return {
          label: "Gamma (Γ)",
          formatter: (value: number) => value.toFixed(4),
        }
      case "theta":
        return {
          label: "Theta (Θ)",
          formatter: (value: number) => value.toFixed(4),
        }
      case "vega":
        return {
          label: "Vega (ν)",
          formatter: (value: number) => value.toFixed(4),
        }
      case "rho":
        return {
          label: "Rho (ρ)",
          formatter: (value: number) => value.toFixed(4),
        }
      default:
        return {
          label: "Value",
          formatter: (value: number) => value.toFixed(2),
        }
    }
  }
  
  const yAxisConfig = getYAxisConfig(viewType)
  
  // Filter data for calls and puts
  const callData = chartData.filter((d) => d.callValue !== null)
  const putData = chartData.filter((d) => d.putValue !== null)
  
  const handleLineClick = (data: any, type: "call" | "put") => {
    if (!onSelectOption || !data || !data.payload) return
    
    const point = data.payload as ChartDataPoint
    const option = type === "call" ? point.callOption : point.putOption
    
    if (option && onSelectOption) {
      onSelectOption(option, type)
    }
  }
  
  const getViewDescription = (type: ViewType): string => {
    switch (type) {
      case "price":
        return "Mid price ((Bid + Ask) / 2) for each strike price. Click on lines to select options."
      case "delta":
        return "Delta (Δ) measures price sensitivity. Call delta: 0-1, Put delta: -1-0. Higher absolute value = more sensitive to underlying price changes."
      case "gamma":
        return "Gamma (Γ) measures Delta's rate of change. Highest at ATM. Higher gamma = faster delta changes with price movement."
      case "theta":
        return "Theta (Θ) measures time decay (typically negative). Shows how much option value decreases per day. More negative = faster time decay."
      case "vega":
        return "Vega (ν) measures volatility sensitivity. Higher vega = more sensitive to implied volatility changes. Highest at ATM."
      case "rho":
        return "Rho (ρ) measures interest rate sensitivity. Typically small. Positive for calls, negative for puts."
      case "iv":
        return "Implied Volatility (IV) shows market's expectation of price movement. Higher IV = higher option prices. Compare to historical volatility."
      default:
        return ""
    }
  }
  
  return (
    <div className="space-y-4">
      {/* View Type Selector */}
      <div className="flex items-center gap-4">
        <Label htmlFor="view-type" className="whitespace-nowrap">View:</Label>
        <Select value={viewType} onValueChange={(value) => setViewType(value as ViewType)}>
          <SelectTrigger id="view-type" className="w-[200px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="price">Price</SelectItem>
            <SelectItem value="delta">Delta (Δ)</SelectItem>
            <SelectItem value="gamma">Gamma (Γ)</SelectItem>
            <SelectItem value="theta">Theta (Θ)</SelectItem>
            <SelectItem value="vega">Vega (ν)</SelectItem>
            <SelectItem value="rho">Rho (ρ)</SelectItem>
            <SelectItem value="iv">Implied Volatility</SelectItem>
          </SelectContent>
        </Select>
      </div>
      
      {/* Description */}
      <div className="text-sm text-muted-foreground bg-muted/50 p-3 rounded-lg">
        {getViewDescription(viewType)}
      </div>
      
      {/* Render based on view type */}
      <>
        {/* Call Options Chart */}
      <div className="border rounded-lg p-4 bg-card">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-blue-600 dark:text-blue-400">Call Options</h3>
          <p className="text-sm text-muted-foreground">
            {viewType === "price" 
              ? "Call option prices by strike price"
              : `Call option ${viewType.toUpperCase()} by strike price`
            }
          </p>
        </div>
        <div>
          {callData.length > 0 ? (
            <ResponsiveContainer width="100%" height={400}>
              <ComposedChart
                data={callData}
                margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
                style={{ cursor: onSelectOption ? "pointer" : "default" }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                <XAxis
                  dataKey="strike"
                  type="number"
                  scale="linear"
                  domain={["dataMin", "dataMax"]}
                  tickFormatter={(value) => `$${value.toFixed(0)}`}
                  label={{ value: "Strike Price", position: "insideBottom", offset: -5 }}
                />
                <YAxis
                  label={{ value: yAxisConfig.label, angle: -90, position: "insideLeft" }}
                  tickFormatter={yAxisConfig.formatter}
                />
                <Tooltip content={<CustomTooltip viewType={viewType} />} />
                <Legend />
                
                {/* Reference line for spot price */}
                {spotPrice > 0 && (
                  <ReferenceLine
                    x={spotPrice}
                    stroke="#fbbf24"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    label={{ value: "Spot Price", position: "top" }}
                  />
                )}
                
                {/* Reference line at zero for Greeks (except delta) */}
                {(viewType !== "delta" && viewType !== "price" && viewType !== "iv") && (
                  <ReferenceLine y={0} stroke="#94a3b8" strokeWidth={1} strokeDasharray="3 3" />
                )}
                
                {/* Main line chart */}
                <Line
                  type="monotone"
                  dataKey="callValue"
                  stroke="#3b82f6"
                  strokeWidth={2.5}
                  dot={{ fill: "#3b82f6", r: 4, strokeWidth: 0 }}
                  activeDot={{ r: 6 }}
                  name={`Call ${viewType === "price" ? "Price" : viewType.toUpperCase()}`}
                  connectNulls={false}
                  onClick={(data) => handleLineClick(data, "call")}
                />
              </ComposedChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[400px] items-center justify-center text-muted-foreground">
              No call option data available
            </div>
          )}
        </div>
      </div>
      
      {/* Put Options Chart */}
      <div className="border rounded-lg p-4 bg-card">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-red-600 dark:text-red-400">Put Options</h3>
          <p className="text-sm text-muted-foreground">
            {viewType === "price" 
              ? "Put option prices by strike price"
              : `Put option ${viewType.toUpperCase()} by strike price`
            }
          </p>
        </div>
        <div>
          {putData.length > 0 ? (
            <ResponsiveContainer width="100%" height={400}>
              <ComposedChart
                data={putData}
                margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
                style={{ cursor: onSelectOption ? "pointer" : "default" }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.3} />
                <XAxis
                  dataKey="strike"
                  type="number"
                  scale="linear"
                  domain={["dataMin", "dataMax"]}
                  tickFormatter={(value) => `$${value.toFixed(0)}`}
                  label={{ value: "Strike Price", position: "insideBottom", offset: -5 }}
                />
                <YAxis
                  label={{ value: yAxisConfig.label, angle: -90, position: "insideLeft" }}
                  tickFormatter={yAxisConfig.formatter}
                />
                <Tooltip content={<CustomTooltip viewType={viewType} />} />
                <Legend />
                
                {/* Reference line for spot price */}
                {spotPrice > 0 && (
                  <ReferenceLine
                    x={spotPrice}
                    stroke="#fbbf24"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    label={{ value: "Spot Price", position: "top" }}
                  />
                )}
                
                {/* Reference line at zero for Greeks (except delta) */}
                {(viewType !== "delta" && viewType !== "price" && viewType !== "iv") && (
                  <ReferenceLine y={0} stroke="#94a3b8" strokeWidth={1} strokeDasharray="3 3" />
                )}
                
                {/* Main line chart */}
                <Line
                  type="monotone"
                  dataKey="putValue"
                  stroke="#ef4444"
                  strokeWidth={2.5}
                  dot={{ fill: "#ef4444", r: 4, strokeWidth: 0 }}
                  activeDot={{ r: 6 }}
                  name={`Put ${viewType === "price" ? "Price" : viewType.toUpperCase()}`}
                  connectNulls={false}
                  onClick={(data) => handleLineClick(data, "put")}
                />
              </ComposedChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[400px] items-center justify-center text-muted-foreground">
              No put option data available
            </div>
          )}
        </div>
      </div>
      </>
    </div>
  )
}

