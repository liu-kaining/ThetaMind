import * as React from "react"
import { useState } from "react"
import { Check, Sparkles, Zap, Shield } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuth } from "@/features/auth/AuthProvider"
import { paymentService } from "@/services/api/payment"
import { toast } from "sonner"

export const Pricing: React.FC = () => {
  const { user } = useAuth()
  const [isLoading, setIsLoading] = useState(false)

  const handleUpgrade = async () => {
    try {
      setIsLoading(true)
      const response = await paymentService.createCheckoutSession()
      // Redirect to checkout URL
      window.location.href = response.checkout_url
    } catch (error: any) {
      toast.error(
        error.response?.data?.detail || "Failed to create checkout session"
      )
      setIsLoading(false)
    }
  }

  const features = {
    free: [
      "Delayed market data (15 min)",
      "1 AI report per day",
      "Basic strategy builder",
      "Community support",
    ],
    pro: [
      "Real-time market data (5s refresh)",
      "50 AI reports per day",
      "Advanced strategy analysis",
      "Priority support",
      "Unlimited strategy saves",
    ],
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Pricing</h1>
        <p className="text-muted-foreground">
          Choose the plan that fits your trading needs
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 max-w-4xl mx-auto">
        {/* Free Plan */}
        <Card>
          <CardHeader>
            <CardTitle>Free</CardTitle>
            <CardDescription>Perfect for getting started</CardDescription>
            <div className="mt-4">
              <span className="text-4xl font-bold">$0</span>
              <span className="text-muted-foreground">/month</span>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <ul className="space-y-2">
              {features.free.map((feature, index) => (
                <li key={index} className="flex items-start gap-2">
                  <Check className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
                  <span className="text-sm">{feature}</span>
                </li>
              ))}
            </ul>
            {!user?.is_pro && (
              <Button className="w-full" variant="outline" disabled>
                Current Plan
              </Button>
            )}
          </CardContent>
        </Card>

        {/* Pro Plan */}
        <Card className="border-primary">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Pro</CardTitle>
              {user?.is_pro && (
                <span className="text-xs bg-primary text-primary-foreground px-2 py-1 rounded">
                  Active
                </span>
              )}
            </div>
            <CardDescription>For serious option traders</CardDescription>
            <div className="mt-4">
              <span className="text-4xl font-bold">$29</span>
              <span className="text-muted-foreground">/month</span>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <ul className="space-y-2">
              {features.pro.map((feature, index) => (
                <li key={index} className="flex items-start gap-2">
                  <Sparkles className="h-5 w-5 text-primary mt-0.5 flex-shrink-0" />
                  <span className="text-sm">{feature}</span>
                </li>
              ))}
            </ul>
            {user?.is_pro ? (
              <Button className="w-full" variant="outline" disabled>
                Already Subscribed
              </Button>
            ) : (
              <Button
                className="w-full"
                onClick={handleUpgrade}
                disabled={isLoading}
              >
                {isLoading ? "Processing..." : "Upgrade Now"}
              </Button>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="max-w-4xl mx-auto">
        <CardHeader>
          <CardTitle>Why Upgrade to Pro?</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="flex items-start gap-3">
              <Zap className="h-6 w-6 text-primary mt-1" />
              <div>
                <h3 className="font-semibold mb-1">Real-Time Data</h3>
                <p className="text-sm text-muted-foreground">
                  Get market data with 5-second refresh rates for accurate
                  decision-making
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Sparkles className="h-6 w-6 text-primary mt-1" />
              <div>
                <h3 className="font-semibold mb-1">AI-Powered Analysis</h3>
                <p className="text-sm text-muted-foreground">
                  Generate up to 50 AI reports per day with advanced insights
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Shield className="h-6 w-6 text-primary mt-1" />
              <div>
                <h3 className="font-semibold mb-1">Priority Support</h3>
                <p className="text-sm text-muted-foreground">
                  Get faster response times and dedicated support channels
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

