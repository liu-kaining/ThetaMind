import * as React from "react"
import { useState, useEffect } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Link, useNavigate } from "react-router-dom"
import { ExternalLink, Trash2, FileText, FlaskConical, AlertTriangle, RefreshCw } from "lucide-react"
import { format } from "date-fns"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/features/auth/AuthProvider"
import { strategyService, StrategyResponse } from "@/services/api/strategy"
import { aiService, AIReportResponse } from "@/services/api/ai"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"
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
  
  // Refresh user data when reports change (in case a new report was generated)
  useEffect(() => {
    if (user) {
      refreshUser()
    }
  }, [reports?.length])

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

  const hasStrategies = strategies && strategies.length > 0
  const hasReports = reports && reports.length > 0
  // Only show onboarding if data has loaded and user has no strategies/reports
  const isNewUser = !isLoadingStrategies && !isLoadingReports && !hasStrategies && !hasReports

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome back, {user?.email || "User"}!
          </p>
        </div>
      </div>

      {/* New User Onboarding - Prominent CTA */}
      {isNewUser && (
        <Card className="border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-primary/10">
          <CardHeader>
            <CardTitle className="text-2xl">🚀 Get Started with Option Strategy Analysis</CardTitle>
            <CardDescription className="text-base">
              Start analyzing option strategies with AI-powered insights. Search for a stock and build your first strategy!
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="max-w-md">
              <SymbolSearch
                onSelect={handleSymbolSelect}
                placeholder="Search symbol (e.g., AAPL, TSLA)..."
              />
            </div>
            <div className="flex gap-3">
              <Button
                size="lg"
                onClick={() => navigate("/strategy-lab")}
                className="flex items-center gap-2"
              >
                <FlaskConical className="h-5 w-5" />
                Go to Strategy Lab
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick Search for Returning Users */}
      {!isNewUser && (
        <Card>
          <CardHeader>
            <CardTitle>Quick Search</CardTitle>
            <CardDescription>Search for a stock symbol to start analyzing</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="max-w-md">
              <SymbolSearch
                onSelect={handleSymbolSelect}
                placeholder="Search symbol (e.g., AAPL, TSLA)..."
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats Cards */}
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
