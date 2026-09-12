#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "$0")/.."
ENV_FILE="${1:-.env.prod}"
set -a
source "$ENV_FILE"
set +a

declare -A SECRETS=(
  [github-webhook-secret]="${GITHUB_WEBHOOK_SECRET:-}"
  [github-app-id]="${GITHUB_APP_ID:-}"
  [github-private-key-b64]="${GITHUB_PRIVATE_KEY_B64:-}"
  [github-client-id]="${GITHUB_CLIENT_ID:-}"
  [github-client-secret]="${GITHUB_CLIENT_SECRET:-}"
  [jwt-secret-key]="${JWT_SECRET_KEY:-}"
  [secret-encryption-key]="${SECRET_ENCRYPTION_KEY:-}"
  [stripe-secret-key]="${STRIPE_SECRET_KEY:-}"
  [stripe-webhook-secret]="${STRIPE_WEBHOOK_SECRET:-}"
  [stripe-pro-price-id]="${STRIPE_PRO_PRICE_ID:-}"
  [stripe-team-price-id]="${STRIPE_TEAM_PRICE_ID:-}"
  [anthropic-api-key]="${ANTHROPIC_API_KEY:-}"
  [voyage-api-key]="${VOYAGE_API_KEY:-}"
  [database-url]="${DATABASE_URL:-}"
  [redis-url]="${REDIS_URL:-}"
  [celery-broker-url]="${CELERY_BROKER_URL:-}"
  [qdrant-url]="${QDRANT_URL:-}"
  [qdrant-api-key]="${QDRANT_API_KEY:-}"
)

for name in "${!SECRETS[@]}"; do
  value="${SECRETS[$name]}"
  if [ -z "$value" ]; then
    echo "skip   $name (empty/missing in $ENV_FILE)"
    continue
  fi
  if gcloud secrets describe "$name" >/dev/null 2>&1; then
    printf '%s' "$value" | gcloud secrets versions add "$name" --data-file=-
    echo "update $name"
  else
    printf '%s' "$value" | gcloud secrets create "$name" --data-file=-
    echo "create $name"
  fi
done
