import apiClient from "../client"

export interface StrategyLeg {
  type: "call" | "put"
  action: "buy" | "sell"
  strike: number
  quantity: number
  expiry: string
  premium?: number
}

export interface StrategyRequest {
  name: string
  legs_json: {
    symbol: string
    legs: StrategyLeg[]
    [key: string]: any
  }
}

export interface StrategyResponse {
  id: string
  name: string
  legs_json: {
    symbol: string
    legs: StrategyLeg[]
    [key: string]: any
  }
  created_at: string
}

export const strategyService = {
  /**
   * Create a new strategy
   */
  create: async (strategy: StrategyRequest): Promise<StrategyResponse> => {
    const response = await apiClient.post<StrategyResponse>(
      "/api/v1/strategies",
      strategy
    )
    return response.data
  },

  /**
   * Get all strategies for current user
   */
  list: async (limit = 10, offset = 0): Promise<StrategyResponse[]> => {
    const response = await apiClient.get<StrategyResponse[]>(
      "/api/v1/strategies",
      {
        params: { limit, offset },
      }
    )
    return response.data
  },

  /**
   * Get a specific strategy by ID
   */
  get: async (strategyId: string): Promise<StrategyResponse> => {
    const response = await apiClient.get<StrategyResponse>(
      `/api/v1/strategies/${strategyId}`
    )
    return response.data
  },

  /**
   * Update a strategy
   */
  update: async (
    strategyId: string,
    strategy: StrategyRequest
  ): Promise<StrategyResponse> => {
    const response = await apiClient.put<StrategyResponse>(
      `/api/v1/strategies/${strategyId}`,
      strategy
    )
    return response.data
  },

  /**
   * Delete a strategy
   */
  delete: async (strategyId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/strategies/${strategyId}`)
  },
}

