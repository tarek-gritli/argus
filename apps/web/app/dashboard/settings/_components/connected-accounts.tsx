"use client"

import { useEffect } from "react"
import { useQuery } from "@tanstack/react-query"
import { Link2, X } from "lucide-react"
import { toast } from "sonner"
import { ProviderIcon } from "@/components/provider-icons"
import { api, errorDetail } from "@/lib/api"
import { identitiesOptions, providersOptions, useUnlinkIdentity } from "@/lib/queries"

const LINK_ERRORS: Record<string, string> = {
  already_linked: "That account is already connected to another Argus user.",
  provider_taken: "You've already connected a different account from that provider.",
  state: "The connection attempt expired. Please try again.",
}

export function ConnectedAccounts() {
  const { data: identities = [] } = useQuery(identitiesOptions())
  const { data: providers = [] } = useQuery(providersOptions())
  const unlink = useUnlinkIdentity()

  // The OAuth callback redirects back here with ?linked=<provider> or ?link_error=<code>
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const linked = params.get("linked")
    const error = params.get("link_error")
    if (linked) toast.success(`${linked === "gitlab" ? "GitLab" : "GitHub"} account connected`)
    if (error) toast.error(LINK_ERRORS[error] ?? "Could not connect that account")
    if (linked || error) history.replaceState(null, "", window.location.pathname)
  }, [])

  const connectable = providers.filter((p) => !identities.some((i) => i.provider === p.id && i.host === p.host))

  return (
    <section className="border border-white/8 p-4" style={{ background: "rgba(255,255,255,0.04)" }}>
      <div className="flex items-start gap-3 mb-4">
        <Link2 className="h-5 w-5 text-[#c6c6c7] shrink-0 mt-0.5" />
        <div>
          <h3 className="text-[18px] font-semibold leading-6 tracking-[-0.01em] text-[#e5e2e1]">Connected accounts</h3>
          <p className="text-[12px] text-[#8e9192] mt-0.5">Ways you can sign in to Argus</p>
        </div>
      </div>

      <div className="space-y-1">
        {identities.map((i) => (
          <div key={i.id} className="flex items-center gap-4 p-3 bg-white/5">
            <span className="text-[#c6c6c7]">
              <ProviderIcon provider={i.provider} size={18} />
            </span>
            <div className="flex-1 min-w-0">
              <p className="text-[14px] text-[#e5e2e1]">
                @{i.login}
                <span className="ml-2 text-[11px] text-[#8e9192] capitalize">{i.provider}</span>
              </p>
              {i.host && <p className="text-[11px] text-[#8e9192] truncate">{i.host.replace(/^https?:\/\//, "")}</p>}
            </div>
            <button
              title={identities.length === 1 ? "You need at least one sign-in method" : "Disconnect"}
              disabled={identities.length === 1 || unlink.isPending}
              onClick={() =>
                unlink.mutate(i.id, {
                  onSuccess: () => toast.success("Account disconnected"),
                  onError: (err) => toast.error(errorDetail(err, "Failed to disconnect")),
                })
              }
              className="text-[#8e9192] hover:text-[#ffb4ab] transition-colors disabled:opacity-30 disabled:hover:text-[#8e9192]"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        ))}
      </div>

      {connectable.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-3">
          {connectable.map((p) => (
            <a
              key={p.id}
              href={api.auth.linkUrl(p.id)}
              className="flex items-center gap-2 px-3 py-1.5 text-[12px] font-medium border border-white/10 text-[#c6c6c7] hover:bg-white/5 transition-colors"
            >
              <ProviderIcon provider={p.id} size={14} /> Connect {p.label}
            </a>
          ))}
        </div>
      )}
    </section>
  )
}
