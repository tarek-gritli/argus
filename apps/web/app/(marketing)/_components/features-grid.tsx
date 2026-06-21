"use client"

import { motion, useInView } from "framer-motion"
import { useRef } from "react"
import { ShieldCheck, Gauge, FlaskConical, BookOpen, TicketCheck, Wrench } from "lucide-react"

const FEATURES = [
  {
    icon: ShieldCheck,
    title: "Security Agent",
    desc: "OWASP Top 10, secret detection, dependency CVE scanning. Catches injections and exposed credentials before they ship.",
  },
  {
    icon: Gauge,
    title: "Quality Agent",
    desc: "Cyclomatic complexity, code duplication, dead code, naming — across 9 languages. No false-positive noise.",
  },
  {
    icon: FlaskConical,
    title: "Testing Agent",
    desc: "Coverage gap detection, weak assertion analysis, and test anti-pattern identification on every diff.",
  },
  {
    icon: BookOpen,
    title: "Documentation Agent",
    desc: "Flags undocumented public APIs, stale comments, and auto-generates PR descriptions. Team plan and above.",
  },
  {
    icon: TicketCheck,
    title: "Ticket Compliance",
    desc: "Validates that merged code matches the linked Jira or Linear ticket scope. Enterprise and team plan.",
  },
  {
    icon: Wrench,
    title: "Fix Engine",
    desc: "Generates validated, multi-language code patches and posts them as native GitHub suggestion blocks you commit directly.",
  },
]

function FeatureCard({ feature, index }: { feature: typeof FEATURES[number]; index: number }) {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: "-80px" })
  const Icon = feature.icon

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 20 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.45, delay: (index % 3) * 0.08 }}
      className="rounded-xl border border-white/[0.07] bg-white/[0.02] p-6 hover:border-white/[0.14] hover:bg-white/[0.04] transition-all duration-200"
    >
      <div className="w-9 h-9 rounded-lg bg-white/[0.06] flex items-center justify-center mb-5">
        <Icon className="text-zinc-300" size={18} />
      </div>
      <h3 className="font-semibold text-white text-[15px] mb-2">{feature.title}</h3>
      <p className="text-[13px] text-zinc-500 leading-relaxed">{feature.desc}</p>
    </motion.div>
  )
}

export function FeaturesGrid() {
  return (
    <section id="features-section" className="py-24 max-w-6xl mx-auto px-6">
      <div className="mb-16">
        <h2 className="text-4xl font-bold text-white mb-4 tracking-tight">Five agents. One pull request.</h2>
        <p className="text-zinc-500 text-lg max-w-xl">
          Each agent is a domain specialist. They run in parallel — never sequentially — so you get a
          complete review in seconds.
        </p>
      </div>
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {FEATURES.map((f, i) => (
          <FeatureCard key={f.title} feature={f} index={i} />
        ))}
      </div>
    </section>
  )
}
