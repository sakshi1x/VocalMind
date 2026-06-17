#!/usr/bin/env bash
set -euo pipefail

cd /app

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is not set; cannot run migrations."
  exit 1
fi

echo "Running Alembic migrations..."
python -m alembic upgrade head

echo "Migrations complete. Starting application..."
exec python main.py
