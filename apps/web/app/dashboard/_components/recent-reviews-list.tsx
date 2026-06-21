import Link from "next/link"
import { ReviewStatusBadge } from "../reviews/_components/review-status-badge"
import type { Review } from "@/lib/types"

export function RecentReviewsList({ reviews }: { reviews: Review[] }) {
  if (!reviews.length) {
    return (
      <div className="py-12 text-center">
        <p className="text-[13px] text-[#8e9192]">No reviews yet.</p>
        <p className="text-[11px] text-[#444748] mt-1">Reviews will appear here once your first PR is analyzed.</p>
      </div>
    )
  }

  return (
    <div className="divide-y divide-white/5">
      {reviews.map((r) => (
        <Link
          key={r.id}
          href={`/dashboard/reviews/${r.id}`}
          className="flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors"
        >
          <div className="flex items-center gap-6">
            <span className="font-mono text-[13px] text-[#c6c6c7]">#{r.pr_number}</span>
            <div className="flex flex-col">
              <span className="text-[14px] text-[#e5e2e1]">PR #{r.pr_number}</span>
              <span className="font-mono text-[10px] text-[#8e9192]">{r.head_sha.slice(0, 7)}</span>
            </div>
          </div>
          <div className="flex items-center gap-8">
            <ReviewStatusBadge status={r.status} />
            <span className="font-mono text-[11px] text-[#8e9192]">
              {new Date(r.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
            </span>
          </div>
        </Link>
      ))}
    </div>
  )
}
