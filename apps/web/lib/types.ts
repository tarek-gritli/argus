import { z } from "zod"

export const SeveritySchema = z.enum(["critical", "high", "medium", "low", "info"])
export const AgentSchema = z.enum(["security", "quality", "testing", "documentation", "ticket_compliance"])

export const FindingSchema = z.object({
  id: z.string(),
  agent: AgentSchema,
  severity: SeveritySchema,
  file: z.string(),
  line_start: z.number(),
  line_end: z.number(),
  title: z.string(),
  description: z.string(),
  suggestion: z.string().nullable(),
  confidence: z.number(),
  is_accepted: z.boolean().nullable(),
})

export const ReviewSchema = z.object({
  id: z.string(),
  pr_number: z.number(),
  head_sha: z.string(),
  status: z.string(),
  created_at: z.string(),
  completed_at: z.string().nullable(),
})

export const ReviewDetailSchema = ReviewSchema.extend({
  findings: z.array(FindingSchema),
})

export const BillingSchema = z.object({
  plan: z.enum(["free", "pro", "team", "enterprise"]),
  seat_count: z.number(),
  reviews_used_this_month: z.number(),
  monthly_limit: z.number(),
  has_stripe_customer: z.boolean(),
})

export const InvoiceSchema = z.object({
  id: z.string(),
  number: z.string(),
  amount_paid: z.number(),
  created: z.number(),
  invoice_pdf: z.string().nullable(),
  status: z.string(),
})

export const MemberSchema = z.object({
  user_id: z.string(),
  github_login: z.string(),
  avatar_url: z.string().nullable(),
  role: z.string(),
  joined_at: z.string(),
})

export const PendingInviteSchema = z.object({
  id: z.string(),
  email: z.string(),
  role: z.string(),
  invited_by_login: z.string(),
  expires_at: z.string(),
  created_at: z.string(),
})

export const IntegrationSchema = z.object({
  id: z.string(),
  kind: z.string(),
  enabled: z.boolean(),
  ready: z.boolean(),
  config: z.record(z.string(), z.unknown()),
  webhook_url: z.string().optional(),
  created_at: z.string(),
  updated_at: z.string(),
})

export type Severity = z.infer<typeof SeveritySchema>
export type Agent = z.infer<typeof AgentSchema>
export type Finding = z.infer<typeof FindingSchema>
export type Review = z.infer<typeof ReviewSchema>
export type ReviewDetail = z.infer<typeof ReviewDetailSchema>
export type Billing = z.infer<typeof BillingSchema>
export type Invoice = z.infer<typeof InvoiceSchema>
export type Member = z.infer<typeof MemberSchema>
export type PendingInvite = z.infer<typeof PendingInviteSchema>
export type Integration = z.infer<typeof IntegrationSchema>

export type GitlabWebhookDetails = { webhook_url: string; webhook_secret: string }
