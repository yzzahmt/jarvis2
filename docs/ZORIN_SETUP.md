# Zorin OS ajanı (kod/test)
Zorin OS Ubuntu tabanlıdır (apt). Jarvis bu makineye SSH ile bağlanır; kod yazdırma (Gemini CLI) ve testler burada çalışır.

## Adımlar
1. **Mac'te** (Jarvis klasöründe): `scripts/serve_setup.sh` → ekrana Zorin'de çalıştırılacak tek satırlık komutu yazar.
2. **Zorin'de** Terminal aç, o satırı yapıştır (sudo şifresi sorar):
   `curl -fsS http://<MAC_IP>:8799/setup.sh -o /tmp/setup.sh && MAC_IP=<MAC_IP> bash /tmp/setup.sh zorin`
   Kurar: openssh-server, Mac'in anahtarı (yalnızca 192.168.1.* ağından), ufw'de yalnız yerel ağa 22,
   python3-tk (alt çubuk), git, pytest, Node 22 (~/.local/node), Gemini CLI (~/.local/bin).
3. Son satırı (`zorin <ip> <kullanıcı>`) Jarvis'e (Claude'a) ilet → `config/machines.yaml` doldurulur. Mac'te Ctrl+C.
4. **Gemini CLI girişi** (bir kez, ücretsiz Google hesabı): Zorin'de yeni Terminal → `gemini` → Google ile giriş → çık.
5. Projeler `~/projeler/<ad>` altında olmalı.
6. Test: "bilgisayarlar çevrimiçi mi", "zorin'de <ad> projesinin testlerini çalıştır".

## Öneriler
- Zorin'e sabit IP ver (modem DHCP rezervasyonu); IP değişirse machines.yaml güncellenir.
- Ayarlar > Güç: otomatik uykuyu kapat (uykudaysa Jarvis "çevrimdışı" der).
- Alt çubuk için masaüstü oturumu açık olmalı.
