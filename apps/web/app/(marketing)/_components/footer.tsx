import Link from "next/link"

export function Footer() {
  return (
    <footer className="border-t border-white/[0.05] py-12">
      <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="flex items-center gap-2.5">
          <div className="w-5 h-5 rounded bg-white/10 flex items-center justify-center">
            <svg width="11" height="11" viewBox="0 0 14 14" fill="none">
              <circle cx="7" cy="7" r="6" stroke="white" strokeWidth="1.5" />
              <circle cx="7" cy="7" r="2.5" fill="white" />
            </svg>
          </div>
          <span className="text-[12px] font-semibold text-zinc-500 tracking-wide">ARGUS</span>
          <span className="text-zinc-700 text-[12px] ml-1">© {new Date().getFullYear()}</span>
        </div>

        <nav className="flex items-center gap-6 text-[13px] text-zinc-600">
          <Link href="/docs" className="hover:text-zinc-400 transition-colors">Docs</Link>
          <Link href="/home#pricing" className="hover:text-zinc-400 transition-colors">Pricing</Link>
          <a href="https://github.com/argus-ai/argus" className="hover:text-zinc-400 transition-colors">GitHub</a>
          <a href="mailto:support@argus.dev" className="hover:text-zinc-400 transition-colors">Support</a>
          <Link href="/privacy" className="hover:text-zinc-400 transition-colors">Privacy</Link>
        </nav>

        <div className="flex items-center gap-1.5 text-[11px] text-zinc-700 bg-white/[0.03] border border-white/[0.05] rounded-lg px-3 py-1.5">
          <svg className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          SOC 2 Type II
        </div>
      </div>
    </footer>
  )
}
