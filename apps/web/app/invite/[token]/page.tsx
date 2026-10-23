"use client"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { ProviderButtons } from "@/components/provider-buttons"

interface InviteDetails {
  org_name: string
  org_id: string
  inviter_login: string
  role: string
  email: string
  expires_at: string
}

export default function InvitePage() {
  const { token } = useParams<{ token: string }>()
  const [invite, setInvite] = useState<InviteDetails | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch(`/api/v1/invites/${token}`, { credentials: "include" })
      .then(async (res) => {
        if (!res.ok) throw new Error("Invite not found or expired")
        return res.json() as Promise<InviteDetails>
      })
      .then(setInvite)
      .catch((e: Error) => setError(e.message))
  }, [token])

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div
          className="w-full max-w-sm border border-white/[0.12] p-8 text-center"
          style={{ background: "rgba(255,255,255,0.04)" }}
        >
          <p className="text-[16px] text-[#ffb4ab] mb-4">{error}</p>
          <a href="/dashboard" className="text-[13px] text-[#8e9192] hover:text-[#c6c6c7] underline">
            Go to dashboard
          </a>
        </div>
      </div>
    )
  }

  if (!invite) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-[#8e9192] text-[14px]">Loading invite…</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div
        className="w-full max-w-sm border border-white/[0.12] overflow-hidden"
        style={{ background: "rgba(255,255,255,0.04)" }}
      >
        <div className="p-8 flex flex-col items-center text-center gap-4">
          <div className="space-y-1">
            <h2 className="text-[22px] font-semibold leading-8 tracking-[-0.02em] text-[#e5e2e1]">
              You&apos;ve been invited
            </h2>
            <p className="text-[14px] text-[#8e9192]">
              <strong className="text-[#c6c6c7]">@{invite.inviter_login}</strong> invited you to join{" "}
              <strong className="text-[#c6c6c7]">{invite.org_name}</strong> as{" "}
              <span className="capitalize">{invite.role}</span>.
            </p>
          </div>

          <div className="w-full border-t border-white/5 pt-4 text-left font-mono space-y-2">
            <div className="flex justify-between">
              <span className="text-[12px] text-[#8e9192]">For</span>
              <span className="text-[12px] text-[#e5e2e1]">{invite.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[12px] text-[#8e9192]">Expires</span>
              <span className="text-[12px] text-[#e5e2e1]">
                {new Date(invite.expires_at).toLocaleDateString()}
              </span>
            </div>
          </div>

          <div className="w-full pt-1">
            <ProviderButtons inviteToken={token} prefix="Accept with" />
            <p className="text-[11px] text-[#8e9192] mt-3">
              Sign in with an account that has a verified email matching {invite.email}.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
