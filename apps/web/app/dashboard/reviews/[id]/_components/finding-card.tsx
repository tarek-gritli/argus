"use client"

import { Check, X, BarChart2 } from "lucide-react"
import type { Finding } from "@/lib/types"
import { SeverityBadge } from "./severity-badge"
import { AgentBadge } from "./agent-badge"
import { cn } from "@/lib/utils"

interface Props {
  finding: Finding
  onAccept?: (id: string) => void
  onReject?: (id: string) => void
  isPending?: boolean
}

export function FindingCard({ finding, onAccept, onReject, isPending }: Props) {
  const fileLocation =
    finding.line_end && finding.line_end !== finding.line_start
      ? `${finding.file}:${finding.line_start}–${finding.line_end}`
      : `${finding.file}:${finding.line_start}`

  return (
    <article className="border border-white/[0.08] p-4 hover:bg-white/[0.02] transition-colors" style={{ background: "rgba(255,255,255,0.04)" }}>
      {/* Header row */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <AgentBadge agent={finding.agent} />
          <SeverityBadge severity={finding.severity} />
        </div>
        <div className="flex items-center gap-1.5 text-[11px] font-mono text-[#8e9192]">
          <BarChart2 className="h-3.5 w-3.5" />
          <span>{Math.round(finding.confidence * 100)}% Confidence</span>
        </div>
      </div>

      {/* Title */}
      <p className="text-[14px] font-bold text-[#e5e2e1] mb-2">{finding.title}</p>

      {/* File location */}
      <p className="font-mono text-[11px] text-[#c6c6c7] mb-3 inline-block px-2 py-0.5 bg-[#0e0e0e]/50">
        {fileLocation}
      </p>

      {/* Description */}
      <p className="text-[14px] text-[#c4c7c8] leading-relaxed mb-4">{finding.description}</p>

      {/* Suggested fix */}
      {finding.suggestion && (
        <div className="border border-[#444748] mb-4 overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 border-b border-[#444748]" style={{ background: "#0e0e0e" }}>
            <span className="text-[10px] font-bold tracking-[0.05em] uppercase text-[#8e9192]">SUGGESTED FIX</span>
          </div>
          <pre className="px-3 py-3 text-[13px] font-mono whitespace-pre-wrap text-[#e5e2e1] leading-relaxed overflow-x-auto" style={{ background: "#0e0e0e" }}>
            {finding.suggestion}
          </pre>
        </div>
      )}

      {/* Actions */}
      {(onAccept || onReject) && finding.is_accepted === null && (
        <div className="flex items-center justify-end gap-3">
          <button
            disabled={isPending}
            onClick={() => onReject?.(finding.id)}
            className="px-4 py-1.5 text-[10px] font-bold tracking-[0.05em] uppercase text-[#c4c7c8] border border-[#444748] hover:text-white hover:bg-white/5 transition-colors disabled:opacity-50"
          >
            Reject
          </button>
          <button
            disabled={isPending}
            onClick={() => onAccept?.(finding.id)}
            className="px-4 py-1.5 text-[10px] font-bold tracking-[0.05em] uppercase bg-[#e2e2e2] text-[#636565] hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            Accept Fix
          </button>
        </div>
      )}

      {finding.is_accepted === true && (
        <div className="flex items-center gap-1.5 pt-3 border-t border-white/5 text-[12px] font-medium text-[#e2e2e2]">
          <Check className="h-3.5 w-3.5" /> Accepted
        </div>
      )}
      {finding.is_accepted === false && (
        <div className="flex items-center gap-1.5 pt-3 border-t border-white/5 text-[12px] text-[#8e9192]">
          <X className="h-3.5 w-3.5" /> Rejected
        </div>
      )}
    </article>
  )
}
