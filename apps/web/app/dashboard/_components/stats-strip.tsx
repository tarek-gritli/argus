import type { Severity } from "@/lib/types"

const SEVERITY_CONFIG: Record<Severity, { label: string; color: string; borderColor: string; iconColor: string }> = {
  critical: { label: "CRITICAL", color: "text-[#ffb4ab]", borderColor: "border-l-[#ffb4ab]", iconColor: "text-[#ffb4ab]" },
  high:     { label: "HIGH",     color: "text-[#e2e2e2]", borderColor: "border-l-[#e2e2e2]", iconColor: "text-[#e2e2e2]" },
  medium:   { label: "MEDIUM",   color: "text-[#c6c6c7]", borderColor: "border-l-[#c6c6c7]", iconColor: "text-[#c6c6c7]" },
  low:      { label: "LOW",      color: "text-[#c4c7c8]", borderColor: "border-l-[#c4c7c8]", iconColor: "text-[#c4c7c8]" },
  info:     { label: "INFO",     color: "text-[#8e9192]", borderColor: "border-l-[#8e9192]", iconColor: "text-[#8e9192]" },
}

const SEVERITIES: Severity[] = ["critical", "high", "medium", "low", "info"]

interface Props {
  counts: Record<Severity, number>
  total: number
}

export function StatsStrip({ counts, total }: Props) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-6">
      {/* Total */}
      <div className="border border-white/5 p-3 flex flex-col gap-1" style={{ background: "#1c1b1b" }}>
        <span className="text-[10px] font-bold tracking-[0.05em] uppercase text-[#8e9192]">Total Reviews</span>
        <span className="text-[24px] font-semibold leading-8 tracking-[-0.02em] text-[#e5e2e1]">{total.toLocaleString()}</span>
      </div>

      {/* Per severity */}
      {SEVERITIES.map((s) => {
        const cfg = SEVERITY_CONFIG[s]
        return (
          <div
            key={s}
            className={`border border-white/5 border-l-2 ${cfg.borderColor} p-3 flex flex-col gap-1`}
            style={{ background: "#1c1b1b" }}
          >
            <span className={`text-[10px] font-bold tracking-[0.05em] uppercase ${cfg.color}`}>{cfg.label}</span>
            <span className="text-[24px] font-semibold leading-8 tracking-[-0.02em] text-[#e5e2e1]">{counts[s]}</span>
          </div>
        )
      })}
    </div>
  )
}
