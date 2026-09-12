# Deployment

Argus deployed to GCP

- [`architecture.md`](architecture.md) — what was built: compute, data,
  security, governance, and how it's verified to actually work
- [`../../SECURITY.md`](../../SECURITY.md) — vulnerability disclosure policy

## At a glance

- **Compute:** Cloud Run Service (gateway) + Cloud Run Worker Pool (agents) —
  all-serverless, scales to zero
- **Data:** Neon (Postgres), Qdrant Cloud (vectors), Redis Cloud (broker/cache)
  — managed free tiers, not self-hosted
- **Security:** Secret Manager, per-service least-privilege IAM, keyless
  CI/CD via Workload Identity Federation, Artifact Registry vuln scanning + SBOM
- **CI/CD:** GitHub Actions → Artifact Registry → Cloud Run
  ([`.github/workflows/deploy.yml`](../../.github/workflows/deploy.yml))
