"use client"

import { useQuery } from "@tanstack/react-query"
import { reviewsListOptions } from "@/lib/queries"
import { RecentReviewsList } from "./_components/recent-reviews-list"
import { Topbar } from "@/components/topbar"
import Link from "next/link"

export default function OverviewPage() {
  const { data: reviews, isLoading } = useQuery(reviewsListOptions(1))
  const recent = reviews?.slice(0, 5) ?? []

  return (
    <>
      <Topbar title="Overview" />
      <div className="px-8 py-8 space-y-3">
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
      </div>
    </>
  )
}
