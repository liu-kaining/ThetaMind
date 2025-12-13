import * as React from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { RefreshCw, FileText, AlertTriangle, Trash2 } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
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
        const completedCount = data.filter(
          (task) => task.status === "SUCCESS" && task.task_type === "ai_report"
        ).length
        if (completedCount > previousCompletedCount) {
          // Task completed, refresh user data to update usage
          refreshUser()
          setPreviousCompletedCount(completedCount)
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

      {/* Tasks table */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Tasks</CardTitle>
          <CardDescription>
            View the status and results of your background tasks
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          ) : tasks && tasks.length > 0 ? (
            <TaskTable 
              tasks={tasks} 
              onViewResult={handleViewResult}
              onViewDetails={handleViewDetails}
              onDelete={handleDelete}
            />
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <FileText className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">
                No tasks found. Tasks will appear here when you start background jobs.
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

