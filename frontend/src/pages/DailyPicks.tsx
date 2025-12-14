import * as React from "react"
import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { Calendar, TrendingUp, ExternalLink, AlertTriangle, Target, Clock, DollarSign, ArrowUpRight, ArrowDownRight, Minus } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { aiService, DailyPickItem } from "@/services/api/ai"
import { formatInTimeZone } from "date-fns-tz"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { toast } from "sonner"

export const DailyPicks: React.FC = () => {
  const navigate = useNavigate()
  const [selectedPick, setSelectedPick] = useState<DailyPickItem | null>(null)
  
  const { data: dailyPicks, isLoading } = useQuery({
    queryKey: ["dailyPicks"],
    queryFn: () => aiService.getDailyPicks(),
  })

  const handleOpenInStrategyLab = (pick: DailyPickItem) => {
    try {
      // Extract strategy data from pick
      const strategyData = pick.strategy || {}
      const legs = pick.legs || strategyData.legs || []
      const symbol = pick.symbol

      // Navigate to Strategy Lab with strategy data
      // We'll pass the data via URL params and localStorage
      const strategyPayload = {
        symbol,
        legs,
        strategyName: pick.headline || `${pick.symbol} ${pick.strategy_type}`,
      }
      
      // Store in sessionStorage for StrategyLab to pick up
      sessionStorage.setItem("dailyPickStrategy", JSON.stringify(strategyPayload))
      
      // Navigate to Strategy Lab
      navigate(`/strategy-lab?symbol=${symbol}`)
      toast.success(`Loading ${pick.symbol} strategy in Strategy Lab...`)
    } catch (error) {
      console.error("Error opening strategy in Strategy Lab:", error)
      toast.error("Failed to open strategy in Strategy Lab")
    }
  }

  const getOutlookIcon = (outlook: string | undefined) => {
    if (!outlook) return <Minus className="h-4 w-4 text-gray-600" />
    switch (outlook.toLowerCase()) {
      case "bullish":
        return <ArrowUpRight className="h-4 w-4 text-green-600" />
      case "bearish":
        return <ArrowDownRight className="h-4 w-4 text-red-600" />
      default:
        return <Minus className="h-4 w-4 text-gray-600" />
    }
  }

  const getRiskBadgeVariant = (risk: string | undefined): "default" | "secondary" | "destructive" => {
    if (!risk) return "secondary"
    switch (risk.toLowerCase()) {
      case "low":
        return "default"
      case "medium":
        return "secondary"
      case "high":
        return "destructive"
      default:
        return "secondary"
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Daily Picks</h1>
          <p className="text-muted-foreground">
            AI-generated strategy recommendations
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-32" />
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (!dailyPicks || dailyPicks.content_json.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Daily Picks</h1>
          <p className="text-muted-foreground">
            AI-generated strategy recommendations
          </p>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <Calendar className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              No daily picks available for today
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Format date in US/Eastern timezone
  const displayDate = dailyPicks.date
    ? formatInTimeZone(
        new Date(dailyPicks.date),
        "US/Eastern",
        "EEEE, MMMM d, yyyy"
      )
    : "Today"

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Daily Picks</h1>
        <p className="text-muted-foreground">
          AI-generated strategy recommendations for {displayDate}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {dailyPicks.content_json.map((pick, index) => {
          const legs = pick.legs || pick.strategy?.legs || []
          const outlook = pick.outlook || "Neutral"
          const riskLevel = pick.risk_level || "Medium"
          return (
            <Card key={index} className="hover:shadow-lg transition-shadow cursor-pointer" onClick={() => setSelectedPick(pick)}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <CardTitle className="text-lg">{pick.symbol || "N/A"}</CardTitle>
                      {getOutlookIcon(outlook)}
                    </div>
                    <CardDescription className="mt-1">
                      {pick.strategy_type || "Strategy"}
                    </CardDescription>
                  </div>
                  <TrendingUp className="h-5 w-5 text-primary" />
                </div>
                <div className="flex gap-2 mt-2">
                  <Badge variant={getRiskBadgeVariant(riskLevel)} className="text-xs">
                    {riskLevel} Risk
                  </Badge>
                  <Badge variant="outline" className="text-xs">
                    {outlook}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <h4 className="font-semibold text-sm mb-1">{pick.headline || "Strategy Analysis"}</h4>
                  <p className="text-sm text-muted-foreground line-clamp-3">
                    {pick.analysis || "No analysis available"}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex items-center gap-1">
                    <DollarSign className="h-3 w-3 text-green-600" />
                    <span className="text-muted-foreground">Max Profit:</span>
                    <span className="font-medium">${pick.max_profit?.toFixed(2) || "N/A"}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3 text-red-600" />
                    <span className="text-muted-foreground">Max Loss:</span>
                    <span className="font-medium">${Math.abs(pick.max_loss || 0).toFixed(2)}</span>
                  </div>
                </div>

                {legs.length > 0 && (
                  <div className="space-y-1">
                    <p className="text-xs font-medium text-muted-foreground">
                      Strategy Legs:
                    </p>
                    <div className="space-y-1">
                      {legs.slice(0, 2).map((leg: any, legIndex: number) => (
                        <div
                          key={legIndex}
                          className="text-xs bg-muted p-2 rounded flex items-center justify-between"
                        >
                          <span>
                            {leg.action === "buy" ? "Buy" : "Sell"} {leg.quantity}x{" "}
                            {leg.type === "call" ? "Call" : "Put"}
                          </span>
                          <span className="font-medium">
                            ${leg.strike?.toFixed(2) || "N/A"}
                          </span>
                        </div>
                      ))}
                      {legs.length > 2 && (
                        <p className="text-xs text-muted-foreground text-center">
                          +{legs.length - 2} more leg{legs.length - 2 > 1 ? "s" : ""}
                        </p>
                      )}
                    </div>
                  </div>
                )}

                <Button
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={(e) => {
                    e.stopPropagation()
                    handleOpenInStrategyLab(pick)
                  }}
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Open in Strategy Lab
                </Button>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Detail Modal */}
      <Dialog open={!!selectedPick} onOpenChange={(open) => !open && setSelectedPick(null)}>
        <DialogContent className="max-w-4xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {selectedPick?.symbol} - {selectedPick?.strategy_type}
              {selectedPick && getOutlookIcon(selectedPick.outlook)}
            </DialogTitle>
            <DialogDescription>
              {selectedPick?.headline}
            </DialogDescription>
          </DialogHeader>

          {selectedPick && (
            <div className="space-y-6">
              {/* Badges */}
              <div className="flex gap-2">
                <Badge variant={getRiskBadgeVariant(selectedPick.risk_level)}>
                  {selectedPick.risk_level} Risk
                </Badge>
                <Badge variant="outline">
                  {selectedPick.outlook} Outlook
                </Badge>
              </div>

              {/* Key Metrics */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card>
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-2 mb-1">
                      <DollarSign className="h-4 w-4 text-green-600" />
                      <span className="text-sm text-muted-foreground">Max Profit</span>
                    </div>
                    <p className="text-lg font-semibold text-green-600">
                      ${selectedPick.max_profit?.toFixed(2) || "N/A"}
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-2 mb-1">
                      <AlertTriangle className="h-4 w-4 text-red-600" />
                      <span className="text-sm text-muted-foreground">Max Loss</span>
                    </div>
                    <p className="text-lg font-semibold text-red-600">
                      ${Math.abs(selectedPick.max_loss || 0).toFixed(2)}
                    </p>
                  </CardContent>
                </Card>
                {selectedPick.target_price && (
                  <Card>
                    <CardContent className="pt-4">
                      <div className="flex items-center gap-2 mb-1">
                        <Target className="h-4 w-4 text-primary" />
                        <span className="text-sm text-muted-foreground">Target Price</span>
                      </div>
                      <p className="text-lg font-semibold">
                        {selectedPick.target_price}
                      </p>
                    </CardContent>
                  </Card>
                )}
                {selectedPick.timeframe && (
                  <Card>
                    <CardContent className="pt-4">
                      <div className="flex items-center gap-2 mb-1">
                        <Clock className="h-4 w-4 text-primary" />
                        <span className="text-sm text-muted-foreground">Timeframe</span>
                      </div>
                      <p className="text-lg font-semibold">
                        {selectedPick.timeframe}
                      </p>
                    </CardContent>
                  </Card>
                )}
              </div>

              {/* AI Analysis */}
              <Card>
                <CardHeader>
                  <CardTitle>AI Analysis</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="prose prose-sm max-w-none">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        p: ({ node, ...props }) => <p className="mb-3 leading-6" {...props} />,
                        ul: ({ node, ...props }) => <ul className="list-disc list-inside mb-3 space-y-1 ml-4" {...props} />,
                        ol: ({ node, ...props }) => <ol className="list-decimal list-inside mb-3 space-y-1 ml-4" {...props} />,
                        strong: ({ node, ...props }) => <strong className="font-semibold" {...props} />,
                      }}
                    >
                      {selectedPick.analysis}
                    </ReactMarkdown>
                  </div>
                </CardContent>
              </Card>

              {/* Risks */}
              {selectedPick.risks && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <AlertTriangle className="h-5 w-5 text-amber-600" />
                      Key Risks
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">{selectedPick.risks}</p>
                  </CardContent>
                </Card>
              )}

              {/* Strategy Legs */}
              {(selectedPick.legs || selectedPick.strategy?.legs) && (
                <Card>
                  <CardHeader>
                    <CardTitle>Strategy Legs</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {(selectedPick.legs || selectedPick.strategy?.legs || []).map((leg: any, legIndex: number) => (
                        <div
                          key={legIndex}
                          className="flex items-center justify-between p-3 bg-muted rounded-lg"
                        >
                          <div className="flex items-center gap-3">
                            <Badge variant={leg.action === "buy" ? "default" : "secondary"}>
                              {leg.action === "buy" ? "Buy" : "Sell"}
                            </Badge>
                            <span className="font-medium">{leg.quantity}x</span>
                            <span className="text-muted-foreground">
                              {leg.type === "call" ? "Call" : "Put"}
                            </span>
                            <span className="text-muted-foreground">@</span>
                            <span className="font-semibold">${leg.strike?.toFixed(2)}</span>
                          </div>
                          {leg.expiry && (
                            <span className="text-sm text-muted-foreground">
                              Exp: {new Date(leg.expiry).toLocaleDateString()}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Breakeven Points */}
              {selectedPick.breakeven && selectedPick.breakeven.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Breakeven Points</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex gap-2 flex-wrap">
                      {selectedPick.breakeven.map((be: number, index: number) => (
                        <Badge key={index} variant="outline" className="text-sm">
                          ${be.toFixed(2)}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setSelectedPick(null)}
            >
              Close
            </Button>
            {selectedPick && (
              <Button
                onClick={() => {
                  handleOpenInStrategyLab(selectedPick)
                  setSelectedPick(null)
                }}
              >
                <ExternalLink className="h-4 w-4 mr-2" />
                Open in Strategy Lab
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

