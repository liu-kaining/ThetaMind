import * as React from "react"
import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Check, Sparkles, Zap, Shield } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { useAuth } from "@/features/auth/AuthProvider"
import { paymentService } from "@/services/api/payment"
import { toast } from "sonner"
import { Skeleton } from "@/components/ui/skeleton"

export const Pricing: React.FC = () => {
  const { user } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [isYearly, setIsYearly] = useState(false)

  // Fetch pricing from API
  const { data: pricing, isLoading: isLoadingPricing } = useQuery({
    queryKey: ["pricing"],
    queryFn: () => paymentService.getPricing(),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  })

  const handleUpgrade = async () => {
    try {
      setIsLoading(true)
      const variantType = isYearly ? "yearly" : "monthly"
      const response = await paymentService.createCheckoutSession(variantType)
      // Redirect to checkout URL
      window.location.href = response.checkout_url
    } catch (error: any) {
      toast.error(
        error.response?.data?.detail || "Failed to create checkout session"
      )
      setIsLoading(false)
    }
  }

  // Daily quota: Free 5 units (1 run), Monthly 40 (8 runs), Yearly 100 (20 runs). One Deep Research = 5 units.
  const features = {
    free: [
      "Delayed market data (15 min cache)",
      "1 Deep Research report per day (5 units, Gemini 3.0 Pro)",
      "1 AI chart per day (Gemini 3.0 Pro)",
      "Basic strategy builder",
      "Community support",
      "❌ No real-time data refresh",
    ],
    proMonthly: [
      "Real-time market data (5s refresh)",
      "8 Deep Research reports per day (40 units, Gemini 3.0 Pro)",
      "10 AI charts per day (Gemini 3.0 Pro)",
      "Advanced strategy analysis",
      "Priority support",
      "Unlimited strategy saves",
    ],
    proYearly: [
      "Real-time market data (5s refresh)",
      "20 Deep Research reports per day (100 units, Gemini 3.0 Pro)",
      "30 AI charts per day (Gemini 3.0 Pro)",
      "Advanced strategy analysis",
      "Priority support",
      "Unlimited strategy saves",
    ],
  }

  // Use pricing from API, fallback to defaults if not loaded
  const proMonthlyPrice = pricing?.monthly_price ?? 9.9
  const proYearlyPrice = pricing?.yearly_price ?? 99.0
  const proPrice = isYearly ? proYearlyPrice : proMonthlyPrice
  const monthlySavings = Math.round(((proMonthlyPrice * 12 - proYearlyPrice) / (proMonthlyPrice * 12)) * 100)

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight">Pricing</h1>
        <p className="text-muted-foreground">
          Choose the plan that fits your trading needs
        </p>
        
        {/* Monthly/Yearly Toggle */}
        <div className="flex items-center justify-center gap-4 mt-6">
          <Label htmlFor="billing-toggle" className={!isYearly ? "font-semibold" : ""}>
            Monthly
          </Label>
          <Switch
            id="billing-toggle"
            checked={isYearly}
            onCheckedChange={setIsYearly}
          />
          <div className="flex items-center gap-2">
            <Label htmlFor="billing-toggle" className={isYearly ? "font-semibold" : ""}>
              Yearly
            </Label>
            {isYearly && (
              <span className="text-xs bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400 px-2 py-0.5 rounded-full">
                Save {monthlySavings}%
              </span>
            )}
          </div>
        </div>
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
              {isLoadingPricing ? (
                <Skeleton className="h-12 w-32" />
              ) : (
                <>
                  <div className="flex items-baseline gap-2">
                    <span className="text-4xl font-bold">${proPrice.toFixed(1)}</span>
                    <span className="text-muted-foreground">/{isYearly ? "year" : "month"}</span>
                  </div>
                  {isYearly && (
                    <p className="text-sm text-muted-foreground mt-1">
                      ${(proYearlyPrice / 12).toFixed(2)}/month billed annually
                    </p>
                  )}
                </>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <ul className="space-y-2">
              {(isYearly ? features.proYearly : features.proMonthly).map((feature, index) => (
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

      {/* Daily quota rule — transparent, encourages yearly */}
      <Card className="max-w-4xl mx-auto border-primary/20 bg-primary/5">
        <CardHeader>
          <CardTitle className="text-lg">Daily AI Report Quota</CardTitle>
          <CardDescription>
            One Deep Research run = 5 units. Quota resets at midnight UTC. Yearly gets 2.5× more runs per day than Monthly.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="rounded-lg border bg-background p-4">
              <p className="text-2xl font-bold text-muted-foreground">5</p>
              <p className="text-xs text-muted-foreground">units/day</p>
              <p className="mt-1 text-sm font-semibold">1 run</p>
              <p className="text-xs text-muted-foreground">Free</p>
            </div>
            <div className="rounded-lg border bg-background p-4">
              <p className="text-2xl font-bold">40</p>
              <p className="text-xs text-muted-foreground">units/day</p>
              <p className="mt-1 text-sm font-semibold">8 runs</p>
              <p className="text-xs text-muted-foreground">Pro Monthly</p>
            </div>
            <div className="rounded-lg border-2 border-primary bg-primary/10 p-4">
              <p className="text-2xl font-bold text-primary">100</p>
              <p className="text-xs text-muted-foreground">units/day</p>
              <p className="mt-1 text-sm font-semibold">20 runs</p>
              <p className="text-xs font-medium text-primary">Pro Yearly · Best value</p>
            </div>
          </div>
        </CardContent>
      </Card>

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
                  Generate AI reports and charts using the strongest Gemini 3.0 Pro model with Deep Research mode
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

