# Linux Mint ajanı (tarayıcı/YouTube)
## Betiği aktarma (iki makine için de)
Mac'te bir kerelik geçici sunucu (yalnızca kurulum süresince, sonra Ctrl+C):
`python3 -m http.server 8799 --bind 192.168.1.31 --directory /Volumes/HDD/projeler/projeler/Jarvis/data/serve`
Linux'ta: `curl -fsS http://192.168.1.31:8799/setup.sh -o /tmp/setup.sh && bash /tmp/setup.sh mint`
(Sunucuda yalnızca kurulum betiği, açık anahtar ve browser.py var; gizli bilgi yok.)

## Adımlar
1. `bash /tmp/setup.sh mint` → openssh-server, Mac anahtarı (yalnızca 192.168.1.*), ufw'de yalnız yerel ağa 22,
   `~/jarvis-agent` (browser.py + Playwright Chromium).
2. Son satırı (`mint <ip> <kullanıcı>`) Jarvis'e ilet.
3. Masaüstü oturumu açık olmalı (videolar `DISPLAY=:0` ile varsayılan tarayıcıda açılır).
4. Test: "mint'te youtube'da lofi ara", "birinci videoyu aç".
