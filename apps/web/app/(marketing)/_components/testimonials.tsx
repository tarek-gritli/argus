"use client"

import { Swiper, SwiperSlide } from "swiper/react"
import { Autoplay, Pagination } from "swiper/modules"
import "swiper/css"
import "swiper/css/pagination"

const TESTIMONIALS = [
  {
    quote: "Argus catches things in 4 seconds that our senior engineers would miss in a 30-minute review. The security agent alone has saved us twice.",
    author: "Sofia M.",
    role: "Engineering Lead",
    company: "Acme Corp",
    initials: "SM",
  },
  {
    quote: "We merged two critical bugs last quarter that Argus would have flagged. The day we installed it, it caught three SQL injections in the first PR.",
    author: "Daniel K.",
    role: "CTO",
    company: "StartupXYZ",
    initials: "DK",
  },
  {
    quote: "The ticket compliance agent alone is worth the team plan. We were shipping code that had nothing to do with the Jira ticket constantly.",
    author: "Rachel T.",
    role: "Staff Engineer",
    company: "ScaleOrg",
    initials: "RT",
  },
  {
    quote: "Inline fix suggestions that actually pass CI. That's the thing no one else does. We commit them directly without editing.",
    author: "Marcus L.",
    role: "Principal Engineer",
    company: "DevCo",
    initials: "ML",
  },
]

export function Testimonials() {
  return (
    <section className="py-24 border-t border-white/[0.05] overflow-hidden">
      <div className="max-w-6xl mx-auto px-6">
        <div className="mb-16">
          <h2 className="text-4xl font-bold text-white mb-4 tracking-tight">Trusted by engineering teams</h2>
          <p className="text-zinc-500 text-lg">Real quotes from developers who ship with Argus.</p>
        </div>
        <Swiper
          modules={[Autoplay, Pagination]}
          spaceBetween={20}
          slidesPerView={1}
          breakpoints={{ 768: { slidesPerView: 2 }, 1024: { slidesPerView: 3 } }}
          autoplay={{ delay: 4500, disableOnInteraction: false }}
          pagination={{ clickable: true }}
          loop
          className="pb-10"
        >
          {TESTIMONIALS.map((t) => (
            <SwiperSlide key={t.author}>
              <div className="rounded-xl border border-white/[0.07] bg-white/[0.02] p-6 h-full flex flex-col gap-5">
                <p className="text-zinc-400 text-[13px] leading-relaxed flex-1">&ldquo;{t.quote}&rdquo;</p>
                <div className="flex items-center gap-3 pt-3 border-t border-white/[0.05]">
                  <div className="w-8 h-8 rounded-full bg-white/[0.06] border border-white/[0.08] flex items-center justify-center text-[11px] font-semibold text-zinc-400 shrink-0">
                    {t.initials}
                  </div>
                  <div>
                    <p className="text-[12px] font-semibold text-white">{t.author}</p>
                    <p className="text-[11px] text-zinc-600">{t.role} · {t.company}</p>
                  </div>
                </div>
              </div>
            </SwiperSlide>
          ))}
        </Swiper>
      </div>
    </section>
  )
}
