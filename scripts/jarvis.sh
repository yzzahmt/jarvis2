#!/usr/bin/env bash
# Jarvis başlatıcı. Kullanım: scripts/jarvis.sh [app|voice|text|serve|status]
source "$(dirname "$0")/env.sh"
if [ ! -d "$JARVIS_HOME/data" ]; then echo "HDD takılı değil veya Jarvis klasörü yok"; exit 1; fi
if ! curl -s -m 2 "http://$OLLAMA_HOST/api/tags" >/dev/null; then
  nohup ollama serve >> "$JARVIS_HOME/data/logs/ollama.log" 2>&1 &
  sleep 2
fi
cd "$JARVIS_HOME" && exec python -m jarvis "${1:-app}"
