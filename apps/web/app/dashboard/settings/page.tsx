import { Topbar } from "@/components/topbar"
import { Building2, Users, Info } from "lucide-react"

const MEMBERS = [
  { initials: "JD", name: "Jared Dunn",       email: "j.dunn@argus.ai",        role: "OWNER" },
  { initials: "GH", name: "Gavin Belson",     email: "g.belson@hooli.com",      role: "ADMIN" },
  { initials: "RH", name: "Richard Hendricks", email: "richard@piedpiper.com",  role: "EDITOR" },
]

export default function SettingsPage() {
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
              <span className="text-[10px] font-bold tracking-wider uppercase text-[#8e9192]">NAME</span>
              <span className="text-[14px] font-semibold text-[#e5e2e1]">Argus AI Labs, Inc.</span>
            </div>
            <div className="flex items-center justify-between py-2 border-b border-white/5">
              <span className="text-[10px] font-bold tracking-wider uppercase text-[#8e9192]">RENAME POLICY</span>
              <span className="text-[12px] text-[#8e9192]">Restricted until 2024-12-01</span>
            </div>
            <div className="flex items-center justify-between py-2">
              <span className="text-[10px] font-bold tracking-wider uppercase text-[#8e9192]">TRANSFER</span>
              <span className="text-[12px] text-[#ffb4ab]">Ownership locked (SSO Required)</span>
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
            <div className="border-l-2 border-[#b4c5ff] bg-[#b4c5ff]/10 px-2 py-0.5">
              <span className="text-[10px] font-bold tracking-wider uppercase text-[#b4c5ff]">TEAM+</span>
            </div>
          </div>

          <div className="space-y-1">
            {MEMBERS.map((m) => (
              <div key={m.email} className="flex items-center gap-4 p-3 bg-white/5">
                <div className="w-8 h-8 bg-[#2a2a2a] flex items-center justify-center shrink-0">
                  <span className="text-[11px] font-bold text-[#c6c6c7]">{m.initials}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[14px] text-[#e5e2e1]">{m.name}</p>
                  <p className="font-mono text-[11px] text-[#8e9192]">{m.email}</p>
                </div>
                <span className="text-[10px] font-bold tracking-wider uppercase text-[#c6c6c7]">{m.role}</span>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-2 mt-4 pt-3 border-t border-white/5 text-[#8e9192]">
            <Info className="h-3.5 w-3.5 shrink-0" />
            <span className="text-[12px]">Seat usage: 12 / 50 available seats.</span>
          </div>
        </section>

        {/* Status */}
        <div className="flex justify-center pt-4 opacity-50">
          <div className="flex items-center gap-2 font-mono text-[11px] text-[#8e9192]">
            <span className="w-2 h-2 rounded-full bg-[#00E5FF] animate-pulse" />
            SYSTEM CONNECTED: US-EAST-1
          </div>
        </div>

      </div>
    </>
  )
}
