import * as React from "react"
import { ChevronRight, ChevronDown } from "lucide-react"

type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue }

interface JsonViewerProps {
  data: JsonValue
  defaultExpandedDepth?: number
  /** Collapse arrays longer than this by default (0 = no limit) */
  collapseArraysLongerThan?: number
}

const formatPrimitive = (value: JsonValue): string => {
  if (value === null) return "null"
  if (typeof value === "string") return `"${value}"`
  return String(value)
}

const isObject = (value: JsonValue): value is { [key: string]: JsonValue } =>
  typeof value === "object" && value !== null && !Array.isArray(value)

const PrimitiveValue: React.FC<{ value: JsonValue }> = ({ value }) => {
  const v = formatPrimitive(value)
  let colorClass = "text-foreground"
  if (value === null) colorClass = "text-muted-foreground italic"
  else if (typeof value === "string") colorClass = "text-emerald-600 dark:text-emerald-400"
  else if (typeof value === "number") colorClass = "text-blue-600 dark:text-blue-400"
  else if (typeof value === "boolean") colorClass = "text-amber-600 dark:text-amber-400"
  return <span className={`font-mono text-[13px] ${colorClass}`}>{v}</span>
}

const JsonNode: React.FC<{
  name?: string
  value: JsonValue
  depth: number
  defaultExpandedDepth: number
  collapseArraysLongerThan: number
}> = ({ name, value, depth, defaultExpandedDepth, collapseArraysLongerThan }) => {
  const padding = depth * 16
  const isArray = Array.isArray(value)
  const isObj = isObject(value)

  if (!isArray && !isObj) {
    return (
      <div
        style={{ paddingLeft: padding }}
        className="flex items-baseline gap-1.5 py-0.5 text-[13px] hover:bg-muted/30 rounded px-1 -mx-1 transition-colors"
      >
        {name !== undefined && (
          <span className="text-primary font-medium shrink-0">{name}:</span>
        )}
        <PrimitiveValue value={value} />
      </div>
    )
  }

  const entries = isArray ? value.map((item, index) => [String(index), item]) : Object.entries(value)
  const count = entries.length
  const label = isArray ? `Array(${count})` : `Object(${count})`
  const forceCollapsed =
    isArray &&
    collapseArraysLongerThan > 0 &&
    count > collapseArraysLongerThan &&
    depth >= defaultExpandedDepth
  const [open, setOpen] = React.useState(
    !forceCollapsed && depth < defaultExpandedDepth
  )

  return (
    <div className="rounded">
      <button
        type="button"
        style={{ paddingLeft: padding }}
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 w-full text-left py-0.5 hover:bg-muted/40 rounded px-1 -mx-1 transition-colors group"
      >
        {open ? (
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
        )}
        {name !== undefined && (
          <span className="text-primary font-medium shrink-0">{name}:</span>
        )}
        <span className="text-muted-foreground font-mono text-[13px]">{label}</span>
      </button>
      {open && (
        <div className="mt-0.5 ml-2 border-l border-border/60 pl-2 space-y-0.5">
          {entries.map(([key, child]) => (
            <JsonNode
              key={`${name ?? "root"}-${key}`}
              name={isArray ? undefined : String(key)}
              value={child as JsonValue}
              depth={depth + 1}
              defaultExpandedDepth={defaultExpandedDepth}
              collapseArraysLongerThan={collapseArraysLongerThan}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export const JsonViewer: React.FC<JsonViewerProps> = ({
  data,
  defaultExpandedDepth = 1,
  collapseArraysLongerThan = 20,
}) => {
  return (
    <div className="rounded-lg border border-border bg-card/50 dark:bg-card/30 p-4 max-h-[500px] overflow-auto font-sans">
      <JsonNode
        value={data}
        depth={0}
        defaultExpandedDepth={defaultExpandedDepth}
        collapseArraysLongerThan={collapseArraysLongerThan}
      />
    </div>
  )
}
