export const BASE = process.env.NEXT_PUBLIC_API_URL ?? ""

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new ApiError(res.status, text)
  }
  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return undefined as T
  }
  return res.json() as Promise<T>
}

export const api = {
  reviews: {
    list: (page = 1, perPage = 20) =>
      request<unknown[]>(`/api/v1/reviews/?page=${page}&per_page=${perPage}`),
    get: (id: string) => request<unknown>(`/api/v1/reviews/${id}`),
    findings: (id: string, params?: { severity?: string; agent?: string }) => {
      const qs = new URLSearchParams()
      if (params?.severity) qs.set("severity", params.severity)
      if (params?.agent) qs.set("agent", params.agent)
      return request<unknown[]>(`/api/v1/reviews/${id}/findings?${qs}`)
    },
    acceptFinding: (reviewId: string, findingId: string) =>
      request(`/api/v1/reviews/${reviewId}/findings/${findingId}/accept`, { method: "POST" }),
    rejectFinding: (reviewId: string, findingId: string) =>
      request(`/api/v1/reviews/${reviewId}/findings/${findingId}/reject`, { method: "POST" }),
  },
  billing: {
    get: () => request<unknown>(`/api/v1/billing/`),
    checkout: (plan: "pro" | "team", seats: number) =>
      request<{ checkout_url: string }>(`/api/v1/billing/checkout`, {
        method: "POST",
        body: JSON.stringify({ plan, seats }),
      }),
    portal: () =>
      request<{ portal_url: string }>(`/api/v1/billing/portal`, { method: "POST" }),
  },
  integrations: {
    list: (orgId: string) =>
      request<unknown[]>(`/api/v1/orgs/${orgId}/integrations`),
    toggle: (orgId: string, integrationId: string, enabled: boolean) =>
      request(`/api/v1/orgs/${orgId}/integrations/${integrationId}`, {
        method: "PATCH",
        body: JSON.stringify({ enabled }),
      }),
    remove: (orgId: string, integrationId: string) =>
      request(`/api/v1/orgs/${orgId}/integrations/${integrationId}`, { method: "DELETE" }),
    notionDatabases: (orgId: string, integrationId: string) =>
      request<{ id: string; title: string }[]>(
        `/api/v1/orgs/${orgId}/integrations/${integrationId}/notion/databases`
      ),
    selectNotionDatabase: (orgId: string, integrationId: string, databaseId: string) =>
      request(`/api/v1/orgs/${orgId}/integrations/${integrationId}/notion/database`, {
        method: "PATCH",
        body: JSON.stringify({ database_id: databaseId }),
      }),
    connectUrl: (kind: string, orgId: string) =>
      `${BASE}/api/v1/oauth/${kind}/authorize?org_id=${orgId}`,
  },
  auth: {
    logout: () => request("/api/v1/auth/logout", { method: "DELETE" }),
    loginUrl: () => `${BASE}/api/v1/auth/github/login`,
  },
}

export { ApiError }
