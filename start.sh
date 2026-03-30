#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$ROOT_DIR/env/env.sh"

if [[ -f "$ENV_FILE" ]]; then
  set -a
  source "$ENV_FILE"
  set +a
fi

ENABLE_FEISHU=0
for arg in "$@"; do
  case "$arg" in
    --feishu|--enable-feishu)
      ENABLE_FEISHU=1
      ;;
  esac
done

python "$ROOT_DIR/api/server.py" &
BACK_PID=$!

python -m http.server 5173 --directory "$ROOT_DIR/frontend/web" &
FRONT_PID=$!

FEISHU_PID=""
if [[ "$ENABLE_FEISHU" -eq 1 ]]; then
  if [[ -n "${FEISHU_SESSION_PATH:-}" && -f "${FEISHU_SESSION_PATH}" ]]; then
    rm -f "${FEISHU_SESSION_PATH}"
  fi
  python -m channels.feishu_cli &
  FEISHU_PID=$!
fi

cleanup() {
  if [[ -n "${FEISHU_PID}" ]]; then
    kill "$FEISHU_PID" 2>/dev/null || true
  fi
  kill "$BACK_PID" "$FRONT_PID" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

if [[ -n "${FEISHU_PID}" ]]; then
  wait "$BACK_PID" "$FRONT_PID" "$FEISHU_PID"
else
  wait "$BACK_PID" "$FRONT_PID"
fi
