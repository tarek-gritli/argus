"use client"

import Link from "next/link"
import { useState, useEffect } from "react"
import { cn } from "@/lib/utils"
import { BASE as API_URL } from "@/lib/api"

export function Nav() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 20)
    window.addEventListener("scroll", handler, { passive: true })
    return () => window.removeEventListener("scroll", handler)
  }, [])

  return (
    <header
      className={cn(
        "fixed top-0 inset-x-0 z-50 transition-all duration-300",
        scrolled
          ? "bg-[oklch(0.10_0_0)]/90 backdrop-blur border-b border-white/5"
          : "bg-transparent"
      )}
    >
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/home" className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded bg-white/10 flex items-center justify-center">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <circle cx="7" cy="7" r="6" stroke="white" strokeWidth="1.5" />
              <circle cx="7" cy="7" r="2.5" fill="white" />
            </svg>
          </div>
          <span className="font-semibold text-[13px] tracking-wide text-white/90">ARGUS</span>
        </Link>

        <nav className="hidden md:flex items-center gap-8 text-[13px] text-zinc-500">
          <a href="#features" className="hover:text-zinc-200 transition-colors">Features</a>
          <a href="#how-it-works" className="hover:text-zinc-200 transition-colors">How it works</a>
          <a href="#pricing" className="hover:text-zinc-200 transition-colors">Pricing</a>
          <Link href="/docs" className="hover:text-zinc-200 transition-colors">Docs</Link>
        </nav>

        <div className="flex items-center gap-4">
          <a
            href={`${API_URL}/api/v1/auth/github/login`}
            className="text-[13px] text-zinc-500 hover:text-zinc-200 transition-colors"
          >
            Sign in
          </a>
          <a
            href={`${API_URL}/api/v1/auth/github/login`}
            className="text-[13px] bg-white text-black font-semibold px-4 py-2 rounded-lg hover:bg-zinc-100 transition-colors"
          >
            Get started free
          </a>
        </div>
      </div>
    </header>
  )
}
