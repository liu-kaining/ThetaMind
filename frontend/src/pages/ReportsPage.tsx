import * as React from "react"
import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { format } from "date-fns"
import { Search, Trash2, Eye, FileText, AlertTriangle, RefreshCw, Download } from "lucide-react"
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
import { taskService } from "@/services/api/task"
import { toast } from "sonner"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { jsPDF } from "jspdf"
import html2canvas from "html2canvas"
import { marked } from "marked"
import { StrategyLeg } from "@/services/api/strategy"

export const ReportsPage: React.FC = () => {
  const queryClient = useQueryClient()
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedReport, setSelectedReport] = useState<AIReportResponse | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [reportToDelete, setReportToDelete] = useState<string | null>(null)

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
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to delete report")
    },
  })

  // Extract symbol from report content (look for common patterns)
  // Define BEFORE filteredReports to avoid "Cannot access before initialization" error
  const extractSymbol = React.useCallback((content: string): string => {
    try {
      if (!content || typeof content !== 'string') {
        return "N/A"
      }
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
    } catch (error) {
      console.error("Error extracting symbol:", error)
      return "N/A"
    }
  }, [])

  // Filter reports by search query
  const filteredReports = React.useMemo(() => {
    if (!reports || !Array.isArray(reports)) return []
    if (!searchQuery.trim()) return reports

    try {
      const query = searchQuery.toLowerCase().trim()
      return reports.filter((report) => {
        try {
          if (!report) return false
          
          // Search in report content
          const content = (report.report_content || "").toLowerCase()
          
          // Also search in extracted symbol
          const extractedSymbol = extractSymbol(report.report_content || "")
          const symbol = extractedSymbol === "N/A" ? "" : extractedSymbol.toLowerCase()
          
          // Search in model name as well
          const model = (report.model_used || "").toLowerCase()
          
          // Match if query appears in any of these fields
          return content.includes(query) || 
                 symbol.includes(query) || 
                 model.includes(query)
        } catch (error) {
          console.error("Error filtering report:", error)
          // If error occurs, include the report to avoid losing data
          return true
        }
      })
    } catch (error) {
      console.error("Error in filteredReports:", error)
      // Return all reports if search fails
      return reports || []
    }
  }, [reports, searchQuery, extractSymbol])

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
    setReportToDelete(reportId)
    setDeleteDialogOpen(true)
  }

  const handleConfirmDelete = () => {
    if (reportToDelete) {
      deleteMutation.mutate(reportToDelete)
      setDeleteDialogOpen(false)
      setReportToDelete(null)
    }
  }

  const handleCancelDelete = () => {
    setDeleteDialogOpen(false)
    setReportToDelete(null)
  }

  // Helper function to calculate payoff data from strategy
  const calculatePayoffData = (
    legs: StrategyLeg[],
    spotPrice: number,
    optionChain?: any
  ): Array<{ price: number; profit: number }> => {
    if (!legs || legs.length === 0 || !spotPrice) return []

    const minPrice = spotPrice * 0.7
    const maxPrice = spotPrice * 1.3
    const step = (maxPrice - minPrice) / 200

    const data: Array<{ price: number; profit: number }> = []

    for (let price = minPrice; price <= maxPrice; price += step) {
      let totalProfit = 0

      legs.forEach((leg) => {
        if (!leg || !leg.strike) return

        const options = leg.type === "call" ? optionChain?.calls : optionChain?.puts
        const option = options?.find((o: any) => {
          const optionStrike = o.strike ?? o.strike_price
          return optionStrike !== undefined && Math.abs(optionStrike - leg.strike) < 0.01
        })

        let premium = leg.premium || 0
        if (option) {
          const bid = Number(option.bid ?? option.bid_price ?? 0)
          const ask = Number(option.ask ?? option.ask_price ?? 0)
          if (bid > 0 && ask > 0) {
            premium = (bid + ask) / 2
          }
        }

        const isInTheMoney = leg.type === "call" ? price > leg.strike : price < leg.strike
        const intrinsicValue = isInTheMoney
          ? leg.type === "call"
            ? price - leg.strike
            : leg.strike - price
          : 0

        const profit = leg.action === "buy"
          ? intrinsicValue - premium
          : premium - intrinsicValue

        totalProfit += profit * (leg.quantity || 1)
      })

      data.push({ price, profit: totalProfit })
    }

    return data
  }


  const handleDownloadPDF = async () => {
    if (!selectedReport) return

    try {
      toast.info("Generating comprehensive PDF report...")
      
      // Try to find the corresponding task to get strategy data
      let strategyData: any = null
      let optionChain: any = null
      let payoffData: Array<{ price: number; profit: number }> = []

      try {
        const tasks = await taskService.getTasks({ limit: 100, skip: 0 })
        // Find task that matches this report (by result_ref or timestamp)
        const matchingTask = tasks.find(
          (task) =>
            task.task_type === "ai_report" &&
            task.status === "SUCCESS" &&
            (task.result_ref === selectedReport.id ||
              Math.abs(
                new Date(task.completed_at || task.created_at).getTime() -
                new Date(selectedReport.created_at).getTime()
              ) < 60000) // Within 1 minute
        )

        if (matchingTask?.metadata) {
          strategyData = matchingTask.metadata.strategy_data
          optionChain = matchingTask.metadata.option_chain

          if (strategyData && optionChain) {
            const spotPrice = optionChain.spot_price || optionChain.underlying_price || 0
            payoffData = calculatePayoffData(strategyData.legs || [], spotPrice, optionChain)
          }
        }
      } catch (error) {
        console.warn("Could not fetch task data:", error)
      }

      // Use the same comprehensive PDF generation logic as StrategyLab
      const pdf = new jsPDF({
        orientation: "portrait",
        unit: "mm",
        format: "a4",
      })

      const pageWidth = pdf.internal.pageSize.getWidth()
      const pageHeight = pdf.internal.pageSize.getHeight()
      const margin = 15
      let yPosition = margin

      // Helper function to add new page if needed
      const checkNewPage = (requiredHeight: number) => {
        if (yPosition + requiredHeight > pageHeight - margin) {
          pdf.addPage()
          yPosition = margin
          addWatermark()
          return true
        }
        return false
      }

      // Helper function to add watermark
      const addWatermark = () => {
        pdf.setGState(pdf.GState({ opacity: 0.1 }))
        pdf.setFontSize(60)
        pdf.setTextColor(200, 200, 200)
        pdf.text("ThetaMind", pageWidth / 2, pageHeight / 2, {
          align: "center",
          angle: 45,
        })
        pdf.setGState(pdf.GState({ opacity: 1 }))
        pdf.setTextColor(0, 0, 0)
      }

      // Add watermark to first page
      addWatermark()

      // Cover Page - Title
      pdf.setFontSize(24)
      pdf.setFont("helvetica", "bold")
      pdf.text("Strategy Analysis Report", pageWidth / 2, yPosition, { align: "center" })
      yPosition += 15

      // Strategy Info Section
      if (strategyData) {
        pdf.setFontSize(14)
        pdf.setFont("helvetica", "bold")
        pdf.text("Strategy Overview", margin, yPosition)
        yPosition += 10

        pdf.setFontSize(12)
        pdf.setFont("helvetica", "normal")
        const symbol = strategyData.symbol || "N/A"
        const spotPrice = optionChain?.spot_price || optionChain?.underlying_price || 0
        const legs = strategyData.legs || []
        const expirationDate = strategyData.expiration_date || legs[0]?.expiry || "N/A"
        const strategyName = strategyData.strategy_name || "Custom Strategy"
        
        pdf.text(`Symbol: ${symbol}`, margin, yPosition)
        yPosition += 6
        pdf.text(`Strategy: ${strategyName}`, margin, yPosition)
        yPosition += 6
        pdf.text(`Expiration: ${expirationDate}`, margin, yPosition)
        yPosition += 6
        if (spotPrice > 0) {
          pdf.text(`Current Price: $${spotPrice.toFixed(2)}`, margin, yPosition)
          yPosition += 6
        }
        pdf.text(`Number of Legs: ${legs.length}`, margin, yPosition)
        yPosition += 6
        pdf.text(`Generated: ${new Date(selectedReport.created_at).toLocaleString()}`, margin, yPosition)
        yPosition += 6
        pdf.text(`Model: ${selectedReport.model_used}`, margin, yPosition)
        yPosition += 10

        // Strategy Legs Table
        if (legs.length > 0) {
          pdf.setFontSize(10)
          pdf.setFont("helvetica", "bold")
          const colWidths = [15, 25, 20, 25, 30, 20]
          const headers = ["Leg", "Action", "Type", "Strike", "Expiry", "Quantity"]
          let xPos = margin
          
          // Headers
          headers.forEach((header, i) => {
            pdf.text(header, xPos, yPosition)
            xPos += colWidths[i]
          })
          yPosition += 6
          
          // Draw line under headers
          pdf.line(margin, yPosition - 2, pageWidth - margin, yPosition - 2)
          yPosition += 2
          
          // Rows
          pdf.setFont("helvetica", "normal")
          legs.forEach((leg: StrategyLeg, idx: number) => {
            xPos = margin
            const row = [
              `${idx + 1}`,
              leg.action.toUpperCase(),
              leg.type.toUpperCase(),
              `$${leg.strike?.toFixed(2) || "N/A"}`,
              leg.expiry || expirationDate,
              `${leg.quantity || 1}x`
            ]
            row.forEach((cell, i) => {
              pdf.text(cell, xPos, yPosition)
              xPos += colWidths[i]
            })
            yPosition += 6
          })
          yPosition += 5
        }

        // Trade Execution Section (from data)
        if (legs.length > 0) {
          checkNewPage(80)
          pdf.setFontSize(16)
          pdf.setFont("helvetica", "bold")
          pdf.text("1. Trade Execution", margin, yPosition)
          yPosition += 8

          pdf.setFontSize(10)
          pdf.setFont("helvetica", "normal")
          legs.forEach((leg: StrategyLeg) => {
            checkNewPage(10)
            const options = leg.type === "call" ? optionChain?.calls : optionChain?.puts
            const option = options?.find((o: any) => {
              const optionStrike = o.strike ?? o.strike_price
              return optionStrike !== undefined && Math.abs(optionStrike - leg.strike!) < 0.01
            })
            
            let midPrice = leg.premium || 0
            if (option) {
              const bid = Number(option.bid ?? option.bid_price ?? 0)
              const ask = Number(option.ask ?? option.ask_price ?? 0)
              if (bid > 0 && ask > 0) {
                midPrice = (bid + ask) / 2
              }
            }

            pdf.text(
              `${leg.action.toUpperCase()} ${leg.quantity}x ${leg.type.toUpperCase()} $${leg.strike?.toFixed(2)}: Mid $${midPrice.toFixed(2)}`,
              margin,
              yPosition
            )
            yPosition += 6
          })
          yPosition += 5
        }

        // Portfolio Greeks Section (calculate from data)
        if (legs.length > 0 && optionChain) {
          checkNewPage(60)
          pdf.setFontSize(16)
          pdf.setFont("helvetica", "bold")
          pdf.text("2. Portfolio Greeks", margin, yPosition)
          yPosition += 8

          // Calculate combined Greeks
          let totalDelta = 0
          let totalGamma = 0
          let totalTheta = 0
          let totalVega = 0
          let totalRho = 0

          legs.forEach((leg: StrategyLeg) => {
            const options = leg.type === "call" ? optionChain.calls : optionChain.puts
            const option = options?.find((o: any) => {
              const optionStrike = o.strike ?? o.strike_price
              return optionStrike !== undefined && Math.abs(optionStrike - leg.strike!) < 0.01
            })

            if (option) {
              const multiplier = (leg.action === "buy" ? 1 : -1) * (leg.quantity || 1)
              totalDelta += (option.delta || 0) * multiplier
              totalGamma += (option.gamma || 0) * multiplier
              totalTheta += (option.theta || 0) * multiplier
              totalVega += (option.vega || 0) * multiplier
              totalRho += (option.rho || 0) * multiplier
            }
          })

          pdf.setFontSize(10)
          pdf.setFont("helvetica", "normal")
          pdf.text(`Delta (Δ): ${totalDelta.toFixed(4)}`, margin, yPosition)
          yPosition += 6
          pdf.text(`Gamma (Γ): ${totalGamma.toFixed(4)}`, margin, yPosition)
          yPosition += 6
          pdf.text(`Theta (Θ): ${totalTheta.toFixed(4)}`, margin, yPosition)
          yPosition += 6
          pdf.text(`Vega (ν): ${totalVega.toFixed(4)}`, margin, yPosition)
          yPosition += 6
          pdf.text(`Rho (ρ): ${totalRho.toFixed(4)}`, margin, yPosition)
          yPosition += 10
        }
        // Payoff Diagrams Section - Draw on canvas
        if (payoffData.length > 0) {
          checkNewPage(100)
          pdf.setFontSize(16)
          pdf.setFont("helvetica", "bold")
          pdf.text("3. Payoff Diagrams", margin, yPosition)
          yPosition += 8

          // Create a temporary canvas to draw the payoff chart
          const tempCanvas = document.createElement("canvas")
          tempCanvas.width = 700
          tempCanvas.height = 400
          const ctx = tempCanvas.getContext("2d")
          
          if (ctx) {
            const padding = 60
            const chartWidth = tempCanvas.width - padding * 2
            const chartHeight = tempCanvas.height - padding * 2

            // Find min/max values
            const prices = payoffData.map(d => d.price)
            const profits = payoffData.map(d => d.profit)
            const minPrice = Math.min(...prices)
            const maxPrice = Math.max(...prices)
            const minProfit = Math.min(...profits)
            const maxProfit = Math.max(...profits)
            const profitRange = maxProfit - minProfit

            // White background
            ctx.fillStyle = "#ffffff"
            ctx.fillRect(0, 0, tempCanvas.width, tempCanvas.height)

            // Draw axes
            ctx.strokeStyle = "#374151"
            ctx.lineWidth = 2
            ctx.beginPath()
            ctx.moveTo(padding, padding)
            ctx.lineTo(padding, tempCanvas.height - padding)
            ctx.lineTo(tempCanvas.width - padding, tempCanvas.height - padding)
            ctx.stroke()

            // Draw zero line
            const zeroY = padding + chartHeight - ((0 - minProfit) / profitRange) * chartHeight
            ctx.strokeStyle = "#9ca3af"
            ctx.lineWidth = 1
            ctx.setLineDash([5, 5])
            ctx.beginPath()
            ctx.moveTo(padding, zeroY)
            ctx.lineTo(tempCanvas.width - padding, zeroY)
            ctx.stroke()
            ctx.setLineDash([])

            // Draw payoff curve
            ctx.strokeStyle = "#3b82f6"
            ctx.lineWidth = 2
            ctx.beginPath()
            payoffData.forEach((point, index) => {
              const x = padding + ((point.price - minPrice) / (maxPrice - minPrice)) * chartWidth
              const y = padding + chartHeight - ((point.profit - minProfit) / profitRange) * chartHeight
              if (index === 0) {
                ctx.moveTo(x, y)
              } else {
                ctx.lineTo(x, y)
              }
            })
            ctx.stroke()

            // Fill profit area
            const hasProfit = payoffData.some(p => p.profit >= 0)
            ctx.fillStyle = hasProfit ? "rgba(16, 185, 129, 0.2)" : "rgba(239, 68, 68, 0.2)"
            ctx.beginPath()
            ctx.moveTo(padding, zeroY)
            payoffData.forEach((point) => {
              const x = padding + ((point.price - minPrice) / (maxPrice - minPrice)) * chartWidth
              const y = padding + chartHeight - ((point.profit - minProfit) / profitRange) * chartHeight
              ctx.lineTo(x, y)
            })
            ctx.lineTo(tempCanvas.width - padding, zeroY)
            ctx.closePath()
            ctx.fill()

            // Labels
            ctx.fillStyle = "#374151"
            ctx.font = "12px sans-serif"
            ctx.textAlign = "center"
            ctx.fillText("Stock Price ($)", tempCanvas.width / 2, tempCanvas.height - 20)
            ctx.save()
            ctx.translate(20, tempCanvas.height / 2)
            ctx.rotate(-Math.PI / 2)
            ctx.fillText("Profit/Loss ($)", 0, 0)
            ctx.restore()

            // Convert canvas to image and add to PDF
            const imgData = tempCanvas.toDataURL("image/png")
            const imgWidth = pageWidth - 2 * margin
            const imgHeight = (tempCanvas.height * imgWidth) / tempCanvas.width
            
            checkNewPage(imgHeight + 10)
            pdf.addImage(imgData, "PNG", margin, yPosition, imgWidth, imgHeight)
            yPosition += imgHeight + 5
          }
        }
      }

      // AI Report Section
      {
        checkNewPage(50)
        pdf.setFontSize(16)
        pdf.setFont("helvetica", "bold")
        pdf.text("4. AI Analysis Report", margin, yPosition)
        yPosition += 8

        pdf.setFontSize(10)
        pdf.setFont("helvetica", "normal")
        pdf.text(`Generated: ${new Date(selectedReport.created_at).toLocaleString()}`, margin, yPosition)
        yPosition += 5
        pdf.text(`Model: ${selectedReport.model_used}`, margin, yPosition)
        yPosition += 8

        // Convert markdown to HTML then to image
        marked.setOptions({ gfm: true, breaks: false })
        const htmlContent = await marked.parse(selectedReport.report_content)
        
        // Create temporary div to render markdown
        const tempDiv = document.createElement("div")
        tempDiv.innerHTML = htmlContent
        tempDiv.style.width = `${pageWidth - 2 * margin}mm`
        tempDiv.style.padding = "10px"
        tempDiv.style.fontSize = "11px"
        tempDiv.style.fontFamily = "Arial, sans-serif"
        document.body.appendChild(tempDiv)

        try {
          const canvas = await html2canvas(tempDiv, {
            backgroundColor: "#ffffff",
            scale: 2,
            logging: false,
          })
          const imgData = canvas.toDataURL("image/png")
          const imgWidth = pageWidth - 2 * margin
          const imgHeight = (canvas.height * imgWidth) / canvas.width
          
          checkNewPage(imgHeight + 10)
          pdf.addImage(imgData, "PNG", margin, yPosition, imgWidth, imgHeight)
          yPosition += imgHeight + 5
        } catch (error) {
          console.warn("Failed to capture AI Report:", error)
          // Fallback: add text directly
          pdf.setFontSize(10)
          const text = selectedReport.report_content.replace(/[#*`]/g, "").substring(0, 5000)
          const lines = pdf.splitTextToSize(text, pageWidth - 2 * margin)
          checkNewPage(lines.length * 5)
          pdf.text(lines, margin, yPosition)
          yPosition += lines.length * 5
        }

        document.body.removeChild(tempDiv)
      }

      // Footer with copyright
      const totalPages = pdf.internal.pages.length - 1
      for (let i = 1; i <= totalPages; i++) {
        pdf.setPage(i)
        pdf.setFontSize(8)
        pdf.setTextColor(128, 128, 128)
        pdf.text(
          `© ${new Date().getFullYear()} ThetaMind. All rights reserved.`,
          pageWidth / 2,
          pageHeight - 10,
          { align: "center" }
        )
        pdf.text(`Page ${i} of ${totalPages}`, pageWidth / 2, pageHeight - 5, { align: "center" })
      }

      // Save PDF
      const symbol = strategyData?.symbol || extractSymbol(selectedReport.report_content)
      const dateStr = format(new Date(selectedReport.created_at), "yyyy-MM-dd")
      const filename = `ThetaMind_Strategy_Report_${symbol}_${dateStr}.pdf`
      pdf.save(filename)
      
      toast.success("Full report exported successfully!")
    } catch (error) {
      console.error("PDF download error:", error)
      toast.error("Failed to download PDF")
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
                              className="h-8"
                            >
                              <Eye className="h-3.5 w-3.5 mr-1.5" />
                              View
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleDelete(report.id)}
                              disabled={deleteMutation.isPending}
                              className="h-8 border-red-200 text-red-600 hover:bg-red-50 hover:text-red-700 hover:border-red-300 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-950 dark:hover:text-red-300 dark:hover:border-red-700"
                            >
                              <Trash2 className="h-3.5 w-3.5 mr-1.5" />
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
            <div className="markdown-content" id="report-content">
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
            </div>
          )}
          <DialogClose onClose={() => setSelectedReport(null)} />
          <div className="mt-4 flex justify-end gap-2">
            <Button variant="outline" onClick={handleDownloadPDF} disabled={!selectedReport}>
              <Download className="h-4 w-4 mr-2" />
              Download PDF
            </Button>
            <Button variant="outline" onClick={() => setSelectedReport(null)}>
              Close
            </Button>
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
                <DialogTitle className="text-lg font-semibold">Delete Report</DialogTitle>
                <DialogDescription className="mt-2 text-sm">
                  Are you sure you want to delete this report? This action cannot be undone and the report will be permanently removed.
                </DialogDescription>
              </div>
            </div>
          </DialogHeader>
          <div className="flex justify-end gap-3 mt-6 pt-4 border-t">
            <Button 
              variant="outline" 
              onClick={handleCancelDelete}
              disabled={deleteMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleConfirmDelete}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete Report
                </>
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

