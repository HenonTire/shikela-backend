#!/bin/bash
set -e

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"

if [ -n "${DATABASE_URL:-}" ]; then
  parsed_host="$(python - <<'PY'
import os
from urllib.parse import urlparse

url = os.environ.get("DATABASE_URL", "")
if url:
    print(urlparse(url).hostname or "")
PY
)"
  if [ -n "$parsed_host" ]; then
    DB_HOST="$parsed_host"
  fi
fi

echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
until nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 1
done
echo "PostgreSQL is ready"

exec "$@"
