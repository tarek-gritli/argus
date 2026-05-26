import Link from "next/link"
import { ReviewStatusBadge } from "../reviews/_components/review-status-badge"
import { ArrowUpRight } from "lucide-react"
import type { Review } from "@/lib/types"

export function RecentReviewsList({ reviews }: { reviews: Review[] }) {
  if (!reviews.length) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm text-muted-foreground">No reviews yet.</p>
        <p className="text-xs text-muted-foreground/60 mt-1">Reviews will appear here once your first PR is analyzed.</p>
      </div>
    )
  }
  return (
    <ul className="divide-y divide-border">
      {reviews.map((r) => (
        <li key={r.id}>
          <Link
            href={`/dashboard/reviews/${r.id}`}
            className="flex items-center justify-between py-3 px-1 group hover:bg-muted/40 rounded transition-colors -mx-1 px-1"
          >
            <div className="flex items-center gap-3 min-w-0">
              <span className="text-sm font-semibold text-foreground">PR #{r.pr_number}</span>
              <code className="text-[10px] font-mono text-muted-foreground/70 bg-muted px-1.5 py-0.5 rounded hidden sm:block">
                {r.head_sha.slice(0, 7)}
              </code>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <ReviewStatusBadge status={r.status} />
              <span className="text-[11px] text-muted-foreground tabular-nums">
                {new Date(r.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
              </span>
              <ArrowUpRight className="h-3.5 w-3.5 text-muted-foreground/40 group-hover:text-muted-foreground transition-colors" />
            </div>
          </Link>
        </li>
      ))}
    </ul>
  )
}
