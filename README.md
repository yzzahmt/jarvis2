# JARVIS
Üç bilgisayarlı, Türkçe konuşan, **tamamen yerel** kişisel asistan. Claude/bulut kullanmaz.

| Katman | Araç |
|---|---|
| Komut anlama | Türkçe kurallar → yerel model (Ollama `qwen3:4b`, yedek `gemma3:4b`) |
| Uyandırma | "hey jarvis" (openWakeWord) · ⌘⇧J kısayolu · çift alkış (isteğe bağlı) |
| Ses | faster-whisper `large-v3-turbo` (STT) · Edge sinir ağı sesi Ava (TTS), yedek Piper / `say -v Yelda` |
| Makineler | Mac (merkez) · Zorin OS (kod/test, SSH) · Linux Mint (YouTube/tarayıcı, SSH) |
| Kodlama ajanı | Gemini CLI (ücretsiz) → Aider (yerel model) |
| Hafıza | SQLite `data/jarvis.db` |

## Kullanım
```bash
/Volumes/HDD/projeler/projeler/Jarvis/scripts/jarvis.sh          # sesli
/Volumes/HDD/projeler/projeler/Jarvis/scripts/jarvis.sh text     # yazılı
/Volumes/HDD/projeler/projeler/Jarvis/scripts/jarvis.sh serve    # API 127.0.0.1:8765
```
Kısayollar: ⌘⇧J uyandır/sözü kes · ⌘⇧M mikrofonu aç/kapat.

Örnek komutlar: "saat kaç", "bilgisayarlar çevrimiçi mi", "mint'te youtube'da barış manço ara", "ikinci videoyu aç",
"zorin'de tarih projesinin testlerini çalıştır", "hatırla: proje tarih = ~/projeler/tarih", "uyu", "dur".

Kurulum: `docs/macOS_SETUP.md`, `docs/ZORIN_SETUP.md`, `docs/LINUX_MINT_SETUP.md`.
Yeni oturum: `devam.txt` · İlerleme: `docs/PROGRESS.md` · Değişiklik notları: `yenilikler/`.
Testler: `source scripts/env.sh && pytest -q` · Ses kontrolü: `python scripts/check_voice.py`.
