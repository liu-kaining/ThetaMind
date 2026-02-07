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

      {/* Hero Section — value-first: headline, bullets, pipeline visual */}
      <section className="container mx-auto px-6 pt-12 pb-16 sm:pt-14 sm:pb-20">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col lg:flex-row lg:items-center lg:gap-12 xl:gap-16">
            {/* Left: Copy + bullets + CTA */}
            <div className="flex-1 text-center lg:text-left order-2 lg:order-1">
              <p className="text-xs tracking-wide text-slate-500 dark:text-slate-400 uppercase mb-4 flex items-center justify-center lg:justify-start gap-2">
                <Shield className="h-3.5 w-3.5" />
                {t("hero.badge")}
              </p>
              <h1 className="text-3xl sm:text-4xl lg:text-[2.75rem] xl:text-[3rem] font-extrabold tracking-tight text-slate-900 dark:text-white leading-[1.4] mb-7">
                <span className="block">{t("hero.title.part1")}</span>
                <span className="block mt-3 sm:mt-4 bg-gradient-to-r from-indigo-600 to-violet-600 dark:from-indigo-400 dark:to-violet-400 bg-clip-text text-transparent">{t("hero.title.part2")}</span>
              </h1>
              <p className="text-slate-600 dark:text-slate-400 text-base sm:text-lg max-w-xl mx-auto lg:mx-0 leading-relaxed mb-6 font-medium">
                {t("hero.subline")}
              </p>
              {/* 4 punchy bullets — why we're different */}
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2.5 max-w-xl mx-auto lg:mx-0 mb-8 text-left">
                <li className="flex items-center gap-2.5 text-slate-700 dark:text-slate-300 text-sm">
                  <span className="flex-shrink-0 w-6 h-6 rounded-md bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center">
                    <Brain className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
                  </span>
                  {t("hero.bullet1")}
                </li>
                <li className="flex items-center gap-2.5 text-slate-700 dark:text-slate-300 text-sm">
                  <span className="flex-shrink-0 w-6 h-6 rounded-md bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center">
                    <Search className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
                  </span>
                  {t("hero.bullet2")}
                </li>
                <li className="flex items-center gap-2.5 text-slate-700 dark:text-slate-300 text-sm">
                  <span className="flex-shrink-0 w-6 h-6 rounded-md bg-emerald-100 dark:bg-emerald-900/40 flex items-center justify-center">
                    <BarChart3 className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                  </span>
                  {t("hero.bullet3")}
                </li>
                <li className="flex items-center gap-2.5 text-slate-700 dark:text-slate-300 text-sm">
                  <span className="flex-shrink-0 w-6 h-6 rounded-md bg-violet-100 dark:bg-violet-900/40 flex items-center justify-center">
                    <FileText className="h-3.5 w-3.5 text-violet-600 dark:text-violet-400" />
                  </span>
                  {t("hero.bullet4")}
                </li>
              </ul>
              <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-3">
                {!isLoading && isAuthenticated ? (
                  <Button size="lg" className="w-full sm:w-auto rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white px-7" asChild>
                    <Link to="/dashboard" className="inline-flex items-center justify-center gap-2">
                      <LayoutDashboard className="h-4 w-4 shrink-0" />
                      Go to Dashboard
                      <ArrowRight className="h-4 w-4 shrink-0" />
                    </Link>
                  </Button>
                ) : (
                  <>
                    <Button size="lg" className="w-full sm:w-auto rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white px-7 shadow-lg hover:shadow-xl transition-shadow" asChild>
                      <Link to="/login" className="inline-flex items-center justify-center gap-2">
                        {t("hero.cta.primary")}
                        <ArrowRight className="h-4 w-4 shrink-0" />
                      </Link>
                    </Button>
                    <Button size="lg" variant="outline" className="w-full sm:w-auto rounded-lg border-slate-300 dark:border-slate-600 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800" asChild>
                      <Link to="/demo">{t("hero.cta.secondary")}</Link>
                    </Button>
                  </>
                )}
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-5 max-w-lg mx-auto lg:mx-0">
                {t("stack.title")} Google Cloud · Gemini · FMP · Tiger · Real-time charts · Full audit
              </p>
            </div>

            {/* Right: One pipeline — prominent card */}
            <div className="flex-1 flex justify-center lg:justify-end order-1 lg:order-2 mb-8 lg:mb-0">
              <div className="w-full max-w-[380px] lg:max-w-[420px]">
                <div className="rounded-2xl border-2 border-indigo-200/80 dark:border-indigo-500/30 bg-gradient-to-b from-white to-indigo-50/40 dark:from-slate-800 dark:to-indigo-950/30 shadow-2xl shadow-indigo-200/30 dark:shadow-indigo-900/20 overflow-hidden">
                  <div className="px-5 py-4 border-b border-indigo-100 dark:border-indigo-500/20 bg-indigo-50/60 dark:bg-indigo-950/40">
                    <p className="text-sm font-bold text-indigo-900 dark:text-indigo-100">{t("hero.pipeline.label")}</p>
                    <p className="text-xs text-indigo-700/80 dark:text-indigo-300/80 mt-0.5">Strategy → Agents → Research → Report</p>
                  </div>
                  <div className="p-5 sm:p-6 flex flex-col gap-4">
                    {[
                      { icon: Layers, label: t("hero.pipeline.step1"), iconBg: "bg-indigo-100 dark:bg-indigo-900/40", iconColor: "text-indigo-600 dark:text-indigo-400" },
                      { icon: Brain, label: t("hero.pipeline.step2"), iconBg: "bg-blue-100 dark:bg-blue-900/40", iconColor: "text-blue-600 dark:text-blue-400" },
                      { icon: Search, label: t("hero.pipeline.step3"), iconBg: "bg-emerald-100 dark:bg-emerald-900/40", iconColor: "text-emerald-600 dark:text-emerald-400" },
                      { icon: FileText, label: t("hero.pipeline.step4"), iconBg: "bg-violet-100 dark:bg-violet-900/40", iconColor: "text-violet-600 dark:text-violet-400" },
                    ].map((step, i) => (
                      <div key={i} className="flex items-center gap-4">
                        <span className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center ${step.iconBg}`}>
                          <step.icon className={`h-5 w-5 ${step.iconColor}`} />
                        </span>
                        <span className="text-base font-semibold text-slate-800 dark:text-slate-100">{step.label}</span>
                        {i < 3 && <ArrowRight className="h-5 w-5 text-indigo-400 dark:text-indigo-500 flex-shrink-0 ml-auto" />}
                      </div>
                    ))}
                  </div>
                  <div className="px-5 py-3.5 border-t border-indigo-100 dark:border-indigo-500/20 bg-indigo-50/40 dark:bg-indigo-950/30 flex items-center justify-between text-xs font-medium text-indigo-800/90 dark:text-indigo-200/90">
                    <span>Real chains · FMP</span>
                    <span>Full audit</span>
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
