// argus_token is httpOnly — not accessible to JS
// argus_authed=1 is a non-sensitive flag set alongside it to indicate login state
export function isAuthenticated(): boolean {
  if (typeof document === "undefined") return false
  return document.cookie.split("; ").some((row) => row.startsWith("argus_authed=1"))
}
