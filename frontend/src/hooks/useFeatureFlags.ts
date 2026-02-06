import { useQuery } from "@tanstack/react-query"
import { configService } from "@/services/api/config"

/** Feature flags from backend (ENABLE_ANOMALY_RADAR, ENABLE_DAILY_PICKS). Default false when loading so UI stays hidden until enabled. */
export function useFeatureFlags() {
  const { data: features, isLoading } = useQuery({
    queryKey: ["featureFlags"],
    queryFn: () => configService.getFeatures(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
  return {
    anomaly_radar_enabled: features?.anomaly_radar_enabled ?? false,
    daily_picks_enabled: features?.daily_picks_enabled ?? false,
    isLoading,
  }
}
