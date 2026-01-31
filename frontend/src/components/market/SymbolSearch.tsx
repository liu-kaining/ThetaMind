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
  size?: "default" | "large"
}

export const SymbolSearch: React.FC<SymbolSearchProps> = ({
  onSelect,
  value = "",
  className,
  placeholder = "Search symbol (e.g., AAPL, TSLA)...",
  size = "default",
}) => {
  const [query, setQuery] = useState(value)
  const [isOpen, setIsOpen] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const inputRef = useRef<HTMLInputElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Debounce search query
  const [debouncedQuery, setDebouncedQuery] = useState(query)

  useEffect(() => {
    setQuery(value)
  }, [value])

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

  const isLarge = size === "large"
  
  return (
    <div ref={containerRef} className={cn("relative w-full", className)}>
      <div
        className={cn(
          "relative rounded-xl transition-all duration-200",
          isLarge && "border-2 border-primary/30 bg-card shadow-md hover:border-primary/50 hover:shadow-lg focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20 focus-within:shadow-lg"
        )}
      >
        <Search
          className={cn(
            "absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors",
            isLarge ? "h-5 w-5 left-4 text-primary/70" : "h-4 w-4"
          )}
        />
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
          className={cn(
            "focus-visible:ring-0 focus-visible:ring-offset-0",
            isLarge
              ? "h-14 text-lg pl-12 pr-12 border-0 bg-transparent shadow-none placeholder:text-muted-foreground/80"
              : "pl-10"
          )}
        />
        {isLoading && (
          <Loader2 className={cn(
            "absolute right-3 top-1/2 -translate-y-1/2 animate-spin text-muted-foreground",
            isLarge ? "h-5 w-5 right-4" : "h-4 w-4"
          )} />
        )}
      </div>

      {/* Dropdown Results - Styled to match Select component */}
      {isOpen && results.length > 0 && (
        <div className="absolute z-50 mt-1 w-full min-w-[8rem] overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md animate-in fade-in-0 zoom-in-95">
          <div className="max-h-[300px] overflow-auto p-1">
            {results.map((result, index) => (
              <div
                key={result.symbol}
                onClick={() => handleSelect(result)}
                className={cn(
                  "relative flex w-full cursor-pointer select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-sm outline-none transition-colors",
                  index === selectedIndex
                    ? "bg-accent text-accent-foreground"
                    : "hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground"
                )}
              >
                <div className="flex flex-1 items-center justify-between">
                  <div className="flex flex-col">
                    <span className="font-medium">{result.symbol}</span>
                    <span className="text-xs text-muted-foreground">
                      {result.name}
                    </span>
                  </div>
                  <span className="text-xs text-muted-foreground ml-2">
                    {result.market}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No results message - Styled to match Select component */}
      {isOpen && !isLoading && debouncedQuery.length >= 1 && results.length === 0 && (
        <div className="absolute z-50 mt-1 w-full min-w-[8rem] overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md animate-in fade-in-0 zoom-in-95 p-3">
          <div className="text-sm text-muted-foreground">
            No symbols found for "{debouncedQuery}"
          </div>
        </div>
      )}
    </div>
  )
}

