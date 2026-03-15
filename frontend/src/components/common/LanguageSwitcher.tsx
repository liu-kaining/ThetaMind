import * as React from "react"
import { useLanguage, type ReportLocale } from "@/contexts/LanguageContext"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Languages } from "lucide-react"

const LOCALES: { value: ReportLocale; label: string }[] = [
  { value: "zh-CN", label: "中文" },
  { value: "en-US", label: "English" },
]

export function LanguageSwitcher() {
  const { reportLocale, setReportLocale } = useLanguage()
  const currentLabel = LOCALES.find((l) => l.value === reportLocale)?.label ?? "English"
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" title={currentLabel}>
          <Languages className="h-5 w-5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {LOCALES.map(({ value, label }) => (
          <DropdownMenuItem
            key={value}
            onClick={() => setReportLocale(value)}
            className={reportLocale === value ? "bg-accent" : undefined}
          >
            {label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
