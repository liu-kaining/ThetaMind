import * as React from "react"
import { Navigate } from "react-router-dom"
import { useAuth } from "@/features/auth/AuthProvider"

interface AdminRouteProps {
  children: React.ReactNode
}

export const AdminRoute: React.FC<AdminRouteProps> = ({ children }) => {
  const { user, isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  // Check if user is superuser
  // Note: We need to add is_superuser to User interface
  if (!(user as any)?.is_superuser) {
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}

