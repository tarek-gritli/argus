# Architecture

## Scope

Deploy Argus (currently local-only) to GCP.

**Guiding constraint:** traffic is genuinely unpredictable — zero for long
stretches, occasional real use. Every component below is chosen to cost ~$0 at
idle and to need no self-managed server or cluster. This is *the* reason the
shape is "all-serverless + managed free tiers" rather than a VM or GKE.

## Diagram

```
GitHub (webhook, OAuth)         Developer (CLI)
        |                              |
        v                              v
  +---------------------------------------+
  |     Cloud Run Service: gateway        |  <- only public-facing piece
  |     (FastAPI, scale 0..N, auto TLS)   |
  +---------------------------------------+
        |  enqueues via Redis Cloud
        v
  +---------------------------------------+
  |  Cloud Run Worker Pool: agents        |  <- no public ingress
  |  (Celery: security/quality/testing/   |
  |   fix engine, pull-based)             |
  +---------------------------------------+
        |            |            |
        v            v            v
     Neon      Qdrant Cloud   Redis Cloud
   (Postgres)   (vectors)   (broker+cache)
```

Both Cloud Run resources are built from [`apps/gateway/Dockerfile`](../../apps/gateway/Dockerfile)
and [`apps/agents/Dockerfile`](../../apps/agents/Dockerfile), and pull every
credential from Secret Manager at deploy time — nothing is baked into the
image or read from a mounted `.pem`/`.env` file at runtime.

## Compute — Cloud Run (Service + Worker Pool)

- **Gateway** → Cloud Run *Service*: request-driven, needs a public HTTPS
  endpoint for the GitHub webhook and the CLI's OAuth callback. The default
  `*.run.app` domain gives free automatic TLS.
- **Agents** → Cloud Run *Worker Pool* (GA April 2026): pull-based, no HTTP
  port, no load balancer, no public ingress. This is the piece that made "all
  Cloud Run" viable — before worker pools, a persistent Celery consumer had no
  clean serverless home and would have forced a GKE cluster or a VM just to
  run a background loop.
- Both scale toward zero when idle

## Data — external managed free tiers, not self-hosted

- **Neon** (Postgres) — source of truth: users, orgs, reviews, findings,
  billing.
- **Qdrant Cloud** (vector store) — same client library already in
  [`packages/context/context/embeddings.py`](../../packages/context/context/embeddings.py),
  zero code changes, just a different `QDRANT_URL`/API key. Rebuildable from
  source via the existing reindex task if ever lost.
- **Redis Cloud** (Celery broker + gateway rate-limiter/quota store).

None of these need private VPC networking from Cloud Run — they're reached
over the public internet with TLS + credential auth (`sslmode=require` /
`rediss://` / HTTPS+API key). That's also why there's no Compute Engine VM and
no Serverless VPC Access connector anywhere in this design: nothing in the
data layer needs private connectivity, and removing that layer removes real
complexity and attack surface, not just cost.

## Security layer

- **Secret Manager** holds every credential (GitHub App private key, webhook
  secret, JWT secret, Anthropic/Voyage API keys, Stripe keys, Neon/Redis
  Cloud/Qdrant Cloud connection strings). Replaces the current `.env` /
  `argus-private-key.pem` file model for the deployed environment. Cloud Run
  mounts secrets as env vars at revision start.
- **Two service accounts**, one per Cloud Run resource (`argus-gateway-sa`,
  `argus-agents-sa`), each granted `roles/secretmanager.secretAccessor` on
  only the specific secrets it uses — mirrors the real code split (only
  agents call Claude/Voyage; only gateway handles Stripe webhooks and OAuth).
- **Workload Identity Federation** for GitHub Actions → GCP
  ([`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml)):
  CI/CD authenticates via short-lived OIDC tokens, never a downloaded
  service-account JSON key.
- **Artifact Registry** for container images: enabling the Container Scanning
  API (one-time, per-project) turns on both automatic vulnerability scanning
  and SBOM generation for every image pushed — no CI step needed for either.
  On push, every OS package and Python dependency in the image is checked
  against a continuously-updated CVE database, and an SBOM (a generated
  inventory of every package and version in the image, in SPDX format) is
  produced as a side effect of the same scan.
- Dockerfiles: `python:3.12-slim`, multi-stage build, non-root runtime user,
  `uv` for dependency install per the project's tooling rules — a smaller
  image means a smaller attack surface and faster cold starts.
- [`SECURITY.md`](../../SECURITY.md): vulnerability disclosure contact +
  triage SLA.

## Governance / observability

- Cloud Logging — default from Cloud Run, no extra setup.
- A Cloud Monitoring uptime check on the gateway's existing `/ping` endpoint
  (no new health-check route needed).
- A GCP Billing budget alert at two or three thresholds (e.g. $50/$150/$250) to notify when spending approaches the limit.