import * as React from "react"
import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Link, useNavigate } from "react-router-dom"
import { ExternalLink, Trash2, FileText, FlaskConical, AlertTriangle, RefreshCw, TrendingUp, Zap, ArrowUpRight, ArrowDownRight, Minus, Sparkles, Clock } from "lucide-react"
import { format } from "date-fns"
import { formatInTimeZone } from "date-fns-tz"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useAuth } from "@/features/auth/AuthProvider"
import { strategyService, StrategyResponse } from "@/services/api/strategy"
import { aiService, AIReportResponse, DailyPickItem } from "@/services/api/ai"
import { marketService } from "@/services/api/market"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"
import { formatDistanceToNow } from "date-fns"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from "@/components/ui/dialog"
import { SymbolSearch } from "@/components/market/SymbolSearch"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { getMarketStatus } from "@/utils/marketHours"

export const DashboardPage: React.FC = () => {
  const { user, refreshUser } = useAuth()
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [selectedReport, setSelectedReport] = useState<AIReportResponse | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null)

  // Fetch strategies
  const { data: strategies, isLoading: isLoadingStrategies } = useQuery({
    queryKey: ["strategies"],
    queryFn: () => strategyService.list(100, 0),
  })

  // Fetch AI reports
  const { data: reports, isLoading: isLoadingReports } = useQuery({
    queryKey: ["aiReports"],
    queryFn: () => aiService.getReports(10, 0),
  })

  // Fetch Daily Picks (情报局核心)
  const { data: dailyPicks, isLoading: isLoadingDailyPicks } = useQuery({
    queryKey: ["dailyPicks"],
    queryFn: () => aiService.getDailyPicks(),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  })

  // Fetch Anomaly Radar (实时异动)
  const { data: anomalies, isLoading: isLoadingAnomalies } = useQuery({
    queryKey: ["anomalies"],
    queryFn: () => marketService.getAnomalies(5, 1), // Top 5, last 1 hour
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
    staleTime: 2 * 60 * 1000, // Cache for 2 minutes
  })
  
  // Refresh user data when reports count changes (in case a new report was generated)
  // Note: Only refresh when reports count actually changes, not when user object reference changes
  const previousReportsLengthRef = React.useRef<number | undefined>(undefined)
  useEffect(() => {
    const currentReportsLength = reports?.length
    if (user && currentReportsLength !== undefined && currentReportsLength !== previousReportsLengthRef.current) {
      refreshUser()
      previousReportsLengthRef.current = currentReportsLength
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reports?.length]) // Only depend on reports length, not user object

  // Delete strategy mutation
  const deleteStrategyMutation = useMutation({
    mutationFn: (strategyId: string) => strategyService.delete(strategyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["strategies"] })
      toast.success("Strategy deleted successfully")
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to delete strategy")
    },
  })

  const handleDeleteStrategy = (strategyId: string) => {
    setSelectedStrategyId(strategyId)
    setDeleteDialogOpen(true)
  }

  const handleCancelDelete = () => {
    setDeleteDialogOpen(false)
    setSelectedStrategyId(null)
  }

  const handleConfirmDelete = () => {
    if (selectedStrategyId) {
      deleteStrategyMutation.mutate(selectedStrategyId, {
        onSuccess: () => {
          setDeleteDialogOpen(false)
          setSelectedStrategyId(null)
        },
      })
    }
  }

  // Get strategy type from legs
  const getStrategyType = (strategy: StrategyResponse): string => {
    const legs = strategy.legs_json?.legs || []
    if (legs.length === 0) return "Custom"
    
    const callCount = legs.filter((l: any) => l.type === "call").length
    const putCount = legs.filter((l: any) => l.type === "put").length
    
    if (legs.length === 1) {
      return legs[0].type === "call" ? "Long Call" : "Long Put"
    }
    if (legs.length === 2) {
      if (callCount === 2) return "Call Spread"
      if (putCount === 2) return "Put Spread"
      return "Straddle"
    }
    if (legs.length === 4) {
      return "Iron Condor"
    }
    return "Multi-Leg"
  }

  const handleSymbolSelect = (symbol: string) => {
    // Navigate to Strategy Lab with the selected symbol
    navigate(`/strategy-lab?symbol=${symbol}`)
  }

  // Handle Daily Pick click
  const handleDailyPickClick = (pick: DailyPickItem) => {
    try {
      const legs = pick.legs || pick.strategy?.legs || []
      const strategyPayload = {
        symbol: pick.symbol,
        legs,
        strategyName: pick.headline || `${pick.symbol} ${pick.strategy_type}`,
      }
      sessionStorage.setItem("dailyPickStrategy", JSON.stringify(strategyPayload))
      navigate(`/strategy-lab?symbol=${pick.symbol}`)
      toast.success(`Loading ${pick.symbol} strategy in Strategy Lab...`)
    } catch (error) {
      console.error("Error opening daily pick:", error)
      toast.error("Failed to open strategy")
    }
  }

  // Handle Anomaly click
  const handleAnomalyClick = (anomaly: any) => {
    navigate(`/strategy-lab?symbol=${anomaly.symbol}`)
    toast.info(`Opening ${anomaly.symbol} in Strategy Lab...`)
  }

  // Helper functions for Daily Picks
  const getOutlookIcon = (outlook: string | undefined) => {
    if (!outlook) return <Minus className="h-4 w-4 text-muted-foreground" />
    switch (outlook.toLowerCase()) {
      case "bullish":
        return <ArrowUpRight className="h-4 w-4 text-emerald-500" />
      case "bearish":
        return <ArrowDownRight className="h-4 w-4 text-rose-500" />
      default:
        return <Minus className="h-4 w-4 text-muted-foreground" />
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

  // Helper functions for Anomalies
  const getAnomalyIcon = (type: string) => {
    switch (type) {
      case "volume_surge":
        return <TrendingUp className="h-4 w-4" />
      case "iv_spike":
        return <Zap className="h-4 w-4" />
      default:
        return <AlertTriangle className="h-4 w-4" />
    }
  }

  const getAnomalyColor = (score: number): "destructive" | "default" | "secondary" => {
    if (score > 50) return "destructive"
    if (score > 20) return "default"
    return "secondary"
  }

  const getAnomalyLabel = (type: string): string => {
    switch (type) {
      case "volume_surge":
        return "Volume Surge"
      case "iv_spike":
        return "IV Spike"
      case "unusual_activity":
        return "Unusual Activity"
      default:
        return type
    }
  }

  // Removed unused variables

  // Format date for Daily Picks
  const displayDate = dailyPicks?.date
    ? formatInTimeZone(
        new Date(dailyPicks.date),
        "US/Eastern",
        "EEEE, MMMM d, yyyy"
      )
    : "Today"

  // US market status for empty-state messaging (休市时明确显示「不开盘」而非空白)
  const marketStatus = React.useMemo(() => getMarketStatus(), [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome back, {user?.email || "User"}! Here's what's happening today.
          </p>
          {!marketStatus.isOpen && (
            <p className="text-sm text-amber-600 dark:text-amber-500 mt-1 font-medium">
              US market is closed. Regular session: Mon–Fri 9:30 AM–4:00 PM ET. Next open: {marketStatus.nextOpenET}.
            </p>
          )}
        </div>
      </div>

      {/* 🔥 今日 AI 首选 (Daily Picks) - 情报局核心 */}
      <Card className="border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-primary/10">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-2xl flex items-center gap-2">
                <Sparkles className="h-6 w-6 text-primary" />
                🔥 Today's AI Recommendations
              </CardTitle>
              <CardDescription className="text-base mt-1">
                AI-generated strategy picks for {displayDate}
              </CardDescription>
            </div>
            <Button variant="outline" size="sm" asChild>
              <Link to="/daily-picks">
                View All
                <ExternalLink className="h-4 w-4 ml-2" />
              </Link>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoadingDailyPicks ? (
            <div className="grid gap-4 md:grid-cols-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-48 w-full" />
              ))}
            </div>
          ) : dailyPicks && dailyPicks.content_json.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-3">
              {dailyPicks.content_json.slice(0, 3).map((pick, index) => {
                const outlook = pick.outlook || "Neutral"
                const riskLevel = pick.risk_level || "Medium"
                // Calculate confidence score from max_profit/max_loss ratio or default to 8.0
                const maxProfit = pick.max_profit || 0
                const maxLoss = Math.abs(pick.max_loss || 0)
                const confidenceScore = maxLoss > 0 
                  ? Math.min(10, Math.max(5, (maxProfit / maxLoss) * 5 + 5))
                  : 8.0
                
                return (
                  <Card
                    key={index}
                    className="hover:shadow-lg transition-all cursor-pointer border-2 hover:border-primary/50 bg-card"
                    onClick={() => handleDailyPickClick(pick)}
                  >
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <CardTitle className="text-xl font-bold">{pick.symbol || "N/A"}</CardTitle>
                          {getOutlookIcon(outlook)}
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-bold text-primary">
                            {confidenceScore.toFixed(1)}
                          </div>
                          <div className="text-xs text-muted-foreground">AI Score</div>
                        </div>
                      </div>
                      <CardDescription className="text-base font-semibold">
                        {pick.strategy_type || "Strategy"}
                      </CardDescription>
                      <div className="flex gap-2 mt-2">
                        <Badge variant={getRiskBadgeVariant(riskLevel)} className="text-xs">
                          {riskLevel} Risk
                        </Badge>
                        <Badge variant="outline" className="text-xs">
                          {outlook}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div>
                        <h4 className="font-semibold text-sm mb-1 line-clamp-2">
                          {pick.headline || "Strategy Analysis"}
                        </h4>
                        <p className="text-xs text-muted-foreground line-clamp-2">
                          {pick.analysis || "No analysis available"}
                        </p>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t">
                        <div>
                          <div className="text-muted-foreground">Max Profit</div>
                          <div className="font-semibold text-emerald-500">
                            ${pick.max_profit?.toFixed(2) || "N/A"}
                          </div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">Max Loss</div>
                          <div className="font-semibold text-rose-500">
                            ${Math.abs(pick.max_loss || 0).toFixed(2)}
                          </div>
                        </div>
                      </div>
                      <Button
                        variant="default"
                        size="sm"
                        className="w-full mt-2"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDailyPickClick(pick)
                        }}
                      >
                        <FlaskConical className="h-4 w-4 mr-2" />
                        Analyze in Lab
                      </Button>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          ) : (
            <div className="text-center py-8">
              <Sparkles className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              {!marketStatus.isOpen ? (
                <>
                  <p className="font-medium text-foreground mb-1">Market is closed</p>
                  <p className="text-muted-foreground text-sm mb-4">
                    Daily picks update after the market opens (9:30 AM ET). Next open: {marketStatus.nextOpenET}.
                  </p>
                </>
              ) : (
                <p className="text-muted-foreground mb-4">
                  No daily picks available for today
                </p>
              )}
              <Button variant="outline" asChild>
                <Link to="/daily-picks">Check Daily Picks</Link>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 🔴 正在发生的异动 (Anomaly Radar) - 实时情报 */}
      <Card className="border-2 border-rose-500/20 bg-gradient-to-br from-rose-500/5 to-rose-500/10">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-2xl flex items-center gap-2">
                <AlertTriangle className="h-6 w-6 text-rose-500" />
                🔴 Live Anomaly Radar
              </CardTitle>
              <CardDescription className="text-base mt-1">
                Real-time option activity alerts (Last 1 Hour)
                {!marketStatus.isOpen && (
                  <span className="block text-amber-600 dark:text-amber-500 font-medium mt-1">
                    Market closed — no new alerts until next session.
                  </span>
                )}
              </CardDescription>
            </div>
            {marketStatus.isOpen ? (
              <Badge variant="destructive" className="animate-pulse">
                LIVE
              </Badge>
            ) : (
              <Badge variant="secondary">Closed</Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {isLoadingAnomalies ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-20 w-full" />
              ))}
            </div>
          ) : anomalies && anomalies.length > 0 ? (
            <div className="space-y-3 max-h-[400px] overflow-y-auto">
              {anomalies.map((anomaly: any) => (
                <div
                  key={anomaly.id}
                  className="p-4 rounded-lg border border-border hover:bg-accent transition-all cursor-pointer bg-card/50 backdrop-blur-sm"
                  onClick={() => handleAnomalyClick(anomaly)}
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex items-center gap-2 flex-1">
                      {getAnomalyIcon(anomaly.anomaly_type)}
                      <span className="font-bold text-lg">{anomaly.symbol}</span>
                      <Badge
                        variant={getAnomalyColor(anomaly.score)}
                        className="text-xs"
                      >
                        {getAnomalyLabel(anomaly.anomaly_type)}
                      </Badge>
                      <Badge variant="outline" className="text-xs">
                        Score: {anomaly.score}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      <span>
                        {formatDistanceToNow(new Date(anomaly.detected_at), {
                          addSuffix: true,
                        })}
                      </span>
                    </div>
                  </div>

                  {anomaly.details && (
                    <div className="text-xs text-muted-foreground space-y-1 mb-2">
                      {typeof anomaly.details.vol_oi_ratio === "number" && (
                        <div>
                          <span className="font-medium">Vol/OI:</span> {anomaly.details.vol_oi_ratio.toFixed(2)}
                        </div>
                      )}
                      {typeof anomaly.details.volume === "number" && (
                        <div>
                          <span className="font-medium">Volume:</span> {anomaly.details.volume.toLocaleString()}
                        </div>
                      )}
                      {typeof anomaly.details.iv === "number" && (
                        <div>
                          <span className="font-medium">IV:</span> {(anomaly.details.iv * 100).toFixed(1)}%
                        </div>
                      )}
                    </div>
                  )}

                  {anomaly.ai_insight && (
                    <div className="text-sm bg-cyan-500/10 border border-cyan-500/20 p-3 rounded mt-2">
                      <div className="flex items-start gap-2">
                        <Sparkles className="h-4 w-4 text-cyan-400 mt-0.5 shrink-0" />
                        <div>
                          <span className="font-semibold text-cyan-400">AI Insight: </span>
                          <span className="text-foreground">{anomaly.ai_insight}</span>
                        </div>
                      </div>
                    </div>
                  )}

                  <Button
                    variant="ghost"
                    size="sm"
                    className="w-full mt-2 text-xs"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleAnomalyClick(anomaly)
                    }}
                  >
                    <ExternalLink className="h-3 w-3 mr-1" />
                    Analyze {anomaly.symbol} in Strategy Lab
                  </Button>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <AlertTriangle className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              {!marketStatus.isOpen ? (
                <>
                  <p className="font-medium text-foreground mb-1">Market is closed</p>
                  <p className="text-muted-foreground text-sm">
                    Real-time anomalies are only detected during regular trading hours (9:30 AM–4:00 PM ET, Mon–Fri).
                  </p>
                </>
              ) : (
                <p className="text-muted-foreground">
                  No anomalies detected in the last hour
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions - 次要位置 */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Quick Search</CardTitle>
            <CardDescription className="text-sm">Search for a stock symbol</CardDescription>
          </CardHeader>
          <CardContent>
            <SymbolSearch
              onSelect={handleSymbolSelect}
              placeholder="Search symbol..."
            />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">My Strategies</CardTitle>
            <CardDescription className="text-sm">
              {strategies?.length || 0} saved strategies
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" className="w-full" asChild>
              <Link to="/strategy-lab">
                <FlaskConical className="h-4 w-4 mr-2" />
                Open Strategy Lab
              </Link>
            </Button>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-base">AI Reports</CardTitle>
            <CardDescription className="text-sm">
              {reports?.length || 0} reports generated
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" className="w-full" asChild>
              <Link to="/reports">
                <FileText className="h-4 w-4 mr-2" />
                View Reports
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Stats Cards - 次要位置 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Strategies</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {strategies?.length || 0}
            </div>
            <p className="text-xs text-muted-foreground">Total strategies created</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">AI Reports</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{reports?.length || 0}</div>
            <p className="text-xs text-muted-foreground">Reports generated</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Daily Usage</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {user?.daily_ai_usage ?? 0} / {user?.daily_ai_quota ?? (user?.is_pro ? (user?.subscription_type === "yearly" ? 30 : 20) : 1)}
            </div>
            <p className="text-xs text-muted-foreground">AI reports today</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Plan</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{user?.is_pro ? "Pro" : "Free"}</div>
            <p className="text-xs text-muted-foreground">Current subscription</p>
          </CardContent>
        </Card>
      </div>

      {/* My Strategies & Reports - 底部次要位置 */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* My Strategies Section */}
        <Card>
          <CardHeader>
            <CardTitle>My Strategies</CardTitle>
            <CardDescription>Your saved option strategies</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoadingStrategies ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : strategies && strategies.length > 0 ? (
              <div className="space-y-2">
                {strategies.map((strategy) => (
                  <div
                    key={strategy.id}
                    className="flex items-center justify-between border-b border-border pb-3 last:border-0"
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <FlaskConical className="h-4 w-4 text-muted-foreground" />
                        <p className="font-medium">{strategy.name}</p>
                      </div>
                      <div className="mt-1 flex items-center gap-4 text-sm text-muted-foreground">
                        <span>
                          {format(new Date(strategy.created_at), "MMM d, yyyy")}
                        </span>
                        <span>{strategy.legs_json?.symbol || "N/A"}</span>
                        <span>{getStrategyType(strategy)}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        asChild
                      >
                        <Link to={`/strategy-lab?strategy=${strategy.id}`}>
                          <ExternalLink className="h-4 w-4 mr-1" />
                          Open
                        </Link>
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteStrategy(strategy.id)}
                        disabled={deleteStrategyMutation.isPending}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <FlaskConical className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground mb-4">
                  No strategies found. Create one now!
                </p>
                <Button asChild>
                  <Link to="/strategy-lab">Go to Strategy Lab</Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent AI Reports Section */}
        <Card>
          <CardHeader>
            <CardTitle>Recent AI Reports</CardTitle>
            <CardDescription>Your latest AI-generated analyses</CardDescription>
          </CardHeader>
          <CardContent>
            {isLoadingReports ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-16 w-full" />
                ))}
              </div>
            ) : reports && reports.length > 0 ? (
              <div className="space-y-2">
                {reports.map((report: AIReportResponse) => {
                  // Extract symbol from report if available
                  const symbol = "N/A" // Could be extracted from report content if needed
                  return (
                    <div
                      key={report.id}
                      className="flex items-center justify-between border-b border-border pb-3 last:border-0 cursor-pointer hover:bg-accent/50 rounded p-2 -m-2 transition-colors"
                      onClick={() => setSelectedReport(report)}
                    >
                      <div className="flex items-center gap-3 flex-1">
                        <FileText className="h-4 w-4 text-muted-foreground" />
                        <div>
                          <p className="text-sm font-medium">
                            {format(new Date(report.created_at), "MMM d, yyyy HH:mm")}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {symbol} • {report.model_used}
                          </p>
                        </div>
                      </div>
                      <Button variant="ghost" size="sm">
                        View
                      </Button>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="text-center py-8">
                <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground mb-4">
                  No AI reports yet. Analyze a strategy to get started!
                </p>
                <Button asChild>
                  <Link to="/strategy-lab">Go to Strategy Lab</Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* AI Report Modal */}
      <Dialog
        open={!!selectedReport}
        onOpenChange={(open: boolean) => !open && setSelectedReport(null)}
      >
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogClose onClose={() => setSelectedReport(null)} />
          <DialogHeader>
            <DialogTitle>AI Analysis Report</DialogTitle>
            <DialogDescription>
              {selectedReport &&
                `Generated on ${format(
                  new Date(selectedReport.created_at),
                  "MMMM d, yyyy 'at' HH:mm"
                )} using ${selectedReport.model_used}`}
            </DialogDescription>
          </DialogHeader>
          <div className="markdown-content mt-4">
            {selectedReport && (
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  h1: ({ node, ...props }) => <h1 className="text-3xl font-bold mt-6 mb-4 pb-2 border-b border-border" {...props} />,
                  h2: ({ node, ...props }) => <h2 className="text-2xl font-semibold mt-5 mb-3" {...props} />,
                  h3: ({ node, ...props }) => <h3 className="text-xl font-semibold mt-4 mb-2" {...props} />,
                  h4: ({ node, ...props }) => <h4 className="text-lg font-semibold mt-3 mb-2" {...props} />,
                  p: ({ node, ...props }) => <p className="mb-4 leading-7" {...props} />,
                  ul: ({ node, ...props }) => <ul className="list-disc list-inside mb-4 space-y-2 ml-4" {...props} />,
                  ol: ({ node, ...props }) => <ol className="list-decimal list-inside mb-4 space-y-2 ml-4" {...props} />,
                  li: ({ node, ...props }) => <li className="leading-7" {...props} />,
                  blockquote: ({ node, ...props }) => (
                    <blockquote className="border-l-4 border-primary pl-4 italic my-4 text-muted-foreground" {...props} />
                  ),
                  code: ({ node, inline, ...props }: any) =>
                    inline ? (
                      <code className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono" {...props} />
                    ) : (
                      <code className="block bg-muted p-4 rounded-lg my-4 overflow-x-auto text-sm font-mono" {...props} />
                    ),
                  pre: ({ node, ...props }) => <pre className="bg-muted p-4 rounded-lg my-4 overflow-x-auto" {...props} />,
                  strong: ({ node, ...props }) => <strong className="font-semibold" {...props} />,
                  em: ({ node, ...props }) => <em className="italic" {...props} />,
                  a: ({ node, ...props }) => (
                    <a className="text-primary hover:underline" target="_blank" rel="noopener noreferrer" {...props} />
                  ),
                  table: ({ node, ...props }) => (
                    <div className="overflow-x-auto my-4 rounded-lg border border-border">
                      <table className="min-w-full border-collapse" {...props} />
                    </div>
                  ),
                  thead: ({ node, ...props }) => <thead className="bg-muted/50" {...props} />,
                  tbody: ({ node, ...props }) => <tbody {...props} />,
                  tr: ({ node, ...props }) => <tr className="border-b border-border hover:bg-muted/30 transition-colors" {...props} />,
                  th: ({ node, ...props }) => (
                    <th className="border-r border-border px-4 py-3 text-left font-semibold text-sm last:border-r-0" {...props} />
                  ),
                  td: ({ node, ...props }) => (
                    <td className="border-r border-border px-4 py-3 text-sm last:border-r-0" {...props} />
                  ),
                  hr: ({ node, ...props }) => <hr className="my-6 border-border" {...props} />,
                }}
              >
                {selectedReport.report_content}
              </ReactMarkdown>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogClose onClose={handleCancelDelete} />
          <DialogHeader>
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-red-100 dark:bg-red-900/20">
                <AlertTriangle className="h-6 w-6 text-red-600 dark:text-red-400" />
              </div>
              <div className="flex-1 pt-0.5">
                <DialogTitle className="text-lg font-semibold">Delete Strategy</DialogTitle>
                <DialogDescription className="mt-2 text-sm">
                  Are you sure you want to delete this strategy? This action cannot be undone and the strategy will be permanently removed.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>
          <div className="flex justify-end gap-3 mt-6 pt-4 border-t">
            <Button 
              variant="outline" 
              onClick={handleCancelDelete}
              disabled={deleteStrategyMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleConfirmDelete}
              disabled={deleteStrategyMutation.isPending}
            >
              {deleteStrategyMutation.isPending ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete Strategy
                </>
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
