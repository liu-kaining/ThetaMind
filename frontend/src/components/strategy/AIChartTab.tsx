import * as React from "react"
import { useState, useEffect, useMemo, useRef } from "react"
import { useQuery } from "@tanstack/react-query"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Lock, Sparkles, Loader2, Download, ExternalLink, AlertCircle } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { useAuth } from "@/features/auth/AuthProvider"
import { aiService, StrategyAnalysisRequest } from "@/services/api/ai"
import { taskService, TaskResponse } from "@/services/api/task"
import { toast } from "sonner"
import { useNavigate } from "react-router-dom"
import { calculateStrategyHashAsync } from "@/utils/strategyHash"

interface AIChartTabProps {
  strategySummary?: {
    symbol: string
    strategy_name: string
    spot_price: number
    expiration_date?: string
    legs: any[]
    portfolio_greeks?: any
    trade_execution?: any
    strategy_metrics?: any
    payoff_summary?: any
  }
  // Legacy format support (for backward compatibility)
  strategyData?: StrategyAnalysisRequest["strategy_data"]
  optionChain?: StrategyAnalysisRequest["option_chain"]
  // Add flag to check if strategy is saved
  isStrategySaved?: boolean
  strategyId?: string | null
}

export const AIChartTab: React.FC<AIChartTabProps> = ({
  strategySummary,
  strategyData,
  optionChain,
  isStrategySaved = false,
  strategyId = null,
}) => {
  const { user, refreshUser } = useAuth()
  const navigate = useNavigate()
  const [taskId, setTaskId] = useState<string | null>(null)
  const [imageId, setImageId] = useState<string | null>(null)
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)

  const isPro = user?.is_pro ?? false
  const imageQuotaRemaining = Math.max(0, (user?.daily_image_quota ?? 0) - (user?.daily_image_usage ?? 0))
  const hasImageQuota = imageQuotaRemaining > 0

  // Poll task status if taskId is set
  const { data: task } = useQuery({
    queryKey: ["task", taskId],
    queryFn: () => taskService.getTask(taskId!),
    enabled: !!taskId,
    refetchInterval: (query) => {
      const task = query.state.data as TaskResponse | undefined
      // Stop polling if task is completed (success or failed)
      if (task?.status === "SUCCESS" || task?.status === "FAILED") {
        return false
      }
      // Poll every 2 seconds while processing
      return 2000
    },
  })

  // Extract image_id from task result_ref when task succeeds
  useEffect(() => {
    if (task?.status === "SUCCESS" && task.result_ref) {
      try {
        const result = JSON.parse(task.result_ref)
        if (result.image_id) {
          setImageId(result.image_id)
          refreshUser() // Update image quota (incremented on backend)
          // Update checkedHashRef to prevent cache check from overriding this image
          // We'll recalculate hash and update it after loading the image
          if (strategySummary) {
            calculateStrategyHashAsync(strategySummary).then(hash => {
              checkedHashRef.current = hash
            }).catch(err => {
              console.error("Failed to calculate hash:", err)
            })
          }
          // Get R2 URL directly
          aiService
            .getChartImageUrl(result.image_id)
            .then((url) => {
              if (url) {
                setImageUrl(url)
              } else {
                throw new Error("No R2 URL available")
              }
            })
            .catch((error) => {
              console.error("Failed to fetch image URL:", error)
              toast.error("Failed to load chart image")
            })
        }
      } catch (e) {
        console.error("Failed to parse task result_ref:", e)
      }
    }
  }, [task, strategySummary, refreshUser])

  // Create a stable key for strategySummary to avoid unnecessary re-checks
  // Use primitive values in dependency array instead of object reference
  const strategyKey = useMemo(() => {
    if (!strategySummary) return null
    try {
      return JSON.stringify({
        symbol: strategySummary.symbol,
        expiration_date: strategySummary.expiration_date,
        legs: strategySummary.legs?.map(leg => ({
          strike: leg.strike,
          type: leg.type,
          action: leg.action,
          quantity: leg.quantity,
        })).sort((a, b) => {
          if (a.strike !== b.strike) return a.strike - b.strike
          if (a.type !== b.type) return a.type.localeCompare(b.type)
          if (a.action !== b.action) return a.action.localeCompare(b.action)
          return a.quantity - b.quantity
        }),
      })
    } catch (error) {
      console.error("Error calculating strategy key:", error)
      return null
    }
  }, [
    strategySummary?.symbol,
    strategySummary?.expiration_date,
    // Create a stable string representation of legs for comparison
    strategySummary?.legs?.map(l => `${l.strike}-${l.type}-${l.action}-${l.quantity}`).join(',')
  ])

  // Track if we've already checked for this strategy
  const checkedHashRef = useRef<string | null>(null)

  // Track current image URL in ref to avoid closure issues
  const imageUrlRef = useRef<string | null>(null)
  useEffect(() => {
    imageUrlRef.current = imageUrl
  }, [imageUrl])

  // Check for cached image when strategySummary changes (on component load or strategy change)
  // Use strategyKey as the dependency since it's stable and changes when strategySummary changes
  useEffect(() => {
    // Check for cached image when we have strategySummary (free & Pro users)
    // Skip if we have an active task (wait for task to complete first)
    if (!strategySummary || !strategyKey || taskId) {
      return
    }

    // Check for cached image by calculating strategy hash
    const checkCachedImage = async () => {
      try {
        const hash = await calculateStrategyHashAsync(strategySummary)

        // Skip if we've already checked this exact hash and have an image
        if (checkedHashRef.current === hash && imageUrlRef.current) {
          return
        }

        // If strategy changed, clear old image
        if (checkedHashRef.current && checkedHashRef.current !== hash) {
          setImageId(null)
          setImageUrl(null)
        }
        
        checkedHashRef.current = hash

        const result = await aiService.getChartImageByHash(hash)

        if (result.image_id) {
          setImageId(result.image_id)
          const url = result.r2_url || (await aiService.getChartImageUrl(result.image_id))
          if (url) {
            setImageUrl(url)
          } else {
            console.warn("No R2 URL available for cached image")
          }
        }
      } catch (error) {
        // Log error for debugging
        console.error("Error checking for cached image:", error)
      }
    }

    checkCachedImage()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [strategyKey, taskId]) // Skip cache check when taskId is set (task is active)

  // No cleanup needed for R2 URLs (they're direct URLs, not blob URLs)

  const handleGenerateChart = () => {
    if (!hasImageQuota) {
      toast.error("Daily image quota exceeded. Limit resets at midnight UTC.", {
        description: isPro ? "You've used all your chart generations for today." : "Free users get 1 chart per day. Upgrade to Pro for more.",
      })
      return
    }

    // Check if strategy is saved
    if (!isStrategySaved && !strategyId) {
      toast.error("Please save your strategy first before generating AI charts", {
        duration: 4000,
        description: "Click the 'Save' button to save your strategy, then you can use AI features.",
      })
      return
    }

    // Show confirmation dialog
    setConfirmDialogOpen(true)
  }

  const handleConfirmGenerate = async () => {
    setConfirmDialogOpen(false)

    // Prevent duplicate requests
    if (isGenerating) {
      toast.warning("Chart generation is already in progress. Please wait...")
      return
    }

    setIsGenerating(true)

    try {
      // Clear existing image and hash check to force regeneration
      setImageId(null)
      setImageUrl(null)
      checkedHashRef.current = null // Clear cached hash check so useEffect will re-check after new image is generated
      
      // Use strategy_summary if available, otherwise use legacy format
      if (strategySummary) {
        const response = await aiService.generateChart({
          strategy_summary: strategySummary,
          option_chain: optionChain,
        } as any)
        
        // If cached image found, load it (no API cost)
        if (response.cached && response.image_id) {
          setImageId(response.image_id)
          const url = await aiService.getChartImageUrl(response.image_id)
          if (url) {
            setImageUrl(url)
            toast.success("Using cached chart image (no cost)")
          } else {
            toast.error("Failed to load cached image URL")
          }
        } else if (response.task_id) {
          // New generation started (will incur API costs)
          setTaskId(response.task_id)
          toast.success("Chart generation started. This will use AI credits.")
        }
      } else if (strategyData && optionChain) {
        // Legacy format (backward compatibility)
        const response = await aiService.generateChart({
          strategy_data: strategyData,
          option_chain: optionChain,
        })
        if (response.task_id) {
          setTaskId(response.task_id)
          toast.success("Chart generation started. This will use AI credits.")
        }
      } else {
        toast.error("Strategy data is missing")
        return
      }
    } catch (error: any) {
      console.error("Failed to generate chart:", error)
      if (error.response?.status === 429) {
        toast.error("Daily image quota exceeded. Resets at midnight UTC.")
        refreshUser()
      } else if (error.response?.status === 403) {
        toast.error("Access denied. Please upgrade to Pro for more charts.")
      } else {
        toast.error(error.response?.data?.detail || "Failed to generate chart")
      }
    } finally {
      setIsGenerating(false)
    }
  }

  const handleDownloadImage = async () => {
    if (!imageId) return

    try {
      // Download through backend API to avoid CORS issues
      const blob = await aiService.downloadChartImage(imageId)
      
      const url = URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = url
      link.download = `ThetaMind_Strategy_Chart_${imageId}.png`
      document.body.appendChild(link)
      link.click()
      if (link.parentNode === document.body) {
        document.body.removeChild(link)
      }
      
      // Cleanup URL after a delay
      setTimeout(() => {
        URL.revokeObjectURL(url)
      }, 100)
      
      toast.success("Chart downloaded successfully")
    } catch (error: any) {
      console.error("Failed to download image:", error)
      const errorMessage = error.response?.data?.detail || error.message || "Failed to download image"
      toast.error(errorMessage)
    }
  }

  const handleViewTaskCenter = () => {
    if (taskId) {
      navigate(`/dashboard/tasks/${taskId}`)
    } else {
      navigate("/dashboard/tasks")
    }
  }

  // State 1: Empty/Initial (No task, no image)
  if (!taskId && !imageUrl) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            AI Strategy Chart
          </CardTitle>
          <CardDescription>
            Generate a professional, textbook-style visualization of your strategy using AI
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
            {!hasImageQuota && (
              <div className="mb-6">
                <Lock className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
                <p className="text-lg font-medium mb-2">Daily Quota Reached</p>
                <p className="text-sm text-muted-foreground mb-4">
                  {isPro ? "You've used all chart generations for today. Resets at midnight UTC." : "Free: 1 chart per day. Upgrade to Pro for more."}
                </p>
              </div>
            )}
            {hasImageQuota && !isPro && (
              <p className="text-xs text-muted-foreground mb-4">
                Free: {imageQuotaRemaining}/{user?.daily_image_quota ?? 1} chart{imageQuotaRemaining !== 1 ? "s" : ""} remaining today
              </p>
            )}
            <div className="mb-6 max-w-md">
              <p className="text-sm text-muted-foreground">
                Create a professional "Option Strategy Panoramic Analysis Chart" with:
              </p>
              <ul className="mt-4 text-sm text-left text-muted-foreground space-y-2">
                <li>• Opening strategy structure visualization</li>
                <li>• Payoff diagram at expiration</li>
                <li>• Financial metrics annotations</li>
                <li>• Professional Wall Street style</li>
              </ul>
            </div>
            <Button
              onClick={handleGenerateChart}
              disabled={!hasImageQuota || isGenerating || (!isStrategySaved && !strategyId) || !((strategySummary?.legs && strategySummary.legs.length > 0) || (strategyData?.legs && strategyData.legs.length > 0))}
              size="lg"
              className="mt-4"
              title={(!isStrategySaved && !strategyId) ? "Please save your strategy first" : !hasImageQuota ? "Daily quota reached" : undefined}
            >
              {!hasImageQuota ? (
                <>
                  <Lock className="h-4 w-4 mr-2" />
                  Generate AI Chart {isPro ? "(Quota)" : "(Pro for more)"}
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" />
                  Generate AI Chart{!isPro ? ` (${imageQuotaRemaining} left)` : ""}
                </>
              )}
            </Button>
            {!hasImageQuota && !isPro && (
              <Button
                onClick={() => navigate("/pricing")}
                variant="outline"
                className="mt-3"
              >
                Upgrade to Pro for More
              </Button>
            )}
          </div>
        </CardContent>
        {/* Confirmation Dialog */}
        <Dialog open={confirmDialogOpen} onOpenChange={setConfirmDialogOpen}>
          <DialogContent className="sm:max-w-[480px]">
            <DialogHeader>
              <DialogTitle>Generate AI Strategy Chart</DialogTitle>
              <DialogDescription>
                This will generate a professional, textbook-style visualization of your strategy using AI.
                <strong className="block mt-2 text-amber-600 dark:text-amber-400">
                  ⚠️ This will consume AI credits and may incur costs.
                </strong>
                This process may take a few moments. Are you sure you want to continue?
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setConfirmDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button onClick={handleConfirmGenerate} disabled={isGenerating}>
                <Sparkles className="h-4 w-4 mr-2" />
                {isGenerating ? "Generating..." : "Generate Chart"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </Card>
    )
  }

  // State 2: Processing (Task submitted, no image yet)
  if (taskId && task && task.status !== "SUCCESS" && !imageUrl) {
    const isFailed = task.status === "FAILED"
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            AI Strategy Chart
          </CardTitle>
          <CardDescription>Generating your professional strategy visualization...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
            {isFailed ? (
              <>
                <AlertCircle className="h-16 w-16 mx-auto mb-4 text-destructive" />
                <p className="text-lg font-medium mb-2">Generation Failed</p>
                <p className="text-sm text-muted-foreground mb-4">
                  {task.error_message || "An error occurred while generating the chart"}
                </p>
                <div className="flex gap-2">
                  <Button 
                    onClick={handleGenerateChart} 
                    variant="default" 
                    disabled={isGenerating || (!isStrategySaved && !strategyId)}
                    title={(!isStrategySaved && !strategyId) ? "Please save your strategy first" : undefined}
                  >
                    <Sparkles className="h-4 w-4 mr-2" />
                    {isGenerating ? "Generating..." : "Try Again"}
                  </Button>
                  <Button onClick={handleViewTaskCenter} variant="outline">
                    <ExternalLink className="h-4 w-4 mr-2" />
                    View Task Details
                  </Button>
                </div>
              </>
            ) : (
              <>
                <Loader2 className="h-16 w-16 mx-auto mb-4 animate-spin text-primary" />
                <p className="text-lg font-medium mb-2">Generating Chart...</p>
                <p className="text-sm text-muted-foreground mb-4">
                  This may take a few moments. Please wait.
                </p>
                <Button onClick={handleViewTaskCenter} variant="outline">
                  <ExternalLink className="h-4 w-4 mr-2" />
                  View Status in Task Center
                </Button>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    )
  }

  // State 3: Success (Image available)
  if (imageUrl) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-5 w-5" />
              AI Strategy Chart
            </div>
            <Button onClick={handleDownloadImage} variant="outline" size="sm">
              <Download className="h-4 w-4 mr-2" />
              Download Image
            </Button>
          </CardTitle>
          <CardDescription>
            Professional strategy panoramic analysis chart
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center">
            <div className="w-full max-w-4xl border rounded-lg overflow-hidden bg-white">
              <img
                src={imageUrl}
                alt="AI Generated Strategy Chart"
                className="w-full h-auto"
              />
            </div>
            <div className="mt-4 flex gap-2">
              <Button 
                onClick={handleGenerateChart} 
                variant="outline" 
                disabled={isGenerating || (!isStrategySaved && !strategyId)}
                title={(!isStrategySaved && !strategyId) ? "Please save your strategy first" : undefined}
              >
                <Sparkles className="h-4 w-4 mr-2" />
                {isGenerating ? "Generating..." : "Generate New Chart"}
              </Button>
              <Button onClick={handleDownloadImage} variant="default">
                <Download className="h-4 w-4 mr-2" />
                Download PNG
              </Button>
            </div>
          </div>
        </CardContent>
        {/* Confirmation Dialog */}
        <Dialog open={confirmDialogOpen} onOpenChange={setConfirmDialogOpen}>
          <DialogContent className="sm:max-w-[480px]">
            <DialogHeader>
              <DialogTitle>Generate AI Strategy Chart</DialogTitle>
              <DialogDescription>
                This will generate a professional, textbook-style visualization of your strategy using AI.
                <strong className="block mt-2 text-amber-600 dark:text-amber-400">
                  ⚠️ This will consume AI credits and may incur costs.
                </strong>
                This process may take a few moments. Are you sure you want to continue?
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button
                variant="outline"
                onClick={() => setConfirmDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button onClick={handleConfirmGenerate} disabled={isGenerating}>
                <Sparkles className="h-4 w-4 mr-2" />
                {isGenerating ? "Generating..." : "Generate Chart"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </Card>
    )
  }

  // Fallback (should not reach here)
  return (
    <>
      {/* Confirmation Dialog */}
      <Dialog open={confirmDialogOpen} onOpenChange={setConfirmDialogOpen}>
        <DialogContent className="sm:max-w-[480px]">
          <DialogHeader>
            <DialogTitle>Generate AI Strategy Chart</DialogTitle>
            <DialogDescription>
              This will generate a professional, textbook-style visualization of your strategy using AI.
              <strong className="block mt-2 text-amber-600 dark:text-amber-400">
                ⚠️ This will consume AI credits and may incur costs.
              </strong>
              This process may take a few moments. Are you sure you want to continue?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConfirmDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button onClick={handleConfirmGenerate} disabled={isGenerating}>
              <Sparkles className="h-4 w-4 mr-2" />
              {isGenerating ? "Generating..." : "Generate Chart"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}

