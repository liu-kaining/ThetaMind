import apiClient from "./client"

export interface UserMeResponse {
  id: string
  email: string
  is_pro: boolean
  is_superuser: boolean
  subscription_id: string | null
  plan_expiry_date: string | null
  daily_ai_usage: number
  daily_ai_quota: number
  created_at: string
}

export const authApi = {
  /**
   * Get current user information
   */
  getMe: async (): Promise<UserMeResponse> => {
    const response = await apiClient.get<UserMeResponse>("/api/v1/auth/me")
    return response.data
  },
}
