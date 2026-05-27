"use client"

import { useState } from "react"
import { X, Check } from "lucide-react"
import { api } from "@/lib/api"
import { toast } from "sonner"

const PRO_FEATURES = ["Unlimited Automated Reviews", "Advanced Security Scanning", "CI/CD Integration"]
const TEAM_FEATURES = ["Shared Review Standards", "SAML SSO & Admin Logs", "Priority Support"]

export function UpgradeDialog() {
  const [open, setOpen] = useState(false)
  const [plan, setPlan] = useState<"pro" | "team">("pro")
  const [seats, setSeats] = useState(5)
  const [loading, setLoading] = useState(false)

  async function handleCheckout() {
    setLoading(true)
    try {
      const { checkout_url } = await api.billing.checkout(plan, seats)
      window.location.href = checkout_url
    } catch {
      toast.error("Failed to start checkout")
      setLoading(false)
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="flex-1 bg-[#e2e2e2] text-[#2f3131] py-3 text-[14px] font-semibold hover:opacity-90 active:opacity-80 transition-opacity"
      >
        Upgrade Plan
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/80" onClick={() => setOpen(false)} />
          <div className="relative w-full max-w-2xl border border-white/10 overflow-hidden shadow-2xl" style={{ background: "#201f1f" }}>

            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#444748]">
              <h2 className="text-[18px] font-semibold leading-6 tracking-[-0.01em] text-[#e5e2e1]">Select a professional tier</h2>
              <button onClick={() => setOpen(false)} className="text-[#8e9192] hover:text-white transition-colors">
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Plan cards */}
            <div className="grid grid-cols-2 gap-3 p-6">
              {/* Pro */}
              <div
                onClick={() => setPlan("pro")}
                className={`border p-4 cursor-pointer flex flex-col transition-colors ${plan === "pro" ? "border-[#e2e2e2]" : "border-white/10 hover:border-white/20"}`}
                style={{ background: "rgba(255,255,255,0.02)" }}
              >
                <div className="mb-4">
                  <span className="text-[10px] font-bold tracking-wider uppercase bg-[#e2e2e2] text-[#636565] px-2 py-0.5">MOST POPULAR</span>
                </div>
                <h3 className="text-[18px] font-semibold leading-6 text-[#e5e2e1]">Pro</h3>
                <p className="text-[12px] text-[#8e9192] mt-1">Unlimited reviews and advanced AI linting.</p>
                <div className="flex items-baseline gap-1 mt-6">
                  <span className="text-[24px] font-semibold text-[#e5e2e1]">$29</span>
                  <span className="text-[14px] text-[#8e9192]">/mo</span>
                </div>
                <ul className="mt-6 space-y-3 flex-1">
                  {PRO_FEATURES.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-[12px] text-[#c4c7c8]">
                      <Check className="h-3.5 w-3.5 text-[#c6c6c7] shrink-0" /> {f}
                    </li>
                  ))}
                </ul>
                <button
                  onClick={handleCheckout}
                  disabled={loading || plan !== "pro"}
                  className="w-full mt-8 bg-[#e2e2e2] text-[#2f3131] py-2 text-[14px] font-semibold hover:opacity-90 transition-opacity disabled:opacity-40"
                >
                  {loading && plan === "pro" ? "Redirecting…" : "Get Started"}
                </button>
              </div>

              {/* Team */}
              <div
                onClick={() => setPlan("team")}
                className={`border p-4 cursor-pointer flex flex-col transition-colors ${plan === "team" ? "border-[#e2e2e2]" : "border-white/10 hover:border-white/20"}`}
                style={{ background: "rgba(255,255,255,0.02)" }}
              >
                <h3 className="text-[18px] font-semibold leading-6 text-[#e5e2e1]">Team</h3>
                <p className="text-[12px] text-[#8e9192] mt-1">Centralized review engine for engineering orgs.</p>
                <div className="mt-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-bold tracking-wider uppercase text-[#8e9192]">TEAM SEATS</span>
                    <span className="text-[10px] font-bold tracking-wider uppercase text-[#e5e2e1]">{seats} Seats</span>
                  </div>
                  <input
                    type="range"
                    min={3}
                    max={50}
                    value={seats}
                    onChange={(e) => setSeats(Number(e.target.value))}
                    className="w-full h-1 appearance-none cursor-pointer accent-[#e2e2e2]"
                    style={{ background: "#2a2a2a" }}
                  />
                </div>
                <div className="flex items-baseline gap-1 mt-4">
                  <span className="text-[24px] font-semibold text-[#e5e2e1]">${seats * 15}</span>
                  <span className="text-[14px] text-[#8e9192]">/mo</span>
                </div>
                <ul className="mt-6 space-y-3 flex-1">
                  {TEAM_FEATURES.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-[12px] text-[#c4c7c8]">
                      <Check className="h-3.5 w-3.5 text-[#c6c6c7] shrink-0" /> {f}
                    </li>
                  ))}
                </ul>
                <button
                  onClick={handleCheckout}
                  disabled={loading || plan !== "team"}
                  className="w-full mt-8 border border-white/10 text-[#e5e2e1] py-2 text-[14px] font-semibold hover:bg-white/5 transition-colors disabled:opacity-40"
                >
                  {loading && plan === "team" ? "Redirecting…" : "Contact Sales"}
                </button>
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-[#444748] flex items-center justify-center gap-4" style={{ background: "#0e0e0e" }}>
              <span className="text-[12px] text-[#8e9192]">Need more than 50 seats?</span>
              <span className="text-[12px] font-semibold text-[#c6c6c7] cursor-pointer hover:text-white transition-colors">Request Enterprise Quote</span>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
