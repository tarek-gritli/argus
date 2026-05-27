import { NextRequest, NextResponse } from "next/server"

const PUBLIC_PATHS = ["/login", "/auth/callback", "/home"]

export function proxy(req: NextRequest) {
  return NextResponse.next();
  const token = req.cookies.get("argus_token")?.value
  const { pathname } = req.nextUrl

  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) {
    if (token && pathname === "/login") {
      return NextResponse.redirect(new URL("/dashboard", req.url))
    }
    return NextResponse.next()
  }

  if (!token) {
    return NextResponse.redirect(new URL("/login", req.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|public).*)"],
}
