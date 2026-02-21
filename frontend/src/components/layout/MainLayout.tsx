import React, { useState } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import {
  LayoutDashboard,
  FlaskConical,
  Calendar,
  FileText,
  Settings,
  Menu,
  X,
  Moon,
  Sun,
  LogOut,
  Shield,
  Home,
  ListChecks,
  BarChart3,
} from "lucide-react"
import { useAuth } from "@/features/auth/AuthProvider"
import { useFeatureFlags } from "@/hooks/useFeatureFlags"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { cn } from "@/lib/utils"

interface NavItem {
  label: string
  path: string
  icon: React.ComponentType<{ className?: string }>
}

// Base nav: same on every render so Company Data etc. never "missing" on first paint (e.g. after login)
const BASE_NAV_ITEMS: NavItem[] = [
  { label: "Dashboard", path: "/dashboard", icon: LayoutDashboard },
  { label: "Strategy Lab", path: "/strategy-lab", icon: FlaskConical },
  { label: "Company Data", path: "/company-data", icon: BarChart3 },
  { label: "Reports", path: "/reports", icon: FileText },
  { label: "Task Center", path: "/dashboard/tasks", icon: ListChecks },
  { label: "Pricing", path: "/pricing", icon: FileText },
  { label: "Settings", path: "/settings", icon: Settings },
]

function getNavItems(isSuperuser: boolean, dailyPicksEnabled: boolean): NavItem[] {
  const items: NavItem[] = [
    BASE_NAV_ITEMS[0], // Dashboard
    ...(dailyPicksEnabled ? [{ label: "Daily Picks", path: "/daily-picks", icon: Calendar }] : []),
    ...BASE_NAV_ITEMS.slice(1), // Strategy Lab, Company Data, Reports, ...
  ]
  if (isSuperuser) {
    items.push(
      { label: "Admin Settings", path: "/admin/settings", icon: Shield },
      { label: "User Management", path: "/admin/users", icon: Shield }
    )
  }
  return items
}

export const MainLayout: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  // Sidebar state: default to open on desktop, closed on mobile
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    // Check localStorage for saved preference
    const saved = localStorage.getItem("sidebarOpen")
    if (saved !== null) return saved === "true"
    // Default: open on desktop (>= 1024px), closed on mobile
    return window.innerWidth >= 1024
  })
  // Theme: prefer saved, else time-based (UTC+8: 6:00–18:00 light, else dark)
  const getInitialTheme = (): "light" | "dark" => {
    const saved = localStorage.getItem("theme")
    if (saved === "light" || saved === "dark") return saved
    const beijingHour = (new Date().getUTCHours() + 8) % 24
    return beijingHour >= 6 && beijingHour < 18 ? "light" : "dark"
  }
  const [theme, setTheme] = useState<"light" | "dark">(getInitialTheme)
  const { user, logout } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const { daily_picks_enabled = false } = useFeatureFlags()

  // 直接计算，不用 useMemo，确保登录后首帧就有 Company Data（避免 memo 导致首帧用旧值）
  const isSuperuser = Boolean((user as { is_superuser?: boolean })?.is_superuser)
  const navItems = getNavItems(isSuperuser, daily_picks_enabled)

  // Save sidebar state to localStorage
  React.useEffect(() => {
    localStorage.setItem("sidebarOpen", sidebarOpen.toString())
  }, [sidebarOpen])

  // Apply theme on mount and when theme changes
  React.useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark")
  }, [theme])

  const toggleTheme = () => {
    const newTheme = theme === "light" ? "dark" : "light"
    setTheme(newTheme)
    localStorage.setItem("theme", newTheme)
    document.documentElement.classList.toggle("dark", newTheme === "dark")
  }

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen)
  }

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 bg-card border-r border-border transition-transform duration-300",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-full flex-col">
          {/* Logo */}
          <div className="flex h-16 items-center justify-between border-b border-border px-6">
            <Link 
              to="/dashboard" 
              className="text-xl font-bold text-foreground hover:text-primary transition-colors cursor-pointer"
              onClick={() => {
                // Only auto-close on mobile
                if (window.innerWidth < 1024) {
                  setSidebarOpen(false)
                }
              }}
            >
              ThetaMind
            </Link>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 space-y-1 p-4">
            {navItems.map((item) => {
              const Icon = item.icon
              const isActive = location.pathname === item.path
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setSidebarOpen(false)}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  )}
                >
                  <Icon className="h-5 w-5" />
                  {item.label}
                </Link>
              )
            })}
          </nav>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main content — min-w-0 allows flex child to shrink and prevents overflow on small screens */}
      <div className={cn(
        "flex flex-1 flex-col min-w-0 transition-all duration-300",
        sidebarOpen ? "lg:pl-64" : "lg:pl-0"
      )}>
        {/* Header */}
        <header className="sticky top-0 z-40 flex h-16 items-center gap-2 sm:gap-4 border-b border-border bg-background px-3 sm:px-4 lg:px-6">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            title={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
          >
            <Menu className="h-5 w-5" />
          </Button>

          <div className="flex flex-1 items-center justify-end gap-4">
            {/* Theme Toggle */}
            <Button variant="ghost" size="icon" onClick={toggleTheme}>
              {theme === "light" ? (
                <Moon className="h-5 w-5" />
              ) : (
                <Sun className="h-5 w-5" />
              )}
            </Button>

            {/* User Menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative h-10 w-10 rounded-full">
                  <Avatar className="h-10 w-10">
                    <AvatarFallback className="bg-primary/10 text-primary font-semibold">
                      {user?.email?.charAt(0).toUpperCase() || "U"}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <div className="px-2 py-1.5">
                  <p className="text-sm font-medium">{user?.email}</p>
                  {user?.is_pro && (
                    <p className="text-xs text-muted-foreground">Pro Plan</p>
                  )}
                </div>
                <DropdownMenuItem 
                  onClick={() => {
                    navigate("/")
                    setSidebarOpen(false)
                  }}
                >
                  <Home className="mr-2 h-4 w-4" />
                  <span>Home</span>
                </DropdownMenuItem>
                <DropdownMenuItem 
                  onClick={() => {
                    logout()
                    navigate("/login")
                    setSidebarOpen(false)
                  }}
                >
                  <LogOut className="mr-2 h-4 w-4" />
                  <span>Log out</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto overflow-x-hidden p-3 sm:p-4 lg:p-6 min-w-0">{children}</main>
      </div>
    </div>
  )
}

