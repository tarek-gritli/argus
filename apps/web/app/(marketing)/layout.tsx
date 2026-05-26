import { Nav } from "./_components/nav"
import { Footer } from "./_components/footer"

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-[#09090b] text-white">
      <Nav />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  )
}
