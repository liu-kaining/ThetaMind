import * as React from "react"
import { useState, useEffect, useRef } from "react"
import { useQuery } from "@tanstack/react-query"
import { Search, Loader2 } from "lucide-react"
import { Input } from "@/components/ui/input"
import { marketService, SymbolSearchResult } from "@/services/api/market"
import { cn } from "@/lib/utils"

interface SymbolSearchProps {
  onSelect: (symbol: string, name: string) => void
  value?: string
  className?: string
  placeholder?: string
}

export const SymbolSearch: React.FC<SymbolSearchProps> = ({
  onSelect,
  value = "",
  className,
  placeholder = "Search symbol (e.g., AAPL, TSLA)...",
}) => {
  const [query, setQuery] = useState(value)
  const [isOpen, setIsOpen] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Debounce search query
  const [debouncedQuery, setDebouncedQuery] = useState(query)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query)
    }, 300) // 300ms debounce

    return () => clearTimeout(timer)
  }, [query])

  // Fetch search results
  const { data: results = [], isLoading } = useQuery({
    queryKey: ["symbolSearch", debouncedQuery],
    queryFn: () => marketService.searchSymbols(debouncedQuery, 10),
    enabled: debouncedQuery.length >= 1,
  })

  // Show dropdown when there are results or query is being typed
  useEffect(() => {
    setIsOpen(results.length > 0 && debouncedQuery.length >= 1)
  }, [results, debouncedQuery])

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen || results.length === 0) return

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault()
        setSelectedIndex((prev) => (prev < results.length - 1 ? prev + 1 : prev))
        break
      case "ArrowUp":
        e.preventDefault()
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1))
        break
      case "Enter":
        e.preventDefault()
        if (selectedIndex >= 0 && selectedIndex < results.length) {
          handleSelect(results[selectedIndex])
        } else if (results.length > 0) {
          handleSelect(results[0])
        }
        break
      case "Escape":
        setIsOpen(false)
        setSelectedIndex(-1)
        break
    }
  }

  const handleSelect = (result: SymbolSearchResult) => {
    onSelect(result.symbol, result.name)
    setQuery(result.symbol)
    setIsOpen(false)
    setSelectedIndex(-1)
    inputRef.current?.blur()
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setQuery(e.target.value)
    setSelectedIndex(-1)
  }

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false)
      }
    }

    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  return (
    <div ref={containerRef} className={cn("relative w-full", className)}>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          ref={inputRef}
          type="text"
          placeholder={placeholder}
          value={query}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (results.length > 0 && query.length >= 1) {
              setIsOpen(true)
            }
          }}
          className="pl-10"
        />
        {isLoading && (
          <Loader2 className="absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-muted-foreground" />
        )}
      </div>

      {/* Dropdown Results */}
      {isOpen && results.length > 0 && (
        <div className="absolute z-50 mt-1 w-full rounded-md border bg-popover shadow-md">
          <div className="max-h-60 overflow-auto p-1">
            {results.map((result, index) => (
              <div
                key={result.symbol}
                onClick={() => handleSelect(result)}
                className={cn(
                  "flex cursor-pointer items-center justify-between rounded-sm px-3 py-2 text-sm transition-colors",
                  index === selectedIndex
                    ? "bg-accent text-accent-foreground"
                    : "hover:bg-accent hover:text-accent-foreground"
                )}
              >
                <div className="flex flex-col">
                  <span className="font-medium">{result.symbol}</span>
                  <span className="text-xs text-muted-foreground">
                    {result.name}
                  </span>
                </div>
                <span className="text-xs text-muted-foreground">
                  {result.market}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No results message */}
      {isOpen && !isLoading && debouncedQuery.length >= 1 && results.length === 0 && (
        <div className="absolute z-50 mt-1 w-full rounded-md border bg-popover p-3 text-sm text-muted-foreground shadow-md">
          No symbols found for "{debouncedQuery}"
        </div>
      )}
    </div>
  )
}

