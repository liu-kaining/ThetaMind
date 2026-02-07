import * as React from "react"
import { Link } from "react-router-dom"
import { User, Github, Briefcase, Award, Target, ExternalLink, Zap } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { useAuth } from "@/features/auth/AuthProvider"
import { MainLayout } from "@/components/layout/MainLayout"

const AboutContent: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">About</h1>
        <p className="text-muted-foreground">
          Learn about the founder and the vision behind ThetaMind
        </p>
      </div>

      {/* Founder Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Founder
          </CardTitle>
          <CardDescription>Meet the creator of ThetaMind</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex flex-col md:flex-row gap-6 items-start">
            {/* Avatar */}
            <div className="flex-shrink-0">
              <img
                src="https://assets.thetamind.ai/info/WechatIMG5.jpg"
                alt="Albert Liu (Kaining Liu)"
                className="w-32 h-32 rounded-full object-cover border-4 border-primary/20 shadow-lg"
              />
            </div>
            
            {/* Info */}
            <div className="flex-1 space-y-4">
              <div>
                <h2 className="text-2xl font-bold">Albert Liu</h2>
                <p className="text-muted-foreground">Also known as Kaining Liu</p>
              </div>
              
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  asChild
                >
                  <a
                    href="https://github.com/liu-kaining"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2"
                  >
                    <Github className="h-4 w-4" />
                    GitHub Profile
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </Button>
              </div>
            </div>
          </div>

          <Separator />

          {/* Tagline */}
          <div className="space-y-2">
            <h3 className="text-lg font-semibold flex items-center gap-2">
              <Target className="h-5 w-5 text-primary" />
              Vision
            </h3>
            <div className="space-y-3 text-muted-foreground">
              <p className="text-base leading-relaxed">
                <strong className="text-foreground">Architected for Scale. Built by Experience.</strong>
              </p>
              <p className="text-sm leading-relaxed">
                Founded by a Senior Software Architect and Options Trader with 10+ years of frontline experience. 
                ThetaMind was born from the need to bridge the gap between High-Availability institutional quant 
                systems and retail accessibility.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Experience Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Briefcase className="h-5 w-5" />
            Experience
          </CardTitle>
          <CardDescription>Professional background</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <div className="mt-1">
                <Award className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1">
                <p className="font-semibold">10+ Years of Backend Development</p>
                <p className="text-sm text-muted-foreground">
                  Extensive experience in large-scale Chinese internet companies, 
                  specializing in high-availability distributed systems and microservices architecture.
                </p>
              </div>
            </div>
            
            <Separator />
            
            <div className="flex items-start gap-3">
              <div className="mt-1">
                <Award className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1">
                <p className="font-semibold">SRE Technical Expert</p>
                <p className="text-sm text-muted-foreground">
                  Previously served as SRE Technical Expert at a leading fintech company, 
                  responsible for system reliability, performance optimization, and infrastructure automation.
                </p>
              </div>
            </div>
            
            <Separator />
            
            <div className="flex items-start gap-3">
              <div className="mt-1">
                <Award className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1">
                <p className="font-semibold">Options Trading Experience</p>
                <p className="text-sm text-muted-foreground">
                  Years of hands-on experience in options trading, understanding the practical 
                  challenges traders face in strategy analysis and risk management.
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Mission Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Target className="h-5 w-5" />
            Mission
          </CardTitle>
          <CardDescription>Why ThetaMind exists</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 text-muted-foreground">
            <p className="leading-relaxed">
              ThetaMind was created to serve traders, university students, and options enthusiasts 
              by providing educational resources and AI-powered analysis tools for optimal option strategies.
            </p>
            <p className="leading-relaxed">
              Our goal is to democratize access to professional-grade options analysis tools, 
              making complex strategies accessible to everyone while maintaining the rigor and 
              accuracy expected from institutional systems.
            </p>
            <p className="leading-relaxed">
              Through AI-driven insights and intuitive visualization, we aim to bridge the gap 
              between high-availability institutional quant systems and retail accessibility, 
              empowering users to make informed trading decisions.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// Public layout for unauthenticated users
const PublicLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated } = useAuth()
  
  if (isAuthenticated) {
    return <MainLayout>{children}</MainLayout>
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 dark:from-slate-900 dark:via-slate-800 dark:to-slate-900">
      {/* Navigation */}
      <nav className="container mx-auto px-6 py-6">
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
          <div className="flex items-center gap-4">
            <Button variant="ghost" asChild className="hidden md:flex">
              <Link to="/demo">Demo</Link>
            </Button>
            <Button 
              asChild
              className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white shadow-lg hover:shadow-xl transition-all"
            >
              <Link to="/login">Get Started</Link>
            </Button>
            <Button variant="ghost" asChild className="hidden md:flex">
              <Link to="/about">About Founder</Link>
            </Button>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="container mx-auto px-6 py-8 max-w-4xl">
        {children}
      </main>
    </div>
  )
}

export const AboutPage: React.FC = () => {
  return (
    <PublicLayout>
      <AboutContent />
    </PublicLayout>
  )
}
