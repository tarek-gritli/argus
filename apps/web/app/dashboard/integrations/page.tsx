"use client";

import Image from "next/image";
import { useQuery } from "@tanstack/react-query";
import { integrationsOptions, billingOptions } from "@/lib/queries";
import { IntegrationCard } from "./_components/integration-card";
import { Skeleton } from "@/components/ui/skeleton";
import { Topbar } from "@/components/topbar";
import { api } from "@/lib/api";
import { getOrgId } from "@/lib/auth";
import type { Integration } from "@/lib/types";
import { Plus, Lock } from "lucide-react";

const KIND_LOGOS: Record<string, string> = {
  slack: "/slack.png",
  notion: "/notion.png",
  linear: "/linear.png",
  jira: "/jira.png",
};

const ALL_KINDS = ["slack", "notion", "linear", "jira"] as const;
const KIND_LABELS: Record<string, string> = {
  slack: "Slack",
  notion: "Notion",
  linear: "Linear",
  jira: "Jira",
};
const KIND_DESCRIPTIONS: Record<string, string> = {
  slack: "Post findings to a Slack channel",
  notion: "Create Notion pages for findings",
  linear: "Open Linear issues for critical findings",
  jira: "Create Jira tickets from review results",
};

export default function IntegrationsPage() {
  const orgId = getOrgId() ?? "";
  const { data: billing, isLoading: billingLoading } =
    useQuery(billingOptions());
  const { data: integrations, isLoading: integrationsLoading } = useQuery(
    integrationsOptions(orgId),
  );

  const isLoading = billingLoading || integrationsLoading;
  const hasAccess = billing?.plan === "team" || billing?.plan === "enterprise";

  const connectedByKind = (integrations ?? []).reduce<
    Record<string, Integration>
  >((acc, i) => ({ ...acc, [i.kind]: i }), {});

  return (
    <>
      <Topbar title="Integrations" />
      <div className="px-8 py-8">
        <div className="mb-6">
          <h2 className="text-[24px] font-semibold leading-8 tracking-[-0.02em] text-[#c6c6c7]">
            Integrations
          </h2>
          <p className="text-[14px] text-[#8e9192] mt-1">
            Connect Argus to your tools. Findings are posted automatically after
            each review.
          </p>
        </div>

        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-20" />
            ))}
          </div>
        ) : !hasAccess ? (
          <section
            className="border border-white/8 p-8 flex flex-col items-center text-center"
            style={{ background: "rgba(255,255,255,0.04)" }}
          >
            <div
              className="w-10 h-10 border border-white/10 flex items-center justify-center mb-4"
              style={{ background: "rgba(255,255,255,0.06)" }}
            >
              <Lock className="h-5 w-5 text-[#8e9192]" />
            </div>
            <h3 className="text-[18px] font-semibold text-[#e5e2e1] mb-1">
              Team plan required
            </h3>
            <p className="text-[13px] text-[#8e9192] max-w-sm">
              Integrations are available on the Team and Enterprise plans.
              Upgrade to connect Slack, Notion, Linear, and Jira.
            </p>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-[10px] font-bold tracking-wider uppercase text-[#8e9192]">
                Current plan:
              </span>
              <span className="text-[10px] font-bold tracking-wider uppercase text-[#c6c6c7]">
                {billing?.plan ?? "—"}
              </span>
            </div>
            <a
              href="/dashboard/billing"
              className="mt-6 bg-[#e2e2e2] text-[#2f3131] px-6 py-2.5 text-[13px] font-semibold hover:opacity-90 transition-opacity"
            >
              Upgrade Plan
            </a>
          </section>
        ) : (
          <div
            className="border border-white/8 overflow-hidden"
            style={{ background: "rgba(255,255,255,0.04)" }}
          >
            {ALL_KINDS.map((kind, idx) => {
              const integration = connectedByKind[kind];
              const isLast = idx === ALL_KINDS.length - 1;
              if (integration) {
                return (
                  <div
                    key={integration.id}
                    className={!isLast ? "border-b border-white/5" : ""}
                  >
                    <IntegrationCard integration={integration} orgId={orgId} />
                  </div>
                );
              }
              return (
                <div
                  key={kind}
                  className={`flex items-center justify-between px-5 py-4 ${!isLast ? "border-b border-white/5" : ""}`}
                >
                  <div className="flex items-center gap-4">
                    <div className="w-8 h-8 bg-[#2a2a2a] flex items-center justify-center">
                      {KIND_LOGOS[kind] ? (
                        <Image
                          src={KIND_LOGOS[kind]}
                          alt={KIND_LABELS[kind]}
                          width={20}
                          height={20}
                          className="rounded-sm object-contain"
                        />
                      ) : (
                        <span className="text-[11px] font-bold text-[#c6c6c7]">
                          {KIND_LABELS[kind][0]}
                        </span>
                      )}
                    </div>
                    <div>
                      <p className="text-[14px] font-semibold text-[#e5e2e1]">
                        {KIND_LABELS[kind]}
                      </p>
                      <p className="text-[12px] text-[#8e9192]">
                        {KIND_DESCRIPTIONS[kind]}
                      </p>
                    </div>
                  </div>
                  <a href={api.integrations.connectUrl(kind, orgId)}>
                    <button className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium border border-white/10 text-[#c6c6c7] hover:bg-white/5 transition-colors">
                      <Plus className="h-3.5 w-3.5" /> Connect
                    </button>
                  </a>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
