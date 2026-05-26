"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Trash2 } from "lucide-react"
import type { Integration } from "@/lib/types"
import { useToggleIntegration, useRemoveIntegration } from "@/lib/queries"
import { api } from "@/lib/api"
import { NotionDatabasePicker } from "./notion-database-picker"
import { toast } from "sonner"

const KIND_ICONS: Record<string, string> = {
  slack: "💬", notion: "📄", linear: "🔷", jira: "🟦",
}

const KIND_LABELS: Record<string, string> = {
  slack: "Slack", notion: "Notion", linear: "Linear", jira: "Jira",
}

interface Props {
  integration: Integration
  orgId: string
}

export function IntegrationCard({ integration, orgId }: Props) {
  const toggleMutation = useToggleIntegration(orgId)
  const removeMutation = useRemoveIntegration(orgId)
  const [notionPickerOpen, setNotionPickerOpen] = useState(false)

  const notionNeedsDatabase =
    integration.kind === "notion" &&
    !integration.ready &&
    !!(integration.config as Record<string, unknown>)["workspace_id"]

  function handleToggle(enabled: boolean) {
    toggleMutation.mutate(
      { id: integration.id, enabled },
      { onError: () => toast.error("Failed to update integration") }
    )
  }

  function handleRemove() {
    removeMutation.mutate(integration.id, {
      onSuccess: () => toast.success("Integration removed"),
      onError: () => toast.error("Failed to remove integration"),
    })
  }

  return (
    <>
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <span>{KIND_ICONS[integration.kind] ?? "🔗"}</span>
              {KIND_LABELS[integration.kind] ?? integration.kind}
            </CardTitle>
            <div className="flex items-center gap-2">
              {integration.ready ? (
                <Badge className="bg-green-500/15 text-green-600 border-green-500/30 text-xs">Ready</Badge>
              ) : (
                <Badge variant="secondary" className="text-xs">Not configured</Badge>
              )}
              <Switch
                checked={integration.enabled}
                onCheckedChange={handleToggle}
                disabled={toggleMutation.isPending || !integration.ready}
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex justify-between items-center gap-2 flex-wrap">
          <p className="text-xs text-muted-foreground">
            {integration.enabled && integration.ready ? "Active" : "Disabled"} ·{" "}
            Added {new Date(integration.created_at).toLocaleDateString()}
          </p>
          <div className="flex items-center gap-2">
            {notionNeedsDatabase && (
              <Button size="sm" variant="outline" onClick={() => setNotionPickerOpen(true)}>
                Select database
              </Button>
            )}
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-muted-foreground hover:text-destructive"
              disabled={removeMutation.isPending}
              onClick={handleRemove}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {integration.kind === "notion" && (
        <NotionDatabasePicker
          orgId={orgId}
          integrationId={integration.id}
          open={notionPickerOpen}
          onOpenChange={setNotionPickerOpen}
        />
      )}
    </>
  )
}
