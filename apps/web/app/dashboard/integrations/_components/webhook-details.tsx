"use client"

import { Copy } from "lucide-react"
import { toast } from "sonner"
import type { GitlabWebhookDetails } from "@/lib/types"

function CopyRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] font-bold tracking-wider uppercase text-[#8e9192] mb-1">{label}</p>
      <div className="flex items-center gap-2 bg-white/5 border border-white/10 px-3 py-2">
        <code className="flex-1 min-w-0 truncate text-[12px] text-[#e5e2e1]">{value}</code>
        <button
          type="button"
          onClick={() => navigator.clipboard.writeText(value).then(() => toast.success("Copied"))}
          className="text-[#8e9192] hover:text-[#c6c6c7]"
          title={`Copy ${label}`}
        >
          <Copy className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  )
}

/** What to paste into GitLab → Settings → Webhooks (Merge request events). */
export function WebhookDetails({ details }: { details: GitlabWebhookDetails }) {
  return (
    <div className="space-y-3">
      <CopyRow label="URL" value={details.webhook_url} />
      <CopyRow label="Secret token" value={details.webhook_secret} />
      <p className="text-[12px] text-[#8e9192]">
        In your GitLab project, open Settings → Webhooks, paste both values and enable{" "}
        <strong className="text-[#c6c6c7]">Merge request events</strong>. The secret is shown only once.
      </p>
    </div>
  )
}
