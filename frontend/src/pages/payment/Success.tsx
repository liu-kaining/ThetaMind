import * as React from "react"
import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { CheckCircle2, Loader2 } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { authApi } from "@/services/api/auth"

export const PaymentSuccess: React.FC = () => {
  const navigate = useNavigate()
  const [isPro, setIsPro] = useState(false)
  const [isChecking, setIsChecking] = useState(true)
  const [pollCount, setPollCount] = useState(0)
  const maxPolls = 30 // Maximum 30 polls (60 seconds total)

  // Poll user status every 2 seconds
  useEffect(() => {
    const checkProStatus = async () => {
      try {
        const userData = await authApi.getMe()
        if (userData.is_pro) {
          setIsPro(true)
          setIsChecking(false)
          // Redirect after 3 seconds
          setTimeout(() => {
            navigate("/dashboard")
          }, 3000)
          return true
        }
        return false
      } catch (error) {
        console.error("Error checking Pro status:", error)
        return false
      }
    }

    // Initial check
    checkProStatus().then((success) => {
      if (success) return
    })

    // Poll every 2 seconds
    const interval = setInterval(async () => {
      setPollCount((prev) => {
        const newCount = prev + 1
        if (newCount >= maxPolls) {
          clearInterval(interval)
          setIsChecking(false)
          return newCount
        }
        return newCount
      })

      const success = await checkProStatus()
      if (success) {
        clearInterval(interval)
      }
    }, 2000)

    return () => clearInterval(interval)
  }, [navigate])

  return (
    <div className="flex items-center justify-center min-h-screen bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-4">
            {isPro ? (
              <div className="relative">
                <CheckCircle2 className="h-24 w-24 text-green-500 animate-in zoom-in duration-500" />
                <div className="absolute inset-0 bg-green-500/20 rounded-full animate-ping" />
              </div>
            ) : (
              <Loader2 className="h-24 w-24 text-primary animate-spin" />
            )}
          </div>
          <CardTitle className="text-2xl">
            {isPro ? "Payment Successful!" : "Processing Payment..."}
          </CardTitle>
          <CardDescription className="text-base mt-2">
            {isPro
              ? "You are now a Pro Member!"
              : isChecking
                ? "Upgrading your account..."
                : "Payment received. Your account upgrade is being processed. Please check back in a few minutes."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isPro && (
            <div className="text-center space-y-2">
              <p className="text-sm text-muted-foreground">
                Redirecting to dashboard in 3 seconds...
              </p>
              <Button
                onClick={() => navigate("/dashboard")}
                className="w-full"
                variant="default"
              >
                Go to Dashboard Now
              </Button>
            </div>
          )}
          {!isPro && !isChecking && (
            <div className="text-center space-y-2">
              <Button
                onClick={() => navigate("/dashboard")}
                className="w-full"
                variant="default"
              >
                Go to Dashboard
              </Button>
              <Button
                onClick={() => window.location.reload()}
                className="w-full"
                variant="outline"
              >
                Check Again
              </Button>
            </div>
          )}
          {isChecking && (
            <div className="text-center">
              <p className="text-xs text-muted-foreground">
                Checking status... ({pollCount}/{maxPolls})
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

