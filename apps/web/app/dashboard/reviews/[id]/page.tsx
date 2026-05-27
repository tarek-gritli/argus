"use client"

import { use } from "react"
import { useQuery } from "@tanstack/react-query"
import { reviewDetailOptions } from "@/lib/queries"
import { FindingsExplorer } from "./_components/findings-explorer"
import { ReviewStatusBadge } from "../_components/review-status-badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Topbar } from "@/components/topbar"
import Link from "next/link"
import { ChevronLeft } from "lucide-react"

export default function ReviewDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const { data: review, isLoading } = useQuery(reviewDetailOptions(id))

  return (
    <>
      <Topbar title="Review Detail" />
      <div className="px-8 py-8">
        <Link
          href="/dashboard/reviews"
          className="inline-flex items-center gap-1 text-[12px] text-muted-foreground hover:text-foreground mb-6 transition-colors"
        >
          <ChevronLeft className="h-3.5 w-3.5" /> Back to Reviews
        </Link>

        {isLoading || !review ? (
          <div className="space-y-4">
            <Skeleton className="h-7 w-40 rounded" />
            <Skeleton className="h-4 w-24 rounded" />
            <div className="space-y-3 mt-6">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-32 rounded-lg" />
              ))}
            </div>
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-3 mb-8">
              <h2 className="text-lg font-semibold text-foreground">PR #{review.pr_number}</h2>
              <ReviewStatusBadge status={review.status} />
              <code className="text-[11px] font-mono text-muted-foreground bg-muted px-2 py-0.5 rounded">
                {review.head_sha.slice(0, 7)}
              </code>
            </div>
            <FindingsExplorer reviewId={review.id} findings={review.findings} />
          </>
        )}
      </div>
    </>
  )
}
