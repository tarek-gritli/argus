import { NextRequest, NextResponse } from "next/server"

const GATEWAY = process.env.GATEWAY_URL ?? "http://localhost:8000"
const APP_ORIGIN = process.env.FRONTEND_URL ?? "http://localhost:3000"

function decodeJwtPayload(token: string): Record<string, unknown> {
  const part = token.split(".")[1]
  return JSON.parse(Buffer.from(part, "base64url").toString("utf-8"))
}

function isSameOrigin(request: NextRequest): boolean {
  const origin = request.headers.get("origin") ?? ""
  const referer = request.headers.get("referer") ?? ""
  if (origin && origin !== APP_ORIGIN) return false
  if (!origin && referer && !referer.startsWith(APP_ORIGIN + "/")) return false
  return true
}

function isSecFetchSameOrigin(request: NextRequest): boolean {
  const site = request.headers.get("sec-fetch-site") ?? ""
  return site === "" || site === "same-origin"
}

export async function POST(request: NextRequest) {
  // CSRF: reject cross-origin requests — cookies must only be set from our own frontend
  if (!isSameOrigin(request) || !isSecFetchSameOrigin(request)) {
    return NextResponse.json({ error: "forbidden" }, { status: 403 })
  }

  const body = await request.json().catch(() => null)
  const token = body?.token
  const nonce = body?.nonce
  if (!token || typeof token !== "string") {
    return NextResponse.json({ error: "missing token" }, { status: 400 })
  }
  if (!nonce || typeof nonce !== "string") {
    return NextResponse.json({ error: "missing nonce" }, { status: 400 })
  }

  // One-time nonce validation — proves the user came through our OAuth flow
  const nonceCheck = await fetch(`${GATEWAY}/api/v1/auth/validate-nonce`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, nonce }),
  }).catch(() => null)
  if (!nonceCheck?.ok) {
    return NextResponse.json({ error: "invalid nonce" }, { status: 403 })
  }

  // Double-check token validity against the gateway
  const check = await fetch(`${GATEWAY}/api/v1/reviews?page=1&per_page=1`, {
    headers: { Authorization: `Bearer ${token}` },
  }).catch(() => null)
  if (!check?.ok) {
    return NextResponse.json({ error: "invalid token" }, { status: 401 })
  }

  const payload = decodeJwtPayload(token)
  const orgId = typeof payload.oid === "string" ? payload.oid : ""

  const isProd = process.env.NODE_ENV === "production"
  const response = NextResponse.json({ ok: true })

  // httpOnly: token is never accessible to JS, preventing XSS exfiltration
  response.cookies.set("argus_token", token, {
    path: "/",
    sameSite: "lax",
    httpOnly: true,
    secure: isProd,
  })
  // Non-httpOnly cookies let client-side code know login state and org context
  // without exposing the actual bearer token to JavaScript
  response.cookies.set("argus_authed", "1", {
    path: "/",
    sameSite: "lax",
    httpOnly: false,
    secure: isProd,
  })
  response.cookies.set("argus_org_id", orgId, {
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
  response.cookies.set("argus_org_id", "", { path: "/", maxAge: 0 })
  return response
}
