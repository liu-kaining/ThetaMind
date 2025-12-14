import React, { createContext, useContext, useEffect, useState } from "react"
import apiClient from "@/services/api/client"
import { authApi } from "@/services/api/auth"
import { toast } from "sonner"

interface User {
  id: string
  email: string
  name?: string
  picture?: string
  is_pro: boolean
  is_superuser?: boolean
  subscription_type?: string | null
  daily_ai_usage?: number
  daily_ai_quota?: number
  daily_image_usage?: number
  daily_image_quota?: number
}

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (token: string) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider")
  }
  return context
}

interface AuthProviderProps {
  children: React.ReactNode
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Check for existing token on mount and fetch user info
  useEffect(() => {
    const loadUser = async () => {
      const token = localStorage.getItem("access_token")
      if (token) {
        // Set axios default header
        apiClient.defaults.headers.common["Authorization"] = `Bearer ${token}`
        // Fetch user information from /me endpoint
        try {
          const userData = await authApi.getMe()
          setUser({
            id: userData.id,
            email: userData.email,
            is_pro: userData.is_pro,
            is_superuser: userData.is_superuser,
            daily_ai_usage: userData.daily_ai_usage,
            daily_ai_quota: userData.daily_ai_quota,
            daily_image_usage: userData.daily_image_usage,
            daily_image_quota: userData.daily_image_quota,
            subscription_type: userData.subscription_type,
          })
        } catch (e) {
          console.error("Failed to fetch user info:", e)
          // If token is invalid, clear it
          localStorage.removeItem("access_token")
          delete apiClient.defaults.headers.common["Authorization"]
        }
      }
      setIsLoading(false)
    }
    loadUser()
  }, [])

  const login = async (googleToken: string) => {
    try {
      setIsLoading(true)
      // Call the backend login endpoint directly
      const response = await apiClient.post("/api/v1/auth/google", {
        token: googleToken,
      })
      
      // Store JWT token
      const accessToken = response.data.access_token
      if (!accessToken) {
        throw new Error("No access token received from server")
      }
      
      localStorage.setItem("access_token", accessToken)
      
      // Set axios default header
      apiClient.defaults.headers.common["Authorization"] = `Bearer ${accessToken}`
      
      // Decode token to get basic user info (don't call /me immediately to avoid errors)
      const tokenParts = accessToken.split(".")
      if (tokenParts.length === 3) {
        try {
          const payload = JSON.parse(atob(tokenParts[1]))
          setUser({
            id: payload.sub,
            email: payload.email || "",
            is_pro: false, // Will be updated when /me is called later
          })
        } catch (decodeError) {
          console.error("Failed to decode token", decodeError)
        }
      }
      
      // Fetch complete user information from /me endpoint asynchronously (don't block login)
      authApi.getMe()
        .then((userData) => {
          setUser({
            id: userData.id,
            email: userData.email,
            is_pro: userData.is_pro,
            is_superuser: userData.is_superuser,
            daily_ai_usage: userData.daily_ai_usage,
            daily_ai_quota: userData.daily_ai_quota,
            daily_image_usage: userData.daily_image_usage,
            daily_image_quota: userData.daily_image_quota,
            subscription_type: userData.subscription_type,
          })
        })
        .catch((e) => {
          console.warn("Failed to fetch user details, using token info:", e)
          // Don't show error to user - login was successful
        })
      
      toast.success("Successfully signed in!")
    } catch (error: any) {
      console.error("Login error:", error)
      const errorMessage = error.response?.data?.detail || error.message || "Failed to sign in. Please try again."
      toast.error(errorMessage)
      throw error
    } finally {
      setIsLoading(false)
    }
  }

  const logout = () => {
    localStorage.removeItem("access_token")
    delete apiClient.defaults.headers.common["Authorization"]
    setUser(null)
    toast.success("Signed out successfully")
  }

  const refreshUser = async () => {
    const token = localStorage.getItem("access_token")
    if (!token) return
    
    try {
      const userData = await authApi.getMe()
      setUser({
        id: userData.id,
        email: userData.email,
        is_pro: userData.is_pro,
        is_superuser: userData.is_superuser,
        daily_ai_usage: userData.daily_ai_usage,
        daily_ai_quota: userData.daily_ai_quota,
        daily_image_usage: userData.daily_image_usage,
        daily_image_quota: userData.daily_image_quota,
        subscription_type: userData.subscription_type,
      })
    } catch (e) {
      console.error("Failed to refresh user info:", e)
    }
  }

  const value: AuthContextType = {
    user,
    isLoading,
    // Only consider authenticated if we have a user object (token validation is done in useEffect)
    // If isLoading is true, we're still checking, so don't consider authenticated yet
    isAuthenticated: !isLoading && !!user,
    login,
    logout,
    refreshUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

