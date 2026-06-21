"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { notionDatabasesOptions, useSelectNotionDatabase } from "@/lib/queries"
import { Skeleton } from "@/components/ui/skeleton"
import { toast } from "sonner"

interface Props {
  orgId: string
  integrationId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function NotionDatabasePicker({ orgId, integrationId, open, onOpenChange }: Props) {
  const [selected, setSelected] = useState<string | null>(null)
  const { data: databases, isLoading } = useQuery(notionDatabasesOptions(orgId, integrationId))
  const selectMutation = useSelectNotionDatabase(orgId, integrationId)

  function handleConfirm() {
    if (!selected) return
    selectMutation.mutate(selected, {
      onSuccess: () => {
        toast.success("Notion database linked")
        onOpenChange(false)
      },
      onError: () => toast.error("Failed to link database"),
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Select a Notion database</DialogTitle>
          <DialogDescription>
            Argus will post findings as pages in the selected database.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2 max-h-64 overflow-y-auto py-2">
          {isLoading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-10 rounded" />
            ))
          ) : !databases?.length ? (
            <p className="text-sm text-muted-foreground">No databases found in this workspace.</p>
          ) : (
            databases.map((db) => (
              <button
                key={db.id}
                onClick={() => setSelected(db.id)}
                className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                  selected === db.id ? "bg-primary text-primary-foreground" : "hover:bg-muted"
                }`}
              >
                📄 {db.title || "(untitled)"}
              </button>
            ))
          )}
        </div>
        <Button onClick={handleConfirm} disabled={!selected || selectMutation.isPending} className="w-full">
          {selectMutation.isPending ? "Linking…" : "Link database"}
        </Button>
      </DialogContent>
    </Dialog>
  )
}
