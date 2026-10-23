import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "./api"
import { ReviewSchema, ReviewDetailSchema, BillingSchema, InvoiceSchema, MemberSchema, PendingInviteSchema, IntegrationSchema } from "./types"
import { z } from "zod"

export const reviewKeys = {
  all: ["reviews"] as const,
  list: (page: number) => ["reviews", "list", page] as const,
  detail: (id: string) => ["reviews", id] as const,
}

export const reviewsListOptions = (page: number) =>
  queryOptions({
    queryKey: reviewKeys.list(page),
    queryFn: () =>
      api.reviews.list(page, 20).then((data) => z.array(ReviewSchema).parse(data)),
  })

export const reviewDetailOptions = (id: string) =>
  queryOptions({
    queryKey: reviewKeys.detail(id),
    queryFn: () => api.reviews.get(id).then((data) => ReviewDetailSchema.parse(data)),
    enabled: !!id,
  })

export const billingOptions = () =>
  queryOptions({
    queryKey: ["billing"],
    queryFn: () => api.billing.get().then((data) => BillingSchema.parse(data)),
  })

export const invoicesOptions = () =>
  queryOptions({
    queryKey: ["invoices"],
    queryFn: () => api.billing.invoices().then((data) => z.array(InvoiceSchema).parse(data)),
  })

export const membersOptions = (orgId: string) =>
  queryOptions({
    queryKey: ["members", orgId],
    queryFn: () => api.orgs.members(orgId).then((data) => z.array(MemberSchema).parse(data)),
    enabled: !!orgId,
  })

export const pendingInvitesOptions = (orgId: string) =>
  queryOptions({
    queryKey: ["pending-invites", orgId],
    queryFn: () => api.orgs.pendingInvites(orgId).then((data) => z.array(PendingInviteSchema).parse(data)),
    enabled: !!orgId,
  })

export function useCreateInvite(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (email: string) => api.orgs.createInvite(orgId, email),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pending-invites", orgId] }),
  })
}

export function useRevokeInvite(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (inviteId: string) => api.orgs.revokeInvite(orgId, inviteId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pending-invites", orgId] }),
  })
}

export const integrationsOptions = (orgId: string) =>
  queryOptions({
    queryKey: ["integrations", orgId],
    queryFn: () =>
      api.integrations.list(orgId).then((data) => z.array(IntegrationSchema).parse(data)),
    enabled: !!orgId,
  })

export function useAcceptFinding(reviewId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (findingId: string) => api.reviews.acceptFinding(reviewId, findingId),
    onSuccess: () => qc.invalidateQueries({ queryKey: reviewKeys.detail(reviewId) }),
  })
}

export function useRejectFinding(reviewId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (findingId: string) => api.reviews.rejectFinding(reviewId, findingId),
    onSuccess: () => qc.invalidateQueries({ queryKey: reviewKeys.detail(reviewId) }),
  })
}

export function useToggleIntegration(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api.integrations.toggle(orgId, id, enabled),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["integrations", orgId] }),
  })
}

export function useConnectGitlab(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { base_url: string; access_token: string; signing_token?: string }) =>
      api.integrations.connectGitlab(orgId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["integrations", orgId] }),
  })
}

export function useRotateGitlabSecret(orgId: string) {
  return useMutation({
    mutationFn: (integrationId: string) => api.integrations.rotateGitlabSecret(orgId, integrationId),
  })
}

export function useRemoveIntegration(orgId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.integrations.remove(orgId, id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["integrations", orgId] }),
  })
}

export const notionDatabasesOptions = (orgId: string, integrationId: string) =>
  queryOptions({
    queryKey: ["notion-databases", orgId, integrationId],
    queryFn: () => api.integrations.notionDatabases(orgId, integrationId),
    enabled: !!integrationId,
  })

export function useSelectNotionDatabase(orgId: string, integrationId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (databaseId: string) =>
      api.integrations.selectNotionDatabase(orgId, integrationId, databaseId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["integrations", orgId] }),
  })
}
