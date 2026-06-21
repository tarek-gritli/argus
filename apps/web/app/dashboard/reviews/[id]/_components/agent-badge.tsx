import type { Agent } from "@/lib/types"
import { cn } from "@/lib/utils"

const AGENT_CONFIG: Record<Agent, { label: string; color: string; bg: string }> = {
  security:          { label: "SECURITY", color: "text-[#ffb4ab] border-[#ffb4ab]",  bg: "bg-[#ffb4ab]/10" },
  quality:           { label: "QUALITY",  color: "text-[#b4c5ff] border-[#b4c5ff]",  bg: "bg-[#b4c5ff]/10" },
  testing:           { label: "TESTING",  color: "text-[#c6c6c7] border-[#c6c6c7]",  bg: "bg-[#c6c6c7]/10" },
  documentation:     { label: "DOCS",     color: "text-[#cdd7ff] border-[#cdd7ff]",  bg: "bg-[#cdd7ff]/10" },
  ticket_compliance: { label: "TICKET",   color: "text-[#8e9192] border-[#8e9192]",  bg: "bg-[#8e9192]/10" },
}

export function AgentBadge({ agent }: { agent: Agent }) {
  const cfg = AGENT_CONFIG[agent]
  return (
    <span className={cn("inline-flex items-center px-2 py-0.5 border-l text-[10px] font-bold tracking-[0.05em]", cfg.bg, cfg.color)}>
      {cfg.label}
    </span>
  )
}
