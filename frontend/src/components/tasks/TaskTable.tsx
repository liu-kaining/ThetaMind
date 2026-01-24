import * as React from "react"
import { format } from "date-fns"
import { ExternalLink, Trash2, Eye } from "lucide-react"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Button } from "@/components/ui/button"
import { TaskStatusBadge, TaskStatus } from "./TaskStatusBadge"
import { TaskResponse } from "@/services/api/task"

interface TaskTableProps {
  tasks: TaskResponse[]
  extractSymbol?: (task: TaskResponse) => string
  onViewResult?: (taskId: string, resultRef: string) => void
  onViewDetails?: (taskId: string) => void
  onDelete?: (taskId: string) => void
}

export const TaskTable: React.FC<TaskTableProps> = ({
  tasks,
  extractSymbol,
  onViewResult,
  onViewDetails,
  onDelete,
}) => {
  const formatDate = (dateString: string) => {
    try {
      return format(new Date(dateString), "MMM d, yyyy HH:mm:ss")
    } catch {
      return dateString
    }
  }

  const getTaskTypeLabel = (taskType: string) => {
    const labels: Record<string, string> = {
      ai_report: "AI Report",
      multi_agent_report: "Multi-Agent Report",
      options_analysis_workflow: "Options Workflow",
      stock_screening_workflow: "Stock Screening",
      daily_picks: "Daily Picks",
      strategy_analysis: "Strategy Analysis",
      generate_strategy_chart: "AI Chart",
    }
    return labels[taskType] || taskType
  }

  if (tasks.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No tasks found
      </div>
    )
  }

  return (
    <div className="rounded-lg border bg-card">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="font-semibold">Type</TableHead>
            <TableHead className="font-semibold">Symbol</TableHead>
            <TableHead className="font-semibold">Status</TableHead>
            <TableHead className="font-semibold">Created</TableHead>
            <TableHead className="font-semibold">Updated</TableHead>
            <TableHead className="font-semibold">Completed</TableHead>
            <TableHead className="text-right font-semibold">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {tasks.map((task) => (
            <TableRow key={task.id} className="hover:bg-muted/50">
              <TableCell className="font-medium">
                {getTaskTypeLabel(task.task_type)}
              </TableCell>
              <TableCell>
                {extractSymbol ? (
                  <span className="font-mono text-sm">{extractSymbol(task)}</span>
                ) : (
                  <span className="text-muted-foreground text-sm">N/A</span>
                )}
              </TableCell>
              <TableCell>
                <TaskStatusBadge 
                  status={task.status as TaskStatus}
                  progress={task.metadata?.progress}
                  currentStage={task.metadata?.current_stage}
                />
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {formatDate(task.created_at)}
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {formatDate(task.updated_at)}
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {task.completed_at ? formatDate(task.completed_at) : "-"}
              </TableCell>
              <TableCell className="text-right">
                <div className="flex items-center justify-end gap-2">
                  {onViewDetails && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onViewDetails(task.id)}
                      className="h-8"
                    >
                      <Eye className="h-3.5 w-3.5 mr-1.5" />
                      View
                    </Button>
                  )}
                  {task.status === "SUCCESS" && task.result_ref && onViewResult && (
                    <Button
                      variant="default"
                      size="sm"
                      onClick={() => onViewResult(task.id, task.result_ref!)}
                      className="h-8"
                    >
                      <ExternalLink className="h-3.5 w-3.5 mr-1.5" />
                      View Result
                    </Button>
                  )}
                  {onDelete && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => onDelete(task.id)}
                      className="h-8 border-red-200 text-red-600 hover:bg-red-50 hover:text-red-700 hover:border-red-300 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-950 dark:hover:text-red-300 dark:hover:border-red-700"
                    >
                      <Trash2 className="h-3.5 w-3.5 mr-1.5" />
                      Delete
                    </Button>
                  )}
                </div>
                {task.status === "FAILED" && task.error_message && (
                  <div className="text-xs text-red-600 dark:text-red-400 max-w-xs truncate mt-2 text-right">
                    {task.error_message}
                  </div>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}

