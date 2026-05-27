// argus_token is httpOnly — not accessible to JS
// argus_authed=1 and argus_org_id are non-sensitive flags set alongside it
function readCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1]
}

export function isAuthenticated(): boolean {
  return readCookie("argus_authed") === "1"
}

export function getOrgId(): string | undefined {
  return readCookie("argus_org_id")
}
