"use client"

import { useRouter } from "next/navigation"
import { AlertTriangle } from "lucide-react"
import { Topbar } from "@/components/topbar"

export default function PaymentCancelPage() {
  const router = useRouter()
  const timestamp = new Date().toISOString().replace("T", " ").slice(0, 19) + " UTC"

  return (
    <>
      <Topbar title="Billing" />
      <div className="px-8 py-8 flex flex-col items-center">

        {/* Cancellation card */}
        <div
          className="w-full max-w-[480px] border border-white/[0.12] overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-500"
          style={{ background: "rgba(255,255,255,0.04)" }}
        >
          {/* Header */}
          <div className="p-6 flex flex-col items-center text-center border-b border-white/5">
            <div className="w-12 h-12 border border-[#ffb4ab]/40 bg-[#ffb4ab]/5 flex items-center justify-center mb-4">
              <AlertTriangle className="h-7 w-7 text-[#ffb4ab]" strokeWidth={1.5} />
            </div>
            <h2 className="text-[18px] font-semibold leading-6 tracking-[-0.01em] text-[#e5e2e1] mb-1">
              Payment Cancelled
            </h2>
            <p className="text-[14px] text-[#8e9192] max-w-[320px]">
              The checkout process was cancelled. Your current plan remains unchanged. No charges were made.
            </p>
          </div>

          {/* Technical details */}
          <div className="px-6 py-4 space-y-2" style={{ background: "#0e0e0e" }}>
            <div className="flex justify-between items-center">
              <span className="text-[10px] font-bold tracking-widest uppercase text-[#8e9192]/50">Status</span>
              <span className="border border-[#ffb4ab]/30 bg-[#2a2a2a] px-2 py-0.5 font-mono text-[11px] text-[#ffb4ab]">
                DISCONTINUED
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-[10px] font-bold tracking-widest uppercase text-[#8e9192]/50">Timestamp</span>
              <span className="font-mono text-[11px] text-[#8e9192]">{timestamp}</span>
            </div>
          </div>

          {/* CTAs */}
          <div className="p-6 flex flex-col gap-3">
            <button
              onClick={() => router.push("/dashboard/billing")}
              className="w-full bg-[#e2e2e2] text-[#2f3131] py-3 text-[10px] font-bold tracking-widest uppercase hover:opacity-90 active:scale-[0.98] transition-all"
            >
              Return to Billing
            </button>
            <button
              onClick={() => window.open("mailto:support@argus.ai")}
              className="w-full border border-white/10 text-[#e5e2e1] py-3 text-[10px] font-bold tracking-widest uppercase hover:bg-white/5 active:scale-[0.98] transition-all"
            >
              Contact Support
            </button>
          </div>
        </div>

        {/* Footer */}
        <p className="mt-4 text-[12px] text-[#8e9192]/60 text-center max-w-sm">
          If you encountered an error during checkout, browse the{" "}
          <a href="#" className="underline hover:text-[#8e9192] transition-colors">Help Center</a>
          {" "}for common Stripe integration issues.
        </p>

      </div>
    </>
  )
}
