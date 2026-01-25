import * as React from "react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { StrategyLeg } from "@/services/api/strategy"

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

interface OptionChainTableProps {
  calls: Option[]
  puts: Option[]
  spotPrice: number
  onSelectOption?: (option: Option, type: "call" | "put") => void
  // New props for one-click actions
  onAddLeg?: (leg: Omit<StrategyLeg, "expiry">) => void
  expirationDate?: string
}

export const OptionChainTable: React.FC<OptionChainTableProps> = ({
  calls,
  puts,
  spotPrice,
  onSelectOption,
  onAddLeg,
  expirationDate,
}) => {
  const [currentPage, setCurrentPage] = React.useState(1)
  const rowsPerPage = 15

  // Combine calls and puts by strike price
  // Filter to show strikes around spot price (±30%)
  const allStrikes = React.useMemo(() => {
    const strikes = new Set<number>()
    const minStrike = spotPrice * 0.7
    const maxStrike = spotPrice * 1.3
    
    calls.forEach((c) => {
      if (c.strike >= minStrike && c.strike <= maxStrike) {
        strikes.add(c.strike)
      }
    })
    puts.forEach((p) => {
      if (p.strike >= minStrike && p.strike <= maxStrike) {
        strikes.add(p.strike)
      }
    })
    return Array.from(strikes).sort((a, b) => a - b)
  }, [calls, puts, spotPrice])

  // Calculate max Volume and OI for data bars
  const maxVolume = React.useMemo(() => {
    const allOptions = [...calls, ...puts]
    return Math.max(...allOptions.map((opt) => opt.volume || 0), 1)
  }, [calls, puts])

  const maxOI = React.useMemo(() => {
    const allOptions = [...calls, ...puts]
    return Math.max(...allOptions.map((opt) => opt.open_interest || (opt as any).openInterest || 0), 1)
  }, [calls, puts])

  // Pagination
  const totalPages = Math.ceil(allStrikes.length / rowsPerPage)
  const startIndex = (currentPage - 1) * rowsPerPage
  const endIndex = startIndex + rowsPerPage
  const strikes = allStrikes.slice(startIndex, endIndex)

  // Reset to page 1 when strikes change
  React.useEffect(() => {
    setCurrentPage(1)
  }, [allStrikes.length])

  const getOptionByStrike = (strike: number, options: Option[]) => {
    return options.find((o) => {
      if (!o) return false
      const optionStrike = o.strike ?? (o as any).strike_price
      return optionStrike !== undefined && Math.abs(optionStrike - strike) < 0.01
    })
  }

  const getGreek = (option: Option | undefined, greek: string): number | undefined => {
    if (!option) return undefined
    // Try direct field first
    if (option[greek] !== undefined) return option[greek] as number
    // Try nested greeks object
    if (option.greeks) {
      const greeks = option.greeks as Record<string, number | undefined>
      if (greeks[greek] !== undefined) return greeks[greek]
    }
    return undefined
  }

  const getIV = (option: Option | undefined): number | undefined => {
    if (!option) return undefined
    // Try both implied_volatility and implied_vol
    return option.implied_volatility ?? option.implied_vol
  }

  const formatGreek = (value: number | undefined): string => {
    if (value === undefined || value === null) return "-"
    return value.toFixed(4)
  }

  const formatIV = (value: number | undefined): string => {
    if (value === undefined || value === null) return "-"
    // IV is typically shown as percentage (e.g., 0.25 = 25%)
    return `${(value * 100).toFixed(2)}%`
  }

  // Check if option is ITM (In-The-Money)
  const isITM = (strike: number, type: "call" | "put"): boolean => {
    if (type === "call") {
      return strike < spotPrice
    } else {
      return strike > spotPrice
    }
  }

  // Check if strike is ATM (At-The-Money)
  const isATM = (strike: number): boolean => {
    const percentDiff = Math.abs((strike - spotPrice) / spotPrice)
    return percentDiff < 0.02 // Within 2%
  }

  // Handle one-click add leg
  const handleBidClick = (option: Option, type: "call" | "put", e: React.MouseEvent) => {
    e.stopPropagation()
    if (!onAddLeg || !expirationDate) return
    
    const bid = option.bid ?? (option as any).bid_price ?? 0
    if (bid <= 0) return
    
    onAddLeg({
      type,
      action: "sell", // Clicking Bid = Sell
      strike: option.strike,
      quantity: 1,
      premium: bid,
      delta: getGreek(option, "delta"),
      gamma: getGreek(option, "gamma"),
      theta: getGreek(option, "theta"),
      vega: getGreek(option, "vega"),
      rho: getGreek(option, "rho"),
      implied_volatility: getIV(option),
      bid: bid,
      ask: option.ask ?? (option as any).ask_price ?? 0,
      volume: option.volume || 0,
      open_interest: option.open_interest || (option as any).openInterest || 0,
    })
  }

  const handleAskClick = (option: Option, type: "call" | "put", e: React.MouseEvent) => {
    e.stopPropagation()
    if (!onAddLeg || !expirationDate) return
    
    const ask = option.ask ?? (option as any).ask_price ?? 0
    if (ask <= 0) return
    
    onAddLeg({
      type,
      action: "buy", // Clicking Ask = Buy
      strike: option.strike,
      quantity: 1,
      premium: ask,
      delta: getGreek(option, "delta"),
      gamma: getGreek(option, "gamma"),
      theta: getGreek(option, "theta"),
      vega: getGreek(option, "vega"),
      rho: getGreek(option, "rho"),
      implied_volatility: getIV(option),
      bid: option.bid ?? (option as any).bid_price ?? 0,
      ask: ask,
      volume: option.volume || 0,
      open_interest: option.open_interest || (option as any).openInterest || 0,
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Option Chain Table</CardTitle>
        <CardDescription>
          Greeks: Δ (Delta), Γ (Gamma), Θ (Theta), ν (Vega), ρ (Rho), IV (Implied Volatility)
          {onAddLeg && expirationDate && (
            <span className="block mt-1 text-xs text-cyan-400">
              💡 Click Bid to add Sell Leg, Click Ask to add Buy Leg
            </span>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="sticky left-0 bg-background z-10">Strike</TableHead>
                <TableHead className="text-right">Call Bid</TableHead>
                <TableHead className="text-right">Call Ask</TableHead>
                <TableHead className="text-right">Δ</TableHead>
                <TableHead className="text-right">Γ</TableHead>
                <TableHead className="text-right">Θ</TableHead>
                <TableHead className="text-right">ν</TableHead>
                <TableHead className="text-right">ρ</TableHead>
                <TableHead className="text-right">IV</TableHead>
                <TableHead className="text-right">Vol</TableHead>
                <TableHead className="text-right">OI</TableHead>
                <TableHead className="text-right">Put Bid</TableHead>
                <TableHead className="text-right">Put Ask</TableHead>
                <TableHead className="text-right">Δ</TableHead>
                <TableHead className="text-right">Γ</TableHead>
                <TableHead className="text-right">Θ</TableHead>
                <TableHead className="text-right">ν</TableHead>
                <TableHead className="text-right">ρ</TableHead>
                <TableHead className="text-right">IV</TableHead>
                <TableHead className="text-right">Vol</TableHead>
                <TableHead className="text-right">OI</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {strikes.map((strike, index) => {
                const call = getOptionByStrike(strike, calls)
                const put = getOptionByStrike(strike, puts)
                const atm = isATM(strike)
                const callITM = call ? isITM(strike, "call") : false
                const putITM = put ? isITM(strike, "put") : false
                
                // Check if this is the ATM boundary (for border)
                const prevStrike = index > 0 ? strikes[index - 1] : null
                const isATMBoundary = prevStrike && !isATM(prevStrike) && atm

                return (
                  <React.Fragment key={strike}>
                    {/* ATM Boundary Line */}
                    {isATMBoundary && (
                      <TableRow className="h-0 p-0 border-t-2 border-cyan-400">
                        <TableCell colSpan={21} className="h-0 p-0 border-0"></TableCell>
                      </TableRow>
                    )}
                    <TableRow
                      className={`
                        ${atm ? "bg-slate-800/30 font-medium border-l-2 border-cyan-400" : ""}
                        ${callITM ? "bg-yellow-500/10 dark:bg-yellow-500/20" : ""}
                        ${putITM && !callITM ? "bg-purple-500/10 dark:bg-purple-500/20" : ""}
                        ${callITM && putITM ? "bg-gradient-to-r from-yellow-500/10 to-purple-500/10 dark:from-yellow-500/20 dark:to-purple-500/20" : ""}
                        hover:bg-muted/50 transition-colors
                      `}
                      onClick={() => {
                        if (call && onSelectOption) onSelectOption(call, "call")
                        if (put && onSelectOption) onSelectOption(put, "put")
                      }}
                      style={{ cursor: onSelectOption ? "pointer" : "default" }}
                    >
                      <TableCell className="sticky left-0 bg-background z-10 font-medium">
                        {atm && <Badge variant="outline" className="mr-1 border-cyan-400 text-cyan-400">ATM</Badge>}
                        ${strike.toFixed(2)}
                      </TableCell>
                      {/* Call columns */}
                      <TableCell 
                        className={`text-right ${onAddLeg && call && (call.bid ?? (call as any).bid_price ?? 0) > 0 ? "cursor-pointer hover:bg-rose-500/20 hover:text-rose-500 font-semibold" : ""}`}
                        onClick={(e) => call && handleBidClick(call, "call", e)}
                        title={onAddLeg && call ? "Click to add Sell Call Leg" : undefined}
                      >
                        {call ? `$${((call.bid ?? (call as any).bid_price ?? 0)).toFixed(2)}` : "-"}
                      </TableCell>
                      <TableCell 
                        className={`text-right ${onAddLeg && call && (call.ask ?? (call as any).ask_price ?? 0) > 0 ? "cursor-pointer hover:bg-emerald-500/20 hover:text-emerald-500 font-semibold" : ""}`}
                        onClick={(e) => call && handleAskClick(call, "call", e)}
                        title={onAddLeg && call ? "Click to add Buy Call Leg" : undefined}
                      >
                        {call ? `$${((call.ask ?? (call as any).ask_price ?? 0)).toFixed(2)}` : "-"}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {formatGreek(getGreek(call, "delta"))}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {formatGreek(getGreek(call, "gamma"))}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {formatGreek(getGreek(call, "theta"))}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {formatGreek(getGreek(call, "vega"))}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {formatGreek(getGreek(call, "rho"))}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm font-semibold">
                        {formatIV(getIV(call))}
                      </TableCell>
                      {/* Volume with data bar */}
                      <TableCell className="text-right text-muted-foreground relative">
                        {call ? (
                          <div className="flex items-center justify-end gap-2">
                            <div className="relative flex-1 max-w-[80px]">
                              <div 
                                className="absolute inset-0 bg-blue-100 dark:bg-blue-900/30 rounded"
                                style={{ 
                                  width: `${((call.volume || 0) / maxVolume) * 100}%`,
                                  minWidth: call.volume && call.volume > 0 ? "2px" : "0px"
                                }}
                              />
                              <span className="relative z-10">
                                {(call.volume ?? 0).toLocaleString()}
                              </span>
                            </div>
                          </div>
                        ) : "-"}
                      </TableCell>
                      {/* OI with data bar */}
                      <TableCell className="text-right text-muted-foreground relative">
                        {call ? (
                          <div className="flex items-center justify-end gap-2">
                            <div className="relative flex-1 max-w-[80px]">
                              <div 
                                className="absolute inset-0 bg-blue-100 dark:bg-blue-900/30 rounded"
                                style={{ 
                                  width: `${((call.open_interest || (call as any).openInterest || 0) / maxOI) * 100}%`,
                                  minWidth: (call.open_interest || (call as any).openInterest || 0) > 0 ? "2px" : "0px"
                                }}
                              />
                              <span className="relative z-10">
                                {(call.open_interest ?? (call as any).openInterest ?? 0).toLocaleString()}
                              </span>
                            </div>
                          </div>
                        ) : "-"}
                      </TableCell>
                      {/* Put columns */}
                      <TableCell 
                        className={`text-right ${onAddLeg && put && (put.bid ?? (put as any).bid_price ?? 0) > 0 ? "cursor-pointer hover:bg-rose-500/20 hover:text-rose-500 font-semibold" : ""}`}
                        onClick={(e) => put && handleBidClick(put, "put", e)}
                        title={onAddLeg && put ? "Click to add Sell Put Leg" : undefined}
                      >
                        {put ? `$${((put.bid ?? (put as any).bid_price ?? 0)).toFixed(2)}` : "-"}
                      </TableCell>
                      <TableCell 
                        className={`text-right ${onAddLeg && put && (put.ask ?? (put as any).ask_price ?? 0) > 0 ? "cursor-pointer hover:bg-emerald-500/20 hover:text-emerald-500 font-semibold" : ""}`}
                        onClick={(e) => put && handleAskClick(put, "put", e)}
                        title={onAddLeg && put ? "Click to add Buy Put Leg" : undefined}
                      >
                        {put ? `$${((put.ask ?? (put as any).ask_price ?? 0)).toFixed(2)}` : "-"}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {formatGreek(getGreek(put, "delta"))}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {formatGreek(getGreek(put, "gamma"))}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {formatGreek(getGreek(put, "theta"))}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {formatGreek(getGreek(put, "vega"))}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm">
                        {formatGreek(getGreek(put, "rho"))}
                      </TableCell>
                      <TableCell className="text-right font-mono text-sm font-semibold">
                        {formatIV(getIV(put))}
                      </TableCell>
                      {/* Volume with data bar */}
                      <TableCell className="text-right text-muted-foreground relative">
                        {put ? (
                          <div className="flex items-center justify-end gap-2">
                            <div className="relative flex-1 max-w-[80px]">
                              <div 
                                className="absolute inset-0 bg-blue-100 dark:bg-blue-900/30 rounded"
                                style={{ 
                                  width: `${((put.volume || 0) / maxVolume) * 100}%`,
                                  minWidth: put.volume && put.volume > 0 ? "2px" : "0px"
                                }}
                              />
                              <span className="relative z-10">
                                {(put.volume ?? 0).toLocaleString()}
                              </span>
                            </div>
                          </div>
                        ) : "-"}
                      </TableCell>
                      {/* OI with data bar */}
                      <TableCell className="text-right text-muted-foreground relative">
                        {put ? (
                          <div className="flex items-center justify-end gap-2">
                            <div className="relative flex-1 max-w-[80px]">
                              <div 
                                className="absolute inset-0 bg-blue-100 dark:bg-blue-900/30 rounded"
                                style={{ 
                                  width: `${((put.open_interest || (put as any).openInterest || 0) / maxOI) * 100}%`,
                                  minWidth: (put.open_interest || (put as any).openInterest || 0) > 0 ? "2px" : "0px"
                                }}
                              />
                              <span className="relative z-10">
                                {(put.open_interest ?? (put as any).openInterest ?? 0).toLocaleString()}
                              </span>
                            </div>
                          </div>
                        ) : "-"}
                      </TableCell>
                    </TableRow>
                  </React.Fragment>
                )
              })}
            </TableBody>
          </Table>
        </div>
        
        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between mt-4">
            <div className="text-sm text-muted-foreground">
              Showing {startIndex + 1}-{Math.min(endIndex, allStrikes.length)} of {allStrikes.length} strikes
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="font-medium"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <div className="text-sm font-medium text-foreground px-3 py-1 bg-muted/50 rounded-md">
                Page {currentPage} of {totalPages}
              </div>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="font-medium"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
