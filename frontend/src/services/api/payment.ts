import apiClient from "./client"

export interface CheckoutResponse {
  checkout_url: string
  checkout_id: string
}

export interface CustomerPortalResponse {
  portal_url: string
}

export const paymentService = {
  /**
   * Create checkout session for Pro subscription
   */
  createCheckoutSession: async (): Promise<CheckoutResponse> => {
    const response = await apiClient.post<CheckoutResponse>(
      "/api/v1/payment/checkout"
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

