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
}

export const OptionChainTable: React.FC<OptionChainTableProps> = ({
  calls,
  puts,
  spotPrice,
  onSelectOption,
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

  const isATM = (strike: number): boolean => {
    return Math.abs(strike - spotPrice) / spotPrice < 0.02 // Within 2%
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Option Chain Table</CardTitle>
        <CardDescription>
          Greeks: Δ (Delta), Γ (Gamma), Θ (Theta), ν (Vega), ρ (Rho), IV (Implied Volatility)
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
              {strikes.map((strike) => {
                const call = getOptionByStrike(strike, calls)
                const put = getOptionByStrike(strike, puts)
                const atm = isATM(strike)

                return (
                  <TableRow
                    key={strike}
                    className={atm ? "bg-muted/50 font-medium" : ""}
                    onClick={() => {
                      if (call && onSelectOption) onSelectOption(call, "call")
                      if (put && onSelectOption) onSelectOption(put, "put")
                    }}
                    style={{ cursor: onSelectOption ? "pointer" : "default" }}
                  >
                    <TableCell className="sticky left-0 bg-background z-10 font-medium">
                      {atm && <Badge variant="outline" className="mr-1">ATM</Badge>}
                      ${strike.toFixed(2)}
                    </TableCell>
                    {/* Call columns */}
                    <TableCell className="text-right">
                      {call ? `$${((call.bid ?? (call as any).bid_price ?? 0)).toFixed(2)}` : "-"}
                    </TableCell>
                    <TableCell className="text-right">
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
                    <TableCell className="text-right text-muted-foreground">
                      {call ? (call.volume ?? 0).toLocaleString() : "-"}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {call ? (call.open_interest ?? (call as any).openInterest ?? 0).toLocaleString() : "-"}
                    </TableCell>
                    {/* Put columns */}
                    <TableCell className="text-right">
                      {put ? `$${((put.bid ?? (put as any).bid_price ?? 0)).toFixed(2)}` : "-"}
                    </TableCell>
                    <TableCell className="text-right">
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
                    <TableCell className="text-right text-muted-foreground">
                      {put ? (put.volume ?? 0).toLocaleString() : "-"}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {put ? (put.open_interest ?? (put as any).openInterest ?? 0).toLocaleString() : "-"}
                    </TableCell>
                  </TableRow>
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

