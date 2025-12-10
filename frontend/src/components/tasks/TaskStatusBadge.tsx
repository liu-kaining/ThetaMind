import * as React from "react"
import { Loader2, CheckCircle2, XCircle, Clock } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

export type TaskStatus = "PENDING" | "PROCESSING" | "SUCCESS" | "FAILED"

interface TaskStatusBadgeProps {
  status: TaskStatus
  className?: string
}

export const TaskStatusBadge: React.FC<TaskStatusBadgeProps> = ({
  status,
  className,
}) => {
  const statusConfig = {
    PENDING: {
      label: "Pending",
      icon: Clock,
      variant: "secondary" as const,
      className: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
    },
    PROCESSING: {
      label: "Processing",
      icon: Loader2,
      variant: "default" as const,
      className: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    },
    SUCCESS: {
      label: "Success",
      icon: CheckCircle2,
      variant: "default" as const,
      className: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    },
    FAILED: {
      label: "Failed",
      icon: XCircle,
      variant: "destructive" as const,
      className: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
    },
  }

  const config = statusConfig[status]
  const Icon = config.icon
  const isSpinning = status === "PROCESSING"

  return (
    <Badge
      variant={config.variant}
      className={cn(
        "flex items-center gap-1.5 px-2 py-1",
        config.className,
        className
      )}
    >
      <Icon
        className={cn(
          "h-3 w-3",
          isSpinning && "animate-spin"
        )}
      />
      <span>{config.label}</span>
    </Badge>
  )
}

