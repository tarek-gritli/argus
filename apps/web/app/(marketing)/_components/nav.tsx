"use client"

import type React from "react"
import { useState } from "react"
import Link from "next/link"
import { Menu, X } from "lucide-react"
import { BASE as API_URL } from "@/lib/api"

const NAV_ITEMS = [
  { name: "Features", href: "#features-section" },
  { name: "Pricing", href: "#pricing-section" },
  { name: "Testimonials", href: "#testimonials-section" },
]

function handleScroll(e: React.MouseEvent<HTMLAnchorElement>, href: string) {
  e.preventDefault()
  const el = document.getElementById(href.slice(1))
  if (el) el.scrollIntoView({ behavior: "smooth" })
}

export function Nav() {
  const [open, setOpen] = useState(false)

  return (
    <header className="w-full py-4 px-6">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-3">
            <span className="text-foreground text-xl font-semibold">Argus</span>
          </div>
          <nav className="hidden md:flex items-center gap-2">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.name}
                href={item.href}
                onClick={(e) => handleScroll(e, item.href)}
                className="text-[#888888] hover:text-foreground px-4 py-2 rounded-full font-medium transition-colors"
              >
                {item.name}
              </Link>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-4">
          <a
            href={`${API_URL}/api/v1/auth/github/login`}
            className="hidden md:block bg-secondary text-secondary-foreground hover:bg-secondary/90 px-6 py-2 rounded-full font-medium shadow-sm text-sm"
          >
            Try for Free
          </a>
          <button
            className="md:hidden text-foreground"
            onClick={() => setOpen(true)}
            aria-label="Open menu"
          >
            <Menu className="h-7 w-7" />
          </button>
        </div>
      </div>

      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-50 bg-background/80" onClick={() => setOpen(false)}>
          <div
            className="absolute bottom-0 inset-x-0 bg-background border-t border-border p-6 rounded-t-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-6">
              <span className="text-xl font-semibold text-foreground">Navigation</span>
              <button onClick={() => setOpen(false)} className="text-muted-foreground hover:text-foreground">
                <X className="h-5 w-5" />
              </button>
            </div>
            <nav className="flex flex-col gap-4">
              {NAV_ITEMS.map((item) => (
                <a
                  key={item.name}
                  href={item.href}
                  onClick={(e) => { handleScroll(e, item.href); setOpen(false) }}
                  className="text-[#888888] hover:text-foreground text-lg py-2 transition-colors"
                >
                  {item.name}
                </a>
              ))}
              <a
                href={`${API_URL}/api/v1/auth/github/login`}
                className="w-full mt-4 bg-secondary text-secondary-foreground hover:bg-secondary/90 px-6 py-2 rounded-full font-medium shadow-sm text-sm text-center"
              >
                Try for Free
              </a>
            </nav>
          </div>
        </div>
      )}
    </header>
  )
}
