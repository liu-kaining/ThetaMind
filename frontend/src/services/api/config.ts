import apiClient from "./client"

export interface FeaturesResponse {
  anomaly_radar_enabled: boolean
  daily_picks_enabled: boolean
}

export const configService = {
  getFeatures: async (): Promise<FeaturesResponse> => {
    const response = await apiClient.get<FeaturesResponse>(
      "/api/v1/config/features"
    )
    return response.data
  },
}
