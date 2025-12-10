import * as React from "react"
import { X, Copy, Check } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { StrategyLeg } from "@/services/api/strategy"

interface TradeCheatSheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  symbol: string
  expirationDate: string
  legs: StrategyLeg[]
}

export const TradeCheatSheet: React.FC<TradeCheatSheetProps> = ({
  open,
  onOpenChange,
  symbol,
  expirationDate,
  legs,
}) => {
  const [copiedIndex, setCopiedIndex] = React.useState<number | null>(null)

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString)
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    } catch {
      return dateString
    }
  }

  const copyToClipboard = async (text: string, index: number) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedIndex(index)
      setTimeout(() => setCopiedIndex(null), 2000)
    } catch (error) {
      console.error("Failed to copy:", error)
    }
  }

  if (legs.length === 0) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-3xl">Trade Cheat Sheet</DialogTitle>
          </DialogHeader>
          <div className="text-center py-12 text-muted-foreground text-xl">
            Add option legs to generate cheat sheet
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl max-h-[95vh] overflow-y-auto p-0">
        <DialogHeader className="p-6 pb-4 border-b">
          <div className="flex items-center justify-between">
            <DialogTitle className="text-4xl font-bold">Trade Cheat Sheet</DialogTitle>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onOpenChange(false)}
              className="h-10 w-10"
            >
              <X className="h-6 w-6" />
            </Button>
          </div>
        </DialogHeader>
        
        <div className="p-8 space-y-8">
          {/* Header Info */}
          <div className="text-center space-y-4 pb-6 border-b-2 border-dashed">
            <div className="text-6xl font-bold">{symbol}</div>
            <div className="text-3xl text-muted-foreground">
              Expiry: {formatDate(expirationDate)}
            </div>
          </div>

          {/* Legs */}
          {legs.map((leg, index) => {
            const actionText = leg.action === "buy" ? "BUY" : "SELL"
            const typeText = leg.type.toUpperCase()
            const strikeText = `$${leg.strike.toFixed(2)}`
            const quantityText = `${leg.quantity}x`
            const premiumText = leg.premium ? `$${leg.premium.toFixed(2)}` : "N/A"
            
            const fullText = `${actionText} ${quantityText} ${typeText} ${strikeText} @ ${premiumText}`

            return (
              <div
                key={index}
                className="p-8 border-4 border-primary rounded-2xl bg-card space-y-6"
              >
                <div className="flex items-center justify-between">
                  <div className="text-5xl font-bold text-primary">
                    Leg {index + 1}
                  </div>
                  <Button
                    variant="outline"
                    size="lg"
                    onClick={() => copyToClipboard(fullText, index)}
                    className="text-xl px-6 py-6"
                  >
                    {copiedIndex === index ? (
                      <>
                        <Check className="h-6 w-6 mr-2" />
                        Copied!
                      </>
                    ) : (
                      <>
                        <Copy className="h-6 w-6 mr-2" />
                        Copy
                      </>
                    )}
                  </Button>
                </div>

                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <div className="text-2xl font-semibold text-muted-foreground mb-2">
                        Symbol
                      </div>
                      <div className="text-7xl font-bold">{symbol}</div>
                    </div>
                    <div>
                      <div className="text-2xl font-semibold text-muted-foreground mb-2">
                        Expiry
                      </div>
                      <div className="text-5xl font-bold">
                        {formatDate(expirationDate)}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <div className="text-2xl font-semibold text-muted-foreground mb-2">
                        Action
                      </div>
                      <div className="text-7xl font-bold">
                        {actionText}
                      </div>
                    </div>
                    <div>
                      <div className="text-2xl font-semibold text-muted-foreground mb-2">
                        Quantity
                      </div>
                      <div className="text-7xl font-bold">{quantityText}</div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <div className="text-2xl font-semibold text-muted-foreground mb-2">
                        Type
                      </div>
                      <div className="text-7xl font-bold">{typeText}</div>
                    </div>
                    <div>
                      <div className="text-2xl font-semibold text-muted-foreground mb-2">
                        Strike
                      </div>
                      <div className="text-7xl font-bold">{strikeText}</div>
                    </div>
                  </div>

                  <div>
                    <div className="text-2xl font-semibold text-muted-foreground mb-2">
                      Limit Price
                    </div>
                    <div className="text-7xl font-bold">{premiumText}</div>
                  </div>
                </div>

                {/* Full Trade String */}
                <div className="pt-6 border-t-2 border-dashed">
                  <div className="text-2xl font-semibold text-muted-foreground mb-3">
                    Full Trade String
                  </div>
                  <div className="text-4xl font-mono font-bold bg-muted p-4 rounded-lg break-all">
                    {fullText}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </DialogContent>
    </Dialog>
  )
}

