import * as React from "react"
import { Slider } from "@/components/ui/slider"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"

interface ScenarioSimulatorProps {
  currentPrice: number
  daysToExpiry: number | undefined
  onScenarioChange: (scenario: {
    priceChangePercent: number
    volatilityChangePercent: number
    daysRemaining: number
  }) => void
}

export const ScenarioSimulator: React.FC<ScenarioSimulatorProps> = ({
  currentPrice,
  daysToExpiry,
  onScenarioChange,
}) => {
  const [priceChangePercent, setPriceChangePercent] = React.useState(0)
  const [volatilityChangePercent, setVolatilityChangePercent] = React.useState(0)
  const [daysRemaining, setDaysRemaining] = React.useState(daysToExpiry || 30)

  // Update daysRemaining when daysToExpiry changes
  React.useEffect(() => {
    if (daysToExpiry !== undefined) {
      setDaysRemaining(daysToExpiry)
    }
  }, [daysToExpiry])

  // Notify parent of changes
  React.useEffect(() => {
    onScenarioChange({
      priceChangePercent,
      volatilityChangePercent,
      daysRemaining,
    })
  }, [priceChangePercent, volatilityChangePercent, daysRemaining, onScenarioChange])

  const handleReset = () => {
    setPriceChangePercent(0)
    setVolatilityChangePercent(0)
    if (daysToExpiry !== undefined) {
      setDaysRemaining(daysToExpiry)
    }
  }

  const simulatedPrice = currentPrice * (1 + priceChangePercent / 100)
  const simulatedVolatility = 0.25 * (1 + volatilityChangePercent / 100) // Base IV assumption

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">Scenario Simulator</CardTitle>
            <CardDescription className="text-xs">
              Adjust market conditions to see how they affect your strategy
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleReset}
            className="gap-1.5 h-8"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Reset
          </Button>
        </div>
      </CardHeader>
      <CardContent className="pt-0 space-y-4">
        {/* Price Change Slider */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="price-change" className="text-xs font-medium">
              Price Change
            </Label>
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-medium text-muted-foreground">
                ${currentPrice.toFixed(2)}
              </span>
              <span className="text-xs font-bold">
                {priceChangePercent > 0 ? "+" : ""}
                {priceChangePercent.toFixed(1)}%
              </span>
              <span className="text-xs font-medium">
                → ${simulatedPrice.toFixed(2)}
              </span>
            </div>
          </div>
          <Slider
            id="price-change"
            min={-20}
            max={20}
            step={0.5}
            value={[priceChangePercent]}
            onValueChange={(value) => setPriceChangePercent(value[0])}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-muted-foreground/70 px-1">
            <span>-20%</span>
            <span>0%</span>
            <span>+20%</span>
          </div>
        </div>

        {/* Volatility Change Slider */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="volatility-change" className="text-xs font-medium">
              Volatility Change (IV)
            </Label>
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-medium text-muted-foreground">
                25.0%
              </span>
              <span className="text-xs font-bold">
                {volatilityChangePercent > 0 ? "+" : ""}
                {volatilityChangePercent.toFixed(1)}%
              </span>
              <span className="text-xs font-medium">
                → {simulatedVolatility.toFixed(1)}%
              </span>
            </div>
          </div>
          <Slider
            id="volatility-change"
            min={-50}
            max={50}
            step={1}
            value={[volatilityChangePercent]}
            onValueChange={(value) => setVolatilityChangePercent(value[0])}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-muted-foreground/70 px-1">
            <span>-50%</span>
            <span>0%</span>
            <span>+50%</span>
          </div>
        </div>

        {/* Time Decay Slider */}
        {daysToExpiry !== undefined && daysToExpiry > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="time-decay" className="text-xs font-medium">
                Time Decay (Days to Expiration)
              </Label>
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-medium text-muted-foreground">
                  {daysToExpiry} days
                </span>
                <span className="text-xs font-bold">
                  → {daysRemaining} days
                </span>
              </div>
            </div>
            <Slider
              id="time-decay"
              min={0}
              max={Math.max(daysToExpiry * 2, 365)} // Allow up to 2x expiry or 365 days, whichever is larger
              step={1}
              value={[daysRemaining]}
              onValueChange={(value) => setDaysRemaining(value[0])}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-muted-foreground/70 px-1">
              <span>Today</span>
              <span>{Math.floor(Math.max(daysToExpiry * 2, 365) / 2)} days</span>
              <span>{Math.max(daysToExpiry * 2, 365)} days</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

