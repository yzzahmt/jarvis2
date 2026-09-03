#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="${JARVIS_VENV_DIR:-$HOME/.jarvis/venv}"
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../backend" && pwd)"

source "$VENV_DIR/bin/activate"
cd "$BACKEND_DIR"

if ! pgrep -f "ollama serve" > /dev/null; then
  echo "[run_backend] starting ollama serve in the background..."
  nohup ollama serve > /tmp/ollama.log 2>&1 &
  disown
  sleep 2
fi

exec uvicorn jarvis.main:app --host 127.0.0.1 --port 8756
