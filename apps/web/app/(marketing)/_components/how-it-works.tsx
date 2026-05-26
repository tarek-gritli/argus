"use client"

import { motion, useInView } from "framer-motion"
import { useRef } from "react"

const STEPS = [
  {
    number: "01",
    title: "Install the GitHub App",
    desc: "Two clicks. Argus requests the minimum required permissions: read diffs and post review comments. No source code is stored.",
  },
  {
    number: "02",
    title: "Open a pull request",
    desc: "Argus receives the webhook, fetches the diff, and dispatches all five agents in parallel. Your team's context is injected via semantic search.",
  },
  {
    number: "03",
    title: "Get inline suggestions",
    desc: "Findings appear as native GitHub review comments, grouped by severity. One-click fixes are attached as suggestion blocks you can commit directly.",
  },
]

export function HowItWorks() {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: "-80px" })

  return (
    <section id="how-it-works" className="py-24 border-t border-white/[0.05]">
      <div className="max-w-6xl mx-auto px-6">
        <div className="mb-16">
          <h2 className="text-4xl font-bold text-white mb-4 tracking-tight">Up and running in 2 minutes</h2>
          <p className="text-zinc-500 text-lg">No CI changes. No config files. Just install and push.</p>
        </div>
        <div ref={ref} className="grid md:grid-cols-3 gap-10 relative">
          <div className="hidden md:block absolute top-7 left-[calc(16.66%+2rem)] right-[calc(16.66%+2rem)] h-px bg-white/[0.06]" />
          {STEPS.map((step, i) => (
            <motion.div
              key={step.number}
              initial={{ opacity: 0, y: 20 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.45, delay: i * 0.12 }}
            >
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-white/[0.04] border border-white/[0.08] text-zinc-500 font-mono font-bold text-sm mb-6">
                {step.number}
              </div>
              <h3 className="font-semibold text-white text-[15px] mb-2.5">{step.title}</h3>
              <p className="text-[13px] text-zinc-500 leading-relaxed">{step.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
