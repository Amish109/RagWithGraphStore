#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
LOG_DIR="$BACKEND_DIR/.logs"
PID_FILE="$LOG_DIR/backend-services.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No PID file found at $PID_FILE"
  exit 1
fi

while IFS=":" read -r name pid; do
  if kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid"
    echo "Stopped $name (pid $pid)"
  else
    echo "$name (pid $pid) was not running"
  fi
done <"$PID_FILE"

rm -f "$PID_FILE"
echo "Stopping Docker services..."
(cd "$ROOT_DIR" && docker compose down)
