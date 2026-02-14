import { useQuery } from "@tanstack/react-query"
import { configService } from "@/services/api/config"

/** Feature flags from backend. Nav/sidebar use this; refetch on mount so post-login we don't rely on stale cache. */
export function useFeatureFlags() {
  const { data: features, isLoading } = useQuery({
    queryKey: ["featureFlags"],
    queryFn: () => configService.getFeatures(),
    staleTime: 5 * 60 * 1000,
    refetchOnMount: "always", // Fresh flags when MainLayout mounts (e.g. right after login)
  })
  return {
    anomaly_radar_enabled: features?.anomaly_radar_enabled ?? false,
    daily_picks_enabled: features?.daily_picks_enabled ?? false,
    isLoading,
  }
}
