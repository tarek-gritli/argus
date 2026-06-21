import type { Billing } from "@/lib/types"

const PLAN_CONFIG: Record<string, { label: string; price: string; description: string }> = {
  free:       { label: "Starter tier",  price: "$0",   description: "Perfect for individual developers and small open-source projects." },
  pro:        { label: "Pro",           price: "$29",  description: "Unlimited reviews and advanced AI linting." },
  team:       { label: "Team",          price: "$75+", description: "Centralized review engine for engineering orgs." },
  enterprise: { label: "Enterprise",    price: "—",    description: "Custom limits and dedicated support." },
}

export function PlanCard({ billing }: { billing: Billing }) {
  const cfg = PLAN_CONFIG[billing.plan] ?? PLAN_CONFIG.free
  return (
    <div className="border border-white/[0.08] p-6" style={{ background: "rgba(255,255,255,0.04)" }}>
      <div className="flex items-start justify-between mb-6">
        <div>
          <span className="text-[10px] font-bold tracking-wider uppercase text-[#c6c6c7] block mb-1">Current Plan</span>
          <h2 className="text-[18px] font-semibold leading-6 tracking-[-0.01em] text-[#e5e2e1]">{cfg.label}</h2>
          <p className="text-[12px] text-[#8e9192] mt-1">{cfg.description}</p>
        </div>
        <div className="border-l-2 border-[#e2e2e2] bg-[#2a2a2a] px-3 py-1">
          <span className="text-[10px] font-bold tracking-wider uppercase text-[#e2e2e2]">ACTIVE</span>
        </div>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-[24px] font-semibold leading-8 tracking-[-0.02em] text-[#e5e2e1]">{cfg.price}</span>
        <span className="text-[14px] text-[#8e9192]">/ month</span>
      </div>
      {billing.plan !== "free" && (
        <p className="text-[12px] text-[#8e9192] mt-2">
          {billing.seat_count} {billing.seat_count === 1 ? "seat" : "seats"} · {billing.monthly_limit} reviews / month
        </p>
      )}
    </div>
  )
}
