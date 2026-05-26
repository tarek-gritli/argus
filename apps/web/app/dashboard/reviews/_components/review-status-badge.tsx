import { cn } from "@/lib/utils"

const STATUS_CONFIG: Record<string, { dot: string; text: string; bg: string }> = {
  pending: { dot: "bg-yellow-500", text: "text-yellow-700 dark:text-yellow-400", bg: "bg-yellow-500/8 border-yellow-500/20" },
  running: { dot: "bg-blue-500 animate-pulse", text: "text-blue-700 dark:text-blue-400", bg: "bg-blue-500/8 border-blue-500/20" },
  done:    { dot: "bg-green-500",  text: "text-green-700 dark:text-green-400",  bg: "bg-green-500/8 border-green-500/20" },
  failed:  { dot: "bg-red-500",    text: "text-red-700 dark:text-red-400",    bg: "bg-red-500/8 border-red-500/20" },
}

export function ReviewStatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.pending
  return (
    <span className={cn("inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[11px] font-medium", cfg.bg, cfg.text)}>
      <span className={cn("w-1.5 h-1.5 rounded-full", cfg.dot)} />
      <span className="capitalize">{status}</span>
    </span>
  )
}
