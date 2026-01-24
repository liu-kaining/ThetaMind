import * as React from "react"

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
}

const formatPrimitive = (value: JsonValue): string => {
  if (value === null) return "null"
  if (typeof value === "string") return `"${value}"`
  return String(value)
}

const isObject = (value: JsonValue): value is { [key: string]: JsonValue } =>
  typeof value === "object" && value !== null && !Array.isArray(value)

const JsonNode: React.FC<{
  name?: string
  value: JsonValue
  depth: number
  defaultExpandedDepth: number
}> = ({ name, value, depth, defaultExpandedDepth }) => {
  const padding = depth * 12
  const isArray = Array.isArray(value)
  const isObj = isObject(value)

  if (!isArray && !isObj) {
    return (
      <div style={{ paddingLeft: padding }} className="text-xs text-slate-700 dark:text-slate-300">
        {name !== undefined ? (
          <>
            <span className="text-slate-500">{name}: </span>
            <span className="font-mono">{formatPrimitive(value)}</span>
          </>
        ) : (
          <span className="font-mono">{formatPrimitive(value)}</span>
        )}
      </div>
    )
  }

  const entries = isArray ? value.map((item, index) => [String(index), item]) : Object.entries(value)
  const label = isArray ? `Array(${entries.length})` : `Object(${entries.length})`
  const open = depth < defaultExpandedDepth

  return (
    <details open={open} className="rounded-md">
      <summary
        style={{ paddingLeft: padding }}
        className="cursor-pointer select-none text-xs font-medium text-slate-800 dark:text-slate-200"
      >
        {name !== undefined ? `${name}: ` : ""}
        <span className="text-slate-500">{label}</span>
      </summary>
      <div className="mt-1 space-y-1">
        {entries.map(([key, child]) => (
          <JsonNode
            key={`${name ?? "root"}-${key}`}
            name={isArray ? undefined : String(key)}
            value={child as JsonValue}
            depth={depth + 1}
            defaultExpandedDepth={defaultExpandedDepth}
          />
        ))}
      </div>
    </details>
  )
}

export const JsonViewer: React.FC<JsonViewerProps> = ({
  data,
  defaultExpandedDepth = 1,
}) => {
  return (
    <div className="rounded-lg border border-border bg-slate-50 dark:bg-slate-900 p-3">
      <JsonNode value={data} depth={0} defaultExpandedDepth={defaultExpandedDepth} />
    </div>
  )
}
