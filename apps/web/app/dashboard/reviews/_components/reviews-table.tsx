"use client"

import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
} from "@tanstack/react-table"
import { useState } from "react"
import Link from "next/link"
import { ReviewStatusBadge } from "./review-status-badge"
import type { Review } from "@/lib/types"
import { ArrowUpDown, ChevronLeft, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

const col = createColumnHelper<Review>()

const COLUMNS = [
  col.accessor("pr_number", {
    header: "PR",
    cell: (info) => (
      <Link
        href={`/dashboard/reviews/${info.row.original.id}`}
        className="font-semibold text-foreground hover:text-foreground/70 transition-colors tabular-nums"
      >
        #{info.getValue()}
      </Link>
    ),
  }),
  col.accessor("head_sha", {
    header: "Commit",
    cell: (info) => (
      <code className="text-[11px] font-mono text-muted-foreground bg-muted px-2 py-0.5 rounded">
        {info.getValue().slice(0, 7)}
      </code>
    ),
  }),
  col.accessor("status", {
    header: "Status",
    cell: (info) => <ReviewStatusBadge status={info.getValue()} />,
  }),
  col.accessor("created_at", {
    header: ({ column }) => (
      <button
        onClick={() => column.toggleSorting()}
        className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground hover:text-foreground transition-colors"
      >
        Created <ArrowUpDown className="h-3 w-3" />
      </button>
    ),
    cell: (info) => (
      <span className="text-[12px] text-muted-foreground tabular-nums">
        {new Date(info.getValue()).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
      </span>
    ),
  }),
  col.accessor("completed_at", {
    header: "Completed",
    cell: (info) =>
      info.getValue() ? (
        <span className="text-[12px] text-muted-foreground tabular-nums">
          {new Date(info.getValue()!).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
        </span>
      ) : (
        <span className="text-[12px] text-muted-foreground/40">—</span>
      ),
  }),
]

interface Props {
  data: Review[]
  page: number
  onPageChange: (p: number) => void
  hasMore: boolean
}

export function ReviewsTable({ data, page, onPageChange, hasMore }: Props) {
  const [sorting, setSorting] = useState<SortingState>([])

  const table = useReactTable({
    data,
    columns: COLUMNS,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    manualPagination: true,
  })

  return (
    <div>
      <div className="rounded-lg border overflow-hidden bg-card">
        <table className="w-full text-sm">
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className="border-b bg-muted/40">
                {hg.headers.map((h) => (
                  <th
                    key={h.id}
                    className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wide text-muted-foreground"
                  >
                    {h.isPlaceholder ? null : flexRender(h.column.columnDef.header, h.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-border">
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="hover:bg-muted/30 transition-colors">
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-4 py-3">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={COLUMNS.length} className="text-center py-12 text-sm text-muted-foreground">
                  No reviews found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between mt-4">
        <span className="text-[12px] text-muted-foreground">Page {page}</span>
        <div className="flex items-center gap-1">
          <button
            disabled={page <= 1}
            onClick={() => onPageChange(page - 1)}
            className={cn(
              "flex items-center gap-1 px-3 py-1.5 rounded text-[12px] font-medium border transition-colors",
              page <= 1
                ? "opacity-40 cursor-not-allowed border-border text-muted-foreground"
                : "border-border text-foreground hover:bg-muted"
            )}
          >
            <ChevronLeft className="h-3.5 w-3.5" /> Previous
          </button>
          <button
            disabled={!hasMore}
            onClick={() => onPageChange(page + 1)}
            className={cn(
              "flex items-center gap-1 px-3 py-1.5 rounded text-[12px] font-medium border transition-colors",
              !hasMore
                ? "opacity-40 cursor-not-allowed border-border text-muted-foreground"
                : "border-border text-foreground hover:bg-muted"
            )}
          >
            Next <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  )
}
