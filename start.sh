#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

python "$ROOT_DIR/api/server.py" &
BACK_PID=$!

python -m http.server 5173 --directory "$ROOT_DIR/frontend/web" &
FRONT_PID=$!

cleanup() {
  kill "$BACK_PID" "$FRONT_PID" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

wait "$BACK_PID" "$FRONT_PID"
