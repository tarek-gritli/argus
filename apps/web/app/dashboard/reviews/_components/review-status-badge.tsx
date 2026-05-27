import { cn } from "@/lib/utils"

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string; pulse?: boolean }> = {
  pending:  { label: "PENDING",   color: "text-[#8e9192] border-[#8e9192]", bg: "bg-[#8e9192]/10" },
  running:  { label: "RUNNING",   color: "text-white border-white",         bg: "bg-white/10", pulse: true },
  done:     { label: "COMPLETED", color: "text-[#e2e2e2] border-[#e2e2e2]", bg: "bg-[#e2e2e2]/10" },
  failed:   { label: "FAILED",    color: "text-[#ffb4ab] border-[#ffb4ab]", bg: "bg-[#ffb4ab]/10" },
}

export function ReviewStatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2 py-0.5 border-l text-[10px] font-bold tracking-[0.05em]",
        cfg.bg,
        cfg.color,
        cfg.pulse && "animate-pulse"
      )}
    >
      {cfg.pulse && <span className="w-1.5 h-1.5 rounded-full bg-current" />}
      {cfg.label}
    </span>
  )
}
