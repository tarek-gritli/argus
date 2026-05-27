"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { reviewsListOptions } from "@/lib/queries"
import { ReviewsTable } from "./_components/reviews-table"
import { Topbar } from "@/components/topbar"

export default function ReviewsPage() {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useQuery(reviewsListOptions(page))

  return (
    <>
      <Topbar title="Reviews" />
      <div className="px-8 py-8">

        {/* Page header */}
        <div className="flex items-end justify-between border-b border-[#444748] pb-6 mb-3">
          <div>
            <h2 className="text-[24px] font-semibold leading-8 tracking-[-0.02em] text-[#e5e2e1]">
              Security Reviews
            </h2>
            <p className="text-[14px] text-[#c4c7c8] mt-1 max-w-lg">
              Active and historical code quality audits for the main repository.
            </p>
          </div>
          <button className="flex items-center gap-1.5 px-4 py-2 bg-[#e2e2e2] text-[#636565] text-[10px] font-bold tracking-[0.05em] uppercase hover:opacity-90 active:scale-95 transition-all">
            + New Review
          </button>
        </div>

        {/* Table */}
        {isLoading ? (
          <div className="border border-white/10 overflow-hidden" style={{ background: "rgba(255,255,255,0.05)" }}>
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 px-4 py-3 border-b border-white/5 last:border-b-0">
                <div className="h-3 w-12 bg-white/10 animate-pulse" />
                <div className="h-3 w-16 bg-white/10 animate-pulse" />
                <div className="h-3 w-20 bg-white/10 animate-pulse" />
                <div className="h-3 w-24 bg-white/10 animate-pulse ml-auto" />
              </div>
            ))}
          </div>
        ) : (
          <ReviewsTable
            data={data ?? []}
            page={page}
            onPageChange={setPage}
            hasMore={(data?.length ?? 0) === 20}
          />
        )}

        {/* Stats strip */}
        <div className="grid grid-cols-3 gap-3 mt-3">
          <div className="p-4 border border-white/10" style={{ background: "rgba(255,255,255,0.05)" }}>
            <p className="text-[10px] font-bold tracking-[0.05em] uppercase text-[#c4c7c8] mb-1">Weekly Uptime</p>
            <p className="text-[18px] font-semibold leading-6 tracking-[-0.01em] text-[#c6c6c7]">99.98%</p>
          </div>
          <div className="p-4 border border-white/10" style={{ background: "rgba(255,255,255,0.05)" }}>
            <p className="text-[10px] font-bold tracking-[0.05em] uppercase text-[#c4c7c8] mb-1">Avg Audit Time</p>
            <p className="text-[18px] font-semibold leading-6 tracking-[-0.01em] text-[#e5e2e1]">3m 14s</p>
          </div>
          <div className="p-4 border border-white/10" style={{ background: "rgba(255,255,255,0.05)" }}>
            <p className="text-[10px] font-bold tracking-[0.05em] uppercase text-[#c4c7c8] mb-1">Vulnerabilities Found</p>
            <p className="text-[18px] font-semibold leading-6 tracking-[-0.01em] text-[#ffb4ab]">12 Critical</p>
          </div>
        </div>

      </div>
    </>
  )
}
