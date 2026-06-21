"use client"

import { use } from "react"
import { useQuery } from "@tanstack/react-query"
import { reviewDetailOptions } from "@/lib/queries"
import { FindingsExplorer } from "./_components/findings-explorer"
import { ReviewStatusBadge } from "../_components/review-status-badge"
import { Topbar } from "@/components/topbar"
import Link from "next/link"
import { ArrowLeft, GitCommitHorizontal } from "lucide-react"

export default function ReviewDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const { data: review, isLoading } = useQuery(reviewDetailOptions(id))

  return (
    <>
      <Topbar title="Reviews" />
      <div className="px-8 py-8">

        {/* Back link */}
        <Link
          href="/dashboard/reviews"
          className="inline-flex items-center gap-1.5 text-[10px] font-bold tracking-[0.05em] uppercase text-[#8e9192] hover:text-white transition-colors mb-6"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> All Reviews
        </Link>

        {isLoading || !review ? (
          <div className="space-y-4">
            <div className="h-8 w-64 bg-white/5 animate-pulse" />
            <div className="h-4 w-48 bg-white/5 animate-pulse" />
            <div className="space-y-4 mt-8">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-36 bg-white/5 animate-pulse" />
              ))}
            </div>
          </div>
        ) : (
          <>
            {/* Hero header */}
            <section className="mb-8">
              <div className="flex items-center gap-4 mb-3">
                <h2 className="text-[24px] font-semibold leading-8 tracking-[-0.02em] text-[#e5e2e1]">
                  PR #{review.pr_number}
                </h2>
                <ReviewStatusBadge status={review.status} />
              </div>
              <div className="flex items-center gap-3 text-[#c4c7c8]">
                <div className="flex items-center gap-1.5 px-2 py-1 border border-[#444748] bg-[#2a2a2a]">
                  <GitCommitHorizontal className="h-3.5 w-3.5" />
                  <span className="font-mono text-[11px] uppercase">{review.head_sha.slice(0, 7)}</span>
                </div>
                <span className="text-[#444748]">•</span>
                <span className="text-[12px]">
                  Started{" "}
                  <span className="text-[#e5e2e1] font-semibold">
                    {new Date(review.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                  </span>
                </span>
                {review.completed_at && (
                  <>
                    <span className="text-[#444748]">•</span>
                    <span className="text-[12px]">
                      Completed{" "}
                      <span className="text-[#e5e2e1] font-semibold">
                        {new Date(review.completed_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                      </span>
                    </span>
                  </>
                )}
              </div>
            </section>

            <FindingsExplorer reviewId={review.id} findings={review.findings} />
          </>
        )}

      </div>
    </>
  )
}
