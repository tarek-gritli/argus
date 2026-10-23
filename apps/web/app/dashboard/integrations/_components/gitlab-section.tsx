"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { KeyRound, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Switch } from "@/components/ui/switch"
import { errorDetail } from "@/lib/api"
import {
  integrationsOptions,
  useRemoveIntegration,
  useRotateGitlabSecret,
  useToggleIntegration,
} from "@/lib/queries"
import type { GitlabWebhookDetails, Integration } from "@/lib/types"
import { ConnectGitlabDialog } from "./connect-gitlab-dialog"
import { WebhookDetails } from "./webhook-details"

function GitlabRow({ integration, orgId }: { integration: Integration; orgId: string }) {
  const toggle = useToggleIntegration(orgId)
  const remove = useRemoveIntegration(orgId)
  const rotate = useRotateGitlabSecret(orgId)
  const [rotated, setRotated] = useState<GitlabWebhookDetails | null>(null)
  const host = String(integration.config["base_url"] ?? "gitlab").replace(/^https?:\/\//, "")

  return (
    <div className="flex items-center justify-between px-5 py-4 border-b border-white/5 last:border-b-0">
      <div className="min-w-0">
        <p className="text-[14px] font-semibold text-[#e5e2e1] truncate">{host}</p>
        <p className="text-[12px] text-[#8e9192]">
          Added {new Date(integration.created_at).toLocaleDateString()}
        </p>
      </div>
      <div className="flex items-center gap-2">
        {integration.ready ? (
          <Badge className="bg-green-500/15 text-green-600 border-green-500/30 text-xs">Ready</Badge>
        ) : (
          <Badge variant="secondary" className="text-xs">Not configured</Badge>
        )}
        <Switch
          checked={integration.enabled}
          disabled={toggle.isPending}
          onCheckedChange={(enabled) =>
            toggle.mutate({ id: integration.id, enabled }, { onError: () => toast.error("Failed to update") })
          }
        />
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-muted-foreground"
          title="Regenerate webhook secret"
          disabled={rotate.isPending}
          onClick={() =>
            rotate.mutate(integration.id, {
              onSuccess: setRotated,
              onError: (err) => toast.error(errorDetail(err, "Failed to rotate secret")),
            })
          }
        >
          <KeyRound className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-muted-foreground hover:text-destructive"
          disabled={remove.isPending}
          onClick={() =>
            remove.mutate(integration.id, {
              onSuccess: () => toast.success("GitLab connection removed"),
              onError: () => toast.error("Failed to remove connection"),
            })
          }
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>

      <Dialog open={!!rotated} onOpenChange={(o) => !o && setRotated(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>New webhook secret</DialogTitle>
            <DialogDescription>Update the secret token on your GitLab webhook. The old one no longer works.</DialogDescription>
          </DialogHeader>
          {rotated && <WebhookDetails details={rotated} />}
        </DialogContent>
      </Dialog>
    </div>
  )
}

/** Source control: available on every plan, unlike the notification integrations below it. */
export function GitlabSection({ orgId }: { orgId: string }) {
  const { data } = useQuery(integrationsOptions(orgId))
  const connections = (data ?? []).filter((i) => i.kind === "gitlab")

  return (
    <section className="mb-6 border border-white/8" style={{ background: "rgba(255,255,255,0.04)" }}>
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
        <div>
          <p className="text-[14px] font-semibold text-[#e5e2e1]">GitLab</p>
          <p className="text-[12px] text-[#8e9192]">
            Review merge requests on gitlab.com or your self-hosted instance
          </p>
        </div>
        <ConnectGitlabDialog orgId={orgId} />
      </div>
      {connections.map((c) => (
        <GitlabRow key={c.id} integration={c} orgId={orgId} />
      ))}
    </section>
  )
}
