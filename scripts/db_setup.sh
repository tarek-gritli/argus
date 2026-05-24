#!/usr/bin/env bash
# Sets up the database: starts postgres if needed, applies all Alembic migrations.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Load .env if present
if [ -f "$ROOT/.env" ]; then
  set -a
  source "$ROOT/.env"
  set +a
fi

DB_URL="${DATABASE_URL:-postgresql+asyncpg://argus:argus@localhost:5432/argus}"
PSQL_URL="${DB_URL/postgresql+asyncpg/postgresql}"

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

echo "==> Applying Alembic migrations..."
cd "$ROOT"
uv run alembic upgrade head

echo "==> Done. Database is ready."
