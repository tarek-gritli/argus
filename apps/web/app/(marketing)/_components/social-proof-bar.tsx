const STATS = [
  { value: "6M+", label: "Repositories reviewed" },
  { value: "75M+", label: "Defects caught" },
  { value: "4.2s", label: "Avg review time" },
  { value: "SOC 2", label: "Type II certified" },
]

export function SocialProofBar() {
  return (
    <section className="border-y border-white/[0.05] bg-white/[0.01]">
      <div className="max-w-6xl mx-auto px-6 py-10 grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
        {STATS.map(({ value, label }) => (
          <div key={label}>
            <p className="text-3xl font-bold text-white tabular-nums">{value}</p>
            <p className="text-[12px] text-zinc-600 mt-1.5">{label}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
