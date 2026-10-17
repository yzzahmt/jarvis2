# JARVIS — İlerleme

## Durum (2026-10-17)
- **Tamamlanan:** Aşama 1, 2, 5, 6 (Mac tarafı), 7 (kod + çevrimdışı ses testi), 8 (Claude yerine Gemini CLI/Aider adaptörü), genel ajan + beceri belleği + makrolar (yenilikler/005).
- **Bekleyen (kullanıcı eylemi gerekli):** Aşama 3–4 — Linux makinelerinde `setup.sh` çalıştırmak; gerçek mikrofonla ses denemesi.
- **Sıradaki tek adım:** Kullanıcı `setup.sh` çıktısındaki `<rol> <ip> <kullanıcı>` satırlarını iletince `config/machines.yaml` doldur, `python -m jarvis status` ile bağlantıyı test et, Mint'te YouTube ve CachyOS'ta test çalıştırmayı doğrula.

## Testler
| Test | Durum |
|---|---|
| pytest (37 test: yönlendirme, görev durumları, tekrar engeli, bütçe/sonsuz döngü, onay, çevrimdışı, hafıza, gizli bilgi, yeniden başlatma, alkış, ajan/araçlar/beceri/makro) | ✅ |
| Genel ajan gerçek modelle (qwen3:8b, tek model RAM'de) | ✅ 5–25 sn/görev, yönlendirme 1–2 sn |
| ask_ai → Gemini/ChatGPT web sohbeti | ⏳ tarayıcıda oturum açılınca denenecek |
| Yerel model Türkçe niyet ayrıştırma (qwen3:4b → artık qwen3:8b) | ✅ 1–2 sn/komut (sıcak) |
| STT Türkçe (whisper small) | ✅ yükleme 14 sn (bir kez), çeviri 1–2 sn |
| TTS Türkçe (Piper dfki) | ✅ hoparlörden çalındı |
| Uyandırma "hey jarvis" (sentetik ses) / gürültüde yanlış uyanma | ✅ / ✅ yok |
| YouTube araması (Mac, Playwright) | ✅ |
| Metin modu uçtan uca (gerçek model + tarayıcı) | ✅ |
| Gerçek mikrofonla sesli döngü | ⏳ kullanıcı denemesi gerekli (mikrofon izni) |
| CachyOS / Mint SSH | ⏳ setup.sh bekleniyor |
| Gemini CLI bayrakları (`-p`) | ⏳ CachyOS'ta `--help` ile doğrulanacak |
| Çift alkış gerçek mikrofonda | ⏳ (varsayılan kapalı) |

## Bilinen sorunlar
- Türkçe uyandırma kelimesi yok; "hey jarvis" (İngilizce model) kullanılıyor.
- Piper'da tek Türkçe ses var (dfki, erkek); beğenilmezse `voice.tts: say` (Yelda).
- Antigravity (Mac'te kurulu) CLI ile otomasyona uygun değil → adaptör ertelendi (Aşama 9).
- `data/serve/` geçici kurulum dosyaları; kurulum bitince silinebilir.
- qwen3:8b ilk yüklemede HDD'den ~1–2 dk sürer; sonra `keep_alive: 30m` ile bellekte kalır (~5,9 GB).
- Ajan küçük model olduğu için bazen gereksiz adım atıyor; beceri belleği yanlış bir çözümü de örnek diye saklayabilir (ipucunda "doğrula" uyarısı var).

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

