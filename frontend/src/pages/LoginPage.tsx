import * as React from "react"
import { GoogleLogin } from "@react-oauth/google"
import { useNavigate, Navigate, Link } from "react-router-dom"
import { useAuth } from "@/features/auth/AuthProvider"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { FlaskConical, ArrowLeft, Home } from "lucide-react"

export const LoginPage: React.FC = () => {
  const { login, isAuthenticated, isLoading } = useAuth()
  const navigate = useNavigate()

  // If already authenticated, redirect to dashboard
  if (!isLoading && isAuthenticated) {
    return <Navigate to="/dashboard" replace />
  }

  const handleGoogleLogin = async (credentialResponse: { credential?: string }) => {
    try {
      // credentialResponse.credential contains the Google ID token
      if (!credentialResponse.credential) {
        console.error("No credential received from Google")
        return
      }
      await login(credentialResponse.credential)
      navigate("/dashboard")
    } catch (error) {
      console.error("Login error:", error)
    }
  }

  // Show loading state while checking authentication
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-md space-y-4">
        {/* Back to Home Button */}
        <div className="flex justify-start">
          <Button variant="ghost" asChild>
            <Link to="/" className="flex items-center gap-2">
              <ArrowLeft className="h-4 w-4" />
              <Home className="h-4 w-4" />
              Back to Home
            </Link>
          </Button>
        </div>
        
        <Card>
          <CardHeader className="space-y-1 text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <FlaskConical className="h-6 w-6 text-primary" />
            </div>
            <CardTitle className="text-2xl font-bold">Welcome to ThetaMind</CardTitle>
            <CardDescription>
              Sign in with your Google account to access AI-driven option strategy analysis
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex justify-center">
              <GoogleLogin
                onSuccess={handleGoogleLogin}
                onError={() => {
                  console.error("Google login failed")
                }}
                useOneTap={false}
              />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
