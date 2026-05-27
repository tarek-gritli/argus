import type { Billing } from "@/lib/types"

export function QuotaBar({ billing }: { billing: Billing }) {
  const pct = Math.min(100, Math.round((billing.reviews_used_this_month / billing.monthly_limit) * 100))
  const isCritical = pct >= 95
  const isNearLimit = pct >= 80

  const barColor = isCritical ? "#ffb4ab" : isNearLimit ? "#c6c6c7" : "#e2e2e2"

  return (
    <div className="border-t border-white/5 pt-6 mt-2">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-bold tracking-wider uppercase text-[#8e9192]">Reviews This Month</span>
        <span className="text-[10px] font-bold tracking-wider uppercase text-[#e5e2e1]">
          {billing.reviews_used_this_month} / {billing.monthly_limit}
        </span>
      </div>
      <div className="h-1.5 w-full bg-[#2a2a2a] overflow-hidden">
        <div
          className="h-full transition-all duration-1000 ease-out"
          style={{ width: `${pct}%`, backgroundColor: barColor }}
        />
      </div>
      {isNearLimit && (
        <p className="text-[12px] text-[#8e9192] mt-2">
          {isCritical
            ? "Quota nearly exhausted. Upgrade to continue reviewing."
            : "You will reach your limit soon at current usage."}
        </p>
      )}
    </div>
  )
}
