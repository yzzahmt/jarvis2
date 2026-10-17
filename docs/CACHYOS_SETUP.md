# CachyOS ajanı (kod/test)
1. Betiği CachyOS'a aktar (bkz. "Betiği aktarma" — LINUX_MINT_SETUP.md) ve çalıştır: `bash setup.sh cachyos`
   → openssh + sshd, Mac anahtarı (yalnızca 192.168.1.*), ufw'de yalnız yerel ağa 22, nodejs/npm/pytest, Gemini CLI (`~/.local`).
2. Son satırı (`cachyos <ip> <kullanıcı>`) Jarvis'e ilet → `config/machines.yaml` doldurulur.
3. Gemini CLI girişi (bir kez, ücretsiz Google hesabı): CachyOS'ta `~/.local/bin/gemini` çalıştır, Google ile giriş yap, çık.
4. Projeler `~/projeler/<ad>` altında. Test: "bilgisayarlar çevrimiçi mi", "cachyos'ta <ad> projesinin testlerini çalıştır".
