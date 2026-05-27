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
import { ChevronLeft, ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

const col = createColumnHelper<Review>()

const COLUMNS = [
  col.accessor("pr_number", {
    header: "PR #",
    cell: (info) => (
      <Link
        href={`/dashboard/reviews/${info.row.original.id}`}
        className="font-mono text-[13px] text-white/90 hover:text-white transition-colors"
      >
        #{info.getValue()}
      </Link>
    ),
  }),
  col.accessor("status", {
    header: "Status",
    cell: (info) => <ReviewStatusBadge status={info.getValue()} />,
  }),
  col.accessor("head_sha", {
    header: "Commit SHA",
    cell: (info) => (
      <span className="font-mono text-[13px] text-[#c4c7c8]/80">{info.getValue().slice(0, 7)}</span>
    ),
  }),
  col.accessor("created_at", {
    header: "Started",
    cell: (info) => (
      <span className="text-[12px] text-[#c4c7c8]">
        {new Date(info.getValue()).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
      </span>
    ),
  }),
  col.accessor("completed_at", {
    header: "Duration",
    cell: (info) => (
      <span className="text-[12px] text-[#c4c7c8]">
        {info.getValue() ? "—" : "—"}
      </span>
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
    <div className="border border-white/10 overflow-hidden" style={{ background: "rgba(255,255,255,0.05)" }}>
      <table className="w-full text-left border-collapse">
        <thead style={{ background: "rgba(42,42,42,0.5)" }}>
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id} className="border-b border-[#444748]">
              {hg.headers.map((h) => (
                <th
                  key={h.id}
                  className="px-4 py-3 text-[10px] font-bold tracking-[0.05em] uppercase text-[#c4c7c8]"
                >
                  {h.isPlaceholder ? null : flexRender(h.column.columnDef.header, h.getContext())}
                </th>
              ))}
              <th className="px-4 py-3 text-[10px] font-bold tracking-[0.05em] uppercase text-[#c4c7c8] text-right">
                Actions
              </th>
            </tr>
          ))}
        </thead>
        <tbody className="divide-y divide-white/5">
          {table.getRowModel().rows.length ? (
            table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="hover:bg-white/[0.03] transition-colors">
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-4 py-3">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
                <td className="px-4 py-3 text-right">
                  <Link
                    href={`/dashboard/reviews/${row.original.id}`}
                    className={cn(
                      "inline-block px-3 py-1 text-[10px] font-bold tracking-[0.05em] uppercase border transition-colors",
                      row.original.status === "failed"
                        ? "text-[#ffb4ab] border-[#ffb4ab]/30 hover:bg-[#ffb4ab]/10"
                        : row.original.status === "running"
                        ? "text-white border-white/30 hover:bg-white/10"
                        : "text-[#c4c7c8] border-[#444748] hover:text-white hover:bg-white/5"
                    )}
                  >
                    VIEW
                  </Link>
                </td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={COLUMNS.length + 1} className="text-center py-12 text-[13px] text-[#8e9192]">
                No reviews found.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {/* Pagination */}
      <div
        className="px-4 py-4 border-t border-white/5 flex items-center justify-between"
        style={{ background: "rgba(42,42,42,0.3)" }}
      >
        <span className="text-[12px] text-[#c4c7c8]">Page {page}</span>
        <div className="flex items-center gap-2">
          <button
            disabled={page <= 1}
            onClick={() => onPageChange(page - 1)}
            className={cn(
              "flex items-center gap-1 px-3 py-1.5 border text-[10px] font-bold tracking-[0.05em] uppercase transition-colors",
              page <= 1
                ? "opacity-40 cursor-not-allowed border-[#444748] text-[#8e9192]"
                : "border-[#444748] text-[#c4c7c8] hover:border-white hover:text-white"
            )}
          >
            <ChevronLeft className="h-3.5 w-3.5" /> Previous
          </button>
          <button
            disabled={!hasMore}
            onClick={() => onPageChange(page + 1)}
            className={cn(
              "flex items-center gap-1 px-3 py-1.5 border text-[10px] font-bold tracking-[0.05em] uppercase transition-colors",
              !hasMore
                ? "opacity-40 cursor-not-allowed border-[#444748] text-[#8e9192]"
                : "border-[#444748] text-[#c4c7c8] hover:border-white hover:text-white"
            )}
          >
            Next <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </div>
  )
}
