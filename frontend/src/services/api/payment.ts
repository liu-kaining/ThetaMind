import apiClient from "./client"

export interface CheckoutResponse {
  checkout_url: string
  checkout_id: string
}

export interface CustomerPortalResponse {
  portal_url: string
}

export interface PricingResponse {
  monthly_price: number
  yearly_price: number
}

export const paymentService = {
  /**
   * Get subscription pricing information
   */
  getPricing: async (): Promise<PricingResponse> => {
    const response = await apiClient.get<PricingResponse>(
      "/api/v1/payment/pricing"
    )
    return response.data
  },

  /**
   * Create checkout session for Pro subscription
   * @param variantType - "monthly" or "yearly" (default: "monthly")
   */
  createCheckoutSession: async (variantType: string = "monthly"): Promise<CheckoutResponse> => {
    const response = await apiClient.post<CheckoutResponse>(
      "/api/v1/payment/checkout",
      { variant_type: variantType }
    )
    return response.data
  },

  /**
   * Get customer portal URL for subscription management
   */
  getCustomerPortal: async (): Promise<CustomerPortalResponse> => {
    const response = await apiClient.get<CustomerPortalResponse>(
      "/api/v1/payment/portal"
    )
    return response.data
  },
}

