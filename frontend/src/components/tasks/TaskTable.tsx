import * as React from "react"
import { format } from "date-fns"
import { ExternalLink } from "lucide-react"
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
  onViewResult?: (taskId: string, resultRef: string) => void
}

export const TaskTable: React.FC<TaskTableProps> = ({
  tasks,
  onViewResult,
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
      daily_picks: "Daily Picks",
      strategy_analysis: "Strategy Analysis",
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
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Type</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Created</TableHead>
            <TableHead>Updated</TableHead>
            <TableHead>Completed</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {tasks.map((task) => (
            <TableRow key={task.id}>
              <TableCell className="font-medium">
                {getTaskTypeLabel(task.task_type)}
              </TableCell>
              <TableCell>
                <TaskStatusBadge status={task.status as TaskStatus} />
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
                {task.status === "SUCCESS" && task.result_ref && onViewResult && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onViewResult(task.id, task.result_ref!)}
                  >
                    <ExternalLink className="h-4 w-4 mr-1" />
                    View Result
                  </Button>
                )}
                {task.status === "FAILED" && task.error_message && (
                  <div className="text-xs text-red-600 dark:text-red-400 max-w-xs truncate">
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

