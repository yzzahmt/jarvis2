# Linux Mint ajanı (tarayıcı/YouTube)
## Betiği aktarma (iki makine için de)
Geçici sunucu yalnızca kurulum süresince açık kalır (sonra Ctrl+C).

Mac'te `scripts/serve_setup.sh` çalıştır; ekrana yazdığı satırı Linux'ta çalıştır (sondaki zorin yerine mint).
(Sunucuda yalnızca kurulum betiği, açık anahtar ve browser.py var; gizli bilgi yok.)

## Adımlar
1. `bash /tmp/setup.sh mint` → openssh-server, Mac anahtarı (yalnızca 192.168.1.*), ufw'de yalnız yerel ağa 22,
   `~/jarvis-agent` (browser.py + Playwright Chromium).
2. Son satırı (`mint <ip> <kullanıcı>`) Jarvis'e ilet.
3. Masaüstü oturumu açık olmalı (videolar `DISPLAY=:0` ile varsayılan tarayıcıda açılır).
4. Test: "mint'te youtube'da lofi ara", "birinci videoyu aç".
