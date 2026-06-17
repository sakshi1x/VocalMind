#!/usr/bin/env bash
# run_api_with_workers.sh — starts pipeline workers and API gateway together
# Usage: bash scripts/run_api_with_workers.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

export RABBIT_URL="${RABBIT_URL:-amqp://sentiment:password@localhost:5672/}"
export PORT="${PORT:-8000}"

# Start workers in the background (writes logs to logs/*.log)
bash "$ROOT/scripts/run_workers.sh"

echo ""
echo "Starting API Gateway on http://127.0.0.1:$PORT"
echo "Press Ctrl+C to stop API Gateway (workers will keep running)."

cd "$ROOT"
exec "$ROOT/.venv/bin/uvicorn" app.main:app --app-dir services/api-gateway --reload --port "$PORT"
