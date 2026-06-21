import type { Severity } from "@/lib/types"
import { cn } from "@/lib/utils"

const SEVERITY_CONFIG: Record<Severity, { label: string; color: string; bg: string }> = {
  critical: { label: "CRITICAL", color: "text-[#ffb4ab] border-[#ffb4ab]", bg: "bg-[#ffb4ab]/10" },
  high:     { label: "HIGH",     color: "text-[#e2e2e2] border-[#e2e2e2]", bg: "bg-[#e2e2e2]/10" },
  medium:   { label: "MED",      color: "text-[#c6c6c7] border-[#c6c6c7]", bg: "bg-[#c6c6c7]/10" },
  low:      { label: "LOW",      color: "text-[#8e9192] border-[#8e9192]", bg: "bg-[#8e9192]/10" },
  info:     { label: "INFO",     color: "text-[#444748] border-[#444748]", bg: "bg-[#444748]/10" },
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const cfg = SEVERITY_CONFIG[severity]
  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 border-l text-[10px] font-bold tracking-[0.05em]", cfg.bg, cfg.color)}>
      {cfg.label}
    </span>
  )
}
