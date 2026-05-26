"use client"

import { Check, X, FileCode } from "lucide-react"
import type { Finding } from "@/lib/types"
import { SeverityBadge } from "./severity-badge"
import { AgentBadge } from "./agent-badge"
import { cn } from "@/lib/utils"

const SEVERITY_BORDER: Record<string, string> = {
  critical: "border-l-red-500",
  high:     "border-l-orange-500",
  medium:   "border-l-yellow-500",
  low:      "border-l-green-500",
  info:     "border-l-slate-300 dark:border-l-slate-600",
}

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
    <div className={cn(
      "rounded-lg border bg-card border-l-[3px] overflow-hidden transition-shadow hover:shadow-sm",
      SEVERITY_BORDER[finding.severity] ?? SEVERITY_BORDER.info
    )}>
      <div className="p-4">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <SeverityBadge severity={finding.severity} />
          <AgentBadge agent={finding.agent} />
          <div className="ml-auto flex items-center gap-1.5 text-[11px] font-mono text-muted-foreground bg-muted px-2 py-0.5 rounded">
            <FileCode className="h-3 w-3" />
            {fileLocation}
          </div>
        </div>

        <p className="text-sm font-semibold text-foreground mb-1.5">{finding.title}</p>
        <p className="text-[13px] text-muted-foreground leading-relaxed">{finding.description}</p>

        {finding.suggestion && (
          <div className="mt-4 rounded-md border border-blue-500/20 overflow-hidden">
            <div className="bg-blue-500/5 px-3 py-2 text-[11px] font-semibold text-blue-600 dark:text-blue-400 border-b border-blue-500/20 flex items-center gap-1.5">
              <span className="w-1 h-1 rounded-full bg-blue-500" />
              Suggested fix
            </div>
            <pre className="px-3 py-3 text-[12px] font-mono whitespace-pre-wrap bg-blue-500/3 text-foreground leading-relaxed overflow-x-auto">
              {finding.suggestion}
            </pre>
          </div>
        )}

        {(onAccept || onReject) && finding.is_accepted === null && (
          <div className="flex gap-2 mt-4 pt-3 border-t border-border">
            <button
              disabled={isPending}
              onClick={() => onAccept?.(finding.id)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded text-[12px] font-medium text-green-700 dark:text-green-400 bg-green-500/8 border border-green-500/20 hover:bg-green-500/15 transition-colors disabled:opacity-50"
            >
              <Check className="h-3.5 w-3.5" /> Accept
            </button>
            <button
              disabled={isPending}
              onClick={() => onReject?.(finding.id)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded text-[12px] font-medium text-red-700 dark:text-red-400 bg-red-500/8 border border-red-500/20 hover:bg-red-500/15 transition-colors disabled:opacity-50"
            >
              <X className="h-3.5 w-3.5" /> Reject
            </button>
          </div>
        )}

        {finding.is_accepted === true && (
          <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-border text-[12px] font-medium text-green-600">
            <Check className="h-3.5 w-3.5" /> Accepted
          </div>
        )}
        {finding.is_accepted === false && (
          <div className="flex items-center gap-1.5 mt-3 pt-3 border-t border-border text-[12px] text-muted-foreground">
            <X className="h-3.5 w-3.5" /> Rejected
          </div>
        )}
      </div>
    </div>
  )
}
