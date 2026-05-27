import Link from "next/link"
import { BASE as API_URL } from "@/lib/api"

export function CTASection() {
  return (
    <section className="w-full pt-20 md:pt-60 lg:pt-60 pb-10 md:pb-20 px-5 relative flex flex-col justify-center items-center overflow-visible">
      <div className="absolute inset-0 top-[-90px]">
        <svg
          className="w-full h-full"
          viewBox="0 0 1388 825"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          preserveAspectRatio="xMidYMid slice"
        >
          <mask id="mask0_cta" style={{ maskType: "alpha" }} maskUnits="userSpaceOnUse" x="269" y="27" width="850" height="493">
            <rect x="269.215" y="27.4062" width="849.57" height="492.311" fill="url(#paint0_linear_cta)" />
          </mask>
          <g mask="url(#mask0_cta)">
            <g filter="url(#filter0_f_cta)">
              <ellipse cx="694" cy="-93.0414" rx="670.109" ry="354.908" fill="url(#paint1_radial_cta)" fillOpacity="0.8" />
            </g>
            <ellipse cx="694" cy="-91.5385" rx="670.109" ry="354.908" fill="url(#paint2_linear_cta)" />
            <ellipse cx="694" cy="-93.0414" rx="670.109" ry="354.908" fill="url(#paint3_linear_cta)" />
          </g>
          <defs>
            <filter id="filter0_f_cta" x="-234.109" y="-705.949" width="1856.22" height="1225.82" filterUnits="userSpaceOnUse" colorInterpolationFilters="sRGB">
              <feFlood floodOpacity="0" result="BackgroundImageFix" />
              <feBlend mode="normal" in="SourceGraphic" in2="BackgroundImageFix" result="shape" />
              <feGaussianBlur stdDeviation="129" result="effect1_foregroundBlur_cta" />
            </filter>
            <linearGradient id="paint0_linear_cta" x1="1118.79" y1="273.562" x2="269.215" y2="273.562" gradientUnits="userSpaceOnUse">
              <stop stopColor="oklch(0.1 0 0)" stopOpacity="0" />
              <stop offset="0.2" stopColor="oklch(0.1 0 0)" stopOpacity="0.8" />
              <stop offset="0.8" stopColor="oklch(0.1 0 0)" stopOpacity="0.8" />
              <stop offset="1" stopColor="oklch(0.1 0 0)" stopOpacity="0" />
            </linearGradient>
            <radialGradient id="paint1_radial_cta" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(683.482 245.884) rotate(-3.78676) scale(469.009 248.4)">
              <stop offset="0.1294" stopColor="oklch(0.08 0 0)" />
              <stop offset="0.2347" stopColor="oklch(0.15 0 0)" />
              <stop offset="0.3" stopColor="oklch(0.15 0 0)" stopOpacity="0" />
            </radialGradient>
            <linearGradient id="paint2_linear_cta" x1="694" y1="-446.446" x2="694" y2="263.369" gradientUnits="userSpaceOnUse">
              <stop stopColor="white" stopOpacity="0" />
              <stop offset="1" stopColor="white" stopOpacity="0.1" />
            </linearGradient>
            <linearGradient id="paint3_linear_cta" x1="694" y1="-447.949" x2="694" y2="261.866" gradientUnits="userSpaceOnUse">
              <stop stopColor="oklch(0.1 0 0)" />
              <stop offset="1" stopColor="oklch(0.1 0 0)" />
            </linearGradient>
          </defs>
        </svg>
      </div>
      <div className="relative z-10 flex flex-col justify-start items-center gap-9 max-w-4xl mx-auto">
        <div className="flex flex-col justify-start items-center gap-4 text-center">
          <h2 className="text-foreground text-4xl md:text-5xl lg:text-[68px] font-semibold leading-tight md:leading-tight lg:leading-[76px] break-words max-w-[435px]">
            Code review made effortless
          </h2>
          <p className="text-muted-foreground text-sm md:text-base font-medium leading-[18.20px] md:leading-relaxed break-words max-w-2xl">
            Five AI agents. Every pull request. Inline fixes that pass CI. Free plan, no credit card, 2-click GitHub install.
          </p>
        </div>
        <Link href={`${API_URL}/api/v1/auth/github/login`}>
          <button className="px-[30px] py-2 bg-secondary text-secondary-foreground text-base font-medium leading-6 rounded-[99px] shadow-[0px_0px_0px_4px_rgba(255,255,255,0.13)] hover:bg-secondary/90 transition-all duration-200">
            Get started free
          </button>
        </Link>
      </div>
    </section>
  )
}
