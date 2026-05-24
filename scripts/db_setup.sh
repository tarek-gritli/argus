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
# Strip driver prefix so pg_isready and psql can use it
PSQL_URL="${DB_URL/postgresql+asyncpg/postgresql}"

# Extract host and port from URL (e.g. postgresql://user:pass@host:port/db)
DB_HOST="$(echo "$PSQL_URL" | sed -E 's|.*@([^:/]+).*|\1|')"
DB_PORT="$(echo "$PSQL_URL" | sed -E 's|.*:([0-9]+)/.*|\1|')"
DB_PORT="${DB_PORT:-5432}"

export DATABASE_URL="$DB_URL"

echo "==> Checking PostgreSQL is reachable at ${DB_HOST}:${DB_PORT}..."
for i in $(seq 1 20); do
  if pg_isready -h "$DB_HOST" -p "$DB_PORT" -q 2>/dev/null; then
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
