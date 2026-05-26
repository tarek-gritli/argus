"use client"

import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { reviewsListOptions } from "@/lib/queries"
import { ReviewsTable } from "./_components/reviews-table"
import { Skeleton } from "@/components/ui/skeleton"
import { Topbar } from "@/components/topbar"

export default function ReviewsPage() {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useQuery(reviewsListOptions(page))

  return (
    <>
      <Topbar title="Reviews" />
      <div className="p-6 max-w-5xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-base font-semibold text-foreground">All Reviews</h2>
            <p className="text-[12px] text-muted-foreground mt-0.5">Pull request analysis history</p>
          </div>
        </div>
        {isLoading ? (
          <div className="rounded-lg border overflow-hidden">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 px-4 py-3 border-b last:border-b-0">
                <Skeleton className="h-4 w-16 rounded" />
                <Skeleton className="h-4 w-20 rounded" />
                <Skeleton className="h-5 w-16 rounded-full" />
                <Skeleton className="h-4 w-24 rounded ml-auto" />
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
      </div>
    </>
  )
}
