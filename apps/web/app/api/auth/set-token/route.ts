import { NextRequest, NextResponse } from "next/server"

const GATEWAY = process.env.GATEWAY_URL ?? "http://localhost:8000"

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null)
  const token = body?.token
  if (!token || typeof token !== "string") {
    return NextResponse.json({ error: "missing token" }, { status: 400 })
  }

  // Validate token against the gateway before trusting it
  const check = await fetch(`${GATEWAY}/api/v1/reviews/?page=1&per_page=1`, {
    headers: { Authorization: `Bearer ${token}` },
  }).catch(() => null)
  if (!check?.ok) {
    return NextResponse.json({ error: "invalid token" }, { status: 401 })
  }

  const isProd = process.env.NODE_ENV === "production"
  const response = NextResponse.json({ ok: true })

  // httpOnly: token is never accessible to JS, preventing XSS exfiltration
  response.cookies.set("argus_token", token, {
    path: "/",
    sameSite: "lax",
    httpOnly: true,
    secure: isProd,
  })
  // Non-httpOnly flag lets the client-side auth guard know the user is logged in
  // without exposing the actual bearer token to JavaScript
  response.cookies.set("argus_authed", "1", {
    path: "/",
    sameSite: "lax",
    httpOnly: false,
    secure: isProd,
  })
  return response
}

export async function DELETE() {
  const response = NextResponse.json({ ok: true })
  response.cookies.set("argus_token", "", { path: "/", maxAge: 0 })
  response.cookies.set("argus_authed", "", { path: "/", maxAge: 0 })
  return response
}
