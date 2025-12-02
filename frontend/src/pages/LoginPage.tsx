import * as React from "react"
import { GoogleLogin } from "@react-oauth/google"
import { useNavigate } from "react-router-dom"
import { useAuth } from "@/features/auth/AuthProvider"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { FlaskConical } from "lucide-react"

export const LoginPage: React.FC = () => {
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleGoogleLogin = async (credentialResponse: { credential: string }) => {
    try {
      // credentialResponse.credential contains the Google ID token
      await login(credentialResponse.credential)
      navigate("/")
    } catch (error) {
      console.error("Login error:", error)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
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
  )
}
