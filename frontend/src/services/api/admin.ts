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
}

