import axios from "axios"
import { toast } from "sonner"

// Determine API base URL:
// 1. If VITE_API_URL is explicitly set, use it
// 2. In browser: use relative path /api (works with Nginx proxy at /api)
// 3. In Node/SSR: fallback to localhost:5300
const API_BASE_URL = import.meta.env.VITE_API_URL || 
  (typeof window !== 'undefined' ? '/api' : 'http://localhost:5300')

// Create axios instance
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
})

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token")
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle errors
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      if (error.response.status === 401) {
        // Unauthorized - clear token and redirect to login
        localStorage.removeItem("access_token")
        window.location.href = "/login"
      } else if (error.response.status >= 500) {
        // Server Error
        toast.error(`Server Error (${error.response.status}): ${error.response.data?.detail || "Please try again later."}`)
      }
    } else if (error.request) {
      // The request was made but no response was received
      toast.error("Network Error: Could not connect to the server. Please check your internet connection.")
    } else {
      // Something happened in setting up the request that triggered an Error
      toast.error(`Request Error: ${error.message}`)
    }
    return Promise.reject(error)
  }
)

export default apiClient

