"use client";

import { useQuery } from "@tanstack/react-query";
import { billingOptions } from "@/lib/queries";
import { PlanCard } from "./_components/plan-card";
import { QuotaBar } from "./_components/quota-bar";
import { UpgradeDialog } from "./_components/upgrade-dialog";
import { Topbar } from "@/components/topbar";
import { api } from "@/lib/api";
import { FileText } from "lucide-react";

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
            {billing.stripe_customer_id && (
              <div
                className="border border-white/8 overflow-hidden"
                style={{ background: "rgba(255,255,255,0.04)" }}
              >
                <div className="px-4 py-3 border-b border-white/5">
                  <h3 className="text-[10px] font-bold tracking-wider uppercase text-[#8e9192]">
                    Recent Invoices
                  </h3>
                </div>
                <div className="px-4 py-6 flex items-center gap-3 text-[#8e9192]">
                  <FileText className="h-4 w-4 shrink-0" />
                  <span className="text-[13px]">
                    Invoices are managed via the Stripe billing portal.
                  </span>
                  <button
                    onClick={handlePortal}
                    className="ml-auto text-[12px] text-[#c6c6c7] hover:text-white underline underline-offset-2 transition-colors"
                  >
                    Open portal
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}
