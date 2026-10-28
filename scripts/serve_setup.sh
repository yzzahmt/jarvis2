#!/usr/bin/env bash
# Linux makinelerine kurulum dosyalarını yerel ağda geçici olarak sunar. Kurulum bitince Ctrl+C.
# Kullanım (Mac): scripts/serve_setup.sh
set -e
cd "$(dirname "$0")/.."
IP=$(ipconfig getifaddr en0 || ipconfig getifaddr en1)
mkdir -p data/serve
cp scripts/linux_agent_setup.sh data/serve/setup.sh
cp jarvis/automation/browser.py data/serve/browser.py
echo "Mac IP: $IP — Linux'ta (Zorin için) şunu çalıştır:"
echo
echo "  curl -fsS http://$IP:8799/setup.sh -o /tmp/setup.sh && MAC_IP=$IP bash /tmp/setup.sh zorin"
echo
echo "(Mint için sondaki 'zorin' yerine 'mint'.) Bitince burada Ctrl+C."
exec python3 -m http.server 8799 --bind "$IP" --directory data/serve
