import * as React from "react"
import { useMemo, useRef } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { format } from "date-fns"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import html2canvas from "html2canvas"
import { jsPDF } from "jspdf"
import { ArrowLeft, Copy, Download, Loader2 } from "lucide-react"
import { aiService } from "@/services/api/ai"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"

export const ReportDetailPage: React.FC = () => {
  const { reportId } = useParams<{ reportId: string }>()
  const navigate = useNavigate()
  const contentRef = useRef<HTMLDivElement>(null)

  const { data: report, isLoading } = useQuery({
    queryKey: ["aiReport", reportId],
    queryFn: () => aiService.getReport(reportId!),
    enabled: !!reportId,
  })

  const inputSummary = useMemo(() => {
    if (!report?.report_content) return null
    const match = report.report_content.match(/## Input Summary[\s\S]*?(?=## |$)/)
    if (!match) return null
    return match[0]
  }, [report?.report_content])

  const handleCopy = async () => {
    if (!report?.report_content) return
    await navigator.clipboard.writeText(report.report_content)
    toast.success("Report copied to clipboard")
  }

  const handleDownloadPDF = async () => {
    if (!contentRef.current || !report) return
    toast.info("Generating PDF...")
    const canvas = await html2canvas(contentRef.current, { scale: 2, useCORS: true })
    const imgData = canvas.toDataURL("image/png")
    const pdf = new jsPDF("p", "mm", "a4")
    const pageWidth = pdf.internal.pageSize.getWidth()
    const pageHeight = pdf.internal.pageSize.getHeight()
    const imgWidth = pageWidth
    const imgHeight = (canvas.height * imgWidth) / canvas.width
    let position = 0
    let remainingHeight = imgHeight
    pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight)
    remainingHeight -= pageHeight
    while (remainingHeight > 0) {
      position -= pageHeight
      pdf.addPage()
      pdf.addImage(imgData, "PNG", 0, position, imgWidth, imgHeight)
      remainingHeight -= pageHeight
    }
    const dateStr = format(new Date(report.created_at), "yyyy-MM-dd")
    pdf.save(`ThetaMind_Strategy_Report_${report.id}_${dateStr}.pdf`)
  }

  if (isLoading) {
    return (
      <div className="flex h-[60vh] items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        Loading report...
      </div>
    )
  }

  if (!report) {
    return (
      <div className="text-muted-foreground">
        Report not found.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => navigate("/reports")}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Reports
          </Button>
          <div>
            <div className="text-lg font-semibold">AI Analysis Report</div>
            <div className="text-sm text-muted-foreground">
              Generated {format(new Date(report.created_at), "PPpp")} · {report.model_used}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleCopy}>
            <Copy className="mr-2 h-4 w-4" />
            Copy Full Text
          </Button>
          <Button size="sm" onClick={handleDownloadPDF}>
            <Download className="mr-2 h-4 w-4" />
            Export PDF
          </Button>
        </div>
      </div>

      <div ref={contentRef} className="space-y-4">
        {inputSummary && (
          <Card>
            <CardHeader>
              <CardTitle>Core Inputs</CardTitle>
              <CardDescription>Verified inputs extracted from report</CardDescription>
            </CardHeader>
            <CardContent>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {inputSummary}
              </ReactMarkdown>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Analysis Report</CardTitle>
            <CardDescription>Markdown-rendered content (copyable)</CardDescription>
          </CardHeader>
          <CardContent className="prose prose-slate max-w-none dark:prose-invert">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {report.report_content}
            </ReactMarkdown>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
