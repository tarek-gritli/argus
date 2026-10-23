"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { Building } from "lucide-react"
import { toast } from "sonner"
import { errorDetail } from "@/lib/api"
import { orgsOptions, useCreateOrg, useSwitchOrg } from "@/lib/queries"

export function Organizations() {
  const { data: orgs = [] } = useQuery(orgsOptions())
  const switchOrg = useSwitchOrg()
  const createOrg = useCreateOrg()
  const [name, setName] = useState("")

  function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    createOrg.mutate(name, { onError: (err) => toast.error(errorDetail(err, "Failed to create organization")) })
  }

  return (
    <section className="border border-white/8 p-4" style={{ background: "rgba(255,255,255,0.04)" }}>
      <div className="flex items-start gap-3 mb-4">
        <Building className="h-5 w-5 text-[#c6c6c7] shrink-0 mt-0.5" />
        <div>
          <h3 className="text-[18px] font-semibold leading-6 tracking-[-0.01em] text-[#e5e2e1]">Your organizations</h3>
          <p className="text-[12px] text-[#8e9192] mt-0.5">Switch between teams or create a new one</p>
        </div>
      </div>

      <div className="space-y-1">
        {orgs.map((o) => (
          <div key={o.id} className="flex items-center gap-4 p-3 bg-white/5">
            <div className="flex-1 min-w-0">
              <p className="text-[14px] text-[#e5e2e1] truncate">{o.name}</p>
              <p className="text-[11px] text-[#8e9192] capitalize">{o.role}</p>
            </div>
            {o.current ? (
              <span className="text-[10px] font-bold tracking-wider uppercase text-[#4ade80]">Current</span>
            ) : (
              <button
                disabled={switchOrg.isPending}
                onClick={() =>
                  switchOrg.mutate(o.id, { onError: (err) => toast.error(errorDetail(err, "Failed to switch")) })
                }
                className="px-3 py-1 text-[12px] font-medium border border-white/10 text-[#c6c6c7] hover:bg-white/5 transition-colors disabled:opacity-50"
              >
                Switch
              </button>
            )}
          </div>
        ))}
      </div>

      <form onSubmit={handleCreate} className="flex gap-2 mt-3">
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="New organization name"
          minLength={2}
          maxLength={60}
          required
          className="flex-1 bg-white/5 border border-white/10 px-3 py-2 text-[13px] text-[#e5e2e1] placeholder-[#8e9192] focus:outline-none focus:border-white/20"
        />
        <button
          type="submit"
          disabled={createOrg.isPending}
          className="px-4 py-2 bg-[#e2e2e2] text-[#2f3131] text-[12px] font-semibold disabled:opacity-50"
        >
          {createOrg.isPending ? "Creating…" : "Create"}
        </button>
      </form>
    </section>
  )
}
