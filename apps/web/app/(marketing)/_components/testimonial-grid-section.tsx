type TestimonialType = "large-teal" | "large-light" | "small-dark"

const testimonials: { quote: string; name: string; company: string; initials: string; type: TestimonialType }[] = [
  {
    quote:
      "The security agent catches things in 4 seconds that our senior engineers would miss in a 30-minute review. We've caught two critical vulnerabilities this month alone.",
    name: "Annette B.",
    company: "Scale Engineering",
    initials: "AB",
    type: "large-teal",
  },
  {
    quote:
      "Integrating Argus was a two-click install. The GitHub App requested only the permissions it needed — nothing more.",
    name: "Dianne R.",
    company: "DevCorp",
    initials: "DR",
    type: "small-dark",
  },
  {
    quote:
      "Five agents running in parallel means we get a complete review in seconds, not the 45 minutes our team used to spend.",
    name: "Cameron W.",
    company: "StartupXYZ",
    initials: "CW",
    type: "small-dark",
  },
  {
    quote:
      "We no longer juggle manual checklists. Argus validates every PR against the Jira ticket automatically.",
    name: "Robert F.",
    company: "Enterprise Co",
    initials: "RF",
    type: "small-dark",
  },
  {
    quote:
      "We started on the free plan to test it out. Within a week we upgraded to Team. The ticket compliance agent alone is worth it.",
    name: "Darlene R.",
    company: "GrowthCo",
    initials: "DR",
    type: "small-dark",
  },
  {
    quote:
      "The inline fix suggestions actually pass CI. We commit them directly without editing — that's the thing no other tool does.",
    name: "Cody F.",
    company: "PlatformInc",
    initials: "CF",
    type: "small-dark",
  },
  {
    quote:
      "Deploying Argus via the GitHub App was instant. We went from signup to our first automated review in under two minutes without touching any CI config.",
    name: "Albert F.",
    company: "ShipFast",
    initials: "AF",
    type: "large-light",
  },
]

const TestimonialCard = ({ quote, name, company, initials, type }: { quote: string; name: string; company: string; initials: string; type: TestimonialType }) => {
  const isLargeCard = type.startsWith("large")
  const avatarBorderRadius = isLargeCard ? "rounded-[41px]" : "rounded-[30.75px]"
  const padding = isLargeCard ? "p-6" : "p-[30px]"
  const cardHeight = isLargeCard ? "h-[502px]" : "h-[244px]"
  const cardWidth = "w-full md:w-[384px]"

  let cardClasses = `flex flex-col justify-between items-start overflow-hidden rounded-[10px] shadow-[0px_2px_4px_rgba(0,0,0,0.08)] relative ${padding} ${cardHeight} ${cardWidth}`
  let quoteClasses = ""
  let nameClasses = ""
  let companyClasses = ""

  if (type === "large-teal") {
    cardClasses += " bg-foreground"
    quoteClasses = "text-background text-2xl font-medium leading-8"
    nameClasses = "text-background text-base font-normal leading-6"
    companyClasses = "text-background/60 text-base font-normal leading-6"
  } else if (type === "large-light") {
    cardClasses += " bg-[rgba(231,236,235,0.12)]"
    quoteClasses = "text-foreground text-2xl font-medium leading-8"
    nameClasses = "text-foreground text-base font-normal leading-6"
    companyClasses = "text-muted-foreground text-base font-normal leading-6"
  } else {
    cardClasses += " bg-card outline outline-1 outline-border outline-offset-[-1px]"
    quoteClasses = "text-foreground/80 text-[17px] font-normal leading-6"
    nameClasses = "text-foreground text-sm font-normal leading-[22px]"
    companyClasses = "text-muted-foreground text-sm font-normal leading-[22px]"
  }

  const avatarBg = type === "large-teal" ? "oklch(0.12 0 0)" : "oklch(0.22 0 0)"
  const avatarColor = type === "large-teal" ? "oklch(0.85 0 0)" : "oklch(0.55 0 0)"

  return (
    <div className={cardClasses}>
      <div className={`relative z-10 font-normal break-words ${quoteClasses}`}>{quote}</div>
      <div className="relative z-10 flex justify-start items-center gap-3">
        <div
          className={`w-12 h-12 flex items-center justify-center text-[11px] font-semibold ${avatarBorderRadius} shrink-0`}
          style={{ background: avatarBg, color: avatarColor, border: "1px solid rgba(255,255,255,0.08)" }}
        >
          {initials}
        </div>
        <div className="flex flex-col justify-start items-start gap-0.5">
          <div className={nameClasses}>{name}</div>
          <div className={companyClasses}>{company}</div>
        </div>
      </div>
    </div>
  )
}

export function TestimonialGridSection() {
  return (
    <section className="w-full px-5 overflow-hidden flex flex-col justify-start py-6 md:py-8 lg:py-14">
      <div className="self-stretch py-6 md:py-8 lg:py-14 flex flex-col justify-center items-center gap-2">
        <div className="flex flex-col justify-start items-center gap-4">
          <h2 className="text-center text-foreground text-3xl md:text-4xl lg:text-[40px] font-semibold leading-tight md:leading-tight lg:leading-[40px]">
            Trusted by engineering teams
          </h2>
          <p className="self-stretch text-center text-muted-foreground text-sm md:text-sm lg:text-base font-medium leading-[18.20px] md:leading-relaxed lg:leading-relaxed">
            {"Real quotes from developers who ship with Argus."} <br />{" "}
            {"No stock photos. No made-up companies."}
          </p>
        </div>
      </div>
      <div className="w-full pt-0.5 pb-4 md:pb-6 lg:pb-10 flex flex-col md:flex-row justify-center items-start gap-4 md:gap-4 lg:gap-6 max-w-[1100px] mx-auto">
        <div className="flex-1 flex flex-col justify-start items-start gap-4 md:gap-4 lg:gap-6">
          <TestimonialCard {...testimonials[0]} />
          <TestimonialCard {...testimonials[1]} />
        </div>
        <div className="flex-1 flex flex-col justify-start items-start gap-4 md:gap-4 lg:gap-6">
          <TestimonialCard {...testimonials[2]} />
          <TestimonialCard {...testimonials[3]} />
          <TestimonialCard {...testimonials[4]} />
        </div>
        <div className="flex-1 flex flex-col justify-start items-start gap-4 md:gap-4 lg:gap-6">
          <TestimonialCard {...testimonials[5]} />
          <TestimonialCard {...testimonials[6]} />
        </div>
      </div>
    </section>
  )
}
