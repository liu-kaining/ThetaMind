import * as React from "react"
import { useQuery } from "@tanstack/react-query"
import { format } from "date-fns"
import { User, Mail, Crown, Calendar, Zap, ExternalLink } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Separator } from "@/components/ui/separator"
import { useAuth } from "@/features/auth/AuthProvider"
import { paymentService } from "@/services/api/payment"
import apiClient from "@/services/api/client"
import { toast } from "sonner"
import { useNavigate } from "react-router-dom"

export const SettingsPage: React.FC = () => {
  const { user } = useAuth()
  const navigate = useNavigate()

  // Fetch current user details
  const { data: userDetails, isLoading } = useQuery({
    queryKey: ["userMe"],
    queryFn: async () => {
      const response = await apiClient.get("/api/v1/auth/me")
      return response.data
    },
    enabled: !!user,
  })

  const handleManageSubscription = async () => {
    try {
      const response = await paymentService.getCustomerPortal()
      if (response.portal_url) {
        window.open(response.portal_url, "_blank")
      }
    } catch (error: any) {
      if (error.response?.status === 404) {
        toast.error("No active subscription found")
      } else {
        toast.error(error.response?.data?.detail || "Failed to open customer portal")
      }
    }
  }

  const handleUpgradeToPro = () => {
    navigate("/pricing")
  }

  const usagePercentage = userDetails
    ? Math.min((userDetails.daily_ai_usage / userDetails.daily_ai_quota) * 100, 100)
    : 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account settings and subscription
        </p>
      </div>

      {/* Profile Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Profile
          </CardTitle>
          <CardDescription>Your account information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : (
            <>
              <div className="flex items-center gap-4">
                <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
                  <User className="h-8 w-8 text-primary" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold">{userDetails?.email || user?.email}</p>
                    {userDetails?.is_superuser && (
                      <Badge variant="default">Admin</Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Account created {userDetails?.created_at && format(new Date(userDetails.created_at), "PP")}
                  </p>
                </div>
              </div>
              <Separator />
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm">
                  <Mail className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">Email:</span>
                  <span className="font-medium">{userDetails?.email || user?.email}</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Email is managed by Google OAuth and cannot be changed here.
                </p>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Subscription Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Crown className="h-5 w-5" />
            Subscription
          </CardTitle>
          <CardDescription>Manage your Pro subscription</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-20 w-full" />
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <p className="font-semibold text-lg">
                      {userDetails?.is_pro ? "Pro Plan" : "Free Plan"}
                    </p>
                    {userDetails?.is_pro && (
                      <Badge variant="default" className="bg-yellow-500">
                        <Crown className="h-3 w-3 mr-1" />
                        Pro
                      </Badge>
                    )}
                  </div>
                  {userDetails?.is_pro && userDetails?.plan_expiry_date ? (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Calendar className="h-4 w-4" />
                      <span>
                        Renews on: {format(new Date(userDetails.plan_expiry_date), "PP")}
                      </span>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      Upgrade to Pro for real-time data, advanced AI insights, and more.
                    </p>
                  )}
                </div>
                <div className="flex gap-2">
                  {userDetails?.is_pro ? (
                    <Button
                      variant="outline"
                      onClick={handleManageSubscription}
                    >
                      <ExternalLink className="h-4 w-4 mr-2" />
                      Manage Subscription
                    </Button>
                  ) : (
                    <Button onClick={handleUpgradeToPro}>
                      <Crown className="h-4 w-4 mr-2" />
                      Upgrade to Pro
                    </Button>
                  )}
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Usage Quota Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="h-5 w-5" />
            Usage Quota
          </CardTitle>
          <CardDescription>Your daily AI report generation quota</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? (
            <div className="space-y-4">
              <Skeleton className="h-12 w-full" />
            </div>
          ) : (
            <>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">AI Daily Usage</span>
                  <span className="font-semibold">
                    {userDetails?.daily_ai_usage || 0} / {userDetails?.daily_ai_quota || 0}
                  </span>
                </div>
                <Progress value={usagePercentage} className="h-2" />
                <p className="text-xs text-muted-foreground">
                  {userDetails?.daily_ai_usage || 0} of {userDetails?.daily_ai_quota || 0} reports used today.
                  {userDetails?.daily_ai_quota && userDetails.daily_ai_usage >= userDetails.daily_ai_quota && (
                    <span className="text-red-600 dark:text-red-400 ml-1">
                      Quota reached. Quota resets at midnight UTC.
                    </span>
                  )}
                </p>
              </div>
              <Separator />
              <div className="text-sm text-muted-foreground">
                <p className="mb-2">
                  <strong>Free Plan:</strong> 1 AI report per day
                </p>
                <p>
                  <strong>Pro Plan:</strong> 50 AI reports per day
                </p>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

