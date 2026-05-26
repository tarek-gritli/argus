export function getToken(): string | undefined {
  if (typeof document === "undefined") return undefined
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith("argus_token="))
    ?.split("=")[1]
}

export function isAuthenticated(): boolean {
  return !!getToken()
}
