import * as React from "react"
import { useQuery } from "@tanstack/react-query"
import { Calendar, TrendingUp } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { aiService } from "@/services/api/ai"
import { formatInTimeZone } from "date-fns-tz"

export const DailyPicks: React.FC = () => {
  const { data: dailyPicks, isLoading } = useQuery({
    queryKey: ["dailyPicks"],
    queryFn: () => aiService.getDailyPicks(),
  })

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Daily Picks</h1>
          <p className="text-muted-foreground">
            AI-generated strategy recommendations
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-32" />
                <Skeleton className="h-4 w-24" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (!dailyPicks || dailyPicks.content_json.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Daily Picks</h1>
          <p className="text-muted-foreground">
            AI-generated strategy recommendations
          </p>
        </div>
        <Card>
          <CardContent className="py-12 text-center">
            <Calendar className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <p className="text-muted-foreground">
              No daily picks available for today
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Format date in US/Eastern timezone
  const displayDate = dailyPicks.date
    ? formatInTimeZone(
        new Date(dailyPicks.date),
        "US/Eastern",
        "EEEE, MMMM d, yyyy"
      )
    : "Today"

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Daily Picks</h1>
        <p className="text-muted-foreground">
          AI-generated strategy recommendations for {displayDate}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {dailyPicks.content_json.map((pick, index) => (
          <Card key={index} className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle className="text-lg">{pick.strategy_name}</CardTitle>
                  <CardDescription className="mt-1">
                    {pick.symbol}
                  </CardDescription>
                </div>
                <TrendingUp className="h-5 w-5 text-primary" />
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                {pick.description}
              </p>

              {pick.legs && pick.legs.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-medium text-muted-foreground">
                    Strategy Legs:
                  </p>
                  <div className="space-y-1">
                    {pick.legs.map((leg: any, legIndex: number) => (
                      <div
                        key={legIndex}
                        className="text-xs bg-muted p-2 rounded flex items-center justify-between"
                      >
                        <span>
                          {leg.action === "buy" ? "Buy" : "Sell"} {leg.quantity}x{" "}
                          {leg.type === "call" ? "Call" : "Put"}
                        </span>
                        <span className="font-medium">
                          ${leg.strike?.toFixed(2) || "N/A"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

