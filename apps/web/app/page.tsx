import { cookies } from "next/headers"
import { redirect } from "next/navigation"

export default async function RootPage() {
  const cookieStore = await cookies()
  if (cookieStore.get("argus_token")?.value) {
    redirect("/dashboard")
  }
  redirect("/home")
}
