"use client"

import { useState } from "react"
import { FindingCard } from "./finding-card"
import { useAcceptFinding, useRejectFinding } from "@/lib/queries"
import type { Finding, Severity, Agent } from "@/lib/types"
import { toast } from "sonner"
import { cn } from "@/lib/utils"

const SEVERITIES: Severity[] = ["critical", "high", "medium", "low", "info"]
const AGENTS: Agent[] = ["security", "quality", "testing", "documentation", "ticket_compliance"]

const AGENT_LABEL: Record<Agent, string> = {
  security:          "Security",
  quality:           "Quality",
  testing:           "Testing",
  documentation:     "Docs",
  ticket_compliance: "Ticket",
}

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "Critical",
  high:     "High",
  medium:   "Medium",
  low:      "Low",
  info:     "Info",
}

interface Props {
  reviewId: string
  findings: Finding[]
}

export function FindingsExplorer({ reviewId, findings }: Props) {
  const [severityFilter, setSeverityFilter] = useState<Severity | "all">("all")
  const [agentFilter, setAgentFilter] = useState<Agent | "all">("all")
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

  const visibleFindings = findings.filter((f) => {
    if (agentFilter !== "all" && f.agent !== agentFilter) return false
    if (severityFilter !== "all" && f.severity !== severityFilter) return false
    return true
  })

  return (
    <div>
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-4 py-3 border-y border-[#444748] mb-4">
        {/* Agent filter */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold tracking-[0.05em] uppercase text-[#8e9192]">AGENT</span>
          <div className="flex gap-1">
            <button
              onClick={() => setAgentFilter("all")}
              className={cn(
                "px-2 py-1 text-[12px] border transition-colors",
                agentFilter === "all"
                  ? "bg-[#2a2a2a] text-[#e5e2e1] border-[#444748]"
                  : "bg-[#201f1f] text-[#8e9192] border-[#444748] hover:border-white/30 hover:text-[#c4c7c8]"
              )}
            >
              All
            </button>
            {activeAgents.map((a) => (
              <button
                key={a}
                onClick={() => setAgentFilter(a)}
                className={cn(
                  "px-2 py-1 text-[12px] border transition-colors",
                  agentFilter === a
                    ? "bg-[#2a2a2a] text-[#e5e2e1] border-[#444748]"
                    : "bg-[#201f1f] text-[#8e9192] border-[#444748] hover:border-white/30 hover:text-[#c4c7c8]"
                )}
              >
                {AGENT_LABEL[a]}
              </button>
            ))}
          </div>
        </div>

        <div className="w-px h-4 bg-[#444748]" />

        {/* Severity filter */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold tracking-[0.05em] uppercase text-[#8e9192]">SEVERITY</span>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value as Severity | "all")}
            className="bg-[#0e0e0e] border border-[#444748] text-[12px] text-[#c4c7c8] py-1 px-2 focus:outline-none focus:border-white/40 appearance-none pr-6"
          >
            <option value="all">All Severities</option>
            {SEVERITIES.map((s) => (
              <option key={s} value={s}>{SEVERITY_LABEL[s]}</option>
            ))}
          </select>
        </div>

        <div className="ml-auto text-[10px] font-bold tracking-[0.05em] uppercase text-[#8e9192]">
          {visibleFindings.length} Finding{visibleFindings.length !== 1 ? "s" : ""} Found
        </div>
      </div>

      {/* Findings list */}
      <div className="space-y-4">
        {visibleFindings.length === 0 ? (
          <div className="py-12 text-center border border-white/5">
            <p className="text-[13px] text-[#8e9192]">No findings match the current filter.</p>
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
