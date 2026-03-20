#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
LOG_DIR="$BACKEND_DIR/.logs"
PID_FILE="$LOG_DIR/backend-services.pid"

mkdir -p "$LOG_DIR"

if [[ -f "$PID_FILE" ]]; then
  echo "Backend services appear to be running already."
  echo "PID file: $PID_FILE"
  echo "Remove it or stop existing processes before starting again."
  exit 1
fi

start_service() {
  local name="$1"
  shift

  (
    cd "$BACKEND_DIR"
    exec "$@"
  ) >"$LOG_DIR/$name.log" 2>&1 &

  local pid=$!
  echo "$name:$pid" >>"$PID_FILE"
  echo "Started $name (pid $pid) -> $LOG_DIR/$name.log"
}

echo "Starting Docker services..."
(cd "$ROOT_DIR" && docker compose up -d)

echo "Starting backend services..."
: >"$PID_FILE"

start_service api uv run uvicorn app.main:app --reload --port 8000
start_service worker-upload uv run celery -A app.celery_app:celery worker --loglevel=info --pool=solo -Q celery -n upload@%h
start_service worker-summaries uv run celery -A app.celery_app:celery worker --loglevel=info --pool=solo -Q summaries -n summaries@%h
start_service worker-entities uv run celery -A app.celery_app:celery worker --loglevel=info --pool=solo -Q entities -n entities@%h

cat <<EOF

Backend stack started.

Useful commands:
  tail -f $LOG_DIR/api.log
  tail -f $LOG_DIR/worker-upload.log
  tail -f $LOG_DIR/worker-summaries.log
  tail -f $LOG_DIR/worker-entities.log

To stop everything later:
  $ROOT_DIR/scripts/stop-backend.sh
EOF
