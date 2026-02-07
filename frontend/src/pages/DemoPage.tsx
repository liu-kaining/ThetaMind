import * as React from "react"
import { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import { ArrowRight, Lock, Zap, ChevronLeft, ChevronRight, Brain, Sparkles, FileText, TrendingUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { PayoffChart } from "@/components/charts/PayoffChart"
import { cn } from "@/lib/utils"

// Carousel images
const CAROUSEL_IMAGES = Array.from({ length: 20 }, (_, i) => 
  `https://assets.thetamind.ai/info/show/${i}.png`
)

// Carousel Component
const ImageCarousel: React.FC = () => {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isAutoPlaying, setIsAutoPlaying] = useState(true)

  // Auto-play functionality
  useEffect(() => {
    if (!isAutoPlaying) return

    const interval = setInterval(() => {
      setCurrentIndex((prev) => (prev + 1) % CAROUSEL_IMAGES.length)
    }, 3000) // Change image every 3 seconds

    return () => clearInterval(interval)
  }, [isAutoPlaying])

  const goToPrevious = () => {
    setIsAutoPlaying(false)
    setCurrentIndex((prev) => (prev - 1 + CAROUSEL_IMAGES.length) % CAROUSEL_IMAGES.length)
  }

  const goToNext = () => {
    setIsAutoPlaying(false)
    setCurrentIndex((prev) => (prev + 1) % CAROUSEL_IMAGES.length)
  }

  const goToSlide = (index: number) => {
    setIsAutoPlaying(false)
    setCurrentIndex(index)
  }

  return (
    <Card className="overflow-hidden border-2 border-slate-300 dark:border-slate-600 shadow-lg">
      <CardContent className="p-0">
        <div className="relative w-full">
          {/* Image Container */}
          <div className="relative aspect-video w-full overflow-hidden bg-slate-100 dark:bg-slate-800 border-2 border-slate-200 dark:border-slate-700">
            {CAROUSEL_IMAGES.map((image, index) => (
              <img
                key={index}
                src={image}
                alt={`Demo screenshot ${index + 1}`}
                className={cn(
                  "absolute inset-0 h-full w-full object-contain transition-opacity duration-500",
                  index === currentIndex ? "opacity-100" : "opacity-0"
                )}
              />
            ))}

            {/* Navigation Arrows */}
            <button
              onClick={goToPrevious}
              className="absolute left-4 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2 text-white transition-all hover:bg-black/70 focus:outline-none focus:ring-2 focus:ring-white"
              aria-label="Previous image"
            >
              <ChevronLeft className="h-6 w-6" />
            </button>
            <button
              onClick={goToNext}
              className="absolute right-4 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2 text-white transition-all hover:bg-black/70 focus:outline-none focus:ring-2 focus:ring-white"
              aria-label="Next image"
            >
              <ChevronRight className="h-6 w-6" />
            </button>

            {/* Dots Indicator */}
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2">
              {CAROUSEL_IMAGES.map((_, index) => (
                <button
                  key={index}
                  onClick={() => goToSlide(index)}
                  className={cn(
                    "h-2 w-2 rounded-full transition-all",
                    index === currentIndex
                      ? "bg-white w-8"
                      : "bg-white/50 hover:bg-white/75"
                  )}
                  aria-label={`Go to slide ${index + 1}`}
                />
              ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// Demo data - a sample Iron Condor strategy
const DEMO_STRATEGY = {
  symbol: "AAPL",
  expirationDate: "2024-02-16",
  legs: [
    {
      id: "1",
      type: "call",
      action: "sell",
      strike: 200,
      quantity: 1,
      premium: 2.5,
    },
    {
      id: "2",
      type: "call",
      action: "buy",
      strike: 205,
      quantity: 1,
      premium: 1.0,
    },
    {
      id: "3",
      type: "put",
      action: "sell",
      strike: 190,
      quantity: 1,
      premium: 2.0,
    },
    {
      id: "4",
      type: "put",
      action: "buy",
      strike: 185,
      quantity: 1,
      premium: 0.8,
    },
  ],
}

export const DemoPage: React.FC = () => {

  // Calculate demo payoff data
  const payoffData = React.useMemo(() => {
    const data: Array<{ price: number; profit: number }> = []
    const priceRange = [170, 220]
    const step = 1

    for (let price = priceRange[0]; price <= priceRange[1]; price += step) {
      let totalProfit = 0

      DEMO_STRATEGY.legs.forEach((leg) => {
        let legProfit = 0
        const intrinsicValue = Math.max(
          0,
          leg.type === "call" ? price - leg.strike : leg.strike - price
        )

        if (leg.action === "sell") {
          legProfit = leg.premium - intrinsicValue
        } else {
          legProfit = intrinsicValue - leg.premium
        }

        totalProfit += legProfit * leg.quantity
      })

      data.push({ price, profit: totalProfit })
    }

    return data
  }, [])

  const breakEven = React.useMemo(() => {
    // Calculate break-even points for Iron Condor
    const netCredit = DEMO_STRATEGY.legs.reduce((sum, leg) => {
      return sum + (leg.action === "sell" ? leg.premium : -leg.premium) * leg.quantity
    }, 0)

    // Upper break-even: short call strike + net credit
    const upperBE = 200 + netCredit
    // Lower break-even: short put strike - net credit
    const lowerBE = 190 - netCredit

    // Return the average for display (PayoffChart expects a single number)
    return (upperBE + lowerBE) / 2
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900">
      {/* Header */}
      <div className="border-b border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 backdrop-blur">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <Link 
              to="/" 
              className="flex items-center gap-2 hover:opacity-80 transition-opacity group"
            >
              <Zap className="h-8 w-8 text-primary group-hover:scale-105 transition-transform" />
              <span className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
                ThetaMind
              </span>
            </Link>
            <Button asChild className="bg-gradient-to-r from-blue-600 to-indigo-600">
              <Link to="/login">
                Sign In to Use
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>
      </div>

      {/* Demo Content */}
      <div className="container mx-auto px-6 py-8">
        <div className="max-w-7xl mx-auto space-y-6">
          {/* Info Banner */}
          <Card className="border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <Lock className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5" />
                <div>
                  <p className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
                    Interactive Demo Mode
                  </p>
                  <p className="text-sm text-blue-800 dark:text-blue-200">
                    This is a read-only demonstration of ThetaMind's Strategy Lab. Sign in to create
                    your own strategies, access real-time data, and use AI-powered analysis.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Platform Introduction */}
          <Card className="border-2 border-primary/20 bg-gradient-to-br from-slate-50 to-blue-50/50 dark:from-slate-900 dark:to-blue-950/20">
            <CardHeader>
              <CardTitle className="text-2xl md:text-3xl font-bold text-center mb-2">
                ThetaMind: Cognitive Intelligence for Option Strategies
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <p className="text-lg text-center text-slate-700 dark:text-slate-300 leading-relaxed">
                ThetaMind is not just a data wrapper; it is an AI-powered analyst for the next generation of financial researchers.
              </p>

              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <Sparkles className="h-5 w-5 text-primary mt-1 flex-shrink-0" />
                  <div>
                    <p className="text-slate-700 dark:text-slate-300 leading-relaxed">
                      By leveraging <strong className="text-primary">Google's Gemini 1.5 Pro models</strong>, we have built a proprietary <strong>"Deep Research"</strong> pipeline. This system moves beyond simple price tracking to perform holistic market analysis:
                    </p>
                  </div>
                </div>

                <div className="grid md:grid-cols-3 gap-4 mt-6">
                  <div className="flex flex-col items-start gap-3 p-4 rounded-lg bg-blue-50/50 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/30">
                    <div className="h-10 w-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
                      <FileText className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                    </div>
                    <h3 className="font-semibold text-lg text-slate-900 dark:text-slate-100">Ingest</h3>
                    <p className="text-sm text-slate-600 dark:text-slate-300">
                      It reads real-time option chains alongside thousands of news articles and earnings reports.
                    </p>
                  </div>

                  <div className="flex flex-col items-start gap-3 p-4 rounded-lg bg-indigo-50/50 dark:bg-indigo-950/20 border border-indigo-100 dark:border-indigo-900/30">
                    <div className="h-10 w-10 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center">
                      <Brain className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
                    </div>
                    <h3 className="font-semibold text-lg text-slate-900 dark:text-slate-100">Reason</h3>
                    <p className="text-sm text-slate-600 dark:text-slate-300">
                      It correlates volatility spikes with real-world events to distinguish between noise and opportunity.
                    </p>
                  </div>

                  <div className="flex flex-col items-start gap-3 p-4 rounded-lg bg-purple-50/50 dark:bg-purple-950/20 border border-purple-100 dark:border-purple-900/30">
                    <div className="h-10 w-10 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
                      <TrendingUp className="h-5 w-5 text-purple-600 dark:text-purple-400" />
                    </div>
                    <h3 className="font-semibold text-lg text-slate-900 dark:text-slate-100">Deliver</h3>
                    <p className="text-sm text-slate-600 dark:text-slate-300">
                      It produces comprehensive strategy reports that would typically take a human analyst hours to compile—in just seconds.
                    </p>
                  </div>
                </div>

                <div className="text-center pt-4 border-t border-slate-200 dark:border-slate-700">
                  <p className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                    Built for Researchers. Optimized for Education. Powered by AI.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Platform Features Showcase */}
          <div className="space-y-4">
            <div className="text-center space-y-2">
              <h2 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
                Platform Features Showcase
              </h2>
              <p className="text-lg text-muted-foreground max-w-3xl mx-auto">
                Explore ThetaMind's comprehensive features through interactive screenshots. 
                Navigate through different pages to see how our platform helps you analyze 
                option strategies with AI-powered insights.
              </p>
            </div>
            
            {/* Image Carousel */}
            <ImageCarousel />
          </div>

          {/* Divider */}
          <div className="relative py-8">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200 dark:border-slate-700"></div>
            </div>
            <div className="relative flex justify-center">
              <span className="bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900 px-4 text-sm font-medium text-muted-foreground">
                Interactive Strategy Demo
              </span>
            </div>
          </div>

          {/* Strategy Info */}
          <Card>
            <CardHeader>
              <CardTitle>Demo Strategy: Iron Condor on AAPL</CardTitle>
              <CardDescription>
                A neutral strategy with limited risk and limited profit potential
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Symbol</p>
                  <p className="font-semibold">{DEMO_STRATEGY.symbol}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Expiration</p>
                  <p className="font-semibold">{DEMO_STRATEGY.expirationDate}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Strategy Type</p>
                  <p className="font-semibold">Iron Condor</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Net Credit</p>
                  <p className="font-semibold text-green-600">
                    $
                    {DEMO_STRATEGY.legs
                      .reduce(
                        (sum, leg) =>
                          sum + (leg.action === "sell" ? leg.premium : -leg.premium) * leg.quantity,
                        0
                      )
                      .toFixed(2)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Charts */}
          <Card>
            <CardHeader>
              <CardTitle>Payoff Diagram</CardTitle>
              <CardDescription>
                Profit/Loss visualization across stock prices
              </CardDescription>
            </CardHeader>
            <CardContent>
              <PayoffChart
                data={payoffData}
                breakEven={breakEven}
                currentPrice={195}
                expirationDate={DEMO_STRATEGY.expirationDate}
                timeToExpiry={30}
              />
            </CardContent>
          </Card>

          {/* Strategy Legs */}
          <Card>
            <CardHeader>
              <CardTitle>Strategy Legs</CardTitle>
              <CardDescription>Four-leg Iron Condor structure</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {DEMO_STRATEGY.legs.map((leg, index) => (
                  <div
                    key={leg.id}
                    className="flex items-center justify-between p-3 rounded-lg border bg-slate-50 dark:bg-slate-900"
                  >
                    <div className="flex items-center gap-4">
                      <span className="text-sm font-medium text-muted-foreground">
                        Leg {index + 1}
                      </span>
                      <span className="font-semibold">
                        {leg.action.toUpperCase()} {leg.strike} {leg.type.toUpperCase()}
                      </span>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-muted-foreground">Premium</p>
                      <p className="font-semibold">${leg.premium.toFixed(2)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* CTA */}
          <Card className="border-primary bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950">
            <CardContent className="pt-6">
              <div className="text-center space-y-4">
                <h3 className="text-2xl font-bold">Ready to Build Your Own Strategies?</h3>
                <p className="text-muted-foreground">
                  Sign in to access real-time market data, AI analysis, and unlimited strategy
                  building.
                </p>
                <Button size="lg" asChild className="bg-gradient-to-r from-blue-600 to-indigo-600">
                  <Link to="/login">
                    Get Started Free
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

