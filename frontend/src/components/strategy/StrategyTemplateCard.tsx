import * as React from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Layers, TrendingUp, TrendingDown, Minus, Zap } from "lucide-react"
import { StrategyTemplate } from "@/lib/strategyTemplates"

interface StrategyTemplateCardProps {
  template: StrategyTemplate
  onSelect: () => void
  disabled?: boolean
}

const categoryIcons = {
  bullish: TrendingUp,
  bearish: TrendingDown,
  neutral: Minus,
  volatile: Zap,
}

const categoryColors = {
  bullish: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  bearish: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  neutral: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  volatile: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
}

export const StrategyTemplateCard: React.FC<StrategyTemplateCardProps> = ({
  template,
  onSelect,
  disabled,
}) => {
  const Icon = categoryIcons[template.category] || Layers

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <Icon className="h-5 w-5 text-muted-foreground" />
            <CardTitle className="text-base">{template.name}</CardTitle>
          </div>
          <Badge className={categoryColors[template.category]}>
            {template.category}
          </Badge>
        </div>
        <CardDescription className="text-sm mt-2">
          {template.description}
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-0">
        <Button
          onClick={onSelect}
          disabled={disabled}
          className="w-full font-semibold"
          variant="default"
          size="sm"
        >
          Load Template
        </Button>
      </CardContent>
    </Card>
  )
}

