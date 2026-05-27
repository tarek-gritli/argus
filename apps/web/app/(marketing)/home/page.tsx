import { Hero } from "./../_components/hero"
import { BentoSection } from "./../_components/bento-section"
import { LargeTestimonial } from "./../_components/large-testimonial"
import { PricingSection } from "./../_components/pricing-section"
import { TestimonialGridSection } from "./../_components/testimonial-grid-section"
import { FAQSection } from "./../_components/faq-section"
import { CTASection } from "./../_components/cta-section"
import { FooterSection } from "./../_components/footer-section"
import { AnimatedSection } from "./../_components/animated-section"

export default function HomePage() {
  return (
    <div className="min-h-screen bg-background relative overflow-hidden pb-0">
      <div className="relative z-10">
        <main className="max-w-[1320px] mx-auto relative">
          <Hero />
        </main>
        <AnimatedSection id="features-section" className="relative z-10 max-w-[1320px] mx-auto mt-16" delay={0.2}>
          <BentoSection />
        </AnimatedSection>
        <AnimatedSection className="relative z-10 max-w-[1320px] mx-auto mt-8 md:mt-16" delay={0.2}>
          <LargeTestimonial />
        </AnimatedSection>
        <AnimatedSection id="pricing-section" className="relative z-10 max-w-[1320px] mx-auto mt-8 md:mt-16" delay={0.2}>
          <PricingSection />
        </AnimatedSection>
        <AnimatedSection id="testimonials-section" className="relative z-10 max-w-[1320px] mx-auto mt-8 md:mt-16" delay={0.2}>
          <TestimonialGridSection />
        </AnimatedSection>
        <AnimatedSection id="faq-section" className="relative z-10 max-w-[1320px] mx-auto mt-8 md:mt-16" delay={0.2}>
          <FAQSection />
        </AnimatedSection>
        <AnimatedSection className="relative z-10 max-w-[1320px] mx-auto mt-8 md:mt-16" delay={0.2}>
          <CTASection />
        </AnimatedSection>
        <AnimatedSection className="relative z-10 max-w-[1320px] mx-auto mt-8 md:mt-16" delay={0.2}>
          <FooterSection />
        </AnimatedSection>
      </div>
    </div>
  )
}
