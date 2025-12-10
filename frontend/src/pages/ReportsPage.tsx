import * as React from "react"
import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { format } from "date-fns"
import { Search, Trash2, Eye, FileText } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogClose,
} from "@/components/ui/dialog"
import { Skeleton } from "@/components/ui/skeleton"
import { aiService, AIReportResponse } from "@/services/api/ai"
import { toast } from "sonner"
import ReactMarkdown from "react-markdown"

export const ReportsPage: React.FC = () => {
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedReport, setSelectedReport] = useState<AIReportResponse | null>(null)
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null)

  // Fetch all reports (with high limit to get all)
  const { data: reports, isLoading } = useQuery({
    queryKey: ["aiReports", "all"],
    queryFn: () => aiService.getReports(100, 0),
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (reportId: string) => aiService.deleteReport(reportId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["aiReports"] })
      toast.success("Report deleted successfully")
      setDeleteConfirmId(null)
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to delete report")
    },
  })

  // Filter reports by search query
  const filteredReports = React.useMemo(() => {
    if (!reports) return []
    if (!searchQuery.trim()) return reports

    const query = searchQuery.toLowerCase()
    return reports.filter((report) => {
      // Search in report content for symbol mentions
      const content = report.report_content.toLowerCase()
      return content.includes(query)
    })
  }, [reports, searchQuery])

  // Extract symbol from report content (look for common patterns)
  const extractSymbol = (content: string): string => {
    // Try to find symbol patterns like "AAPL", "TSLA", etc.
    const symbolMatch = content.match(/\b([A-Z]{1,5})\b/g)
    if (symbolMatch) {
      // Filter out common words and return first valid-looking symbol
      const commonWords = ["THE", "AND", "FOR", "ARE", "BUT", "NOT", "YOU", "ALL", "CAN", "HER", "WAS", "ONE", "OUR", "OUT", "DAY", "GET", "HAS", "HIM", "HIS", "HOW", "ITS", "MAY", "NEW", "NOW", "OLD", "SEE", "TWO", "WHO", "BOY", "DID", "ITS", "LET", "PUT", "SAY", "SHE", "TOO", "USE"]
      const symbols = symbolMatch.filter(s => s.length >= 2 && s.length <= 5 && !commonWords.includes(s))
      if (symbols.length > 0) {
        return symbols[0]
      }
    }
    return "N/A"
  }

  // Extract AI verdict (Bullish/Bearish) from report content
  const extractVerdict = (content: string): "Bullish" | "Bearish" | "Neutral" => {
    const lowerContent = content.toLowerCase()
    if (lowerContent.includes("bullish") || lowerContent.includes("buy") || lowerContent.includes("positive")) {
      return "Bullish"
    }
    if (lowerContent.includes("bearish") || lowerContent.includes("sell") || lowerContent.includes("negative")) {
      return "Bearish"
    }
    return "Neutral"
  }

  const handleDelete = (reportId: string) => {
    if (window.confirm("Are you sure you want to delete this report?")) {
      deleteMutation.mutate(reportId)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">AI Reports</h1>
        <p className="text-muted-foreground">
          View and manage your AI-generated strategy analysis reports
        </p>
      </div>

      {/* Search */}
      <Card>
        <CardHeader>
          <CardTitle>Search Reports</CardTitle>
          <CardDescription>Filter reports by symbol or content</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by symbol (e.g., AAPL, TSLA)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </CardContent>
      </Card>

      {/* Reports Table */}
      <Card>
        <CardHeader>
          <CardTitle>All Reports</CardTitle>
          <CardDescription>
            {filteredReports.length} report{filteredReports.length !== 1 ? "s" : ""} found
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : filteredReports.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <FileText className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground mb-4">
                {searchQuery ? "No reports match your search." : "No AI reports yet. Analyze a strategy to get started!"}
              </p>
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Symbol</TableHead>
                    <TableHead>Model</TableHead>
                    <TableHead>Verdict</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredReports.map((report) => {
                    const symbol = extractSymbol(report.report_content)
                    const verdict = extractVerdict(report.report_content)
                    return (
                      <TableRow key={report.id}>
                        <TableCell className="font-medium">
                          {format(new Date(report.created_at), "MMM d, yyyy HH:mm")}
                        </TableCell>
                        <TableCell>{symbol}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{report.model_used}</Badge>
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={
                              verdict === "Bullish"
                                ? "default"
                                : verdict === "Bearish"
                                ? "destructive"
                                : "secondary"
                            }
                          >
                            {verdict}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setSelectedReport(report)}
                            >
                              <Eye className="h-4 w-4 mr-1" />
                              View
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleDelete(report.id)}
                              disabled={deleteMutation.isPending}
                            >
                              <Trash2 className="h-4 w-4 mr-1" />
                              Delete
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Report Detail Modal */}
      <Dialog
        open={!!selectedReport}
        onOpenChange={(open: boolean) => !open && setSelectedReport(null)}
      >
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>AI Analysis Report</DialogTitle>
            <DialogDescription>
              {selectedReport && (
                <>
                  Generated on {format(new Date(selectedReport.created_at), "PPpp")} using {selectedReport.model_used}
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          {selectedReport && (
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown>{selectedReport.report_content}</ReactMarkdown>
            </div>
          )}
          <DialogClose asChild>
            <Button variant="outline" className="mt-4">
              Close
            </Button>
          </DialogClose>
        </DialogContent>
      </Dialog>
    </div>
  )
}

