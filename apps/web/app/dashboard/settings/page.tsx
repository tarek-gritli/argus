"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { toast } from "sonner"
import {
  billingOptions,
  membersOptions,
  pendingInvitesOptions,
  useCreateInvite,
  useRevokeInvite,
} from "@/lib/queries"
import { getOrgId } from "@/lib/auth"
import { Topbar } from "@/components/topbar"
import { ConnectedAccounts } from "./_components/connected-accounts"
import { Organizations } from "./_components/organizations"
import { Building2, Users, Info, Mail, X } from "lucide-react"

export default function SettingsPage() {
  const orgId = getOrgId() ?? ""
  const { data: billing } = useQuery(billingOptions())
  const { data: members = [] } = useQuery(membersOptions(orgId))
  const { data: pendingInvites = [] } = useQuery(pendingInvitesOptions(orgId))
  const createInvite = useCreateInvite(orgId)
  const revokeInvite = useRevokeInvite(orgId)
  const [inviteEmail, setInviteEmail] = useState("")
  const [inviteOpen, setInviteOpen] = useState(false)

  const canInvite = !!billing && billing.plan !== "free"

  function handleInvite(e: React.FormEvent) {
    e.preventDefault()
    createInvite.mutate(inviteEmail, {
      onSuccess: () => {
        toast.success(`Invite sent to ${inviteEmail}`)
        setInviteEmail("")
        setInviteOpen(false)
      },
      onError: (err) => {
        let msg = "Failed to send invite"
        try {
          msg = JSON.parse(err.message).detail ?? msg
        } catch {}
        toast.error(typeof msg === "string" ? msg : "Failed to send invite")
      },
    })
  }

  return (
    <>
      <Topbar title="Settings" />
      <div className="px-8 py-8 space-y-3">

        {/* Page header */}
        <div className="mb-6">
          <h2 className="text-[24px] font-semibold leading-8 tracking-[-0.02em] text-[#c6c6c7]">Settings</h2>
          <p className="text-[14px] text-[#8e9192] mt-1">Manage your organization&apos;s core configuration and team access.</p>
        </div>

        {/* Organization */}
        <section className="border border-white/8 p-4" style={{ background: "rgba(255,255,255,0.04)" }}>
          <div className="flex items-start gap-3 mb-4">
            <Building2 className="h-5 w-5 text-[#c6c6c7] shrink-0 mt-0.5" />
            <div>
              <h3 className="text-[18px] font-semibold leading-6 tracking-[-0.01em] text-[#e5e2e1]">Organization</h3>
              <p className="text-[12px] text-[#8e9192] mt-0.5">Identity and ownership controls</p>
            </div>
          </div>
          <div className="space-y-0">
            <div className="flex items-center justify-between py-2 border-b border-white/5">
              <span className="text-[10px] font-bold tracking-wider uppercase text-[#8e9192]">ORG ID</span>
              <span className="font-mono text-[12px] text-[#c6c6c7]">{orgId || "—"}</span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-[10px] font-bold tracking-wider uppercase text-[#8e9192]">PLAN</span>
              <span className="text-[14px] font-semibold text-[#e5e2e1] capitalize">
                {billing?.plan ?? "—"}
              </span>
            </div>
          </div>
        </section>

        <Organizations />

        <ConnectedAccounts />

        {/* Team members */}
        <section className="border border-white/8 p-4" style={{ background: "rgba(255,255,255,0.04)" }}>
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-start gap-3">
              <Users className="h-5 w-5 text-[#c6c6c7] shrink-0 mt-0.5" />
              <div>
                <h3 className="text-[18px] font-semibold leading-6 tracking-[-0.01em] text-[#e5e2e1]">Team Members</h3>
                <p className="text-[12px] text-[#8e9192] mt-0.5">Access control and seat allocation</p>
              </div>
            </div>
            {canInvite ? (
              <button
                onClick={() => setInviteOpen((v) => !v)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium border border-white/10 text-[#c6c6c7] hover:bg-white/5 transition-colors"
              >
                <Mail className="h-3.5 w-3.5" /> Invite
              </button>
            ) : (
              <a
                href="/dashboard/billing"
                className="text-[10px] font-bold tracking-wider uppercase text-[#8e9192] hover:text-[#c6c6c7] transition-colors"
              >
                Upgrade to invite →
              </a>
            )}
          </div>

          {inviteOpen && (
            <form onSubmit={handleInvite} className="flex gap-2 mb-4">
              <input
                type="email"
                placeholder="teammate@example.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                className="flex-1 bg-white/5 border border-white/10 px-3 py-2 text-[13px] text-[#e5e2e1] placeholder-[#8e9192] focus:outline-none focus:border-white/20"
                required
              />
              <button
                type="submit"
                disabled={createInvite.isPending}
                className="px-4 py-2 bg-[#e2e2e2] text-[#2f3131] text-[12px] font-semibold disabled:opacity-50"
              >
                {createInvite.isPending ? "Sending…" : "Send invite"}
              </button>
            </form>
          )}

          <div className="space-y-1">
            {members.map((m) => (
              <div key={m.user_id} className="flex items-center gap-4 p-3 bg-white/5">
                <div className="w-8 h-8 bg-[#2a2a2a] flex items-center justify-center shrink-0 overflow-hidden">
                  {m.avatar_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={m.avatar_url} alt={m.login} className="w-full h-full object-cover" />
                  ) : (
                    <span className="text-[11px] font-bold text-[#c6c6c7]">
                      {m.login[0].toUpperCase()}
                    </span>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[14px] text-[#e5e2e1]">@{m.login}</p>
                  <p className="text-[11px] text-[#8e9192]">
                    Joined {new Date(m.joined_at).toLocaleDateString()}
                  </p>
                </div>
                <span className="text-[10px] font-bold tracking-wider uppercase text-[#c6c6c7]">{m.role}</span>
              </div>
            ))}
          </div>

          {pendingInvites.length > 0 && (
            <div className="mt-3 pt-3 border-t border-white/5">
              <p className="text-[10px] font-bold tracking-wider uppercase text-[#8e9192] mb-2">
                Pending invites
              </p>
              <div className="space-y-1">
                {pendingInvites.map((inv) => (
                  <div
                    key={inv.id}
                    className="flex items-center justify-between px-3 py-2 bg-white/[0.02] border border-white/5"
                  >
                    <div>
                      <p className="text-[13px] text-[#c6c6c7]">{inv.email}</p>
                      <p className="text-[11px] text-[#8e9192]">
                        Invited by @{inv.invited_by_login} · expires{" "}
                        {new Date(inv.expires_at).toLocaleDateString()}
                      </p>
                    </div>
                    <button
                      onClick={() =>
                        revokeInvite.mutate(inv.id, {
                          onSuccess: () => toast.success("Invite revoked"),
                          onError: () => toast.error("Failed to revoke invite"),
                        })
                      }
                      className="text-[#8e9192] hover:text-[#ffb4ab] transition-colors"
                      title="Revoke invite"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="mt-4"></div>

          <div className="flex items-center gap-2 pt-3 border-t border-white/5 text-[#8e9192]">
            <Info className="h-3.5 w-3.5 shrink-0" />
            <span className="text-[12px]">
              {billing
                ? `${members.length} / ${billing.seat_count} seats used on ${billing.plan} plan`
                : "Loading…"}
            </span>
          </div>
        </section>

      </div>
    </>
  )
}
