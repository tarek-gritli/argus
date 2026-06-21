"use client"

import { useRouter } from "next/navigation"
import { api } from "@/lib/api"
import { LogOut } from "lucide-react"

export function Topbar({ title }: { title: string }) {
  const router = useRouter()

  async function handleLogout() {
    await api.auth.logout().catch(() => null)
    router.replace("/login")
  }

  return (
    <header className="h-14 border-b border-border flex items-center justify-between px-6 shrink-0 bg-background">
      <h1 className="text-sm font-semibold text-foreground tracking-tight">{title}</h1>
      <button
        onClick={handleLogout}
        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors py-1.5 px-2 rounded hover:bg-muted"
      >
        <LogOut className="h-3.5 w-3.5" />
        Sign out
      </button>
    </header>
  )
}
