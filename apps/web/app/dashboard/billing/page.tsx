"use client";

import { useQuery } from "@tanstack/react-query";
import { billingOptions } from "@/lib/queries";
import { PlanCard } from "./_components/plan-card";
import { QuotaBar } from "./_components/quota-bar";
import { UpgradeDialog } from "./_components/upgrade-dialog";
import { Topbar } from "@/components/topbar";
import { api } from "@/lib/api";
import { FileText } from "lucide-react";

const MOCK_INVOICES = [
  { id: "INV-2023-010", date: "Oct 01, 2023", amount: "$0.00" },
  { id: "INV-2023-009", date: "Sep 01, 2023", amount: "$0.00" },
];

export default function BillingPage() {
  const { data: billing, isLoading } = useQuery(billingOptions());

  async function handlePortal() {
    const { portal_url } = await api.billing.portal();
    window.location.href = portal_url;
  }

  return (
    <>
      <Topbar title="Billing" />
      <div className="px-8 py-8">
        {isLoading || !billing ? (
          <div className="space-y-3">
            <div className="h-40 bg-white/5 animate-pulse" />
            <div className="h-24 bg-white/5 animate-pulse" />
          </div>
        ) : (
          <div className="space-y-3">
            {/* Current plan + quota */}
            <div
              className="border border-white/[0.08]"
              style={{ background: "rgba(255,255,255,0.04)" }}
            >
              <div className="p-6">
                <PlanCard billing={billing} />
                <QuotaBar billing={billing} />
              </div>
              <div className="flex gap-4 px-6 pb-6 mt-2">
                {billing.plan === "free" && <UpgradeDialog />}
                {billing.stripe_customer_id && (
                  <button
                    onClick={handlePortal}
                    className="flex-1 border border-white/10 text-[#e5e2e1] py-3 text-[14px] font-semibold hover:bg-white/5 transition-colors"
                  >
                    Manage Billing
                  </button>
                )}
              </div>
            </div>

            {/* Invoices */}
            <div
              className="border border-white/[0.08] overflow-hidden"
              style={{ background: "rgba(255,255,255,0.04)" }}
            >
              <div className="px-4 py-3 border-b border-white/5">
                <h3 className="text-[10px] font-bold tracking-wider uppercase text-[#8e9192]">
                  Recent Invoices
                </h3>
              </div>
              <div className="divide-y divide-white/5">
                {MOCK_INVOICES.map((inv) => (
                  <div
                    key={inv.id}
                    className="flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors cursor-pointer"
                  >
                    <div className="flex items-center gap-4">
                      <FileText className="h-5 w-5 text-[#8e9192]" />
                      <div>
                        <p className="text-[14px] text-[#e5e2e1]">{inv.id}</p>
                        <p className="text-[12px] text-[#8e9192]">{inv.date}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-[14px] font-semibold text-[#e5e2e1]">
                        {inv.amount}
                      </p>
                      <p className="text-[12px] text-[#c6c6c7]">Paid</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
