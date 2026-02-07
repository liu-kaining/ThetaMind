import * as React from "react"
import { Link } from "react-router-dom"
import { 
  Brain, 
  TrendingUp, 
  Shield, 
  Zap, 
  BarChart3,
  ArrowRight,
  CheckCircle2,
  LayoutDashboard,
  FileText,
  Sparkles,
  ListTodo,
  Cloud,
  Layers,
  Search,
  Database,
  Server,
  Image as ImageIcon
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useLanguage } from "@/contexts/LanguageContext"
import { useAuth } from "@/features/auth/AuthProvider"

export const LandingPage: React.FC = () => {
  const { t } = useLanguage()
  const { isAuthenticated, user, isLoading } = useAuth()

  return (
    <div className="min-h-screen relative overflow-hidden">
      {/* Calm, premium background - no busy grid */}
      <div className="fixed inset-0 -z-10 bg-slate-50 dark:bg-[#0f1117]" />
      <div className="fixed inset-0 -z-10 bg-[radial-gradient(ellipse_100%_80%_at_70%_-30%,rgba(99,102,241,0.08),transparent_50%)] dark:bg-[radial-gradient(ellipse_100%_80%_at_70%_-30%,rgba(99,102,241,0.12),transparent_50%)]" />
      <div className="fixed inset-0 -z-10 bg-[radial-gradient(ellipse_80%_60%_at_20%_80%,rgba(139,92,246,0.06),transparent_50%)] dark:bg-[radial-gradient(ellipse_80%_60%_at_20%_80%,rgba(139,92,246,0.08),transparent_50%)]" />

      {/* Navigation - clean glass */}
      <nav className="container mx-auto px-6 py-4 sticky top-0 z-50 border-b border-slate-200/60 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 hover:opacity-80 transition-opacity group">
            <Zap className="h-8 w-8 text-primary group-hover:scale-105 transition-transform" />
            <span className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
              ThetaMind
            </span>
          </div>
          <div className="flex items-center gap-4">
            {!isLoading && isAuthenticated ? (
              <>
                <span className="text-sm text-muted-foreground">{user?.email}</span>
                <Button 
                  asChild
                  className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-lg hover:shadow-xl transition-all"
                >
                  <Link to="/dashboard">
                    <LayoutDashboard className="h-4 w-4 mr-2" />
                    Go to Dashboard
                  </Link>
                </Button>
              </>
            ) : (
              <>
                <Button variant="ghost" asChild className="hidden md:flex">
                  <Link to="/demo">Demo</Link>
                </Button>
                <Button 
                  asChild
                  className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-lg hover:shadow-xl transition-all"
                >
                  <Link to="/login">{t("nav.getStarted")}</Link>
                </Button>
                <Button variant="ghost" asChild className="hidden md:flex">
                  <Link to="/about">About Founder</Link>
                </Button>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="container mx-auto px-6 pt-16 pb-24">
        <div className="max-w-5xl mx-auto">
          <div className="flex flex-col lg:flex-row lg:items-center lg:gap-16">
            {/* Left: Copy */}
            <div className="flex-1 text-center lg:text-left">
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-100 dark:bg-slate-800/80 text-slate-600 dark:text-slate-400 text-xs font-medium mb-6 border border-slate-200/80 dark:border-slate-700/80">
                <Shield className="h-3.5 w-3.5 text-slate-500" />
                {t("hero.badge")}
              </div>
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-slate-900 dark:text-white mb-5 leading-[1.1]">
                <span className="block text-slate-900 dark:text-white">
                  {t("hero.title.part1")}
                </span>
                <span className="block mt-1 bg-gradient-to-r from-indigo-600 via-violet-600 to-purple-600 bg-clip-text text-transparent">
                  {t("hero.title.part2")}
                </span>
              </h1>
              <p className="text-base sm:text-lg text-slate-600 dark:text-slate-400 max-w-xl mx-auto lg:mx-0 leading-relaxed mb-8">
                {t("hero.subtitle")}
              </p>

              {/* Stack: unified pills */}
              <div className="flex flex-wrap items-center gap-2 mb-8">
                <span className="text-xs text-slate-400 dark:text-slate-500 w-full sm:w-auto mb-1 sm:mb-0">{t("stack.title")}</span>
                {[
                  { icon: Cloud, label: t("stack.cloud") },
                  { icon: Sparkles, label: t("stack.gemini") },
                  { icon: null, label: "FMP" },
                  { icon: null, label: "Tiger" },
                  { icon: BarChart3, label: t("stack.realtimeCharts") },
                  { icon: null, label: t("stack.nanoBanana"), highlight: true },
                  { icon: ListTodo, label: t("stack.taskSystem") },
                ].map((item, i) => (
                  <span
                    key={i}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium ${
                      item.highlight
                        ? "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-300/50 dark:border-indigo-500/30"
                        : "bg-white dark:bg-slate-800/90 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700 shadow-sm"
                    }`}
                  >
                    {item.icon && <item.icon className="h-3 w-3 opacity-80" />}
                    {item.label}
                  </span>
                ))}
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-3">
                {!isLoading && isAuthenticated ? (
                  <Button size="lg" className="rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white px-8 shadow-lg shadow-indigo-500/25" asChild>
                    <Link to="/dashboard">
                      <LayoutDashboard className="mr-2 h-5 w-5" />
                      Go to Dashboard
                      <ArrowRight className="ml-2 h-5 w-5" />
                    </Link>
                  </Button>
                ) : (
                  <>
                    <Button size="lg" className="rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white px-8 shadow-lg shadow-indigo-500/25" asChild>
                      <Link to="/login">
                        {t("hero.cta.primary")}
                        <ArrowRight className="ml-2 h-5 w-5" />
                      </Link>
                    </Button>
                    <Button size="lg" variant="outline" className="rounded-xl border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800" asChild>
                      <Link to="/demo">{t("hero.cta.secondary")}</Link>
                    </Button>
                  </>
                )}
              </div>
            </div>

            {/* Right: Hero visual - clean line chart + payoff style */}
            <div className="hidden lg:flex flex-1 justify-center items-center mt-16 lg:mt-0">
              <div className="relative w-full max-w-[420px]">
                <div className="absolute -inset-4 bg-gradient-to-br from-indigo-500/5 to-violet-500/10 rounded-[2rem] blur-2xl" />
                <div className="relative rounded-2xl border border-slate-200/80 dark:border-slate-700/80 bg-white dark:bg-slate-800/90 shadow-2xl shadow-slate-200/50 dark:shadow-black/30 overflow-hidden">
                  <div className="p-5 border-b border-slate-100 dark:border-slate-700/80">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-emerald-500" />
                      <span className="text-xs font-medium text-slate-500 dark:text-slate-400">AAPL · Live</span>
                    </div>
                  </div>
                  <div className="p-6 pt-4">
                    <svg viewBox="0 0 280 120" className="w-full h-[140px] text-slate-200 dark:text-slate-600" preserveAspectRatio="none">
                      <defs>
                        <linearGradient id="heroLineGrad" x1="0%" y1="0%" x2="0%" y2="100%">
                          <stop offset="0%" stopColor="rgb(99,102,241)" stopOpacity="0.3" />
                          <stop offset="100%" stopColor="rgb(99,102,241)" stopOpacity="0" />
                        </linearGradient>
                      </defs>
                      <path fill="url(#heroLineGrad)" d="M0,80 Q35,75 70,60 T140,35 T210,25 T280,20 L280,120 L0,120 Z" />
                      <path fill="none" stroke="rgb(99,102,241)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" d="M0,80 Q35,75 70,60 T140,35 T210,25 T280,20" />
                    </svg>
                    <div className="flex justify-between mt-2 text-xs text-slate-400 dark:text-slate-500">
                      <span>Price</span>
                      <span>Real-time</span>
                    </div>
                  </div>
                  <div className="px-6 pb-6">
                    <div className="h-12 rounded-lg bg-slate-50 dark:bg-slate-700/30 flex items-center justify-center">
                      <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Payoff · Greeks</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Disclaimer - minimal, compliant */}
          <div className="mt-20 max-w-2xl mx-auto px-4 py-3 rounded-lg border border-slate-200/80 dark:border-slate-700/80 bg-slate-50/50 dark:bg-slate-800/30">
            <p className="text-left text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              {t("disclaimer.text").split("**").map((part, i) => 
                i % 2 === 1 ? <strong key={i} className="text-slate-600 dark:text-slate-400">{part}</strong> : part
              )}
            </p>
          </div>
        </div>
      </section>

      {/* Tech Stack & Highlights */}
      <section className="container mx-auto px-6 py-16">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 dark:text-white mb-3">
              {t("techHighlights.title")}
            </h2>
            <p className="text-slate-600 dark:text-slate-400 max-w-xl mx-auto">
              {t("techHighlights.subtitle")}
            </p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { icon: Server, label: t("tech.cloud"), desc: t("tech.cloud.desc") },
              { icon: Sparkles, label: t("tech.gemini"), desc: t("tech.gemini.desc") },
              { icon: Database, label: t("tech.fmp"), desc: t("tech.fmp.desc") },
              { icon: Database, label: t("tech.tiger"), desc: t("tech.tiger.desc") },
              { icon: BarChart3, label: t("tech.charts"), desc: t("tech.charts.desc") },
              { icon: Zap, label: t("tech.nano"), desc: t("tech.nano.desc") },
              { icon: ListTodo, label: t("tech.tasks"), desc: t("tech.tasks.desc"), span: true },
            ].map((item, i) => (
              <div
                key={i}
                className={`rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/80 p-4 shadow-sm hover:shadow-md transition-shadow ${item.span ? "md:col-span-2" : ""}`}
              >
                <item.icon className="h-5 w-5 text-indigo-500 mb-2" />
                <p className="font-semibold text-slate-900 dark:text-white text-sm">{item.label}</p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Technical Architecture */}
      <section className="container mx-auto px-6 py-16">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 dark:text-white mb-3">
              {t("arch.title")}
            </h2>
            <p className="text-slate-600 dark:text-slate-400">
              {t("arch.subtitle")}
            </p>
          </div>
          <div className="flex flex-col md:flex-row md:items-stretch gap-4 md:gap-2">
            <div className="flex-1 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/80 p-5 text-center">
              <div className="h-10 w-10 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center mx-auto mb-3">
                <Layers className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
              </div>
              <h3 className="font-semibold text-slate-900 dark:text-white mb-1">{t("arch.step1")}</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">{t("arch.step1.desc")}</p>
            </div>
            <div className="hidden md:flex items-center flex-shrink-0 text-slate-300 dark:text-slate-600">
              <ArrowRight className="h-5 w-5" />
            </div>
            <div className="flex-1 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/80 p-5 text-center">
              <div className="h-10 w-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center mx-auto mb-3">
                <Brain className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
              <h3 className="font-semibold text-slate-900 dark:text-white mb-1">{t("arch.step2")}</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">{t("arch.step2.desc")}</p>
            </div>
            <div className="hidden md:flex items-center flex-shrink-0 text-slate-300 dark:text-slate-600">
              <ArrowRight className="h-5 w-5" />
            </div>
            <div className="flex-1 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/80 p-5 text-center">
              <div className="h-10 w-10 rounded-lg bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center mx-auto mb-3">
                <Search className="h-5 w-5 text-violet-600 dark:text-violet-400" />
              </div>
              <h3 className="font-semibold text-slate-900 dark:text-white mb-1">{t("arch.step3")}</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">{t("arch.step3.desc")}</p>
            </div>
            <div className="hidden md:flex items-center flex-shrink-0 text-slate-300 dark:text-slate-600">
              <ArrowRight className="h-5 w-5" />
            </div>
            <div className="flex-1 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/80 p-5 text-center">
              <div className="h-10 w-10 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center mx-auto mb-3">
                <FileText className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
              </div>
              <h3 className="font-semibold text-slate-900 dark:text-white mb-1">{t("arch.step4")}</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">{t("arch.step4.desc")}</p>
            </div>
          </div>
        </div>
      </section>

      {/* Core value: one sentence + compliance */}
      <section className="container mx-auto px-6 py-12">
        <div className="max-w-3xl mx-auto text-center">
          <p className="text-slate-600 dark:text-slate-400">
            Built on <strong className="text-slate-800 dark:text-slate-200">Google Cloud</strong> & <strong className="text-slate-800 dark:text-slate-200">Google Gemini</strong>. Data from <strong className="text-slate-800 dark:text-slate-200">FMP</strong> (fundamentals) and <strong className="text-slate-800 dark:text-slate-200">Tiger</strong> (option chains). <strong className="text-slate-800 dark:text-slate-200">Five specialist agents</strong> plus <strong className="text-slate-800 dark:text-slate-200">Deep Research</strong> with live search. <strong className="text-slate-800 dark:text-slate-200">Analysis & research only—we do not execute trades.</strong>
          </p>
        </div>
      </section>

      {/* Core Capabilities — each in full detail */}
      <section className="container mx-auto px-6 py-20">
        <div className="text-center mb-14">
          <h2 className="text-3xl md:text-4xl font-bold text-slate-900 dark:text-white mb-3">
            {t("features.title")}
          </h2>
          <p className="text-slate-600 dark:text-slate-400 max-w-xl mx-auto">
            {t("features.subtitle")}
          </p>
        </div>

        <div className="max-w-3xl mx-auto space-y-8">
          <Card className="border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/80 shadow-md rounded-xl overflow-hidden">
            <CardHeader>
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center flex-shrink-0">
                  <Brain className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                </div>
                <div>
                  <CardTitle className="text-xl">{t("features.ai.title")}</CardTitle>
                  <CardDescription>{t("features.ai.desc")}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                {t("features.ai.full")}
              </p>
            </CardContent>
          </Card>

          <Card className="border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/80 shadow-md rounded-xl overflow-hidden">
            <CardHeader>
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 flex items-center justify-center flex-shrink-0">
                  <BarChart3 className="h-6 w-6 text-indigo-600 dark:text-indigo-400" />
                </div>
                <div>
                  <CardTitle className="text-xl">{t("features.charts.title")}</CardTitle>
                  <CardDescription>{t("features.charts.desc")}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                {t("features.charts.full")}
              </p>
            </CardContent>
          </Card>

          <Card className="border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/80 shadow-md rounded-xl overflow-hidden">
            <CardHeader>
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-lg bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center flex-shrink-0">
                  <TrendingUp className="h-6 w-6 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <CardTitle className="text-xl">{t("features.data.title")}</CardTitle>
                  <CardDescription>{t("features.data.desc")}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                {t("features.data.full")}
              </p>
            </CardContent>
          </Card>

          <Card className="border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/80 shadow-md rounded-xl overflow-hidden">
            <CardHeader>
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center flex-shrink-0">
                  <Zap className="h-6 w-6 text-green-600 dark:text-green-400" />
                </div>
                <div>
                  <CardTitle className="text-xl">{t("features.builder.title")}</CardTitle>
                  <CardDescription>{t("features.builder.desc")}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                {t("features.builder.full")}
              </p>
            </CardContent>
          </Card>

          <Card className="border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/80 shadow-md rounded-xl overflow-hidden">
            <CardHeader>
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-lg bg-red-100 dark:bg-red-900/30 flex items-center justify-center flex-shrink-0">
                  <Shield className="h-6 w-6 text-red-600 dark:text-red-400" />
                </div>
                <div>
                  <CardTitle className="text-xl">{t("features.risk.title")}</CardTitle>
                  <CardDescription>{t("features.risk.desc")}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                {t("features.risk.full")}
              </p>
            </CardContent>
          </Card>

          <Card className="border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/80 shadow-md rounded-xl overflow-hidden">
            <CardHeader>
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-lg bg-slate-100 dark:bg-slate-700 flex items-center justify-center flex-shrink-0">
                  <ListTodo className="h-6 w-6 text-slate-600 dark:text-slate-400" />
                </div>
                <div>
                  <CardTitle className="text-xl">{t("features.tasks.title")}</CardTitle>
                  <CardDescription>{t("features.tasks.desc")}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                {t("features.tasks.full")}
              </p>
            </CardContent>
          </Card>

          <Card className="border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/80 shadow-md rounded-xl overflow-hidden">
            <CardHeader>
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center flex-shrink-0">
                  <ImageIcon className="h-6 w-6 text-amber-600 dark:text-amber-400" />
                </div>
                <div>
                  <CardTitle className="text-xl">{t("features.nano.title")}</CardTitle>
                  <CardDescription>{t("features.nano.desc")}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                {t("features.nano.full")}
              </p>
            </CardContent>
          </Card>

          <Card className="border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/80 shadow-md rounded-xl overflow-hidden">
            <CardHeader>
              <div className="flex items-center gap-4">
                <div className="h-12 w-12 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center flex-shrink-0">
                  <FileText className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
                </div>
                <div>
                  <CardTitle className="text-xl">{t("features.reports.title")}</CardTitle>
                  <CardDescription>{t("features.reports.desc")}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed">
                {t("features.reports.full")}
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* How It Works */}
      <section className="container mx-auto px-6 py-20">
        <div className="max-w-4xl mx-auto p-8 md:p-12 rounded-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/80 shadow-xl shadow-slate-200/20 dark:shadow-none">
          <div className="text-center mb-14">
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 dark:text-white mb-3">
              {t("how.title")}
            </h2>
            <p className="text-slate-600 dark:text-slate-400">
              {t("how.subtitle")}
            </p>
          </div>

          <div className="space-y-8">
            <div className="flex gap-6">
              <div className="flex-shrink-0">
                <div className="h-12 w-12 rounded-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white flex items-center justify-center font-bold text-lg">
                  1
                </div>
              </div>
              <div>
                <h3 className="text-xl font-semibold mb-2 text-slate-900 dark:text-slate-100">
                  {t("how.step1.title")}
                </h3>
                <p className="text-slate-600 dark:text-slate-300">
                  {t("how.step1.desc")}
                </p>
              </div>
            </div>

            <div className="flex gap-6">
              <div className="flex-shrink-0">
                <div className="h-12 w-12 rounded-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white flex items-center justify-center font-bold text-lg">
                  2
                </div>
              </div>
              <div>
                <h3 className="text-xl font-semibold mb-2 text-slate-900 dark:text-slate-100">
                  {t("how.step2.title")}
                </h3>
                <p className="text-slate-600 dark:text-slate-300">
                  {t("how.step2.desc")}
                </p>
              </div>
            </div>

            <div className="flex gap-6">
              <div className="flex-shrink-0">
                <div className="h-12 w-12 rounded-full bg-gradient-to-r from-purple-600 to-pink-600 text-white flex items-center justify-center font-bold text-lg">
                  3
                </div>
              </div>
              <div>
                <h3 className="text-xl font-semibold mb-2 text-slate-900 dark:text-slate-100">
                  {t("how.step3.title")}
                </h3>
                <p className="text-slate-600 dark:text-slate-300">
                  {t("how.step3.desc")}
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-6 py-24">
        <div className="max-w-2xl mx-auto text-center p-10 rounded-2xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
          <h2 className="text-2xl md:text-3xl font-bold mb-4 text-slate-900 dark:text-white">
            {t("cta.title")}
          </h2>
          <p className="text-slate-600 dark:text-slate-400 mb-8">
            {t("cta.subtitle")}
          </p>
          <Button 
            size="lg" 
            className="rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white px-8 shadow-lg shadow-indigo-500/25" 
            asChild
          >
            {!isLoading && isAuthenticated ? (
              <Link to="/dashboard">
                <LayoutDashboard className="mr-2 h-5 w-5 inline" />
                Go to Dashboard
                <ArrowRight className="ml-2 h-5 w-5 inline" />
              </Link>
            ) : (
              <Link to="/login">
                {t("cta.button")}
                <ArrowRight className="ml-2 h-5 w-5 inline" />
              </Link>
            )}
          </Button>
          
          <div className="mt-10 flex flex-wrap items-center justify-center gap-6 text-sm text-slate-500 dark:text-slate-400">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <span>{t("cta.free")}</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <span>{t("cta.noCard")}</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <span>{t("cta.toolOnly")}</span>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="container mx-auto px-6 py-12 mt-8 border-t border-slate-200/80 dark:border-slate-700/80 bg-slate-50/50 dark:bg-slate-900/30">
        <div className="flex flex-col items-center gap-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 w-full">
            <div className="flex items-center gap-2">
              <Zap className="h-6 w-6 text-primary" />
              <span className="text-lg font-semibold">ThetaMind</span>
            </div>
            <div className="flex items-center gap-4 text-sm text-slate-500 dark:text-slate-400">
              <a 
                href="https://show.thetamind.ai/privacy_policy" 
                target="_blank" 
                rel="noopener noreferrer"
                className="hover:text-primary dark:hover:text-primary transition-colors"
              >
                Privacy Policy
              </a>
              <span className="text-slate-400">•</span>
              <a 
                href="https://show.thetamind.ai/terms_of_service" 
                target="_blank" 
                rel="noopener noreferrer"
                className="hover:text-primary dark:hover:text-primary transition-colors"
              >
                Terms of Service
              </a>
            </div>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400 text-center">
            {t("footer.copyright")}
          </p>
        </div>
      </footer>
    </div>
  )
}
