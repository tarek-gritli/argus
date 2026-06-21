export function FooterSection() {
  return (
    <footer className="w-full max-w-[1320px] mx-auto px-5 flex flex-col md:flex-row justify-between items-start gap-8 md:gap-0 py-10 md:py-[70px]">
      <div className="flex flex-col justify-start items-start gap-8 p-4 md:p-8">
        <div className="flex gap-3 items-center">
          <div className="text-center text-foreground text-xl font-semibold leading-4">Argus</div>
        </div>
        <p className="text-foreground/90 text-sm font-medium leading-[18px] text-left">Code review made effortless</p>
        <div className="flex justify-start items-start gap-3">
          <a href="#" aria-label="X / Twitter" className="text-muted-foreground hover:text-foreground transition-colors text-sm">𝕏</a>
          <a href="https://github.com" aria-label="GitHub" className="text-muted-foreground hover:text-foreground transition-colors text-sm">GH</a>
          <a href="#" aria-label="LinkedIn" className="text-muted-foreground hover:text-foreground transition-colors text-sm">in</a>
        </div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-8 md:gap-12 p-4 md:p-8 w-full md:w-auto">
        <div className="flex flex-col justify-start items-start gap-3">
          <h3 className="text-muted-foreground text-sm font-medium leading-5">Product</h3>
          <div className="flex flex-col justify-end items-start gap-2">
            <a href="#features-section" className="text-foreground text-sm font-normal leading-5 hover:underline">Features</a>
            <a href="#pricing-section" className="text-foreground text-sm font-normal leading-5 hover:underline">Pricing</a>
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">Integrations</a>
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">Fix Engine</a>
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">Multi-Agent Review</a>
          </div>
        </div>
        <div className="flex flex-col justify-start items-start gap-3">
          <h3 className="text-muted-foreground text-sm font-medium leading-5">Company</h3>
          <div className="flex flex-col justify-center items-start gap-2">
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">About us</a>
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">Our team</a>
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">Careers</a>
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">Brand</a>
            <a href="mailto:support@argus.dev" className="text-foreground text-sm font-normal leading-5 hover:underline">Contact</a>
          </div>
        </div>
        <div className="flex flex-col justify-start items-start gap-3">
          <h3 className="text-muted-foreground text-sm font-medium leading-5">Resources</h3>
          <div className="flex flex-col justify-center items-start gap-2">
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">Terms of use</a>
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">API Reference</a>
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">Documentation</a>
            <a href="#" className="text-foreground text-sm font-normal leading-5 hover:underline">Community</a>
            <a href="mailto:support@argus.dev" className="text-foreground text-sm font-normal leading-5 hover:underline">Support</a>
          </div>
        </div>
      </div>
    </footer>
  )
}
