import apiClient from "./client"

export interface ConfigItem {
  key: string
  value: string
  description: string | null
}

export interface ConfigUpdateRequest {
  value: string
  description?: string | null
}

export interface UserResponse {
  id: string
  email: string
  is_pro: boolean
  is_superuser: boolean
  subscription_id: string | null
  plan_expiry_date: string | null
  daily_ai_usage: number
  created_at: string
  strategies_count: number
  ai_reports_count: number
}

export interface UserUpdateRequest {
  is_pro?: boolean
  is_superuser?: boolean
  plan_expiry_date?: string | null
  daily_ai_usage?: number
}

export const adminService = {
  /**
   * Get all system configurations
   */
  getAllConfigs: async (): Promise<ConfigItem[]> => {
    const response = await apiClient.get<ConfigItem[]>("/api/v1/admin/configs")
    return response.data
  },

  /**
   * Get a specific configuration
   */
  getConfig: async (key: string): Promise<ConfigItem> => {
    const response = await apiClient.get<ConfigItem>(`/api/v1/admin/configs/${key}`)
    return response.data
  },

  /**
   * Update a configuration
   */
  updateConfig: async (
    key: string,
    request: ConfigUpdateRequest
  ): Promise<ConfigItem> => {
    const response = await apiClient.put<ConfigItem>(
      `/api/v1/admin/configs/${key}`,
      request
    )
    return response.data
  },

  /**
   * Delete a configuration
   */
  deleteConfig: async (key: string): Promise<void> => {
    await apiClient.delete(`/api/v1/admin/configs/${key}`)
  },

  /**
   * Get all users with pagination and search
   */
  listUsers: async (
    limit: number = 50,
    offset: number = 0,
    search?: string
  ): Promise<UserResponse[]> => {
    const params: Record<string, string | number> = { limit, offset }
    if (search) {
      params.search = search
    }
    const response = await apiClient.get<UserResponse[]>("/api/v1/admin/users", {
      params,
    })
    return response.data
  },

  /**
   * Get a specific user by ID
   */
  getUser: async (userId: string): Promise<UserResponse> => {
    const response = await apiClient.get<UserResponse>(`/api/v1/admin/users/${userId}`)
    return response.data
  },

  /**
   * Update a user
   */
  updateUser: async (
    userId: string,
    request: UserUpdateRequest
  ): Promise<UserResponse> => {
    const response = await apiClient.put<UserResponse>(
      `/api/v1/admin/users/${userId}`,
      request
    )
    return response.data
  },

  /**
   * Delete a user
   */
  deleteUser: async (userId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/admin/users/${userId}`)
  },
}

