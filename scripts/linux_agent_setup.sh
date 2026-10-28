#!/usr/bin/env bash
# Jarvis Linux ajan kurulumu. Kullanım: bash setup.sh zorin   |   bash setup.sh mint
# Yaptıkları: openssh kur/etkinleştir, Mac'in anahtarını yalnızca yerel ağdan (192.168.1.*) kabul et,
# güvenlik duvarında yalnızca yerel ağa 22 aç, ~/jarvis-agent hazırla. Parola/anahtar kaydedilmez.
set -euo pipefail
ROLE="${1:?rol ver: zorin veya mint}"
PUBKEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPj9n+80o2xjL/e2lRl4yibGkK5PsOCvoaaFKsnb066+ jarvis-mac'
LAN='192.168.1.*'
SRC="http://${MAC_IP:?MAC_IP yok, komutu Mac tarafindaki serve_setup.sh ciktisindan kopyala}:8799"
echo "== Jarvis ajan kurulumu: $ROLE"
command -v apt-get >/dev/null || { echo "Bu betik Ubuntu tabanlı dağıtımlar içindir (Zorin OS, Linux Mint)"; exit 1; }
sudo apt-get update -qq
sudo apt-get install -y -qq openssh-server python3 python3-venv python3-tk curl git xz-utils
sudo systemctl enable --now ssh
mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys
grep -qF "$PUBKEY" ~/.ssh/authorized_keys || echo "from=\"$LAN\" $PUBKEY" >> ~/.ssh/authorized_keys
if command -v ufw >/dev/null && sudo ufw status | grep -q "Status: active"; then
  sudo ufw allow from 192.168.1.0/24 to any port 22 proto tcp
fi
mkdir -p ~/jarvis-agent ~/projeler
if [ "$ROLE" = mint ]; then
  curl -fsS "$SRC/browser.py" -o ~/jarvis-agent/browser.py
  python3 -m venv ~/jarvis-agent/.venv
  ~/jarvis-agent/.venv/bin/pip install -q playwright
  ~/jarvis-agent/.venv/bin/python -m playwright install --with-deps chromium
fi
if [ "$ROLE" = zorin ]; then
  sudo apt-get install -y -qq python3-pytest
  # Ubuntu deposundaki Node eski (Gemini CLI 20+ ister): resmi Node 22 LTS ~/.local/node'a, sudo'suz
  if ! command -v node >/dev/null || [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 20 ]; then
    ARCH=$(uname -m); [ "$ARCH" = x86_64 ] && ARCH=x64; [ "$ARCH" = aarch64 ] && ARCH=arm64
    F=$(curl -fsS https://nodejs.org/dist/latest-v22.x/ | grep -o "node-v22[0-9.]*-linux-$ARCH.tar.xz" | head -1)
    mkdir -p ~/.local/node && curl -fsS "https://nodejs.org/dist/latest-v22.x/$F" | tar -xJ -C ~/.local/node --strip-components=1
    grep -q '.local/node/bin' ~/.profile || echo 'export PATH="$HOME/.local/node/bin:$HOME/.local/bin:$PATH"' >> ~/.profile
    grep -q '.local/node/bin' ~/.bashrc || echo 'export PATH="$HOME/.local/node/bin:$HOME/.local/bin:$PATH"' >> ~/.bashrc
  fi
  export PATH="$HOME/.local/node/bin:$HOME/.local/bin:$PATH"
  npm config set prefix ~/.local
  npm install -g @google/gemini-cli || echo "UYARI: gemini-cli kurulamadı (kodlama ajanı sonra)"
fi
echo
echo "TAMAM. Bu satırı Jarvis'e ilet ->  $ROLE $(hostname -I | awk '{print $1}') $USER"
