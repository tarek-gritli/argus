"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"

export default function AuthCallbackPage() {
  const router = useRouter()
  useEffect(() => {
    // Token + nonce are in the URL fragment (#token=...&nonce=...) — never sent to servers or logged
    const params = new URLSearchParams(window.location.hash.slice(1))
    const token = params.get("token")
    const nonce = params.get("nonce")
    // Strip from URL immediately so it doesn't persist in browser history
    history.replaceState(null, "", window.location.pathname)
    if (!token || !nonce) {
      router.replace("/login")
      return
    }
    fetch("/api/auth/set-token", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, nonce }),
    }).then((res) => {
      if (res.ok) router.replace("/dashboard")
      else router.replace("/login")
    })
  }, [router])
  return (
    <div className="min-h-screen flex items-center justify-center">
      <p className="text-muted-foreground">Signing you in…</p>
    </div>
  )
}
