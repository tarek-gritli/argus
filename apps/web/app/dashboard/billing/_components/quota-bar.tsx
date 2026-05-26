import type { Billing } from "@/lib/types"
import { cn } from "@/lib/utils"

export function QuotaBar({ billing }: { billing: Billing }) {
  const pct = Math.min(100, Math.round((billing.reviews_used_this_month / billing.monthly_limit) * 100))
  const isNearLimit = pct >= 80
  const isCritical = pct >= 95

  return (
    <div className="rounded-lg border bg-card p-5">
      <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-widest mb-4">Monthly Usage</p>
      <div className="flex items-baseline justify-between mb-3">
        <span className="text-sm font-semibold text-foreground tabular-nums">
          {billing.reviews_used_this_month}
          <span className="text-muted-foreground font-normal"> / {billing.monthly_limit} reviews</span>
        </span>
        <span className={cn(
          "text-[12px] font-semibold tabular-nums",
          isCritical ? "text-red-600" : isNearLimit ? "text-orange-600" : "text-muted-foreground"
        )}>
          {pct}%
        </span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
        <div
          className={cn(
            "h-full rounded-full transition-all duration-500",
            isCritical ? "bg-red-500" : isNearLimit ? "bg-orange-500" : "bg-foreground"
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
      {isNearLimit && (
        <p className={cn(
          "text-[11px] mt-2.5 font-medium",
          isCritical ? "text-red-600" : "text-orange-600"
        )}>
          {isCritical
            ? "Quota nearly exhausted. Upgrade to continue reviewing."
            : `${pct}% of monthly quota used. Consider upgrading.`}
        </p>
      )}
    </div>
  )
}
