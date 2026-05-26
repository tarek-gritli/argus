import type { Severity } from "@/lib/types"

const SEVERITIES: Severity[] = ["critical", "high", "medium", "low", "info"]

const SEVERITY_CONFIG: Record<Severity, { label: string; color: string }> = {
  critical: { label: "Critical", color: "bg-red-500" },
  high:     { label: "High",     color: "bg-orange-500" },
  medium:   { label: "Medium",   color: "bg-yellow-500" },
  low:      { label: "Low",      color: "bg-green-500" },
  info:     { label: "Info",     color: "bg-slate-400" },
}

interface Props {
  counts: Record<Severity, number>
  total: number
}

export function StatsStrip({ counts, total }: Props) {
  return (
    <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 mb-8">
      <div className="col-span-1 rounded-lg border bg-card p-4">
        <p className="text-2xl font-bold font-tabular text-foreground">{total}</p>
        <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-widest mt-1">Total</p>
      </div>
      {SEVERITIES.map((s) => (
        <div key={s} className="rounded-lg border bg-card p-4">
          <div className="flex items-center gap-1.5 mb-2">
            <span className={`w-1.5 h-1.5 rounded-full ${SEVERITY_CONFIG[s].color}`} />
          </div>
          <p className="text-2xl font-bold font-tabular text-foreground">{counts[s]}</p>
          <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-widest mt-1">
            {SEVERITY_CONFIG[s].label}
          </p>
        </div>
      ))}
    </div>
  )
}
