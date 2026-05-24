#!/usr/bin/env bash
# Drops all tables by rolling back all migrations, then reapplies them from scratch.
# Use this to get a clean slate in local dev — does NOT touch Docker volumes.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Load .env if present
if [ -f "$ROOT/.env" ]; then
  set -a
  source "$ROOT/.env"
  set +a
fi

echo "WARNING: This will drop all tables and reapply migrations from scratch."
read -r -p "Continue? [y/N] " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 0
fi

echo "==> Checking PostgreSQL is reachable..."
for i in $(seq 1 20); do
  if pg_isready -h localhost -p 5432 -q 2>/dev/null; then
    break
  fi
  if [ "$i" -eq 20 ]; then
    echo "ERROR: PostgreSQL not reachable after 20 attempts. Is docker compose up running?"
    exit 1
  fi
  echo "    waiting... ($i/20)"
  sleep 1
done

cd "$ROOT"

echo "==> Rolling back all migrations..."
uv run alembic downgrade base

echo "==> Reapplying all migrations..."
uv run alembic upgrade head

echo "==> Done. Database purged and rebuilt."
