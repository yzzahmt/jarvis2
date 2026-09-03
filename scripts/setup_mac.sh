#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${JARVIS_VENV_DIR:-$HOME/.jarvis/venv}"

echo "== Jarvis macOS setup =="

if ! xcode-select -p > /dev/null 2>&1; then
  echo "[setup] Xcode Command Line Tools not found — installing (a system dialog may appear)..."
  xcode-select --install
  echo "Re-run this script once the Command Line Tools install finishes."
  exit 1
fi

if ! command -v brew > /dev/null 2>&1; then
  echo "[setup] Homebrew is required: https://brew.sh"
  exit 1
fi

echo "[setup] installing system dependencies via Homebrew..."
brew install python@3.11 ffmpeg ollama portaudio

echo "[setup] starting ollama and pulling the default model (qwen2.5:7b-instruct, ~4.7GB)..."
if ! pgrep -f "ollama serve" > /dev/null; then
  nohup ollama serve > /tmp/ollama.log 2>&1 &
  disown
  sleep 2
fi
ollama pull qwen2.5:7b-instruct

# NOTE: the venv deliberately lives outside ~/Documents. macOS silently denies
# Homebrew Python (an unsigned/ad-hoc-signed binary) permission to create files
# under ~/Documents in headless/non-GUI contexts (no TCC prompt can be shown),
# even though plain shell tools like `cp`/`mkdir` work fine there.
echo "[setup] creating Python 3.11 venv at $VENV_DIR ..."
mkdir -p "$(dirname "$VENV_DIR")"
/opt/homebrew/bin/python3.11 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q

echo "[setup] installing backend package..."
pip install -e "$ROOT_DIR/backend"

echo "[setup] downloading openWakeWord models (includes 'hey_jarvis')..."
python -c "from openwakeword.utils import download_models; download_models()"

echo "[setup] downloading the default Piper voice..."
python -c "from jarvis.tts.voices import ensure_voice; ensure_voice('en_US-lessac-medium')"

echo "[setup] pre-downloading the mlx-whisper STT model (large-v3-turbo, ~1.6GB) so first use isn't slow..."
python -c "
import numpy as np
from jarvis.stt.mlx_whisper_engine import MlxWhisperEngine
MlxWhisperEngine('large-v3-turbo').transcribe(np.zeros(16000, dtype=np.int16))
"

echo "[setup] installing frontend dependencies..."
npm install --prefix "$ROOT_DIR/frontend"

echo "[setup] installing root dev dependencies..."
npm install --prefix "$ROOT_DIR"

echo ""
echo "== Setup complete =="
echo "Run 'npm run dev' from $ROOT_DIR to start Jarvis."
