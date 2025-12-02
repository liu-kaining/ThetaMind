import React, { createContext, useContext, useEffect, useState } from "react"
import { authApi } from "@/services/api/auth"
import apiClient from "@/services/api/client"
import { toast } from "sonner"

interface User {
  id: string
  email: string
  name?: string
  picture?: string
  is_pro: boolean
  is_superuser?: boolean
}

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (token: string) => Promise<void>
  logout: () => void
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

  // Check for existing token on mount
  useEffect(() => {
    const token = localStorage.getItem("access_token")
    if (token) {
      // Token exists, but we don't validate it here
      // It will be validated on first API call
      setIsLoading(false)
    } else {
      setIsLoading(false)
    }
  }, [])

  const login = async (googleToken: string) => {
    try {
      setIsLoading(true)
      const response = await authApi.authenticateWithGoogle(googleToken)
      
      // Store JWT token
      localStorage.setItem("access_token", response.access_token)
      
      // Set axios default header
      apiClient.defaults.headers.common["Authorization"] = `Bearer ${response.access_token}`
      
      // Decode token to get user info (basic decode, not verification)
      // In production, you might want to call a /me endpoint instead
      const tokenParts = response.access_token.split(".")
      if (tokenParts.length === 3) {
        try {
          const payload = JSON.parse(atob(tokenParts[1]))
          setUser({
            id: payload.sub,
            email: payload.email || "",
            is_pro: false, // Will be fetched from backend later
          })
        } catch (e) {
          console.error("Failed to decode token", e)
        }
      }
      
      toast.success("Successfully signed in!")
    } catch (error: any) {
      console.error("Login error:", error)
      toast.error(
        error.response?.data?.detail || "Failed to sign in. Please try again."
      )
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

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user || !!localStorage.getItem("access_token"),
    login,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

