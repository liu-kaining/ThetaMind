import apiClient from "./client"

export interface CompanyDataQuota {
  used: number
  limit: number
  is_pro: boolean
}

export interface CompanyDataSearchItem {
  symbol: string
  name: string
  exchange?: string
  type?: string
}

export interface CompanyDataFullResponse {
  overview?: {
    profile: Record<string, unknown>
    quote: Record<string, unknown>
    stock_price_change: Record<string, unknown>
    market_capitalization: Record<string, unknown>
    shares_float: Record<string, unknown>
    peers: string[]
    /** Next earnings (FMP earnings-calendar); date, epsEstimated, etc. */
    next_earnings?: Record<string, unknown> | null
  }
  valuation?: {
    dcf: Record<string, unknown>
    levered_dcf: Record<string, unknown>
    enterprise_values: unknown[]
  }
  ratios?: {
    key_metrics_ttm: Record<string, unknown>
    ratios_ttm: Record<string, unknown>
    financial_scores: Record<string, unknown>
    owner_earnings: Record<string, unknown>
  }
  analyst?: {
    analyst_estimates: unknown[]
    price_target_summary: Record<string, unknown>
    price_target_consensus: Record<string, unknown>
    grades_consensus: Record<string, unknown>
    ratings_snapshot: Record<string, unknown>
  }
  charts?: {
    historical_eod: Array<{ date?: string; close?: number; volume?: number }>
  }
}

const BASE = "/api/v1/company-data"

export const companyDataApi = {
  getQuota: async (): Promise<CompanyDataQuota> => {
    const { data } = await apiClient.get<CompanyDataQuota>(`${BASE}/quota`)
    return data
  },

  search: async (q: string, limit = 10): Promise<CompanyDataSearchItem[]> => {
    if (!q?.trim()) return []
    const { data } = await apiClient.get<CompanyDataSearchItem[]>(`${BASE}/search`, {
      params: { q: q.trim(), limit },
    })
    return data
  },

  getOverview: async (symbol: string): Promise<CompanyDataFullResponse["overview"]> => {
    const { data } = await apiClient.get(`${BASE}/overview`, {
      params: { symbol: symbol.trim().toUpperCase() },
    })
    return data
  },

  getFull: async (
    symbol: string,
    modules = "overview,valuation,ratios,analyst,charts"
  ): Promise<CompanyDataFullResponse> => {
    const { data } = await apiClient.get<CompanyDataFullResponse>(`${BASE}/full`, {
      params: { symbol: symbol.trim().toUpperCase(), modules },
    })
    return data
  },

  getModule: async (
    symbol: string,
    moduleId: "overview" | "valuation" | "ratios" | "analyst" | "charts"
  ): Promise<Record<string, unknown>> => {
    const { data } = await apiClient.get(`${BASE}/module/${moduleId}`, {
      params: { symbol: symbol.trim().toUpperCase() },
    })
    return data
  },

  /** Stock news. Does not consume quota. */
  getNews: async (symbol: string, limit = 5): Promise<CompanyDataNewsItem[]> => {
    const { data } = await apiClient.get<CompanyDataNewsItem[]>(`${BASE}/news`, {
      params: { symbol: symbol.trim().toUpperCase(), limit },
    })
    return data ?? []
  },

  /** Earnings, dividends, splits calendar. Does not consume quota. */
  getCalendar: async (symbol: string): Promise<CompanyDataCalendarResponse> => {
    const { data } = await apiClient.get<CompanyDataCalendarResponse>(`${BASE}/calendar`, {
      params: { symbol: symbol.trim().toUpperCase() },
    })
    return data ?? { events: [] }
  },

  /** Income, balance sheet, cash flow. Consumes quota. */
  getStatements: async (
    symbol: string,
    period: "annual" | "quarter" = "annual",
    limit = 5
  ): Promise<CompanyDataStatementsResponse> => {
    const { data } = await apiClient.get<CompanyDataStatementsResponse>(`${BASE}/statements`, {
      params: { symbol: symbol.trim().toUpperCase(), period, limit },
    })
    return data ?? { income: [], balance: [], cashflow: [] }
  },

  /** SEC filings. Does not consume quota. */
  getSecFilings: async (symbol: string, limit = 20): Promise<CompanyDataSecFilingItem[]> => {
    const { data } = await apiClient.get<CompanyDataSecFilingItem[]>(`${BASE}/sec-filings`, {
      params: { symbol: symbol.trim().toUpperCase(), limit },
    })
    return data ?? []
  },

  /** Insider trading. Does not consume quota. */
  getInsider: async (symbol: string, limit = 20): Promise<CompanyDataInsiderItem[]> => {
    const { data } = await apiClient.get<CompanyDataInsiderItem[]>(`${BASE}/insider`, {
      params: { symbol: symbol.trim().toUpperCase(), limit },
    })
    return data ?? []
  },

  /** Key executives and compensation. Does not consume quota. */
  getGovernance: async (symbol: string): Promise<CompanyDataGovernanceResponse> => {
    const { data } = await apiClient.get<CompanyDataGovernanceResponse>(`${BASE}/governance`, {
      params: { symbol: symbol.trim().toUpperCase() },
    })
    return data ?? { executives: [], compensation: [] }
  },
}

export interface CompanyDataStatementsResponse {
  income: Record<string, unknown>[]
  balance: Record<string, unknown>[]
  cashflow: Record<string, unknown>[]
}

export interface CompanyDataSecFilingItem {
  type?: string
  fillingDate?: string
  date?: string
  link?: string
  finalLink?: string
  [key: string]: unknown
}

export interface CompanyDataInsiderItem {
  reportingName?: string
  transactionDate?: string
  transactionType?: string
  securitiesTransacted?: number
  price?: number
  [key: string]: unknown
}

export interface CompanyDataGovernanceResponse {
  executives: Record<string, unknown>[]
  compensation: Record<string, unknown>[]
}

export interface CompanyDataNewsItem {
  title?: string
  publishedDate?: string
  text?: string
  url?: string
  site?: string
  image?: string
  symbols?: string[]
}

export interface CompanyDataCalendarEvent {
  type: "earnings" | "dividend" | "split"
  date?: string
  symbol?: string
  [key: string]: unknown
}

export interface CompanyDataCalendarResponse {
  events: CompanyDataCalendarEvent[]
}
