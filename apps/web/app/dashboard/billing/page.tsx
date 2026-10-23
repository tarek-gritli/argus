"use client";

import { useQuery } from "@tanstack/react-query";
import { billingOptions, invoicesOptions } from "@/lib/queries";
import { PlanCard } from "./_components/plan-card";
import { QuotaBar } from "./_components/quota-bar";
import { UpgradeDialog } from "./_components/upgrade-dialog";
import { Topbar } from "@/components/topbar";
import { api } from "@/lib/api";
import { FileText } from "lucide-react";

export default function BillingPage() {
  const { data: billing, isLoading } = useQuery(billingOptions());
  const { data: invoices = [] } = useQuery(invoicesOptions());

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
                {billing.has_stripe_customer && (
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
            {billing.has_stripe_customer && (
              <div
                className="border border-white/8 overflow-hidden"
                style={{ background: "rgba(255,255,255,0.04)" }}
              >
                <div className="px-4 py-3 border-b border-white/5">
                  <h3 className="text-[10px] font-bold tracking-wider uppercase text-[#8e9192]">
                    Recent Invoices
                  </h3>
                </div>
                {invoices.length === 0 ? (
                  <div className="px-4 py-6 text-center text-[13px] text-[#8e9192]">
                    No invoices yet
                  </div>
                ) : (
                  <div className="divide-y divide-white/5">
                    {invoices.map((inv) => (
                      <div
                        key={inv.id}
                        className="flex items-center justify-between px-4 py-3 hover:bg-white/[0.02] transition-colors"
                      >
                        <div className="flex items-center gap-4">
                          <FileText className="h-5 w-5 text-[#8e9192]" />
                          <div>
                            <p className="text-[14px] text-[#e5e2e1]">{inv.number}</p>
                            <p className="text-[12px] text-[#8e9192]">
                              {new Date(inv.created * 1000).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                        <div className="text-right flex items-center gap-3">
                          <div>
                            <p className="text-[14px] font-semibold text-[#e5e2e1]">
                              ${(inv.amount_paid / 100).toFixed(2)}
                            </p>
                            <p className="text-[12px] text-[#4ade80] capitalize">{inv.status}</p>
                          </div>
                          {inv.invoice_pdf && (
                            <a
                              href={inv.invoice_pdf}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[11px] text-[#8e9192] hover:text-[#c6c6c7] underline"
                            >
                              PDF
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}
