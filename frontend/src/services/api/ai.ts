import apiClient from "./client"
import { OptionChainResponse } from "./market"
import { StrategyLeg } from "./strategy"

export interface StrategyAnalysisRequest {
  strategy_summary?: {
    symbol: string
    strategy_name: string
    spot_price: number
    expiration_date?: string
    legs: StrategyLeg[]
    portfolio_greeks?: any
    trade_execution?: any
    strategy_metrics?: any
    payoff_summary?: any
  }
  // Legacy format (for backward compatibility)
  strategy_data?: {
    symbol: string
    legs: StrategyLeg[]
    [key: string]: any
  }
  option_chain?: OptionChainResponse
}

export interface AIReportResponse {
  id: string
  report_content: string
  model_used: string
  created_at: string
}

export interface DailyPickItem {
  symbol: string
  strategy_type: string
  strategy: any
  outlook: "Bullish" | "Bearish" | "Neutral"
  risk_level: "Low" | "Medium" | "High"
  headline: string
  analysis: string
  risks: string
  target_price: string
  timeframe: string
  max_profit: number
  max_loss: number
  breakeven: number[]
  legs?: StrategyLeg[]
}

export interface DailyPickResponse {
  date: string
  content_json: DailyPickItem[]
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

  /**
   * Delete an AI report
   */
  deleteReport: async (reportId: string): Promise<void> => {
    await apiClient.delete(`/api/v1/ai/reports/${reportId}`)
  },

  /**
   * Generate AI strategy chart image (Pro feature)
   * Returns either task_id (for new generation) or image_id (if cached)
   */
  generateChart: async (
    request: StrategyAnalysisRequest
  ): Promise<{ task_id?: string | null; image_id?: string | null; cached?: boolean }> => {
    const response = await apiClient.post<{ task_id?: string | null; image_id?: string | null; cached?: boolean }>(
      "/api/v1/ai/chart",
      request
    )
    return response.data
  },

  /**
   * Get strategy chart image R2 URL
   * Returns the R2 URL for direct image display (no blob download needed)
   */
  getChartImageUrl: async (imageId: string): Promise<string | null> => {
    const response = await apiClient.get<{ r2_url?: string | null; image_id?: string }>(
      `/api/v1/ai/chart/info/${imageId}`
    )
    const r2_url = response.data.r2_url
    if (!r2_url) {
      return null
    }
    // Ensure URL has https:// prefix
    if (!r2_url.startsWith("http://") && !r2_url.startsWith("https://")) {
      return `https://${r2_url}`
    }
    return r2_url
  },

  /**
   * Get existing strategy chart image by strategy hash (for caching)
   * Returns image_id and r2_url if found, or null if not found
   */
  getChartImageByHash: async (strategyHash: string): Promise<{ image_id?: string | null; r2_url?: string | null }> => {
    const response = await apiClient.get<{ image_id?: string | null; r2_url?: string | null }>(
      `/api/v1/ai/chart/by-hash/${strategyHash}`
    )
    return response.data
  },
}

