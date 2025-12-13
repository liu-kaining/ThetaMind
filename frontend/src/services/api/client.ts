import axios from "axios"

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
    if (error.response?.status === 401) {
      // Unauthorized - clear token and redirect to login
      localStorage.removeItem("access_token")
      window.location.href = "/login"
    }
    return Promise.reject(error)
  }
)

export default apiClient

