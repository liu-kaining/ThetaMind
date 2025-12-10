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
    [key: string]: any
  }
  is_pro: boolean
}

export interface SymbolSearchResult {
  symbol: string
  name: string
  market: string
}

export const marketService = {
  /**
   * Get option chain for a symbol and expiration date
   */
  getOptionChain: async (
    symbol: string,
    expirationDate: string
  ): Promise<OptionChainResponse> => {
    const response = await apiClient.get<OptionChainResponse>(
      "/api/v1/market/chain",
      {
        params: {
          symbol: symbol.toUpperCase(),
          expiration_date: expirationDate,
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
    days = 30
  ): Promise<{
    symbol: string
    data: Array<{
      time: string
      open: number
      high: number
      low: number
      close: number
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
      }>
      _source?: string
    }>("/api/v1/market/historical", {
      params: {
        symbol: symbol.toUpperCase(),
        days,
      },
    })
    return response.data
  },
}

