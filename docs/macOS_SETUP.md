# macOS kurulumu (yapıldı)
Her şey HDD'de; dahili diske yazılmaz. `source scripts/env.sh` önbellekleri `data/` altına yönlendirir.
1. `python3.11 -m venv .venv && source scripts/env.sh && pip install -e ".[voice,browser,dev]"`
2. Ollama: `scripts/jarvis.sh` kendisi `OLLAMA_MODELS=data/ollama` ile başlatır. Model: `ollama pull qwen3:4b gemma3:4b`
3. Ses: `python -m piper.download_voices tr_TR-dfki-medium --data-dir data/tts`; uyandırma: `python -c "import openwakeword.utils as u; u.download_models(['hey_jarvis'])"`
4. Tarayıcı: `python -m playwright install chromium`
5. İzinler (ilk çalıştırmada macOS sorar): Mikrofon → Terminal; Erişilebilirlik/Girdi İzleme → Terminal (kısayollar için).
6. SSH anahtarı: `~/.ssh/jarvis_ed25519` (oluşturuldu; izin güvenliği için HDD'de değil).
7. Test: `pytest -q` ve `python scripts/check_voice.py`.
