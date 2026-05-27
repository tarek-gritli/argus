"use client"

import { useQuery } from "@tanstack/react-query"
import { reviewsListOptions } from "@/lib/queries"
import { StatsStrip } from "./_components/stats-strip"
import { RecentReviewsList } from "./_components/recent-reviews-list"
import { Topbar } from "@/components/topbar"
import Link from "next/link"
import type { Severity } from "@/lib/types"

const SEVERITIES: Severity[] = ["critical", "high", "medium", "low", "info"]

export default function OverviewPage() {
  const { data: reviews, isLoading } = useQuery(reviewsListOptions(1))

  const counts = SEVERITIES.reduce(
    (acc, s) => ({ ...acc, [s]: 0 }),
    {} as Record<Severity, number>
  )
  const recent = reviews?.slice(0, 5) ?? []

  return (
    <>
      <Topbar title="Overview" />
      <div className="px-8 py-8 space-y-3">

        {/* Stats strip */}
        {isLoading ? (
          <div className="grid grid-cols-6 gap-3 mb-6">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-16 bg-white/5 animate-pulse" />
            ))}
          </div>
        ) : (
          <StatsStrip counts={counts} total={reviews?.length ?? 0} />
        )}

        {/* Recent reviews */}
        <div className="border border-white/10 overflow-hidden" style={{ background: "#201f1f" }}>
          <div className="px-4 py-3 border-b border-[#444748] flex items-center justify-between bg-white/5">
            <h3 className="text-[10px] font-bold tracking-[0.05em] uppercase text-[#e5e2e1]">Recent Reviews</h3>
            <Link href="/dashboard/reviews" className="text-[10px] font-bold tracking-[0.05em] uppercase text-[#c6c6c7] hover:text-white transition-colors">
              VIEW ALL
            </Link>
          </div>
          {isLoading ? (
            <div className="divide-y divide-white/5">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex items-center justify-between px-4 py-3">
                  <div className="h-3 w-32 bg-white/5 animate-pulse" />
                  <div className="h-3 w-20 bg-white/5 animate-pulse" />
                </div>
              ))}
            </div>
          ) : (
            <RecentReviewsList reviews={recent} />
          )}
        </div>

        {/* Bottom cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">

          {/* Security distribution */}
          <div className="border border-white/10 p-4" style={{ background: "#201f1f" }}>
            <h4 className="text-[10px] font-bold tracking-[0.05em] uppercase text-[#e5e2e1] mb-4">Security Distribution</h4>
            <div className="flex items-center justify-center py-6">
              <div className="w-32 h-32 rounded-full border-8 border-[#2a2a2a] flex items-center justify-center relative">
                <div className="absolute inset-0 rounded-full border-8 border-[#ffb4ab] border-t-transparent border-l-transparent rotate-45" />
                <div className="flex flex-col items-center">
                  <span className="text-[24px] font-semibold leading-8 text-[#e5e2e1]">84%</span>
                  <span className="text-[9px] uppercase tracking-widest text-[#8e9192]">Secure</span>
                </div>
              </div>
            </div>
            <div className="flex flex-wrap gap-4 justify-center mt-2">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#ffb4ab]" />
                <span className="text-[10px] text-[#8e9192]">Critical (12)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#e2e2e2]" />
                <span className="text-[10px] text-[#8e9192]">High (43)</span>
              </div>
            </div>
          </div>

          {/* Active deployments */}
          <div className="border border-white/10 p-4" style={{ background: "#201f1f" }}>
            <h4 className="text-[10px] font-bold tracking-[0.05em] uppercase text-[#e5e2e1] mb-4">Active Deployments</h4>
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-[#2a2a2a] flex items-center justify-center shrink-0">
                  <span className="text-[10px] font-bold text-[#c6c6c7]">PROD</span>
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-[12px] font-semibold text-[#e5e2e1]">Production (US-EAST)</span>
                    <span className="font-mono text-[10px] text-[#c6c6c7]">UP</span>
                  </div>
                  <div className="w-full bg-[#2a2a2a] h-1">
                    <div className="bg-[#c6c6c7] h-full" style={{ width: "99.9%" }} />
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-[#2a2a2a] flex items-center justify-center shrink-0">
                  <span className="text-[10px] font-bold text-[#e2e2e2]">STG</span>
                </div>
                <div className="flex-1">
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-[12px] font-semibold text-[#e5e2e1]">Staging (EU-WEST)</span>
                    <span className="font-mono text-[10px] text-[#e2e2e2]">DEPLOYING</span>
                  </div>
                  <div className="w-full bg-[#2a2a2a] h-1">
                    <div className="bg-[#e2e2e2] h-full animate-pulse" style={{ width: "65%" }} />
                  </div>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </>
  )
}
