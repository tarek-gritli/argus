import type { Billing } from "@/lib/types"
import { cn } from "@/lib/utils"

const PLAN_CONFIG: Record<string, { label: string; style: string }> = {
  free:       { label: "Free",       style: "bg-muted border-border text-muted-foreground" },
  pro:        { label: "Pro",        style: "bg-blue-500/8 border-blue-500/20 text-blue-700 dark:text-blue-400" },
  team:       { label: "Team",       style: "bg-violet-500/8 border-violet-500/20 text-violet-700 dark:text-violet-400" },
  enterprise: { label: "Enterprise", style: "bg-amber-500/8 border-amber-500/20 text-amber-700 dark:text-amber-400" },
}

export function PlanCard({ billing }: { billing: Billing }) {
  const cfg = PLAN_CONFIG[billing.plan] ?? PLAN_CONFIG.free
  return (
    <div className="rounded-lg border bg-card p-5">
      <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-widest mb-4">Current Plan</p>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-2xl font-bold text-foreground">{cfg.label}</p>
          <p className="text-[12px] text-muted-foreground mt-1.5">
            {billing.plan !== "free" && (
              <span>{billing.seat_count} {billing.seat_count === 1 ? "seat" : "seats"} · </span>
            )}
            {billing.monthly_limit} reviews / month
          </p>
        </div>
        <span className={cn("px-3 py-1 rounded-full border text-[11px] font-semibold", cfg.style)}>
          {cfg.label}
        </span>
      </div>
    </div>
  )
}
