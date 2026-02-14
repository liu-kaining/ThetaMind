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
}
