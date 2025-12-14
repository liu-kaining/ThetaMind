import * as React from "react"
import { useState, useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { useParams, useNavigate, useSearchParams } from "react-router-dom"
import { format } from "date-fns"
import { ArrowLeft, Clock, CheckCircle, XCircle, AlertCircle, RefreshCw, Code, Brain, Play, Download, Image as ImageIcon } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { TaskStatusBadge, TaskStatus } from "@/components/tasks/TaskStatusBadge"
import { taskService, TaskExecutionEvent } from "@/services/api/task"
import { aiService } from "@/services/api/ai"
import { toast } from "sonner"

export const TaskDetailPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [imageId, setImageId] = useState<string | null>(null)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [isLoadingImage, setIsLoadingImage] = useState(false)

  const { data: task, isLoading } = useQuery({
    queryKey: ["task", taskId],
    queryFn: () => taskService.getTask(taskId!),
    enabled: !!taskId,
  })

  // Extract image_id from task result_ref or URL params
  useEffect(() => {
    if (!task) return

    // First, check URL params (from "View Result" button)
    const urlImageId = searchParams.get("image_id")
    if (urlImageId) {
      setImageId(urlImageId)
      return
    }

    // Then, check task result_ref for generate_strategy_chart tasks
    if (task.task_type === "generate_strategy_chart" && task.result_ref && task.status === "SUCCESS") {
      try {
        const result = JSON.parse(task.result_ref)
        if (result.image_id) {
          setImageId(result.image_id)
        }
      } catch (e) {
        console.error("Failed to parse result_ref:", e)
      }
    }
  }, [task, searchParams])

  // Fetch image when imageId is available
  useEffect(() => {
    if (!imageId) return

    setIsLoadingImage(true)
    let currentImageUrl: string | null = null
    
    aiService
      .getChartImage(imageId)
      .then((blob) => {
        // Verify blob is valid
        if (!blob || blob.size === 0) {
          throw new Error("Invalid image blob: empty or null")
        }
        
        // Verify blob type
        if (blob.type && !blob.type.startsWith("image/")) {
          console.warn(`Unexpected blob type: ${blob.type}, expected image/*`)
        }
        
        // Verify blob size (at least 100 bytes for a valid image)
        if (blob.size < 100) {
          throw new Error(`Invalid image blob: too small (${blob.size} bytes)`)
        }
        
        console.log(`Image blob loaded: ${blob.size} bytes, type: ${blob.type || "unknown"}`)
        
        // Create object URL
        const url = URL.createObjectURL(blob)
        currentImageUrl = url
        setImageUrl(url)
        setIsLoadingImage(false)
      })
      .catch((error) => {
        console.error("Failed to fetch image:", error)
        const errorMessage = error.response?.data?.detail || error.message || "Unknown error"
        toast.error(`Failed to load chart image: ${errorMessage}`)
        setIsLoadingImage(false)
        setImageUrl(null)
      })

    // Cleanup
    return () => {
      if (currentImageUrl) {
        URL.revokeObjectURL(currentImageUrl)
      }
    }
  }, [imageId])

  const handleDownloadImage = async () => {
    if (!imageId) return

    try {
      // Fetch fresh blob for download to ensure it's not corrupted
      const blob = await aiService.getChartImage(imageId)
      
      if (!blob || blob.size === 0) {
        toast.error("Invalid image data")
        return
      }

      const url = URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = url
      link.download = `ThetaMind_Strategy_Chart_${imageId}.png`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      // Cleanup URL after a delay
      setTimeout(() => {
        URL.revokeObjectURL(url)
      }, 100)
      
      toast.success("Chart downloaded successfully")
    } catch (error: any) {
      console.error("Failed to download image:", error)
      toast.error(`Failed to download image: ${error.message || "Unknown error"}`)
    }
  }

  const formatDate = (dateString: string | null | undefined): string => {
    if (!dateString) return "-"
    try {
      return format(new Date(dateString), "PPpp")
    } catch {
      return dateString
    }
  }

  const getEventIcon = (type: TaskExecutionEvent["type"]) => {
    switch (type) {
      case "start":
        return <Play className="h-4 w-4 text-blue-500" />
      case "success":
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case "error":
        return <XCircle className="h-4 w-4 text-red-500" />
      case "retry":
        return <RefreshCw className="h-4 w-4 text-amber-500" />
      case "info":
        return <AlertCircle className="h-4 w-4 text-blue-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-500" />
    }
  }

  const getEventColor = (type: TaskExecutionEvent["type"]) => {
    switch (type) {
      case "start":
        return "border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950"
      case "success":
        return "border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-950"
      case "error":
        return "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950"
      case "retry":
        return "border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-950"
      case "info":
        return "border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950"
      default:
        return "border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-gray-950"
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (!task) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => navigate("/dashboard/tasks")}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Tasks
        </Button>
        <Card>
          <CardContent className="pt-6">
            <p className="text-center text-muted-foreground">Task not found</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button 
            variant="outline" 
            onClick={() => navigate("/dashboard/tasks")}
            className="font-medium hover:bg-accent hover:text-accent-foreground"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Tasks
          </Button>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Task Details</h1>
            <p className="text-muted-foreground">View execution details and timeline</p>
          </div>
        </div>
        <TaskStatusBadge 
          status={task.status as TaskStatus}
          progress={task.metadata?.progress}
          currentStage={task.metadata?.current_stage}
        />
      </div>

      {/* Progress Card (only show if task is processing and has progress) */}
      {task.status === "PROCESSING" && task.metadata?.progress !== undefined && (
        <Card className="border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950">
          <CardHeader>
            <CardTitle className="text-sm font-medium">Progress</CardTitle>
            <CardDescription>
              {task.metadata?.current_stage || "Processing task..."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <Progress value={task.metadata.progress} className="h-2" />
              <div className="flex justify-between text-sm text-muted-foreground">
                <span>{task.metadata.progress}% complete</span>
                <span>{task.metadata.current_stage || ""}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Task Type</CardTitle>
            <Code className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{task.task_type}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">AI Model</CardTitle>
            <Brain className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{task.model_used || "N/A"}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Retries</CardTitle>
            <RefreshCw className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{task.retry_count}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Duration</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {task.started_at && task.completed_at ? (
              <div className="text-2xl font-bold">
                {Math.round(
                  (new Date(task.completed_at).getTime() - new Date(task.started_at).getTime()) / 1000
                )}s
              </div>
            ) : task.started_at ? (
              <div className="text-2xl font-bold">
                {Math.round(
                  (Date.now() - new Date(task.started_at).getTime()) / 1000
                )}s
              </div>
            ) : (
              <div className="text-2xl font-bold">-</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs defaultValue={imageId ? "result" : "timeline"} className="space-y-4">
        <TabsList>
          {imageId && (
            <TabsTrigger value="result">
              <ImageIcon className="h-4 w-4 mr-2" />
              Generated Image
            </TabsTrigger>
          )}
          <TabsTrigger value="timeline">Execution Timeline</TabsTrigger>
          <TabsTrigger value="input">Input Data</TabsTrigger>
          <TabsTrigger value="prompt">Prompt</TabsTrigger>
        </TabsList>

        {/* Result Tab (Generated Image) */}
        {imageId && (
          <TabsContent value="result" className="space-y-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Generated Strategy Chart</CardTitle>
                    <CardDescription>
                      AI-generated panoramic analysis chart for your strategy
                    </CardDescription>
                  </div>
                  {imageUrl && (
                    <Button onClick={handleDownloadImage} variant="outline" size="sm">
                      <Download className="h-4 w-4 mr-2" />
                      Download Image
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {isLoadingImage ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="text-center">
                      <Skeleton className="h-64 w-full mb-4" />
                      <p className="text-sm text-muted-foreground">Loading image...</p>
                    </div>
                  </div>
                ) : imageUrl ? (
                  <div className="flex flex-col items-center">
                    <div className="w-full max-w-4xl border rounded-lg overflow-hidden bg-white">
                      <img
                        src={imageUrl}
                        alt="AI Generated Strategy Chart"
                        className="w-full h-auto"
                        onError={(e) => {
                          console.error("Image load error:", e)
                          const target = e.target as HTMLImageElement
                          console.error("Image src:", target.src?.substring(0, 100))
                          console.error("Image naturalWidth:", target.naturalWidth)
                          console.error("Image naturalHeight:", target.naturalHeight)
                          toast.error("Failed to display image. Please try downloading it.")
                          setIsLoadingImage(false)
                        }}
                        onLoad={(e) => {
                          const target = e.target as HTMLImageElement
                          console.log("Image loaded successfully:", {
                            naturalWidth: target.naturalWidth,
                            naturalHeight: target.naturalHeight,
                            src: target.src?.substring(0, 100)
                          })
                        }}
                      />
                    </div>
                    <div className="mt-4">
                      <Button onClick={handleDownloadImage} variant="default">
                        <Download className="h-4 w-4 mr-2" />
                        Download PNG
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-center py-12">
                    <div className="text-center">
                      <AlertCircle className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                      <p className="text-sm text-muted-foreground">Failed to load image</p>
                      <Button 
                        onClick={() => {
                          // Retry loading
                          if (imageId) {
                            setImageUrl(null)
                            setIsLoadingImage(true)
                            // Trigger re-fetch by clearing and re-setting imageId
                            const currentId = imageId
                            setImageId(null)
                            setTimeout(() => setImageId(currentId), 100)
                          }
                        }}
                        variant="outline"
                        className="mt-4"
                      >
                        Retry
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        )}

        {/* Timeline Tab */}
        <TabsContent value="timeline" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Execution Timeline</CardTitle>
              <CardDescription>
                Detailed execution history with timestamps
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Task Creation */}
                <div className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <div className="h-8 w-8 rounded-full bg-gray-200 dark:bg-gray-800 flex items-center justify-center">
                      <Clock className="h-4 w-4 text-gray-600 dark:text-gray-400" />
                    </div>
                    <div className="w-px h-full bg-gray-200 dark:bg-gray-800" />
                  </div>
                  <div className="flex-1 pb-4">
                    <div className="font-semibold">Task Created</div>
                    <div className="text-sm text-muted-foreground">{formatDate(task.created_at)}</div>
                  </div>
                </div>

                {/* Started */}
                {task.started_at && (
                  <div className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <div className="h-8 w-8 rounded-full bg-blue-200 dark:bg-blue-800 flex items-center justify-center">
                        <Play className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                      </div>
                      <div className="w-px h-full bg-gray-200 dark:bg-gray-800" />
                    </div>
                    <div className="flex-1 pb-4">
                      <div className="font-semibold">Processing Started</div>
                      <div className="text-sm text-muted-foreground">{formatDate(task.started_at)}</div>
                    </div>
                  </div>
                )}

                {/* Execution History Events */}
                {task.execution_history && task.execution_history.length > 0 && (
                  <>
                    {task.execution_history.map((event, index) => (
                      <div key={index} className="flex gap-4">
                        <div className="flex flex-col items-center">
                          <div className={`h-8 w-8 rounded-full border-2 flex items-center justify-center ${getEventColor(event.type)}`}>
                            {getEventIcon(event.type)}
                          </div>
                          {index < task.execution_history!.length - 1 && (
                            <div className="w-px h-full bg-gray-200 dark:bg-gray-800" />
                          )}
                        </div>
                        <div className="flex-1 pb-4">
                          <div className={`font-semibold ${event.type === "error" ? "text-red-600 dark:text-red-400" : ""}`}>
                            {event.type.charAt(0).toUpperCase() + event.type.slice(1)}
                          </div>
                          <div className="text-sm text-muted-foreground">{event.message}</div>
                          <div className="text-xs text-muted-foreground mt-1">
                            {formatDate(event.timestamp)}
                          </div>
                        </div>
                      </div>
                    ))}
                  </>
                )}

                {/* Completed/Failed */}
                {task.completed_at && (
                  <div className="flex gap-4">
                    <div className="flex flex-col items-center">
                      <div
                        className={`h-8 w-8 rounded-full flex items-center justify-center ${
                          task.status === "SUCCESS"
                            ? "bg-green-200 dark:bg-green-800"
                            : "bg-red-200 dark:bg-red-800"
                        }`}
                      >
                        {task.status === "SUCCESS" ? (
                          <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                        )}
                      </div>
                    </div>
                    <div className="flex-1">
                      <div className="font-semibold">
                        {task.status === "SUCCESS" ? "Completed Successfully" : "Failed"}
                      </div>
                      <div className="text-sm text-muted-foreground">{formatDate(task.completed_at)}</div>
                      {task.status === "FAILED" && task.error_message && (
                        <div className="mt-2 p-3 rounded-md bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800">
                          <div className="text-sm font-medium text-red-800 dark:text-red-200">Error:</div>
                          <div className="text-sm text-red-700 dark:text-red-300 mt-1">{task.error_message}</div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Input Data Tab */}
        <TabsContent value="input" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Input Data</CardTitle>
              <CardDescription>Strategy and option chain data used for this task</CardDescription>
            </CardHeader>
            <CardContent>
              <pre className="bg-slate-50 dark:bg-slate-900 p-4 rounded-lg overflow-auto text-sm">
                {JSON.stringify(task.metadata, null, 2)}
              </pre>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Prompt Tab */}
        <TabsContent value="prompt" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Full Prompt</CardTitle>
              <CardDescription>
                Complete prompt sent to AI model ({task.model_used || "N/A"})
              </CardDescription>
            </CardHeader>
            <CardContent>
              {task.prompt_used ? (
                <div className="relative">
                  <pre className="bg-slate-50 dark:bg-slate-900 p-4 rounded-lg overflow-auto text-sm whitespace-pre-wrap max-h-[600px] border border-slate-200 dark:border-slate-800">
                    {(() => {
                      // Try to parse as JSON for better formatting
                      try {
                        const parsed = JSON.parse(task.prompt_used)
                        return JSON.stringify(parsed, null, 2)
                      } catch {
                        // If not JSON, return as-is
                        return task.prompt_used
                      }
                    })()}
                  </pre>
                  <div className="absolute top-2 right-2 text-xs text-muted-foreground bg-background/80 px-2 py-1 rounded">
                    {task.prompt_used.length} characters
                  </div>
                </div>
              ) : (
                <p className="text-muted-foreground">Prompt not available</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Time Information */}
      <Card>
        <CardHeader>
          <CardTitle>Time Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <div className="text-sm font-medium text-muted-foreground">Created At</div>
              <div className="text-base">{formatDate(task.created_at)}</div>
            </div>
            {task.started_at && (
              <div>
                <div className="text-sm font-medium text-muted-foreground">Started At</div>
                <div className="text-base">{formatDate(task.started_at)}</div>
              </div>
            )}
            <div>
              <div className="text-sm font-medium text-muted-foreground">Last Updated</div>
              <div className="text-base">{formatDate(task.updated_at)}</div>
            </div>
            {task.completed_at && (
              <div>
                <div className="text-sm font-medium text-muted-foreground">Completed At</div>
                <div className="text-base">{formatDate(task.completed_at)}</div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

