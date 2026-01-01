import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { GoogleOAuthProvider } from "@react-oauth/google"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { Toaster } from "@/components/ui/toaster"
import { LanguageProvider } from "@/contexts/LanguageContext"
import { AuthProvider } from "@/features/auth/AuthProvider"
import { ProtectedRoute } from "@/components/auth/ProtectedRoute"
import { MainLayout } from "@/components/layout/MainLayout"
import { LandingPage } from "@/pages/LandingPage"
import { LoginPage } from "@/pages/LoginPage"
import { DashboardPage } from "@/pages/DashboardPage"
import { StrategyLab } from "@/pages/StrategyLab"
import { Pricing } from "@/pages/Pricing"
import { DailyPicks } from "@/pages/DailyPicks"
import { TaskCenter } from "@/pages/TaskCenter"
import { TaskDetailPage } from "@/pages/TaskDetailPage"
import { ReportsPage } from "@/pages/ReportsPage"
import { SettingsPage } from "@/pages/SettingsPage"
import { AboutPage } from "@/pages/AboutPage"
import { PaymentSuccess } from "@/pages/payment/Success"
import { DemoPage } from "@/pages/DemoPage"
import { AdminSettings } from "@/pages/admin/AdminSettings"
import { AdminUsers } from "@/pages/admin/AdminUsers"
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
      <LanguageProvider>
        <QueryClientProvider client={queryClient}>
          <AuthProvider>
            <BrowserRouter>
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/demo" element={<DemoPage />} />
              <Route path="/about" element={<AboutPage />} />
              <Route path="/payment/success" element={<PaymentSuccess />} />
              <Route
                path="/*"
                element={
                  <ProtectedRoute>
                    <MainLayout>
                      <Routes>
                        <Route path="/dashboard" element={<DashboardPage />} />
                        <Route path="/dashboard/tasks" element={<TaskCenter />} />
                        <Route path="/dashboard/tasks/:taskId" element={<TaskDetailPage />} />
                        <Route path="/strategy-lab" element={<StrategyLab />} />
                        <Route path="/daily-picks" element={<DailyPicks />} />
                        <Route path="/pricing" element={<Pricing />} />
                        <Route path="/reports" element={<ReportsPage />} />
                        <Route path="/settings" element={<SettingsPage />} />
                        <Route
                          path="/admin/settings"
                          element={
                            <AdminRoute>
                              <AdminSettings />
                            </AdminRoute>
                          }
                        />
                        <Route
                          path="/admin/users"
                          element={
                            <AdminRoute>
                              <AdminUsers />
                            </AdminRoute>
                          }
                        />
                        <Route path="*" element={<Navigate to="/dashboard" replace />} />
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
      </LanguageProvider>
    </GoogleOAuthProvider>
  )
}

export default App

