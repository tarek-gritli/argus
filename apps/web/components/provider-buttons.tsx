"use client"

import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import { providersOptions } from "@/lib/queries"
import type { Provider } from "@/lib/types"
import { ProviderIcon } from "./provider-icons"

const GITHUB_ONLY: Provider[] = [{ id: "github", label: "GitHub", host: "" }]

/** One "Continue with …" button per sign-in method this deployment offers. */
export function ProviderButtons({ inviteToken, prefix = "Continue with" }: { inviteToken?: string; prefix?: string }) {
  const { data } = useQuery(providersOptions())
  const providers = data?.length ? data : GITHUB_ONLY

  return (
    <div className="space-y-3">
      {providers.map((p, i) => (
        <a
          key={p.id}
          href={api.auth.loginUrl(p.id, inviteToken)}
          className={`flex items-center justify-center gap-3 w-full rounded-lg text-sm font-semibold h-11 transition-opacity hover:opacity-90 ${
            i === 0 ? "bg-white text-[oklch(0.10_0_0)]" : "bg-white/8 text-white border border-white/10"
          }`}
        >
          <ProviderIcon provider={p.id} />
          {prefix} {p.label}
        </a>
      ))}
    </div>
  )
}
