import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { GoogleOAuthProvider } from "@react-oauth/google"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Toaster } from "@/components/ui/toaster"
import { AuthProvider } from "@/features/auth/AuthProvider"
import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import { MainLayout } from "@/components/layout/MainLayout"
import { LoginPage } from "@/pages/LoginPage"
import { DashboardPage } from "@/pages/DashboardPage"
import { StrategyLab } from "@/pages/StrategyLab"
import { Pricing } from "@/pages/Pricing"
import { DailyPicks } from "@/pages/DailyPicks"
import { AdminSettings } from "@/pages/admin/AdminSettings"
import { AdminRoute } from "@/components/auth/AdminRoute"

// Create a client for React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

// Google OAuth Client ID - should be in .env file
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ""

function App() {
  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route
                path="/*"
                element={
                  <ProtectedRoute>
                    <MainLayout>
                      <Routes>
                        <Route path="/" element={<DashboardPage />} />
                        <Route path="/strategy-lab" element={<StrategyLab />} />
                        <Route path="/daily-picks" element={<DailyPicks />} />
                        <Route path="/pricing" element={<Pricing />} />
                        <Route path="/reports" element={<div>Reports (Coming Soon)</div>} />
                        <Route path="/settings" element={<div>Settings (Coming Soon)</div>} />
                        <Route
                          path="/admin/settings"
                          element={
                            <AdminRoute>
                              <AdminSettings />
                            </AdminRoute>
                          }
                        />
                        <Route path="*" element={<Navigate to="/" replace />} />
                      </Routes>
                    </MainLayout>
                  </ProtectedRoute>
                }
              />
            </Routes>
          </BrowserRouter>
          <Toaster />
        </AuthProvider>
      </QueryClientProvider>
    </GoogleOAuthProvider>
  )
}

export default App
