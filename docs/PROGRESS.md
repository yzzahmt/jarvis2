# JARVIS — İlerleme

## Durum
- **Tamamlanan:** Aşama 1 (ortam incelemesi + plan) — 2026-10-17
- **Sıradaki tek adım:** Aşama 2'yi kullanıcı onayıyla başlatmak (önce HDD'de venv + veri klasörleri).

## Aşama 1 — Ortam (MacBook, ölçüldü)
| Öğe | Değer |
|---|---|
| CPU/GPU | Apple M3 (8 çekirdek CPU, 10 çekirdek GPU, Metal 4), arm64 |
| RAM | 16 GB |
| macOS | 26.6.2 (25G83) |
| Dahili disk | 460 GB, 338 GB boş — **Jarvis kullanmayacak** |
| HDD | `/Volumes/HDD`, APFS, USB, dönen disk (SSD değil), 620 GB boş, "Owners: Disabled" |
| Ağ | 192.168.1.31, ağ geçidi 192.168.1.1 |
| Python | 3.14.7 (varsayılan), **3.11.16** (`/opt/homebrew/bin/python3.11`) |
| Diğer | Homebrew 7.0.7, git 2.54, node 26.7, ffmpeg 9.0.1, Ollama 0.33.2 (kurulu, çalışmıyor, model yok), Claude Code 2.1.301, Antigravity.app kurulu |
| Yok | uv, pipx, sox, docker |
| SSH | `~/.ssh`'de anahtar yok; Uzak Giriş durumu yönetici yetkisi olmadan okunamadı |
| Proje klasörü | Boştu |

Claude Code CLI'da `claude --help` ile doğrulanan seçenekler: `-p/--print`, `--output-format`,
`--allowedTools`, `--disallowedTools`, `--permission-mode`, `--max-budget-usd` (yalnızca `--print` ile),
`--model`, `--resume`, `--continue`, `--add-dir`. `--max-turns` yardım çıktısında **görünmedi** → Aşama 8'de doğrulanacak, varsayılmayacak.

## Depolama kuralı (dahili diske yazmama)
Her şey `Jarvis/` altında, `data/` git dışı:
```
Jarvis/.venv                 Python 3.11 sanal ortamı
Jarvis/data/ollama/          OLLAMA_MODELS
Jarvis/data/hf/              HF_HOME (whisper modelleri)
Jarvis/data/pip-cache/       PIP_CACHE_DIR
Jarvis/data/playwright/      PLAYWRIGHT_BROWSERS_PATH
Jarvis/data/tts/             Piper sesleri
Jarvis/data/jarvis.db        SQLite
Jarvis/data/logs/
```
- Ollama sunucusu `OLLAMA_MODELS` ortam değişkeniyle `scripts/` altındaki betikten başlatılacak (Homebrew servisi değil).
- SSH anahtarları istisna: `~/.ssh` içinde kalmalı (izin kontrolü; "Owners: Disabled" HDD'de güvenli değil). Birkaç KB.

## Mimari kararlar
- **Python 3.11** (3.14 için faster-whisper/onnx tekerlekleri riskli).
- **Komut sırası:** kural tabanlı Python → yerel model (Ollama) → Claude Code (`-p`, dar `--allowedTools`, bütçe/tur/zaman sınırları, görev başına tek oturum).
- **Yerel model adayları (Aşama 2'de Türkçe + hız testi):** 3–4B sınıfı, ~2–3 GB (ör. qwen3:4b, gemma3:4b). Tek model kalıcı tutulur.
- **Uyandırma:** openWakeWord (hazır "hey jarvis" modeli, CPU'da hafif) + klavye kısayolu + isteğe bağlı çift alkış (numpy enerji tepe algılama). Ayrı bileşenler; biri çökerse diğerleri çalışır.
- **STT:** faster-whisper (small/base, Türkçe); Metal için whisper.cpp alternatif olarak ölçülecek.
- **TTS:** Piper Türkçe ses (yerel); yedek: macOS `say` (Yelda), sıfır kurulum.
- **Yankı engeli:** TTS konuşurken mikrofon girişi yok sayılır + kısa susturma penceresi.
- **Ağ:** FastAPI yalnızca `127.0.0.1`/LAN; ajanlara SSH ile komut, ayrı API açılmaz (başlangıçta).
- **Dosya yapısı:** önerilen yapı kullanılacak, kök `Jarvis/` (alt klasör `personal-ai/` yok). Dosyalar ancak gerçek işlevle oluşturulacak.

## Riskler
1. HDD takılı değilse Jarvis çalışmaz → başlangıçta kontrol edilip net hata verilecek.
2. Dönen disk: model ilk yüklemesi yavaş (onlarca saniye); RAM'de kalınca sorun değil.
3. 16 GB RAM: LLM + whisper aynı anda ~5–6 GB; büyük model yok.
4. Türkçe uyandırma kelimesi hazır değil → "hey jarvis" (İngilizce model) kullanılacak; özel Türkçe model sonra.
5. Uzak Giriş/SSH için Mac'te değil, Linux makinelerinde sshd gerekiyor (Aşama 3–4).

## Aşama 2 planı (onay bekliyor)
1. `python3.11 -m venv Jarvis/.venv`, `data/` klasörleri, `.gitignore`, `git init`.
2. Paketler (venv'e, ~100 MB): fastapi, uvicorn, httpx, pyyaml, pytest.
3. Ollama'yı `OLLAMA_MODELS=data/ollama` ile başlat, 1–2 küçük model indir (~2–3 GB/adet, HDD'ye).
4. `memory/` (SQLite), `controller/task_manager.py`, `budget.py`, `router.py` (kural tabanlı komutlar), `models/ollama_client.py`.
5. Testler: SQLite kayıt, görev durumları, tekrar engeli, basit komut Claude'suz, model yanıtı.

## Testler
Henüz test yok (Aşama 1 yalnızca inceleme).

## Bilinen sorunlar
- `--max-turns` doğrulanmadı.
- Diğer iki bilgisayarın IP/sürüm bilgisi henüz alınmadı (Aşama 3–4).
