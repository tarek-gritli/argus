"use client";

import { useQuery } from "@tanstack/react-query";
import { billingOptions } from "@/lib/queries";
import { PlanCard } from "./_components/plan-card";
import { QuotaBar } from "./_components/quota-bar";
import { UpgradeDialog } from "./_components/upgrade-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Topbar } from "@/components/topbar";
import { api } from "@/lib/api";
import { ExternalLink } from "lucide-react";

export default function BillingPage() {
  const { data: billing, isLoading } = useQuery(billingOptions());

  async function handlePortal() {
    const { portal_url } = await api.billing.portal();
    window.location.href = portal_url;
  }

  // billing = {
  //   plan: "free",
  //   seat_count: 5,
  //   reviews_used_this_month: 12,
  //   monthly_limit: 100,
  //   stripe_customer_id: "cus_1234567890",
  // }; // TODO: remove after testing
  // isLoading = false;

  return (
    <>
      <Topbar title="Billing" />
      <div className="px-8 py-8">
        <div className="mb-6">
          <h2 className="text-base font-semibold text-foreground">Billing</h2>
          <p className="text-[12px] text-muted-foreground mt-0.5">
            Manage your plan and usage
          </p>
        </div>

        {isLoading || !billing ? (
          <div className="space-y-3">
            <Skeleton className="h-28 rounded-lg" />
            <Skeleton className="h-28 rounded-lg" />
          </div>
        ) : (
          <div className="space-y-3">
            <PlanCard billing={billing} />
            <QuotaBar billing={billing} />
            <div className="flex gap-2 pt-1">
              {billing.plan === "free" && <UpgradeDialog />}
              {billing.stripe_customer_id && (
                <button
                  onClick={handlePortal}
                  className="flex items-center gap-1.5 px-3 py-2 rounded text-[12px] font-medium border border-border text-foreground hover:bg-muted transition-colors"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  Manage Subscription
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
