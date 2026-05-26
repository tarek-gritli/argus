import { Hero } from "./../_components/hero"
import { SocialProofBar } from "./../_components/social-proof-bar"
import { FeaturesGrid } from "./../_components/features-grid"
import { HowItWorks } from "./../_components/how-it-works"
import { PricingSection } from "./../_components/pricing-section"
import { Testimonials } from "./../_components/testimonials"
import { CtaBanner } from "./../_components/cta-banner"

export default function HomePage() {
  return (
    <>
      <Hero />
      <SocialProofBar />
      <FeaturesGrid />
      <HowItWorks />
      <PricingSection />
      <Testimonials />
      <CtaBanner />
    </>
  )
}
