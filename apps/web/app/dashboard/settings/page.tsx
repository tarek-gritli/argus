"use client"

import { useQuery } from "@tanstack/react-query"
import { billingOptions } from "@/lib/queries"
import { getOrgId } from "@/lib/auth"
import { Topbar } from "@/components/topbar"
import { Building2, Users, Info } from "lucide-react"

export default function SettingsPage() {
  const orgId = getOrgId() ?? ""
  const { data: billing } = useQuery(billingOptions())

  return (
    <>
      <Topbar title="Settings" />
      <div className="px-8 py-8 space-y-3">

        {/* Page header */}
        <div className="mb-6">
          <h2 className="text-[24px] font-semibold leading-8 tracking-[-0.02em] text-[#c6c6c7]">Settings</h2>
          <p className="text-[14px] text-[#8e9192] mt-1">Manage your organization's core configuration and team access.</p>
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
          </div>

          <div className="py-6 text-center text-[13px] text-[#8e9192]">
            Team management coming soon.
          </div>

          <div className="flex items-center gap-2 pt-3 border-t border-white/5 text-[#8e9192]">
            <Info className="h-3.5 w-3.5 shrink-0" />
            <span className="text-[12px]">
              {billing
                ? `${billing.seat_count} ${billing.seat_count === 1 ? "seat" : "seats"} on ${billing.plan} plan`
                : "Loading…"}
            </span>
          </div>
        </section>

      </div>
    </>
  )
}
