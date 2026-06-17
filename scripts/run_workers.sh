#!/usr/bin/env bash
# run_workers.sh — starts all pipeline worker services in the background
# Each service logs to logs/<service>.log
# Usage: bash scripts/run_workers.sh

set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export RABBIT_URL="${RABBIT_URL:-amqp://sentiment:password@rabbitmq:5672/}"
export HF_HUB_DISABLE_PROGRESS_BARS=1
export TRANSFORMERS_NO_PROGRESS_BAR=1
export HF_HUB_DISABLE_TELEMETRY=1
export TQDM_DISABLE=1
PYTHON_BIN="${PYTHON_BIN:-$ROOT/.venv/bin/python}"

SERVICES=(
  "audio-service"
  "asr-service"
  "language-service"
  "translation-service"
  "nlp-service"
  "urgency-service"
  "persistence-service"
)

mkdir -p "$ROOT/logs"

echo "Starting pipeline workers (RABBIT_URL=$RABBIT_URL)"
echo "Using Python: $PYTHON_BIN"
echo "Logs in: $ROOT/logs/"
echo ""

for svc in "${SERVICES[@]}"; do
  SVC_DIR="$ROOT/services/$svc"
  LOG_FILE="$ROOT/logs/$svc.log"

  echo "  ▶ $svc → $LOG_FILE"
  (
    cd "$SVC_DIR" &&
    nohup env PYTHONUNBUFFERED=1 PYTHONPATH="$SVC_DIR:$ROOT" RABBIT_URL="$RABBIT_URL" "$PYTHON_BIN" -u -m app.main \
      > "$LOG_FILE" 2>&1 < /dev/null &
  )
done

echo ""
echo "All workers started. Monitor logs with:"
echo "  tail -f $ROOT/logs/*.log"
echo ""
echo "To stop all workers:"
echo "  pkill -f '$PYTHON_BIN -m app.main'"
