import * as React from "react"
import { useQuery } from "@tanstack/react-query"
import { AlertCircle, TrendingUp, Zap, Clock } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { marketService } from "@/services/api/market"
import { formatDistanceToNow } from "date-fns"

interface Anomaly {
  id: string
  symbol: string
  anomaly_type: string
  score: number
  details: Record<string, any>
  ai_insight: string | null
  detected_at: string
}

const getAnomalyIcon = (type: string) => {
  switch (type) {
    case "volume_surge":
      return <TrendingUp className="h-4 w-4" />
    case "iv_spike":
      return <Zap className="h-4 w-4" />
    default:
      return <AlertCircle className="h-4 w-4" />
  }
}

const getAnomalyColor = (score: number): "destructive" | "default" | "secondary" => {
  if (score > 50) return "destructive"
  if (score > 20) return "default"
  return "secondary"
}

const getAnomalyLabel = (type: string): string => {
  switch (type) {
    case "volume_surge":
      return "Volume Surge"
    case "iv_spike":
      return "IV Spike"
    case "unusual_activity":
      return "Unusual Activity"
    default:
      return type
  }
}

export const AnomalyRadar: React.FC = () => {
  const { data: anomalies, isLoading, refetch } = useQuery({
    queryKey: ["anomalies"],
    queryFn: () => marketService.getAnomalies(10, 1), // Last 1 hour, top 10
    refetchInterval: 5 * 60 * 1000, // Refetch every 5 minutes
  })

  React.useEffect(() => {
    // Refetch on mount and every 5 minutes
    const interval = setInterval(() => {
      refetch()
    }, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [refetch])

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            Anomaly Radar
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-16 w-full" />
          ))}
        </CardContent>
      </Card>
    )
  }

  if (!anomalies || anomalies.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            Anomaly Radar
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground text-center py-4">
            No anomalies detected
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          <AlertCircle className="h-4 w-4" />
          Anomaly Radar
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 max-h-[400px] overflow-y-auto">
        {anomalies.map((anomaly: Anomaly) => (
          <div
            key={anomaly.id}
            className="p-3 rounded-lg border border-border hover:bg-accent transition-colors cursor-pointer"
          >
            <div className="flex items-start justify-between gap-2 mb-2">
              <div className="flex items-center gap-2 flex-1">
                {getAnomalyIcon(anomaly.anomaly_type)}
                <span className="font-semibold text-sm">{anomaly.symbol}</span>
                <Badge
                  variant={getAnomalyColor(anomaly.score)}
                  className="text-xs"
                >
                  {getAnomalyLabel(anomaly.anomaly_type)}
                </Badge>
              </div>
              <div className="flex items-center gap-1 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                <span>
                  {formatDistanceToNow(new Date(anomaly.detected_at), {
                    addSuffix: true,
                  })}
                </span>
              </div>
            </div>

            {anomaly.details && (
              <div className="text-xs text-muted-foreground space-y-1 mb-2">
                {typeof anomaly.details.vol_oi_ratio === "number" && (
                  <div>
                    Vol/OI: {anomaly.details.vol_oi_ratio.toFixed(2)}
                  </div>
                )}
                {typeof anomaly.details.volume === "number" && (
                  <div>Volume: {anomaly.details.volume.toLocaleString()}</div>
                )}
                {typeof anomaly.details.iv === "number" && (
                  <div>IV: {(anomaly.details.iv * 100).toFixed(1)}%</div>
                )}
              </div>
            )}

            {anomaly.ai_insight && (
              <div className="text-xs bg-primary/10 p-2 rounded mt-2">
                <span className="font-medium">AI Insight: </span>
                <span className="text-muted-foreground">{anomaly.ai_insight}</span>
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
