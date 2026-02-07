import * as React from "react"
import { X } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "./button"

interface DialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  children: React.ReactNode
}

interface DialogContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode
}

const Dialog: React.FC<DialogProps> = ({ open, onOpenChange, children }) => {
  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      onClick={() => onOpenChange(false)}
    >
      <div
        className="fixed inset-0 bg-black/50"
        onClick={(e) => {
          e.stopPropagation()
          onOpenChange(false)
        }}
      />
      <div onClick={(e) => e.stopPropagation()}>{children}</div>
    </div>
  )
}

const DialogContent: React.FC<DialogContentProps> = ({
  className,
  children,
  ...props
}) => {
  return (
    <div
      className={cn(
        "relative z-50 w-full max-w-[95vw] sm:max-w-lg rounded-lg border bg-background p-4 sm:p-6 shadow-lg",
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
}

const DialogHeader: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  ...props
}) => {
  return (
    <div
      className={cn("flex flex-col space-y-1.5 text-center sm:text-left", className)}
      {...props}
    />
  )
}

const DialogTitle: React.FC<React.HTMLAttributes<HTMLHeadingElement>> = ({
  className,
  ...props
}) => {
  return (
    <h2
      className={cn("text-lg font-semibold leading-none tracking-tight", className)}
      {...props}
    />
  )
}

const DialogDescription: React.FC<React.HTMLAttributes<HTMLParagraphElement>> = ({
  className,
  ...props
}) => {
  return (
    <p className={cn("text-sm text-muted-foreground", className)} {...props} />
  )
}

const DialogClose: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  return (
    <Button
      variant="ghost"
      size="icon"
      className="absolute right-4 top-4"
      onClick={onClose}
    >
      <X className="h-4 w-4" />
    </Button>
  )
}

const DialogFooter: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({
  className,
  ...props
}) => {
  return (
    <div
      className={cn(
        "flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 mt-4",
        className
      )}
      {...props}
    />
  )
}

export {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogClose,
  DialogFooter,
}

