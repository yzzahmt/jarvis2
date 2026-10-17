#!/usr/bin/env bash
# Jarvis Linux ajan kurulumu. Kullanım: bash setup.sh cachyos   |   bash setup.sh mint
# Yaptıkları: openssh kur/etkinleştir, Mac'in anahtarını yalnızca yerel ağdan (192.168.1.*) kabul et,
# güvenlik duvarında yalnızca yerel ağa 22 aç, ~/jarvis-agent hazırla. Parola/anahtar kaydedilmez.
set -euo pipefail
ROLE="${1:?rol ver: cachyos veya mint}"
PUBKEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPj9n+80o2xjL/e2lRl4yibGkK5PsOCvoaaFKsnb066+ jarvis-mac'
LAN='192.168.1.*'
SRC='http://192.168.1.31:8799'
echo "== Jarvis ajan kurulumu: $ROLE"
if command -v pacman >/dev/null; then
  sudo pacman -S --needed --noconfirm openssh python; SVC=sshd
elif command -v apt-get >/dev/null; then
  sudo apt-get update -qq && sudo apt-get install -y -qq openssh-server python3-venv curl; SVC=ssh
else echo "Desteklenmeyen dağıtım"; exit 1; fi
sudo systemctl enable --now "$SVC"
mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys
grep -qF "$PUBKEY" ~/.ssh/authorized_keys || echo "from=\"$LAN\" $PUBKEY" >> ~/.ssh/authorized_keys
if command -v ufw >/dev/null && sudo ufw status | grep -q "Status: active"; then
  sudo ufw allow from 192.168.1.0/24 to any port 22 proto tcp
fi
mkdir -p ~/jarvis-agent ~/projeler
if [ "$ROLE" = mint ]; then
  curl -fsS "$SRC/browser.py" -o ~/jarvis-agent/browser.py
  # alt çubuk (overlay) için tk
  if command -v pacman >/dev/null; then sudo pacman -S --needed --noconfirm tk; else sudo apt-get install -y -qq python3-tk; fi
  python3 -m venv ~/jarvis-agent/.venv
  ~/jarvis-agent/.venv/bin/pip install -q playwright
  ~/jarvis-agent/.venv/bin/python -m playwright install --with-deps chromium
fi
if [ "$ROLE" = cachyos ]; then
  sudo pacman -S --needed --noconfirm nodejs npm python-pytest git
  npm config set prefix ~/.local
  npm install -g @google/gemini-cli || echo "UYARI: gemini-cli kurulamadı (kodlama ajanı sonra)"
fi
echo
echo "TAMAM. Bu satırı Jarvis'e ilet ->  $ROLE $(hostname -I | awk '{print $1}') $USER"
