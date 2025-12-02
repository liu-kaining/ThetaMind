import apiClient from "../client"
import { OptionChainResponse } from "./market"
import { StrategyLeg } from "./strategy"

export interface StrategyAnalysisRequest {
  strategy_data: {
    symbol: string
    legs: StrategyLeg[]
    [key: string]: any
  }
  option_chain: OptionChainResponse
}

export interface AIReportResponse {
  id: string
  report_content: string
  model_used: string
  created_at: string
}

export interface DailyPickResponse {
  date: string
  content_json: Array<{
    symbol: string
    strategy_name: string
    description: string
    legs: StrategyLeg[]
    [key: string]: any
  }>
  created_at: string
}

export const aiService = {
  /**
   * Generate AI analysis report for a strategy
   * Handles long-running requests with timeout
   */
  generateReport: async (
    request: StrategyAnalysisRequest
  ): Promise<AIReportResponse> => {
    const response = await apiClient.post<AIReportResponse>(
      "/api/v1/ai/report",
      request,
      {
        timeout: 60000, // 60 seconds timeout for long-running requests
      }
    )
    return response.data
  },

  /**
   * Get daily AI-generated strategy picks
   */
  getDailyPicks: async (date?: string): Promise<DailyPickResponse> => {
    const response = await apiClient.get<DailyPickResponse>(
      "/api/v1/ai/daily-picks",
      {
        params: date ? { date } : {},
      }
    )
    return response.data
  },

  /**
   * Get user's AI reports (paginated)
   */
  getReports: async (
    limit = 10,
    offset = 0
  ): Promise<AIReportResponse[]> => {
    const response = await apiClient.get<AIReportResponse[]>(
      "/api/v1/ai/reports",
      {
        params: { limit, offset },
      }
    )
    return response.data
  },
}

