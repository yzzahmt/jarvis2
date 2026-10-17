# Jarvis: tüm önbellek ve modelleri HDD'de tut. Kullanım: source scripts/env.sh
export JARVIS_HOME="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
D="$JARVIS_HOME/data"
export OLLAMA_MODELS="$D/ollama" HF_HOME="$D/hf" PIP_CACHE_DIR="$D/pip-cache" \
  PLAYWRIGHT_BROWSERS_PATH="$D/playwright" XDG_CACHE_HOME="$D/cache" TMPDIR="$D/tmp" \
  OLLAMA_HOST="127.0.0.1:11434" OLLAMA_KEEP_ALIVE="30m" \
  PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"   # Finder/Dock ile açılınca Homebrew yolu yok
[ -d "$JARVIS_HOME/.venv" ] && . "$JARVIS_HOME/.venv/bin/activate"
