# Argus Gateway

FastAPI API gateway. Receives external HTTP requests, validates them, enqueues work, returns 200. No business logic lives here.

## Active Endpoints

- `POST /api/v1/webhooks/github` — GitHub PR webhook receiver
- `GET /api/v1/auth/login` — GitHub OAuth redirect
- `GET /api/v1/auth/callback` — GitHub OAuth callback, issues JWT
- `GET /api/v1/reviews/` — List reviews for the authenticated org
- `GET /api/v1/reviews/{review_id}` — Get review detail + findings
- `POST /api/v1/admin/plan` — Update org plan (dev/testing only)

## Webhook Flow

1. Validate `X-Hub-Signature-256` HMAC-SHA256 — 403 if invalid
2. Filter: only `pull_request` events with action in `[opened, synchronize, reopened]`
3. Deduplicate on `X-GitHub-Delivery` header via Redis
4. Resolve org from `installation_id` (upsert `Org` + `Repo`)
5. Enqueue Celery task `review_pr` with `org_id` in payload
6. Return 200

## Configuration

```bash
GITHUB_APP_ID=
GITHUB_PRIVATE_KEY_B64=      # base64 of .pem
GITHUB_WEBHOOK_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
JWT_SECRET_KEY=
DATABASE_URL=postgresql+asyncpg://argus:argus@localhost:5432/argus
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
```

## Rate Limiting

Redis token-bucket per org, enforced in `middleware/rate_limit.py`.