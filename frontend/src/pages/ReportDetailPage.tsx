import * as React from "react"
import { useMemo, useRef } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { format } from "date-fns"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import html2canvas from "html2canvas"
import { jsPDF } from "jspdf"
import { ArrowLeft, Copy, Download, Loader2, LayoutGrid } from "lucide-react"
import { aiService } from "@/services/api/ai"
import { taskService } from "@/services/api/task"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"

const markdownComponents = {
  h1: ({ node, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h1 className="text-2xl font-bold mt-8 mb-4 pb-2 border-b border-border text-foreground first:mt-0" {...props} />
  ),
  h2: ({ node, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h2 className="text-xl font-semibold mt-6 mb-3 text-foreground" {...props} />
  ),
  h3: ({ node, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h3 className="text-lg font-semibold mt-5 mb-2 text-foreground" {...props} />
  ),
  h4: ({ node, ...props }: React.HTMLAttributes<HTMLHeadingElement>) => (
    <h4 className="text-base font-semibold mt-4 mb-2 text-foreground" {...props} />
  ),
  p: ({ node, ...props }: React.HTMLAttributes<HTMLParagraphElement>) => (
    <p className="mb-4 leading-7 text-foreground" {...props} />
  ),
  ul: ({ node, ...props }: React.HTMLAttributes<HTMLUListElement>) => (
    <ul className="list-disc list-outside mb-4 space-y-2 ml-5 pl-1 text-foreground" {...props} />
  ),
  ol: ({ node, ...props }: React.HTMLAttributes<HTMLOListElement>) => (
    <ol className="list-decimal list-outside mb-4 space-y-2 ml-5 pl-1 text-foreground" {...props} />
  ),
  li: ({ node, ...props }: React.HTMLAttributes<HTMLLIElement>) => (
    <li className="leading-7" {...props} />
  ),
  blockquote: ({ node, ...props }: React.HTMLAttributes<HTMLQuoteElement>) => (
    <blockquote className="border-l-4 border-primary pl-4 my-4 italic text-muted-foreground bg-muted/30 py-2 rounded-r" {...props} />
  ),
  code: ({ node, className, children, ...props }: React.HTMLAttributes<HTMLElement>) => {
    const isBlock = typeof className === "string" && /language-/.test(className)
    return isBlock ? (
      <code className="text-sm font-mono text-foreground" {...props}>{children}</code>
    ) : (
      <code className="bg-muted px-1.5 py-0.5 rounded text-sm font-mono text-foreground" {...props}>{children}</code>
    )
  },
  pre: ({ node, ...props }: React.HTMLAttributes<HTMLPreElement>) => (
    <pre className="bg-muted p-4 rounded-lg my-4 overflow-x-auto text-sm font-mono border border-border/50" {...props} />
  ),
  strong: ({ node, ...props }: React.HTMLAttributes<HTMLElement>) => (
    <strong className="font-semibold text-foreground" {...props} />
  ),
  em: ({ node, ...props }: React.HTMLAttributes<HTMLElement>) => (
    <em className="italic" {...props} />
  ),
  a: ({ node, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a className="text-primary hover:underline underline-offset-2" target="_blank" rel="noopener noreferrer" {...props} />
  ),
  table: ({ node, ...props }: React.HTMLAttributes<HTMLTableElement>) => (
    <div className="overflow-x-auto my-4 rounded-lg border border-border">
      <table className="min-w-full border-collapse text-sm" {...props} />
    </div>
  ),
  thead: ({ node, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) => (
    <thead className="bg-muted/60" {...props} />
  ),
  tbody: ({ node, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) => (
    <tbody {...props} />
  ),
  tr: ({ node, ...props }: React.HTMLAttributes<HTMLTableRowElement>) => (
    <tr className="border-b border-border hover:bg-muted/30 transition-colors" {...props} />
  ),
  th: ({ node, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) => (
    <th className="border-r border-border px-4 py-3 text-left font-semibold last:border-r-0" {...props} />
  ),
  td: ({ node, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) => (
    <td className="border-r border-border px-4 py-3 last:border-r-0" {...props} />
  ),
  hr: ({ node, ...props }: React.HTMLAttributes<HTMLHRElement>) => (
    <hr className="my-6 border-border" {...props} />
  ),
}

function ReportMarkdown({ content }: { content: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
      {content}
    </ReactMarkdown>
  )
}

export const ReportDetailPage: React.FC = () => {
  const { reportId } = useParams<{ reportId: string }>()
  const navigate = useNavigate()
  const contentRef = useRef<HTMLDivElement>(null)

  const { data: report, isLoading } = useQuery({
    queryKey: ["aiReport", reportId],
    queryFn: () => aiService.getReport(reportId!),
    enabled: !!reportId,
  })

  const { data: sourceTasks } = useQuery({
    queryKey: ["tasksByResultRef", reportId],
    queryFn: () => taskService.getTasks({ result_ref: reportId!, limit: 1, skip: 0 }),
    enabled: !!reportId,
  })
  const sourceTask = sourceTasks?.[0] ?? null
  const recommendedStrategies = (sourceTask?.metadata?.recommended_strategies as Array<Record<string, unknown>>) ?? []
  const strategySummary = sourceTask?.metadata?.strategy_summary as { symbol?: string; expiration_date?: string } | undefined

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
        {recommendedStrategies.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <LayoutGrid className="h-4 w-4" />
                System-Recommended Strategies
              </CardTitle>
              <CardDescription>
                Load a recommended strategy into Strategy Lab to edit or analyze
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {recommendedStrategies.map((rec: Record<string, unknown>, i: number) => {
                const name = (rec.strategy_name as string) ?? `Strategy ${i + 1}`
                const legs = (rec.legs as Array<{ type?: string; action?: string; strike?: number; quantity?: number; expiry?: string }>) ?? []
                const rationale = (rec.rationale as string) ?? ""
                const symbol = String(strategySummary?.symbol ?? "").trim()
                const expirationDate = String(strategySummary?.expiration_date ?? legs[0]?.expiry ?? "").trim()
                const canLoad = symbol.length > 0 && legs.length > 0
                return (
                  <div key={i} className="rounded-lg border border-border/50 bg-muted/10 p-3">
                    <div className="font-medium">{name}</div>
                    {rationale && <p className="text-sm text-muted-foreground mt-1">{rationale}</p>}
                    <Button
                      size="sm"
                      className="mt-2"
                      disabled={!canLoad}
                      title={!canLoad ? "Symbol and legs are required to load" : undefined}
                      onClick={() => {
                        navigate("/strategy-lab", {
                          state: {
                            loadRecommended: {
                              strategy: rec,
                              symbol,
                              expiration_date: expirationDate,
                            },
                          },
                        })
                        toast.success(`Loading "${name}" into Strategy Lab`)
                      }}
                    >
                      <LayoutGrid className="mr-2 h-4 w-4" />
                      Load to Strategy Lab
                    </Button>
                  </div>
                )
              })}
            </CardContent>
          </Card>
        )}
        {inputSummary && (
          <Card>
            <CardHeader>
              <CardTitle>Core Inputs</CardTitle>
              <CardDescription>Verified inputs extracted from report</CardDescription>
            </CardHeader>
            <CardContent>
              <ReportMarkdown content={inputSummary} />
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Analysis Report</CardTitle>
            <CardDescription>Full AI analysis in readable format</CardDescription>
          </CardHeader>
          <CardContent className="rounded-lg border border-border/50 bg-muted/20 p-6 sm:p-8">
            <div className="report-markdown text-base leading-relaxed text-foreground">
              <ReportMarkdown content={report.report_content} />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
