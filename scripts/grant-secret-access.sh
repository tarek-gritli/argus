#!/usr/bin/env bash

set -euo pipefail

PROJECT_ID=$(gcloud config get-value project)

GATEWAY_SECRETS=(
  github-webhook-secret
  github-app-id
  github-private-key-b64
  github-client-id
  github-client-secret
  jwt-secret-key
  secret-encryption-key
  stripe-secret-key
  stripe-webhook-secret
  stripe-pro-price-id
  stripe-team-price-id
  database-url
  redis-url
  celery-broker-url
)

AGENTS_SECRETS=(
  anthropic-api-key
  voyage-api-key
  github-private-key-b64
  github-app-id
  secret-encryption-key
  database-url
  redis-url
  celery-broker-url
  qdrant-url
  qdrant-api-key
)

grant() {
  local secret="$1" sa="$2"
  gcloud secrets add-iam-policy-binding "$secret" \
    --member="serviceAccount:${sa}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" >/dev/null
  echo "granted $secret -> $sa"
}

for s in "${GATEWAY_SECRETS[@]}"; do grant "$s" argus-gateway; done
for s in "${AGENTS_SECRETS[@]}"; do grant "$s" argus-agents; done
