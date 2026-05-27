"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { CheckCircle, Zap, Receipt } from "lucide-react";
import { Topbar } from "@/components/topbar";

export default function PaymentSuccessPage() {
  const router = useRouter();
  const qc = useQueryClient();

  useEffect(() => {
    // Invalidate billing cache so the dashboard reflects the new plan immediately
    qc.invalidateQueries({ queryKey: ["billing"] });
  }, [qc]);

  return (
    <>
      <Topbar title="Billing" />
      <div className="px-8 py-8 flex flex-col items-center">
        {/* Success card */}
        <div
          className="w-full max-w-[480px] border border-white/[0.12] overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-500"
          style={{ background: "rgba(255,255,255,0.04)" }}
        >
          <div className="p-6 flex flex-col items-center text-center gap-4">
            {/* Icon */}
            <div className="w-16 h-16 flex items-center justify-center border border-white/10 mt-2">
              <CheckCircle
                className="h-10 w-10 text-[#4ade80] animate-pulse"
                strokeWidth={1.5}
              />
            </div>

            {/* Headline */}
            <div className="space-y-1">
              <h2 className="text-[24px] font-semibold leading-8 tracking-[-0.02em] text-[#e5e2e1]">
                Payment Successful
              </h2>
              <p className="text-[14px] text-[#8e9192] max-w-[320px] mx-auto">
                Your organization has been upgraded. All features and agent
                capabilities are now active.
              </p>
            </div>

            {/* Order details */}
            <div className="w-full border-t border-white/5 pt-4 pb-2 text-left font-mono space-y-2">
              <div className="flex justify-between">
                <span className="text-[12px] text-[#8e9192]">Plan</span>
                <span className="text-[12px] text-[#e5e2e1]">Upgraded</span>
              </div>
              <div className="flex justify-between pt-2">
                <span className="text-[12px] text-[#8e9192]">Status</span>
                <span className="flex items-center gap-1.5 text-[12px] font-bold text-[#4ade80]">
                  <span className="w-1.5 h-1.5 bg-[#4ade80] rounded-full animate-pulse" />
                  COMPLETED
                </span>
              </div>
            </div>

            {/* CTA */}
            <div className="w-full pt-1">
              <button
                onClick={() => router.push("/dashboard")}
                className="w-full bg-[#e2e2e2] text-[#2f3131] py-3 text-[10px] font-bold tracking-widest uppercase hover:opacity-90 active:scale-[0.98] transition-all"
              >
                Go to Dashboard
              </button>
            </div>
          </div>
        </div>

        {/* Bento info cards */}
        <div className="mt-3 grid grid-cols-2 gap-3 w-full max-w-[480px]">
          <div
            className="border border-white/[0.12] p-4 flex flex-col gap-2"
            style={{ background: "rgba(255,255,255,0.04)" }}
          >
            <Zap className="h-5 w-5 text-[#e5e2e1]" strokeWidth={1.5} />
            <h3 className="text-[10px] font-bold tracking-wider uppercase text-[#e5e2e1]">
              Instant Provisioning
            </h3>
            <p className="text-[12px] text-[#8e9192]">
              Cloud nodes are being spun up now.
            </p>
          </div>
          <div
            className="border border-white/[0.12] p-4 flex flex-col gap-2"
            style={{ background: "rgba(255,255,255,0.04)" }}
          >
            <Receipt className="h-5 w-5 text-[#e5e2e1]" strokeWidth={1.5} />
            <h3 className="text-[10px] font-bold tracking-wider uppercase text-[#e5e2e1]">
              Auto-Invoicing
            </h3>
            <p className="text-[12px] text-[#8e9192]">
              Receipt sent to your billing email.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
