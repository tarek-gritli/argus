"use client"

import { useQuery } from "@tanstack/react-query"
import { reviewsListOptions } from "@/lib/queries"
import { StatsStrip } from "./_components/stats-strip"
import { RecentReviewsList } from "./_components/recent-reviews-list"
import { Skeleton } from "@/components/ui/skeleton"
import { Topbar } from "@/components/topbar"
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
      <div className="p-6 max-w-5xl">
        {isLoading ? (
          <div className="grid grid-cols-6 gap-3 mb-8">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-20 rounded-lg" />
            ))}
          </div>
        ) : (
          <StatsStrip counts={counts} total={reviews?.length ?? 0} />
        )}

        <div className="rounded-lg border bg-card">
          <div className="px-5 py-4 border-b border-border">
            <h2 className="text-[13px] font-semibold text-foreground">Recent Reviews</h2>
          </div>
          <div className="px-4">
            {isLoading ? (
              <div className="space-y-3 py-4">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 rounded" />
                ))}
              </div>
            ) : (
              <RecentReviewsList reviews={recent} />
            )}
          </div>
        </div>
      </div>
    </>
  )
}
