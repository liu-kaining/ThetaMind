import * as React from "react"
import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { RefreshCw, FileText } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { TaskTable } from "@/components/tasks/TaskTable"
import { taskService, TaskResponse } from "@/services/api/task"
import { toast } from "sonner"

export const TaskCenter: React.FC = () => {
  const navigate = useNavigate()
  const [hasActiveTasks, setHasActiveTasks] = React.useState(false)

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
        return hasActive ? 2000 : false // Poll every 2s if active, otherwise stop
      }
      return false
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
            <TaskTable tasks={tasks} onViewResult={handleViewResult} />
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
    </div>
  )
}

