import apiClient from "./client"

export interface OptionChainResponse {
  symbol: string
  expiration_date: string
  calls: Array<{
    strike: number
    bid: number
    ask: number
    volume: number
    open_interest: number
    [key: string]: any
  }>
  puts: Array<{
    strike: number
    bid: number
    ask: number
    volume: number
    open_interest: number
    [key: string]: any
  }>
  spot_price: number
  _source?: string
}

export interface StockQuoteResponse {
  symbol: string
  data: {
    price?: number
    change?: number
    change_percent?: number
    volume?: number
    error?: string
    [key: string]: any
  }
  is_pro: boolean
  price_source?: "inferred" | "inference_failed" | "api"  // Removed "mock" - no longer used
}

export interface SymbolSearchResult {
  symbol: string
  name: string
  market: string
}

export interface FinancialProfileResponse {
  ticker: string
  error?: string
  ratios?: Record<string, Record<string, Record<string, number | null>>>
  technical_indicators?: Record<string, Record<string, Record<string, number | null>>>
  valuation?: {
    dcf?: { value?: number | null }
    ddm?: { value?: number | null }
  }
  analysis?: {
    health_score?: { overall?: number | null; category?: string | null }
    risk_score?: Record<string, any>
    technical_signals?: Record<string, string>
    warnings?: string[]
  }
  profile?: Record<string, any>
  // Extended fields from full profile API
  risk_metrics?: Record<string, any>
  performance_metrics?: Record<string, any>
  financial_statements?: Record<string, any>
  dupont_analysis?: { standard?: any; extended?: any }
}

export const marketService = {
  /**
   * Get option chain for a symbol and expiration date
   */
  getOptionChain: async (
    symbol: string,
    expirationDate: string,
    forceRefresh = false
  ): Promise<OptionChainResponse> => {
    const response = await apiClient.get<OptionChainResponse>(
      "/api/v1/market/chain",
      {
        params: {
          symbol: symbol.toUpperCase(),
          expiration_date: expirationDate,
          force_refresh: forceRefresh,
        },
      }
    )
    return response.data
  },

  /**
   * Get stock quote/brief information
   */
  getStockQuote: async (symbol: string): Promise<StockQuoteResponse> => {
    const response = await apiClient.get<StockQuoteResponse>(
      "/api/v1/market/quote",
      {
        params: {
          symbol: symbol.toUpperCase(),
        },
      }
    )
    return response.data
  },

  /**
   * Search stock symbols by symbol or company name
   */
  searchSymbols: async (query: string, limit = 10): Promise<SymbolSearchResult[]> => {
    if (!query || query.trim().length < 1) {
      return []
    }
    const response = await apiClient.get<SymbolSearchResult[]>(
      "/api/v1/market/search",
      {
        params: {
          q: query.trim(),
          limit,
        },
      }
    )
    return response.data
  },

  /**
   * Get historical candlestick data for a symbol
   */
  getHistoricalData: async (
    symbol: string,
    limit = 500,
    period: "day" | "week" | "month" = "day"
  ): Promise<{
    symbol: string
    data: Array<{
      time: string
      open: number
      high: number
      low: number
      close: number
      volume?: number
    }>
    _source?: string
  }> => {
    const response = await apiClient.get<{
      symbol: string
      data: Array<{
        time: string
        open: number
        high: number
        low: number
        close: number
        volume?: number
      }>
      _source?: string
    }>("/api/v1/market/history", {
      params: {
        symbol: symbol.toUpperCase(),
        limit,
        period,
      },
    })
    return response.data
  },

  /**
   * Get available option expiration dates for a symbol
   */
  getOptionExpirations: async (symbol: string): Promise<string[]> => {
    const response = await apiClient.get<string[]>("/api/v1/market/expirations", {
      params: {
        symbol: symbol.toUpperCase(),
      },
    })
    return response.data
  },

  /**
   * Get financial profile (fundamental + technical data)
   */
  getFinancialProfile: async (symbol: string): Promise<FinancialProfileResponse> => {
    const response = await apiClient.get<FinancialProfileResponse>("/api/v1/market/profile", {
      params: {
        symbol: symbol.toUpperCase(),
      },
    })
    return response.data
  },

  /**
   * Get market scanner results for discovery
   */
  getMarketScanner: async (
    criteria: "high_iv" | "top_gainers" | "most_active" | "top_losers" | "high_volume",
    options?: {
      marketValueMin?: number
      volumeMin?: number
      limit?: number
    }
  ): Promise<{
    criteria: string
    count: number
    stocks: Array<{
      symbol: string
      name: string
      price?: number
      change?: number
      change_percent?: number
      volume?: number
      market_value?: number
    }>
  }> => {
    const response = await apiClient.post<{
      criteria: string
      count: number
      stocks: Array<{
        symbol: string
        name: string
        price?: number
        change?: number
        change_percent?: number
        volume?: number
        market_value?: number
      }>
    }>("/api/v1/market/scanner", null, {
      params: {
        criteria,
        ...(options?.marketValueMin && { market_value_min: options.marketValueMin }),
        ...(options?.volumeMin && { volume_min: options.volumeMin }),
        ...(options?.limit && { limit: options.limit }),
      },
    })
    return response.data
  },

  /**
   * Get recent option anomalies (Anomaly Radar)
   */
  getAnomalies: async (
    limit = 20,
    hours = 1
  ): Promise<Array<{
    id: string
    symbol: string
    anomaly_type: string
    score: number
    details: Record<string, any>
    ai_insight: string | null
    detected_at: string
  }>> => {
    const response = await apiClient.get<
      Array<{
        id: string
        symbol: string
        anomaly_type: string
        score: number
        details: Record<string, any>
        ai_insight: string | null
        detected_at: string
      }>
    >("/api/v1/market/anomalies", {
      params: {
        limit,
        hours,
      },
    })
    return response.data
  },
}

