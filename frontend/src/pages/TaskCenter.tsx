import * as React from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { RefreshCw, FileText, AlertTriangle, Trash2, Search, ChevronLeft, ChevronRight } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogClose,
} from "@/components/ui/dialog"
import { TaskTable } from "@/components/tasks/TaskTable"
import { taskService, TaskResponse } from "@/services/api/task"
import { toast } from "sonner"
import { useAuth } from "@/features/auth/AuthProvider"

export const TaskCenter: React.FC = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { refreshUser } = useAuth()
  const [hasActiveTasks, setHasActiveTasks] = React.useState(false)
  const [previousCompletedCount, setPreviousCompletedCount] = React.useState(0)
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false)
  const [taskToDelete, setTaskToDelete] = React.useState<string | null>(null)
  const [searchQuery, setSearchQuery] = React.useState("")
  const [currentPage, setCurrentPage] = React.useState(1)
  const tasksPerPage = 10

  // Fetch tasks with smart polling
  const { data: tasks, isLoading, refetch } = useQuery({
    queryKey: ["tasks"],
    queryFn: () => taskService.getTasks({ limit: 50, skip: 0 }),
    refetchInterval: (query) => {
      // Check if there are any PENDING or PROCESSING tasks
      const data = query.state.data as TaskResponse[] | undefined
      if (data) {
        const hasActive = data.some(
          (task) => task.status === "PENDING" || task.status === "PROCESSING"
        )
        setHasActiveTasks(hasActive)
        
        // Check if any tasks completed since last check
        // Note: This comparison happens in refetchInterval callback, so it's safe
        const completedCount = data.filter(
          (task) => task.status === "SUCCESS" && task.task_type === "ai_report"
        ).length
        if (completedCount > previousCompletedCount) {
          // Task completed, refresh user data to update usage
          // Use setTimeout to debounce and avoid multiple rapid calls
          setTimeout(() => {
            refreshUser()
          }, 500)
          setPreviousCompletedCount(completedCount)
        }
        
        // Check for long-running tasks (more than 10 minutes) and warn
        const longRunningTasks = data.filter((task) => {
          if (task.status !== "PROCESSING" && task.status !== "PENDING") return false
          if (!task.created_at) return false
          const createdTime = new Date(task.created_at).getTime()
          const now = Date.now()
          const durationMinutes = (now - createdTime) / (1000 * 60)
          return durationMinutes > 10
        })
        
        if (longRunningTasks.length > 0) {
          console.warn(`Found ${longRunningTasks.length} long-running task(s) (>10 minutes):`, longRunningTasks.map(t => ({ id: t.id, type: t.task_type, status: t.status, created: t.created_at })))
        }
        
        return hasActive ? 2000 : false // Poll every 2s if active, otherwise stop
      }
      return false
    },
  })
  
  // Initialize previous completed count
  React.useEffect(() => {
    if (tasks) {
      const completedCount = tasks.filter(
        (task) => task.status === "SUCCESS" && task.task_type === "ai_report"
      ).length
      setPreviousCompletedCount(completedCount)
    }
  }, [tasks])

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (taskId: string) => taskService.deleteTask(taskId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
      toast.success("Task deleted successfully")
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to delete task")
    },
  })

  const handleViewResult = (taskId: string, resultRef: string) => {
    // Navigate based on task type
    const task = tasks?.find((t) => t.id === taskId)
    if (!task) return

    if (task.task_type === "ai_report" && resultRef) {
      // Navigate to reports page or show report in modal
      navigate(`/reports?reportId=${resultRef}`)
      toast.success("Opening report...")
    } else if (task.task_type === "generate_strategy_chart" && resultRef) {
      // Parse result_ref to get image_id
      try {
        const result = JSON.parse(resultRef)
        if (result.image_id) {
          // Navigate to task detail page with image view
          navigate(`/dashboard/tasks/${taskId}?image_id=${result.image_id}`)
        } else {
          toast.error("Image ID not found in result")
        }
      } catch (e) {
        console.error("Failed to parse result_ref:", e)
        toast.error("Failed to parse task result")
      }
    } else {
      toast.info("Result view not implemented for this task type")
    }
  }

  const handleViewDetails = (taskId: string) => {
    navigate(`/dashboard/tasks/${taskId}`)
  }

  const handleDelete = (taskId: string) => {
    setTaskToDelete(taskId)
    setDeleteDialogOpen(true)
  }

  const handleConfirmDelete = () => {
    if (taskToDelete) {
      deleteMutation.mutate(taskToDelete)
      setDeleteDialogOpen(false)
      setTaskToDelete(null)
    }
  }

  const handleCancelDelete = () => {
    setDeleteDialogOpen(false)
    setTaskToDelete(null)
  }

  const handleRefresh = () => {
    refetch()
    toast.success("Tasks refreshed")
  }

  // Extract symbol from task metadata
  const extractSymbol = (task: TaskResponse): string => {
    try {
      // Priority 1: Check strategy_summary (new format)
      if (task.metadata?.strategy_summary?.symbol) {
        return task.metadata.strategy_summary.symbol
      }
      
      // Priority 2: Check strategy_data (legacy format)
      if (task.metadata?.strategy_data?.symbol) {
        return task.metadata.strategy_data.symbol
      }
      
      // Priority 3: Check direct symbol in metadata
      if (task.metadata?.symbol) {
        return task.metadata.symbol
      }
      
      // Priority 4: Try to extract from prompt_used (for AI reports)
      if (task.prompt_used) {
        try {
          // Look for "Target Ticker: SYMBOL" or "Symbol: SYMBOL" pattern
          const tickerMatch = task.prompt_used.match(/(?:Target Ticker|Symbol|Ticker):\s*([A-Z]{1,5})\b/i)
          if (tickerMatch && tickerMatch[1]) {
            return tickerMatch[1]
          }
        } catch (e) {
          // Ignore errors in prompt parsing
        }
      }
      
      return "N/A"
    } catch (error) {
      console.error("Error extracting symbol from task:", error)
      return "N/A"
    }
  }

  // Filter tasks by search query
  const filteredTasks = React.useMemo(() => {
    if (!tasks) return []
    if (!searchQuery.trim()) return tasks

    const query = searchQuery.toLowerCase().trim()
    return tasks.filter((task) => {
      // Search in task type
      const taskType = (task.task_type || "").toLowerCase()
      // Search in symbol
      const symbol = extractSymbol(task).toLowerCase()
      // Search in status
      const status = (task.status || "").toLowerCase()
      // Search in model used
      const model = (task.model_used || "").toLowerCase()
      // Search in error message
      const errorMessage = (task.error_message || "").toLowerCase()

      return (
        taskType.includes(query) ||
        symbol.includes(query) ||
        status.includes(query) ||
        model.includes(query) ||
        errorMessage.includes(query)
      )
    })
  }, [tasks, searchQuery])

  // Pagination
  const totalPages = Math.ceil(filteredTasks.length / tasksPerPage)
  const startIndex = (currentPage - 1) * tasksPerPage
  const endIndex = startIndex + tasksPerPage
  const paginatedTasks = filteredTasks.slice(startIndex, endIndex)

  // Reset to page 1 when search query changes
  React.useEffect(() => {
    setCurrentPage(1)
  }, [searchQuery])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Task Center</h1>
          <p className="text-muted-foreground">
            Monitor your background tasks and view results
          </p>
        </div>
        <Button
          variant="outline"
          onClick={handleRefresh}
          disabled={isLoading}
        >
          <RefreshCw
            className={`h-4 w-4 mr-2 ${isLoading ? "animate-spin" : ""}`}
          />
          Refresh
        </Button>
      </div>

      {/* Status indicator */}
      {hasActiveTasks && (
        <Card className="border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-blue-800 dark:text-blue-200">
              <RefreshCw className="h-4 w-4 animate-spin" />
              <span className="text-sm font-medium">
                Active tasks detected. Auto-refreshing every 2 seconds...
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Search Tasks */}
      <Card>
        <CardHeader>
          <CardTitle>Search Tasks</CardTitle>
          <CardDescription>Filter tasks by symbol, type, or status</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by symbol, type, or status (e.g., GOOG, ai_report)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </CardContent>
      </Card>

      {/* Tasks table */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Tasks</CardTitle>
          <CardDescription>
            {filteredTasks.length > 0
              ? `${filteredTasks.length} task${filteredTasks.length !== 1 ? "s" : ""} found`
              : "View the status and results of your background tasks"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : paginatedTasks && paginatedTasks.length > 0 ? (
            <>
              <TaskTable 
                tasks={paginatedTasks}
                extractSymbol={extractSymbol}
                onViewResult={handleViewResult}
                onViewDetails={handleViewDetails}
                onDelete={handleDelete}
              />
              
              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <div className="text-sm text-muted-foreground">
                    Showing {startIndex + 1}-{Math.min(endIndex, filteredTasks.length)} of {filteredTasks.length} tasks
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                      className="font-medium"
                    >
                      <ChevronLeft className="h-4 w-4 mr-1" />
                      Previous
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
                      Next
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <FileText className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">
                {searchQuery
                  ? `No tasks match your search "${searchQuery}".`
                  : "No tasks found. Tasks will appear here when you start background jobs."}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

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
                <DialogTitle className="text-lg font-semibold">Delete Task</DialogTitle>
                <DialogDescription className="mt-2 text-sm">
                  Are you sure you want to delete this task? This action cannot be undone and all associated data will be permanently removed.
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
                  Delete Task
                </>
              )}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

