import type { Agent } from "@/lib/types"
import { cn } from "@/lib/utils"

const AGENT_CONFIG: Record<Agent, { label: string; style: string }> = {
  security:         { label: "Security",         style: "bg-violet-500/8 border-violet-500/20 text-violet-700 dark:text-violet-400" },
  quality:          { label: "Quality",          style: "bg-sky-500/8 border-sky-500/20 text-sky-700 dark:text-sky-400" },
  testing:          { label: "Testing",          style: "bg-teal-500/8 border-teal-500/20 text-teal-700 dark:text-teal-400" },
  documentation:    { label: "Docs",             style: "bg-amber-500/8 border-amber-500/20 text-amber-700 dark:text-amber-400" },
  ticket_compliance:{ label: "Ticket",           style: "bg-rose-500/8 border-rose-500/20 text-rose-700 dark:text-rose-400" },
}

export function AgentBadge({ agent }: { agent: Agent }) {
  const cfg = AGENT_CONFIG[agent]
  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 rounded-full border text-[10px] font-semibold uppercase tracking-wide", cfg.style)}>
      {cfg.label}
    </span>
  )
}
