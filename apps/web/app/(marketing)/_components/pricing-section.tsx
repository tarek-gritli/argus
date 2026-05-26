import { Check } from "lucide-react"
import { BASE as API_URL } from "@/lib/api"

const PLANS = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "For individual developers and open-source projects.",
    cta: "Get started",
    features: [
      "50 reviews / month",
      "Security, Quality & Testing agents",
      "GitHub inline suggestions",
      "Fix engine",
      "Community support",
    ],
    highlight: false,
  },
  {
    name: "Pro",
    price: "$19",
    period: "per seat / month",
    description: "For developers who review code every day.",
    cta: "Start free trial",
    features: [
      "100 reviews / seat / month",
      "All Free features",
      "Documentation agent",
      "Semantic context injection",
      "Priority support",
    ],
    highlight: true,
  },
  {
    name: "Team",
    price: "$49",
    period: "per seat / month",
    description: "For engineering teams shipping fast.",
    cta: "Start free trial",
    features: [
      "100 reviews / seat / month",
      "All Pro features",
      "Ticket compliance agent",
      "Slack, Notion, Linear, Jira integrations",
      "Review analytics dashboard",
    ],
    highlight: false,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "contact us",
    description: "For large orgs with compliance and SSO requirements.",
    cta: "Contact sales",
    features: [
      "Unlimited reviews",
      "All Team features",
      "SAML SSO",
      "Audit logs",
      "Dedicated support SLA",
    ],
    highlight: false,
  },
]

export function PricingSection() {
  return (
    <section id="pricing" className="py-24 border-t border-white/5">
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-extrabold mb-4">Simple pricing</h2>
          <p className="text-zinc-400 text-lg">Start free. Upgrade when you need more.</p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className={`rounded-2xl border p-6 flex flex-col gap-5 transition-all ${
                plan.highlight
                  ? "border-indigo-500/60 bg-indigo-500/5 shadow-[0_0_40px_rgba(99,102,241,.15)]"
                  : "border-white/[0.08] bg-white/[0.02]"
              }`}
            >
              {plan.highlight && (
                <span className="self-start text-[10px] font-bold uppercase tracking-widest text-indigo-400 bg-indigo-400/10 border border-indigo-400/20 rounded-full px-2.5 py-1">
                  Most popular
                </span>
              )}
              <div>
                <p className="font-semibold text-zinc-300 text-sm">{plan.name}</p>
                <p className="text-4xl font-extrabold text-white mt-1">{plan.price}</p>
                <p className="text-xs text-zinc-500 mt-0.5">{plan.period}</p>
              </div>
              <p className="text-sm text-zinc-400">{plan.description}</p>
              <ul className="space-y-2 flex-1">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-zinc-300">
                    <Check className="h-3.5 w-3.5 text-emerald-400 shrink-0 mt-0.5" />
                    {f}
                  </li>
                ))}
              </ul>
              <a
                href={plan.name === "Enterprise" ? "mailto:sales@argus.dev" : `${API_URL}/api/v1/auth/github/login`}
                className={`block text-center text-sm font-semibold py-2.5 rounded-xl transition-colors ${
                  plan.highlight
                    ? "bg-indigo-500 hover:bg-indigo-400 text-white"
                    : "border border-white/10 text-zinc-300 hover:border-white/30 hover:text-white"
                }`}
              >
                {plan.cta}
              </a>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
