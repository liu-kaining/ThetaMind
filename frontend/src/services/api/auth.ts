import apiClient from "./client"

export interface GoogleTokenRequest {
  token: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export const authApi = {
  /**
   * Authenticate with Google OAuth2 token
   */
  authenticateWithGoogle: async (token: string): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>(
      "/api/v1/auth/google",
      { token }
    )
    return response.data
  },
}

