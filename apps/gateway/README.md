# Argus Gateway

FastAPI API gateway for handling GitHub/GitLab webhooks, authentication, and rate limiting.

## Endpoints

- `POST /webhooks/github` - GitHub PR webhook receiver
- `POST /webhooks/gitlab` - GitLab MR webhook receiver
- `GET /health` - Health check endpoint
- `GET /reviews/{id}` - Get review status

## Configuration

```bash
# Environment variables
GITHUB_APP_ID=...
GITHUB_PRIVATE_KEY=...
GITHUB_WEBHOOK_SECRET=...
DATABASE_URL=...
CELERY_BROKER_URL=...
```

## Webhook Events

- `pull_request.opened` - New PR created
- `pull_request.synchronize` - New commits pushed
- `pull_request.ready_for_review` - PR marked ready

## Rate Limiting

Per-user/per-repo rate limits enforced via Redis-based sliding window.