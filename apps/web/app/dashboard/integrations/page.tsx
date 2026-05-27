"use client"

import { useQuery } from "@tanstack/react-query"
import { integrationsOptions } from "@/lib/queries"
import { IntegrationCard } from "./_components/integration-card"
import { Skeleton } from "@/components/ui/skeleton"
import { Topbar } from "@/components/topbar"
import { api } from "@/lib/api"
import type { Integration } from "@/lib/types"
import { Plus } from "lucide-react"

const ORG_ID_PLACEHOLDER = "current"

const ALL_KINDS = ["slack", "notion", "linear", "jira"] as const
const KIND_LABELS: Record<string, string> = {
  slack: "Slack", notion: "Notion", linear: "Linear", jira: "Jira",
}
const KIND_DESCRIPTIONS: Record<string, string> = {
  slack: "Post findings to a Slack channel",
  notion: "Create Notion pages for findings",
  linear: "Open Linear issues for critical findings",
  jira: "Create Jira tickets from review results",
}

export default function IntegrationsPage() {
  const { data: integrations, isLoading } = useQuery(integrationsOptions(ORG_ID_PLACEHOLDER))

  const connectedByKind = (integrations ?? []).reduce<Record<string, Integration>>(
    (acc, i) => ({ ...acc, [i.kind]: i }),
    {}
  )

  return (
    <>
      <Topbar title="Integrations" />
      <div className="px-8 py-8">
        <div className="mb-6">
          <h2 className="text-base font-semibold text-foreground">Integrations</h2>
          <p className="text-[12px] text-muted-foreground mt-0.5">
            Connect Argus to your tools. Findings are posted automatically after each review.
          </p>
        </div>

        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-20 rounded-lg" />
            ))}
          </div>
        ) : (
          <div className="rounded-lg border overflow-hidden">
            {ALL_KINDS.map((kind, idx) => {
              const integration = connectedByKind[kind]
              const isLast = idx === ALL_KINDS.length - 1
              if (integration) {
                return (
                  <div key={integration.id} className={!isLast ? "border-b border-border" : ""}>
                    <IntegrationCard integration={integration} orgId={ORG_ID_PLACEHOLDER} />
                  </div>
                )
              }
              return (
                <div
                  key={kind}
                  className={`flex items-center justify-between px-5 py-4 bg-card ${!isLast ? "border-b border-border" : ""}`}
                >
                  <div className="flex items-center gap-4">
                    <div className="w-8 h-8 rounded bg-muted flex items-center justify-center text-[11px] font-bold text-muted-foreground">
                      {KIND_LABELS[kind][0]}
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-foreground">{KIND_LABELS[kind]}</p>
                      <p className="text-[12px] text-muted-foreground">{KIND_DESCRIPTIONS[kind]}</p>
                    </div>
                  </div>
                  <a href={api.integrations.connectUrl(kind, ORG_ID_PLACEHOLDER)}>
                    <button className="flex items-center gap-1.5 px-3 py-1.5 rounded text-[12px] font-medium border border-border text-foreground hover:bg-muted transition-colors">
                      <Plus className="h-3.5 w-3.5" /> Connect
                    </button>
                  </a>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </>
  )
}
