import { useSyncExternalStore } from "react"

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

/**
 * False only when we positively know the user is a plain member. Sessions that predate the
 * role cookie keep their controls (the gateway rejects anything they aren't allowed to do).
 * Hydration-safe: the server render and first client render both say true.
 */
export function useCanManageOrg(): boolean {
  return useSyncExternalStore(
    () => () => {},
    () => readCookie("argus_role") !== "member",
    () => true,
  )
}
