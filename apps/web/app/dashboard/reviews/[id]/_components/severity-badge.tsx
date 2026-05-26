import type { Severity } from "@/lib/types"
import { cn } from "@/lib/utils"

const SEVERITY_CONFIG: Record<Severity, { dot: string; label: string; style: string }> = {
  critical: { dot: "bg-red-500",    label: "Critical", style: "bg-red-500/8 border-red-500/20 text-red-700 dark:text-red-400" },
  high:     { dot: "bg-orange-500", label: "High",     style: "bg-orange-500/8 border-orange-500/20 text-orange-700 dark:text-orange-400" },
  medium:   { dot: "bg-yellow-500", label: "Medium",   style: "bg-yellow-500/8 border-yellow-500/20 text-yellow-700 dark:text-yellow-400" },
  low:      { dot: "bg-green-500",  label: "Low",      style: "bg-green-500/8 border-green-500/20 text-green-700 dark:text-green-400" },
  info:     { dot: "bg-slate-400",  label: "Info",     style: "bg-muted border-border text-muted-foreground" },
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const cfg = SEVERITY_CONFIG[severity]
  return (
    <span className={cn("inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[10px] font-bold uppercase tracking-wide", cfg.style)}>
      <span className={cn("w-1.5 h-1.5 rounded-full shrink-0", cfg.dot)} />
      {cfg.label}
    </span>
  )
}
