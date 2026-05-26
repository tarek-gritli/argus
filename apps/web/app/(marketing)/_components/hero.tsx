"use client"

import { motion } from "framer-motion"
import { BASE as API_URL } from "@/lib/api"

const FINDING_LINES = [
  { label: "CRIT", color: "#ef4444", bg: "rgba(239,68,68,.08)", text: "SQL injection via unsanitised user input", file: "auth/login.py:47" },
  { label: "HIGH", color: "#f97316", bg: "rgba(249,115,22,.08)", text: "Hardcoded secret detected", file: "config/settings.py:12" },
  { label: "MED",  color: "#eab308", bg: "rgba(234,179,8,.08)",  text: "Missing test for edge case", file: "tests/test_billing.py" },
  { label: "LOW",  color: "#22c55e", bg: "rgba(34,197,94,.08)",  text: "Dead code: unused import", file: "utils/helpers.py:3" },
]

export function Hero() {
  return (
    <section className="relative min-h-screen flex items-center overflow-hidden pt-16">
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[500px] bg-white/[0.03] rounded-full blur-[100px]" />
      </div>

      <div className="max-w-6xl mx-auto px-6 py-24 grid lg:grid-cols-2 gap-16 items-center w-full">
        <motion.div
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        >
          <div className="inline-flex items-center gap-2 bg-white/[0.05] border border-white/[0.08] rounded-full px-4 py-1.5 text-[11px] text-zinc-500 mb-7 font-medium tracking-wide">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Now in public beta
          </div>

          <h1 className="text-5xl lg:text-6xl font-bold tracking-tight leading-[1.08] mb-6 text-white">
            Code review that catches{" "}
            <span className="text-zinc-400">what humans miss</span>
          </h1>

          <p className="text-lg text-zinc-500 leading-relaxed mb-10 max-w-lg">
            Five AI agents run in parallel on every pull request — security, quality,
            testing, docs, and ticket compliance. Inline suggestions posted to GitHub in seconds.
          </p>

          <div className="flex flex-wrap gap-3">
            <a
              href={`${API_URL}/api/v1/auth/github/login`}
              className="inline-flex items-center gap-2.5 bg-white text-black font-semibold px-6 py-3 rounded-lg hover:bg-zinc-100 transition-colors text-sm"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
              </svg>
              Start reviewing free
            </a>
            <a
              href="#how-it-works"
              className="inline-flex items-center gap-2 border border-white/[0.10] text-zinc-400 hover:text-zinc-200 hover:border-white/20 font-medium px-6 py-3 rounded-lg transition-colors text-sm"
            >
              See how it works
            </a>
          </div>

          <p className="text-[11px] text-zinc-600 mt-4">Free plan · No credit card · 2-click GitHub install</p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 32 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2, ease: "easeOut" }}
          className="relative"
        >
          <div className="rounded-xl border border-white/[0.08] bg-[oklch(0.14_0_0)] overflow-hidden shadow-2xl">
            <div className="flex items-center gap-1.5 px-4 py-3 border-b border-white/[0.05]">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500/50" />
              <span className="w-2.5 h-2.5 rounded-full bg-yellow-500/50" />
              <span className="w-2.5 h-2.5 rounded-full bg-green-500/50" />
              <span className="ml-3 text-[11px] text-zinc-600 font-mono">argus · PR #142 · acme/backend</span>
            </div>
            <div className="px-5 py-3.5 border-b border-white/[0.05] flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-5 h-5 rounded bg-white/10 flex items-center justify-center">
                  <svg width="11" height="11" viewBox="0 0 14 14" fill="none">
                    <circle cx="7" cy="7" r="6" stroke="white" strokeWidth="1.5" />
                    <circle cx="7" cy="7" r="2.5" fill="white" />
                  </svg>
                </div>
                <span className="text-[12px] font-semibold text-white/80">Argus Code Review</span>
              </div>
              <span className="text-[11px] bg-red-500/15 text-red-400 border border-red-500/20 rounded-full px-2.5 py-0.5 font-semibold">
                7 findings
              </span>
            </div>
            <div className="px-5 py-4 space-y-2">
              {FINDING_LINES.map((f, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: 12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.5 + i * 0.1, duration: 0.35 }}
                  className="flex items-start gap-3 rounded-lg p-3"
                  style={{ background: f.bg }}
                >
                  <span
                    className="shrink-0 text-[9px] font-bold rounded px-1.5 py-0.5 mt-0.5 font-mono"
                    style={{ color: f.color, border: `1px solid ${f.color}30` }}
                  >
                    {f.label}
                  </span>
                  <div className="min-w-0">
                    <span className="text-[12px] text-zinc-300 leading-relaxed block">{f.text}</span>
                    <span className="text-[10px] text-zinc-600 font-mono">{f.file}</span>
                  </div>
                </motion.div>
              ))}
            </div>
            <div className="px-5 py-3 border-t border-white/[0.05] flex items-center justify-between">
              <span className="text-[11px] text-zinc-600">Reviewed in 4.2s · 5 agents</span>
              <span className="text-[11px] text-zinc-400 font-medium">3 fixes ready</span>
            </div>
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 0.85 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 1.0, type: "spring", stiffness: 180 }}
            className="absolute -bottom-5 -left-5 bg-[oklch(0.16_0_0)] border border-white/[0.08] rounded-xl px-4 py-3 shadow-xl"
          >
            <p className="text-[11px] text-zinc-500">Parallel agents</p>
            <p className="text-lg font-bold text-white">5× faster</p>
          </motion.div>
        </motion.div>
      </div>
    </section>
  )
}
