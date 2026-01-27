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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { StrategyLeg } from "@/services/api/strategy"
import { GreekCurveDialog } from "./GreekCurveDialog"

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
  const scrollContainerRef = React.useRef<HTMLDivElement>(null)
  const [greekDialogOpen, setGreekDialogOpen] = React.useState(false)
  const [selectedGreek, setSelectedGreek] = React.useState<"delta" | "gamma" | "theta" | "vega" | "rho" | "iv">("delta")
  const [selectedStrike, setSelectedStrike] = React.useState<number | undefined>(undefined)
  
  // Confirmation dialog state
  const [confirmDialogOpen, setConfirmDialogOpen] = React.useState(false)
  const [pendingLeg, setPendingLeg] = React.useState<Omit<StrategyLeg, "expiry"> | null>(null)

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

  // Find ATM strike index for auto-scroll
  const atmStrikeIndex = React.useMemo(() => {
    if (!spotPrice || allStrikes.length === 0) return 0
    let closestIndex = 0
    let minDistance = Infinity
    allStrikes.forEach((strike, index) => {
      const distance = Math.abs(strike - spotPrice)
      if (distance < minDistance) {
        minDistance = distance
        closestIndex = index
      }
    })
    return closestIndex
  }, [allStrikes, spotPrice])

  // Auto-scroll to ATM strike on mount and when strikes change
  React.useEffect(() => {
    if (scrollContainerRef.current && allStrikes.length > 0) {
      // Wait for DOM to render
      setTimeout(() => {
        const container = scrollContainerRef.current
        if (!container) return
        
        // Find the row element for ATM strike
        const rows = container.querySelectorAll('tbody tr')
        if (rows.length > atmStrikeIndex) {
          const targetRow = rows[atmStrikeIndex] as HTMLElement
          if (targetRow) {
            // Scroll to center the row
            const rowTop = targetRow.offsetTop
            const containerHeight = container.clientHeight
            const rowHeight = targetRow.clientHeight
            const scrollPosition = rowTop - (containerHeight / 2) + (rowHeight / 2)
            
            container.scrollTo({
              top: Math.max(0, scrollPosition),
              behavior: 'smooth'
            })
          }
        }
      }, 100)
    }
  }, [allStrikes.length, atmStrikeIndex])

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

  // Handle one-click add leg with confirmation
  const handleBidClick = (option: Option, type: "call" | "put", e: React.MouseEvent) => {
    e.stopPropagation()
    if (!onAddLeg || !expirationDate) return
    
    const bid = option.bid ?? (option as any).bid_price ?? 0
    if (bid <= 0) return
    
    // Store pending leg and show confirmation dialog
    setPendingLeg({
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
    setConfirmDialogOpen(true)
  }

  const handleAskClick = (option: Option, type: "call" | "put", e: React.MouseEvent) => {
    e.stopPropagation()
    if (!onAddLeg || !expirationDate) return
    
    const ask = option.ask ?? (option as any).ask_price ?? 0
    if (ask <= 0) return
    
    // Store pending leg and show confirmation dialog
    setPendingLeg({
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
    setConfirmDialogOpen(true)
  }

  // Confirm and add leg
  const handleConfirmAddLeg = () => {
    if (pendingLeg && onAddLeg) {
      onAddLeg(pendingLeg)
      setPendingLeg(null)
      setConfirmDialogOpen(false)
    }
  }

  // Cancel adding leg
  const handleCancelAddLeg = () => {
    setPendingLeg(null)
    setConfirmDialogOpen(false)
  }

  const handleGreekClick = (greekName: "delta" | "gamma" | "theta" | "vega" | "rho" | "iv", strike?: number, e?: React.MouseEvent) => {
    if (e) e.stopPropagation()
    setSelectedGreek(greekName)
    setSelectedStrike(strike)
    setGreekDialogOpen(true)
  }

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex-shrink-0 pb-3">
        <CardTitle className="text-base">Option Chain Table</CardTitle>
        <CardDescription className="text-xs leading-relaxed">
          <span className="inline-block">Greeks: Δ (Delta), Γ (Gamma), Θ (Theta), ν (Vega), ρ (Rho), IV (Implied Volatility) - Click to view curves</span>
          {onAddLeg && expirationDate && (
            <span className="block mt-1 text-xs text-cyan-400">
              💡 Click Bid to add Sell Leg, Click Ask to add Buy Leg
            </span>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden flex flex-col min-h-0">
        <div ref={scrollContainerRef} className="flex-1 overflow-auto -mx-2 px-2">
          <Table className="min-w-full">
            <TableHeader className="sticky top-0 z-20 bg-background border-b shadow-sm">
              <TableRow>
                <TableHead className="sticky left-0 bg-background z-30 border-r">Strike</TableHead>
                <TableHead className="text-right">Type</TableHead>
                <TableHead className="text-right">Bid</TableHead>
                <TableHead className="text-right">Ask</TableHead>
                <TableHead className="text-right cursor-pointer hover:bg-muted/50" onClick={() => handleGreekClick("delta")} title="Click to view Delta curve">
                  Δ
                </TableHead>
                <TableHead className="text-right cursor-pointer hover:bg-muted/50" onClick={() => handleGreekClick("gamma")} title="Click to view Gamma curve">
                  Γ
                </TableHead>
                <TableHead className="text-right cursor-pointer hover:bg-muted/50" onClick={() => handleGreekClick("theta")} title="Click to view Theta curve">
                  Θ
                </TableHead>
                <TableHead className="text-right cursor-pointer hover:bg-muted/50" onClick={() => handleGreekClick("vega")} title="Click to view Vega curve">
                  ν
                </TableHead>
                <TableHead className="text-right cursor-pointer hover:bg-muted/50" onClick={() => handleGreekClick("rho")} title="Click to view Rho curve">
                  ρ
                </TableHead>
                <TableHead className="text-right cursor-pointer hover:bg-muted/50" onClick={() => handleGreekClick("iv")} title="Click to view IV curve">
                  IV
                </TableHead>
                <TableHead className="text-right">Vol</TableHead>
                <TableHead className="text-right">OI</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {allStrikes.map((strike, index) => {
                const call = getOptionByStrike(strike, calls)
                const put = getOptionByStrike(strike, puts)
                const atm = isATM(strike)
                const callITM = call ? isITM(strike, "call") : false
                const putITM = put ? isITM(strike, "put") : false
                
                // Check if this is the ATM boundary (for border)
                const prevStrike = index > 0 ? allStrikes[index - 1] : null
                const isATMBoundary = prevStrike && !isATM(prevStrike) && atm

                return (
                  <React.Fragment key={strike}>
                    {/* ATM Boundary Line */}
                    {isATMBoundary && (
                      <TableRow className="h-0 p-0 border-t-2 border-cyan-400">
                        <TableCell colSpan={13} className="h-0 p-0 border-0"></TableCell>
                      </TableRow>
                    )}
                    {/* Call Row */}
                    <TableRow
                      className={`
                        ${atm ? "bg-slate-800/30 font-medium border-l-2 border-cyan-400" : ""}
                        ${callITM ? "bg-yellow-500/10 dark:bg-yellow-500/20" : ""}
                        hover:bg-muted/50 transition-colors
                      `}
                      onClick={() => {
                        if (call && onSelectOption) onSelectOption(call, "call")
                      }}
                      style={{ cursor: onSelectOption ? "pointer" : "default" }}
                    >
                      <TableCell className="sticky left-0 bg-background z-10 font-medium min-w-[100px] px-3" rowSpan={put ? 2 : 1}>
                        {atm && <Badge variant="outline" className="mr-1 border-cyan-400 text-cyan-400 text-xs">ATM</Badge>}
                        <span className="whitespace-nowrap">${strike.toFixed(2)}</span>
                      </TableCell>
                      <TableCell className="text-right px-2 font-semibold text-blue-500">
                        CALL
                      </TableCell>
                      <TableCell 
                        className={`text-right px-2 min-w-[80px] ${onAddLeg && call && (call.bid ?? (call as any).bid_price ?? 0) > 0 ? "cursor-pointer hover:bg-rose-500/20 hover:text-rose-500 font-semibold" : ""}`}
                        onClick={(e) => call && handleBidClick(call, "call", e)}
                        title={onAddLeg && call ? "Click to add Sell Call Leg" : undefined}
                      >
                        <span className="whitespace-nowrap">{call ? `$${((call.bid ?? (call as any).bid_price ?? 0)).toFixed(2)}` : "-"}</span>
                      </TableCell>
                      <TableCell 
                        className={`text-right px-2 min-w-[80px] ${onAddLeg && call && (call.ask ?? (call as any).ask_price ?? 0) > 0 ? "cursor-pointer hover:bg-emerald-500/20 hover:text-emerald-500 font-semibold" : ""}`}
                        onClick={(e) => call && handleAskClick(call, "call", e)}
                        title={onAddLeg && call ? "Click to add Buy Call Leg" : undefined}
                      >
                        <span className="whitespace-nowrap">{call ? `$${((call.ask ?? (call as any).ask_price ?? 0)).toFixed(2)}` : "-"}</span>
                      </TableCell>
                      <TableCell 
                        className="text-right font-mono text-xs px-1.5 min-w-[60px] cursor-pointer hover:bg-primary/20 hover:text-primary transition-colors"
                        onClick={(e) => handleGreekClick("delta", strike, e)}
                        title="Click to view Delta curve"
                      >
                        {formatGreek(getGreek(call, "delta"))}
                      </TableCell>
                      <TableCell 
                        className="text-right font-mono text-xs px-1.5 min-w-[60px] cursor-pointer hover:bg-primary/20 hover:text-primary transition-colors"
                        onClick={(e) => handleGreekClick("gamma", strike, e)}
                        title="Click to view Gamma curve"
                      >
                        {formatGreek(getGreek(call, "gamma"))}
                      </TableCell>
                      <TableCell 
                        className="text-right font-mono text-xs px-1.5 min-w-[60px] cursor-pointer hover:bg-primary/20 hover:text-primary transition-colors"
                        onClick={(e) => handleGreekClick("theta", strike, e)}
                        title="Click to view Theta curve"
                      >
                        {formatGreek(getGreek(call, "theta"))}
                      </TableCell>
                      <TableCell 
                        className="text-right font-mono text-xs px-1.5 min-w-[60px] cursor-pointer hover:bg-primary/20 hover:text-primary transition-colors"
                        onClick={(e) => handleGreekClick("vega", strike, e)}
                        title="Click to view Vega curve"
                      >
                        {formatGreek(getGreek(call, "vega"))}
                      </TableCell>
                      <TableCell 
                        className="text-right font-mono text-xs px-1.5 min-w-[60px] cursor-pointer hover:bg-primary/20 hover:text-primary transition-colors"
                        onClick={(e) => handleGreekClick("rho", strike, e)}
                        title="Click to view Rho curve"
                      >
                        {formatGreek(getGreek(call, "rho"))}
                      </TableCell>
                      <TableCell 
                        className="text-right font-mono text-xs font-semibold px-2 min-w-[70px] cursor-pointer hover:bg-primary/20 hover:text-primary transition-colors"
                        onClick={(e) => handleGreekClick("iv", strike, e)}
                        title="Click to view IV curve"
                      >
                        {formatIV(getIV(call))}
                      </TableCell>
                      <TableCell 
                        className="text-right text-muted-foreground relative px-2 min-w-[70px]"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {call ? (
                          <div className="flex items-center justify-end gap-1">
                            <div className="relative flex-1 max-w-[90px]">
                              <div 
                                className="absolute inset-0 bg-blue-100 dark:bg-blue-900/30 rounded"
                                style={{ 
                                  width: `${((call.volume || 0) / maxVolume) * 100}%`,
                                  minWidth: call.volume && call.volume > 0 ? "2px" : "0px"
                                }}
                              />
                              <span className="relative z-10 text-xs whitespace-nowrap">
                                {(call.volume ?? 0).toLocaleString()}
                              </span>
                            </div>
                          </div>
                        ) : "-"}
                      </TableCell>
                      <TableCell 
                        className="text-right text-muted-foreground relative px-2 min-w-[70px]"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {call ? (
                          <div className="flex items-center justify-end gap-1">
                            <div className="relative flex-1 max-w-[90px]">
                              <div 
                                className="absolute inset-0 bg-blue-100 dark:bg-blue-900/30 rounded"
                                style={{ 
                                  width: `${((call.open_interest || (call as any).openInterest || 0) / maxOI) * 100}%`,
                                  minWidth: (call.open_interest || (call as any).openInterest || 0) > 0 ? "2px" : "0px"
                                }}
                              />
                              <span className="relative z-10 text-xs whitespace-nowrap">
                                {(call.open_interest ?? (call as any).openInterest ?? 0).toLocaleString()}
                              </span>
                            </div>
                          </div>
                        ) : "-"}
                      </TableCell>
                    </TableRow>
                    {/* Put Row */}
                    {put && (
                      <TableRow
                        className={`
                          ${atm ? "bg-slate-800/30 font-medium border-l-2 border-cyan-400" : ""}
                          ${putITM ? "bg-purple-500/10 dark:bg-purple-500/20" : ""}
                          hover:bg-muted/50 transition-colors
                        `}
                        onClick={() => {
                          if (put && onSelectOption) onSelectOption(put, "put")
                        }}
                        style={{ cursor: onSelectOption ? "pointer" : "default" }}
                      >
                        <TableCell className="text-right px-2 font-semibold text-purple-500">
                          PUT
                        </TableCell>
                        <TableCell 
                          className={`text-right px-2 min-w-[80px] ${onAddLeg && put && (put.bid ?? (put as any).bid_price ?? 0) > 0 ? "cursor-pointer hover:bg-rose-500/20 hover:text-rose-500 font-semibold" : ""}`}
                          onClick={(e) => put && handleBidClick(put, "put", e)}
                          title={onAddLeg && put ? "Click to add Sell Put Leg" : undefined}
                        >
                          <span className="whitespace-nowrap">{put ? `$${((put.bid ?? (put as any).bid_price ?? 0)).toFixed(2)}` : "-"}</span>
                        </TableCell>
                        <TableCell 
                          className={`text-right px-2 min-w-[80px] ${onAddLeg && put && (put.ask ?? (put as any).ask_price ?? 0) > 0 ? "cursor-pointer hover:bg-emerald-500/20 hover:text-emerald-500 font-semibold" : ""}`}
                          onClick={(e) => put && handleAskClick(put, "put", e)}
                          title={onAddLeg && put ? "Click to add Buy Put Leg" : undefined}
                        >
                          <span className="whitespace-nowrap">{put ? `$${((put.ask ?? (put as any).ask_price ?? 0)).toFixed(2)}` : "-"}</span>
                        </TableCell>
                        <TableCell 
                          className="text-right font-mono text-xs px-1.5 min-w-[60px] cursor-pointer hover:bg-primary/20 hover:text-primary transition-colors"
                          onClick={(e) => handleGreekClick("delta", strike, e)}
                          title="Click to view Delta curve"
                        >
                          {formatGreek(getGreek(put, "delta"))}
                        </TableCell>
                        <TableCell 
                          className="text-right font-mono text-xs px-1.5 min-w-[60px] cursor-pointer hover:bg-primary/20 hover:text-primary transition-colors"
                          onClick={(e) => handleGreekClick("gamma", strike, e)}
                          title="Click to view Gamma curve"
                        >
                          {formatGreek(getGreek(put, "gamma"))}
                        </TableCell>
                        <TableCell 
                          className="text-right font-mono text-xs px-1.5 min-w-[60px] cursor-pointer hover:bg-primary/20 hover:text-primary transition-colors"
                          onClick={(e) => handleGreekClick("theta", strike, e)}
                          title="Click to view Theta curve"
                        >
                          {formatGreek(getGreek(put, "theta"))}
                        </TableCell>
                        <TableCell 
                          className="text-right font-mono text-xs px-1.5 min-w-[60px] cursor-pointer hover:bg-primary/20 hover:text-primary transition-colors"
                          onClick={(e) => handleGreekClick("vega", strike, e)}
                          title="Click to view Vega curve"
                        >
                          {formatGreek(getGreek(put, "vega"))}
                        </TableCell>
                        <TableCell 
                          className="text-right font-mono text-xs px-1.5 min-w-[60px] cursor-pointer hover:bg-primary/20 hover:text-primary transition-colors"
                          onClick={(e) => handleGreekClick("rho", strike, e)}
                          title="Click to view Rho curve"
                        >
                          {formatGreek(getGreek(put, "rho"))}
                        </TableCell>
                        <TableCell 
                          className="text-right font-mono text-xs font-semibold px-2 min-w-[70px] cursor-pointer hover:bg-primary/20 hover:text-primary transition-colors"
                          onClick={(e) => handleGreekClick("iv", strike, e)}
                          title="Click to view IV curve"
                        >
                          {formatIV(getIV(put))}
                        </TableCell>
                        <TableCell 
                          className="text-right text-muted-foreground relative px-2 min-w-[70px]"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {put ? (
                            <div className="flex items-center justify-end gap-1">
                              <div className="relative flex-1 max-w-[90px]">
                                <div 
                                  className="absolute inset-0 bg-purple-100 dark:bg-purple-900/30 rounded"
                                  style={{ 
                                    width: `${((put.volume || 0) / maxVolume) * 100}%`,
                                    minWidth: put.volume && put.volume > 0 ? "2px" : "0px"
                                  }}
                                />
                                <span className="relative z-10 text-xs whitespace-nowrap">
                                  {(put.volume ?? 0).toLocaleString()}
                                </span>
                              </div>
                            </div>
                          ) : "-"}
                        </TableCell>
                        <TableCell 
                          className="text-right text-muted-foreground relative px-2 min-w-[70px]"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {put ? (
                            <div className="flex items-center justify-end gap-1">
                              <div className="relative flex-1 max-w-[90px]">
                                <div 
                                  className="absolute inset-0 bg-purple-100 dark:bg-purple-900/30 rounded"
                                  style={{ 
                                    width: `${((put.open_interest || (put as any).openInterest || 0) / maxOI) * 100}%`,
                                    minWidth: (put.open_interest || (put as any).openInterest || 0) > 0 ? "2px" : "0px"
                                  }}
                                />
                                <span className="relative z-10 text-xs whitespace-nowrap">
                                  {(put.open_interest ?? (put as any).openInterest ?? 0).toLocaleString()}
                                </span>
                              </div>
                            </div>
                          ) : "-"}
                        </TableCell>
                      </TableRow>
                    )}
                  </React.Fragment>
                )
              })}
            </TableBody>
          </Table>
        </div>
        
        {/* Greek Curve Dialog */}
        <GreekCurveDialog
          open={greekDialogOpen}
          onOpenChange={setGreekDialogOpen}
          calls={calls}
          puts={puts}
          spotPrice={spotPrice}
          greekName={selectedGreek}
          strike={selectedStrike}
        />

        {/* Add Leg Confirmation Dialog */}
        <Dialog open={confirmDialogOpen} onOpenChange={(open) => {
          if (!open) {
            handleCancelAddLeg()
          } else {
            setConfirmDialogOpen(true)
          }
        }}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Option Leg</DialogTitle>
              <DialogDescription>
                {pendingLeg && (
                  <div className="space-y-2 mt-2">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">Action:</span>
                      <Badge variant={pendingLeg.action === "buy" ? "default" : "secondary"}>
                        {pendingLeg.action.toUpperCase()}
                      </Badge>
                      <Badge variant="outline">
                        {pendingLeg.type.toUpperCase()}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">Strike:</span>
                      <span className="text-lg font-bold">${pendingLeg.strike.toFixed(2)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">Premium:</span>
                      <span className="text-lg font-bold text-primary">${(pendingLeg.premium || 0).toFixed(2)}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">Quantity:</span>
                      <span className="text-lg font-bold">{pendingLeg.quantity}</span>
                    </div>
                    <div className="pt-2 border-t text-sm text-muted-foreground">
                      Click "Confirm" to add this leg to your strategy.
                    </div>
                  </div>
                )}
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={handleCancelAddLeg}
              >
                Cancel
              </Button>
              <Button onClick={handleConfirmAddLeg}>
                Confirm Add Leg
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  )
}
