import AiCodeReviews from "./bento/ai-code-reviews"
import RealtimeReview from "./bento/realtime-review"
import IntegrationsIllustration from "./bento/integrations-illustration"
import ContextSearch from "./bento/context-search"
import ParallelAgents from "./bento/parallel-agents"
import FixEngine from "./bento/fix-engine"

const BentoCard = ({ title, description, Component }: { title: string; description: string; Component: React.ComponentType }) => (
  <div className="overflow-hidden rounded-2xl border border-white/20 flex flex-col justify-start items-start relative">
    <div
      className="absolute inset-0 rounded-2xl"
      style={{
        background: "rgba(231, 236, 235, 0.08)",
        backdropFilter: "blur(4px)",
        WebkitBackdropFilter: "blur(4px)",
      }}
    />
    <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent rounded-2xl" />
    <div className="self-stretch p-6 flex flex-col justify-start items-start gap-2 relative z-10">
      <div className="self-stretch flex flex-col justify-start items-start gap-1.5">
        <p className="self-stretch text-foreground text-lg font-normal leading-7">
          {title} <br />
          <span className="text-muted-foreground">{description}</span>
        </p>
      </div>
    </div>
    <div className="self-stretch h-72 relative -mt-0.5 z-10">
      <Component />
    </div>
  </div>
)

export function BentoSection() {
  const cards = [
    {
      title: "AI-powered code reviews.",
      description: "Inline fix suggestions that actually pass CI — commit them directly.",
      Component: AiCodeReviews,
    },
    {
      title: "Real-time diff analysis",
      description: "Every changed line annotated by specialized agents in seconds.",
      Component: RealtimeReview,
    },
    {
      title: "One-click integrations",
      description: "GitHub, Linear, Jira, Slack — connect your entire workflow.",
      Component: IntegrationsIllustration,
    },
    {
      title: "Semantic context injection",
      description: "Qdrant-powered vector search surfaces relevant codebase context for every review.",
      Component: ContextSearch,
    },
    {
      title: "Five parallel agents",
      description: "Security, Quality, Testing, Docs, and Ticket Compliance — all running at once.",
      Component: ParallelAgents,
    },
    {
      title: "Fix engine built-in",
      description: "Validated, multi-language patches posted as native GitHub suggestion blocks.",
      Component: FixEngine,
    },
  ]

  return (
    <section className="w-full px-5 flex flex-col justify-center items-center overflow-visible bg-transparent">
      <div className="w-full py-8 md:py-16 relative flex flex-col justify-start items-start gap-6">
        <div className="w-[547px] h-[938px] absolute top-[614px] left-[80px] origin-top-left rotate-[-33.39deg] bg-primary/10 blur-[130px] z-0" />
        <div className="self-stretch py-8 md:py-14 flex flex-col justify-center items-center gap-2 z-10">
          <div className="flex flex-col justify-start items-center gap-4">
            <h2 className="w-full max-w-[655px] text-center text-foreground text-4xl md:text-6xl font-semibold leading-tight md:leading-[66px]">
              Empower Your Code Review with AI
            </h2>
            <p className="w-full max-w-[600px] text-center text-muted-foreground text-lg md:text-xl font-medium leading-relaxed">
              Five specialized agents run in parallel on every pull request — delivering complete coverage in seconds,
              not hours.
            </p>
          </div>
        </div>
        <div className="self-stretch grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 z-10">
          {cards.map((card) => (
            <BentoCard key={card.title} {...card} />
          ))}
        </div>
      </div>
    </section>
  )
}
