import * as React from "react"
import { cn } from "@/lib/utils"

interface FlashEffectProps {
  value: number | string
  previousValue?: number | string
  className?: string
  formatValue?: (value: number | string) => string
}

/**
 * Flash Effect Component
 * Shows a flash animation (green/red) when value changes
 */
export const FlashEffect: React.FC<FlashEffectProps> = ({
  value,
  previousValue,
  className,
  formatValue,
}) => {
  const [isFlashing, setIsFlashing] = React.useState(false)
  const [flashColor, setFlashColor] = React.useState<"green" | "red" | null>(null)
  const prevValueRef = React.useRef(previousValue)

  React.useEffect(() => {
    // Only flash if value actually changed and both are numbers
    if (prevValueRef.current !== undefined && prevValueRef.current !== value) {
      const prevNum = typeof prevValueRef.current === "string" 
        ? parseFloat(prevValueRef.current) 
        : prevValueRef.current
      const currNum = typeof value === "string" 
        ? parseFloat(value) 
        : value

      if (!isNaN(prevNum) && !isNaN(currNum) && prevNum !== currNum) {
        // Determine flash color based on direction
        const color = currNum > prevNum ? "green" : "red"
        setFlashColor(color)
        setIsFlashing(true)

        // Reset after animation
        const timer = setTimeout(() => {
          setIsFlashing(false)
          setFlashColor(null)
        }, 600) // Animation duration

        return () => clearTimeout(timer)
      }
    }

    prevValueRef.current = value
  }, [value, previousValue])

  const displayValue = formatValue ? formatValue(value) : String(value)

  return (
    <span
      className={cn(
        "transition-all duration-300",
        isFlashing && flashColor === "green" && "text-emerald-500 animate-pulse",
        isFlashing && flashColor === "red" && "text-rose-500 animate-pulse",
        className
      )}
    >
      {displayValue}
    </span>
  )
}
