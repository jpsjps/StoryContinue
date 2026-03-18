#!/usr/bin/env bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi

if [ -f "requirements.txt" ]; then
  echo "Installing Python dependencies (if needed)..."
  $PY -m pip install -r requirements.txt
fi

export PYTHONPATH="$ROOT_DIR:$PYTHONPATH"

BACKEND_PORT=${BACKEND_PORT:-8000}

echo "Starting backend (with built-in static frontend) on http://127.0.0.1:${BACKEND_PORT} ..."
uvicorn backend.main:app --reload --host 127.0.0.1 --port "${BACKEND_PORT}" &
BACKEND_PID=$!

echo "Backend PID: ${BACKEND_PID}"
echo
echo "Open browser at: http://127.0.0.1:${BACKEND_PORT}"
echo "Press Ctrl+C to stop the service."

trap 'echo "Stopping..."; kill ${BACKEND_PID} 2>/dev/null || true; exit 0' INT TERM

wait

