"use client"

import { useState } from "react"
import { FindingCard } from "./finding-card"
import { useAcceptFinding, useRejectFinding } from "@/lib/queries"
import type { Finding, Severity, Agent } from "@/lib/types"
import { toast } from "sonner"
import { cn } from "@/lib/utils"

const SEVERITIES: Severity[] = ["critical", "high", "medium", "low", "info"]
const AGENTS: Agent[] = ["security", "quality", "testing", "documentation", "ticket_compliance"]

const SEVERITY_DOT: Record<Severity, string> = {
  critical: "bg-red-500",
  high:     "bg-orange-500",
  medium:   "bg-yellow-500",
  low:      "bg-green-500",
  info:     "bg-slate-400",
}

const AGENT_LABEL: Record<Agent, string> = {
  security:          "Security",
  quality:           "Quality",
  testing:           "Testing",
  documentation:     "Docs",
  ticket_compliance: "Ticket",
}

interface Props {
  reviewId: string
  findings: Finding[]
}

export function FindingsExplorer({ reviewId, findings }: Props) {
  const [severityFilter, setSeverityFilter] = useState<Severity | "all">("all")
  const [agentTab, setAgentTab] = useState<Agent | "all">("all")
  const acceptMutation = useAcceptFinding(reviewId)
  const rejectMutation = useRejectFinding(reviewId)

  const isPending = acceptMutation.isPending || rejectMutation.isPending

  function handleAccept(id: string) {
    acceptMutation.mutate(id, {
      onSuccess: () => toast.success("Finding accepted"),
      onError: () => toast.error("Failed to accept finding"),
    })
  }

  function handleReject(id: string) {
    rejectMutation.mutate(id, {
      onSuccess: () => toast.success("Finding rejected"),
      onError: () => toast.error("Failed to reject finding"),
    })
  }

  const activeAgents = AGENTS.filter((a) => findings.some((f) => f.agent === a))

  function getFiltered(subset: Finding[]) {
    return severityFilter === "all" ? subset : subset.filter((f) => f.severity === severityFilter)
  }

  const visibleFindings = agentTab === "all"
    ? getFiltered(findings)
    : getFiltered(findings.filter((f) => f.agent === agentTab))

  return (
    <div>
      {/* Agent tabs */}
      <div className="flex items-center gap-0 mb-5 border-b border-border">
        {(["all", ...activeAgents] as (Agent | "all")[]).map((tab) => {
          const count = tab === "all"
            ? findings.length
            : findings.filter((f) => f.agent === tab).length
          const active = agentTab === tab
          return (
            <button
              key={tab}
              onClick={() => setAgentTab(tab)}
              className={cn(
                "px-4 py-2.5 text-[12px] font-medium border-b-2 -mb-px transition-colors",
                active
                  ? "border-foreground text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              {tab === "all" ? "All" : AGENT_LABEL[tab]}
              <span className={cn(
                "ml-1.5 text-[10px] tabular-nums",
                active ? "text-foreground/60" : "text-muted-foreground/60"
              )}>
                {count}
              </span>
            </button>
          )
        })}
      </div>

      {/* Severity filters */}
      <div className="flex flex-wrap items-center gap-1.5 mb-5">
        <button
          onClick={() => setSeverityFilter("all")}
          className={cn(
            "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium transition-colors",
            severityFilter === "all"
              ? "bg-foreground text-background border-foreground"
              : "border-border text-muted-foreground hover:text-foreground hover:border-foreground/30"
          )}
        >
          All <span className="tabular-nums">{findings.length}</span>
        </button>
        {SEVERITIES.map((s) => {
          const count = (agentTab === "all"
            ? findings
            : findings.filter((f) => f.agent === agentTab)
          ).filter((f) => f.severity === s).length
          if (!count) return null
          return (
            <button
              key={s}
              onClick={() => setSeverityFilter(s)}
              className={cn(
                "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium transition-colors capitalize",
                severityFilter === s
                  ? "bg-foreground text-background border-foreground"
                  : "border-border text-muted-foreground hover:text-foreground hover:border-foreground/30"
              )}
            >
              <span className={cn("w-1.5 h-1.5 rounded-full", SEVERITY_DOT[s])} />
              {s}
              <span className="tabular-nums">{count}</span>
            </button>
          )
        })}
      </div>

      {/* Findings list */}
      <div className="space-y-3">
        {visibleFindings.length === 0 ? (
          <div className="py-12 text-center rounded-lg border border-dashed">
            <p className="text-sm text-muted-foreground">No findings match the current filter.</p>
          </div>
        ) : (
          visibleFindings.map((f) => (
            <FindingCard
              key={f.id}
              finding={f}
              onAccept={handleAccept}
              onReject={handleReject}
              isPending={isPending}
            />
          ))
        )}
      </div>
    </div>
  )
}
