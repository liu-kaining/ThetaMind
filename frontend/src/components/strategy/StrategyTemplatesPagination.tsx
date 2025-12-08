import * as React from "react"
import { StrategyTemplate } from "@/lib/strategyTemplates"
import { StrategyTemplateCard } from "./StrategyTemplateCard"
import { Button } from "@/components/ui/button"
import { ChevronLeft, ChevronRight } from "lucide-react"

interface StrategyTemplatesPaginationProps {
  templates: StrategyTemplate[]
  onSelect: (templateId: string) => void
  disabled?: boolean
  templatesPerPage?: number
}

export const StrategyTemplatesPagination: React.FC<StrategyTemplatesPaginationProps> = ({
  templates,
  onSelect,
  disabled,
  templatesPerPage = 4,
}) => {
  const [currentPage, setCurrentPage] = React.useState(1)
  const totalPages = Math.ceil(templates.length / templatesPerPage)
  const startIndex = (currentPage - 1) * templatesPerPage
  const endIndex = startIndex + templatesPerPage
  const currentTemplates = templates.slice(startIndex, endIndex)

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2">
        {currentTemplates.map((template) => (
          <StrategyTemplateCard
            key={template.id}
            template={template}
            onSelect={() => onSelect(template.id)}
            disabled={disabled}
          />
        ))}
      </div>
      
      {totalPages > 1 && (
        <div className="flex items-center justify-between bg-muted/30 rounded-lg p-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage === 1}
            className="font-medium"
          >
            <ChevronLeft className="h-4 w-4 mr-1" />
            Previous
          </Button>
          <div className="text-sm font-medium text-foreground px-3 py-1 bg-background rounded-md">
            Page {currentPage} of {totalPages}
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage === totalPages}
            className="font-medium"
          >
            Next
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        </div>
      )}
    </div>
  )
}

