# 003 — Ses, tarayıcı, Linux ajan kurulumu
**Ses** (`jarvis/voice/`): `wakeword.py` (hey jarvis), `clap_detector.py` (çift alkış, varsayılan kapalı),
`speech_to_text.py` (whisper small, TR, ses diske yazılmaz), `text_to_speech.py` (Piper TR, kesilebilir, yedek `say`),
`loop.py` (UYKU↔AKTİF, ⌘⇧J uyandır/sözü kes, ⌘⇧M mikrofon, 60 sn boşta → uyku, kendi sesini duymama, mikrofon yoksa metin modu).
**Modeller (HDD):** qwen3:4b + gemma3:4b (Ollama), whisper small, Piper tr_TR-dfki-medium, hey_jarvis.
**Tarayıcı:** YouTube sonuçları `ytInitialData`'dan okunuyor (yeni YouTube düzeninde de çalışıyor). Chromium HDD'de.
**Yönlendirme:** "şarkı/müzik/video ... aç/çal" → YouTube; Türkçe uygulama adları (notlar→Notes vb.); yerel modele örnekli istem.
**Linux:** `scripts/linux_agent_setup.sh` (sshd, anahtar yalnız 192.168.1.*, ufw, Mint'e Playwright, CachyOS'a Gemini CLI).
SSH anahtarı: `~/.ssh/jarvis_ed25519`. Başlatıcı: `scripts/jarvis.sh`. Belgeler: `docs/*_SETUP.md`, `README.md`.
**Test:** 27/27 pytest + `scripts/check_voice.py` BAŞARILI. Commit'ler `02ea0d5`, `ac4d106`.
**Bekleyen:** Linux'ta setup.sh, gerçek mikrofon denemesi.
