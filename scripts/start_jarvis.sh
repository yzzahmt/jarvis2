#!/usr/bin/env bash
set -euo pipefail

# Apps launched by double-clicking in Finder (unlike a Terminal shell) get a
# minimal PATH that's missing Homebrew's bin dirs — without this, npm/node/
# ollama silently "command not found" and the whole launch fails invisibly.
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="/tmp/jarvis_dev.log"

# Clean slate: kill any previous Jarvis backend/frontend instance so relaunching
# never hits "address already in use" or leaves a duplicate audio-capture stream.
pkill -f "uvicorn jarvis.main" 2>/dev/null || true
pkill -f "electron-vite" 2>/dev/null || true
pkill -f "$ROOT_DIR/frontend/node_modules/electron/dist/Electron.app" 2>/dev/null || true
sleep 1

cd "$ROOT_DIR"
nohup npm run dev > "$LOG_FILE" 2>&1 &
disown
