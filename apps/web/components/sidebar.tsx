"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { LayoutDashboard, GitPullRequest, CreditCard, Plug, Settings } from "lucide-react"

const NAV = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/reviews", label: "Reviews", icon: GitPullRequest },
  { href: "/dashboard/billing", label: "Billing", icon: CreditCard },
  { href: "/dashboard/integrations", label: "Integrations", icon: Plug },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()
  return (
    <aside className="hidden md:flex w-56 flex-col bg-sidebar shrink-0 border-r border-sidebar-border">
      <div className="flex items-center gap-2.5 px-5 h-14 border-b border-sidebar-border">
        <div className="w-6 h-6 rounded bg-white/10 flex items-center justify-center">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <circle cx="7" cy="7" r="6" stroke="white" strokeWidth="1.5" />
            <circle cx="7" cy="7" r="2.5" fill="white" />
          </svg>
        </div>
        <span className="font-semibold text-[13px] tracking-wide text-white/90">ARGUS</span>
      </div>
      <nav className="flex flex-col gap-0.5 flex-1 px-3 py-4">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href))
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded px-3 py-2 text-[13px] font-medium transition-all duration-150",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground hover:text-sidebar-accent-foreground hover:bg-sidebar-accent/60"
              )}
            >
              <Icon className={cn("h-4 w-4 shrink-0", active ? "opacity-100" : "opacity-60")} />
              {label}
            </Link>
          )
        })}
      </nav>
      <div className="px-5 py-4 border-t border-sidebar-border">
        <p className="text-[10px] font-mono text-sidebar-foreground/40 uppercase tracking-wider">v0.1.0</p>
      </div>
    </aside>
  )
}
