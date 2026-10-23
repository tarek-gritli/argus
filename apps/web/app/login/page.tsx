import { ProviderButtons } from "@/components/provider-buttons"

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[oklch(0.10_0_0)]">
      <div className="w-full max-w-sm px-8">
        <div className="mb-10 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-white/8 border border-white/10 mb-6">
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
              <circle cx="11" cy="11" r="9.5" stroke="white" strokeWidth="1.5" />
              <circle cx="11" cy="11" r="4" fill="white" />
            </svg>
          </div>
          <h1 className="text-xl font-semibold text-white tracking-tight">Argus</h1>
          <p className="mt-1.5 text-sm text-white/40">AI-powered code review</p>
        </div>

        <ProviderButtons />

        <p className="mt-6 text-center text-[11px] text-white/25">
          By continuing you agree to our terms of service.
        </p>
      </div>
    </div>
  )
}
