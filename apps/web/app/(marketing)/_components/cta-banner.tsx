import { BASE as API_URL } from "@/lib/api"

export function CtaBanner() {
  return (
    <section className="py-24 border-t border-white/[0.05]">
      <div className="max-w-4xl mx-auto px-6 text-center">
        <div className="rounded-2xl bg-white/[0.02] border border-white/[0.07] px-8 py-16 relative overflow-hidden">
          <div className="absolute inset-0 -z-10">
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[300px] bg-white/[0.02] rounded-full blur-[80px]" />
          </div>
          <h2 className="text-4xl lg:text-5xl font-bold text-white mb-4 tracking-tight">
            Start reviewing in 2 minutes
          </h2>
          <p className="text-zinc-500 text-lg mb-8 max-w-lg mx-auto">
            Free plan. No credit card. Works with any GitHub repository.
          </p>
          <a
            href={`${API_URL}/api/v1/auth/github/login`}
            className="inline-flex items-center gap-2.5 bg-white text-black font-semibold px-8 py-4 rounded-lg hover:bg-zinc-100 transition-colors text-[15px]"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
            </svg>
            Get started with GitHub
          </a>
        </div>
      </div>
    </section>
  )
}
