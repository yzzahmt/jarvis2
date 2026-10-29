# JARVIS — İlerleme

## Durum (2026-10-28)
- **Tamamlanan:** Aşama 1, 2, 5, 6 (Mac), 7, 8, genel ajan + beceri + makrolar, **tam bilgisayar kontrolü + Edge sesi + kasa (yenilikler/009)**, Ava sesi + devam.txt (010), donma düzeltmesi + ayarlar paneli + Zorin OS (011), Gemini bağlandı + hız + uyandırma ayarı (012), akışlı ses + tek çağrıda sohbet (013).
- **Bekleyen (kullanıcı):** `.env`'e `GEMINI_API_KEY`; Mac izinleri (Erişilebilirlik + Ekran Kaydı, Jarvis'i çalıştıran uygulamaya);
  sık kullanılan siteler için bir kez tarayıcıda giriş veya `python -m jarvis secret set site.com:email|sifre`;
  Aşama 3–4 Linux `setup.sh`.
- **Sıradaki tek adım:** Anahtar gelince `python -m jarvis` metin modunda gerçek görevler: "Finder'da İndirilenler'i aç"
  (click_on), bir sitede ürünü sepete ekleme (ödeme onayında durmalı), iyzico sandbox API anahtarını test projesinin .env'ine alma.
  Gemini model adını `/models` listesinden doğrula.

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
| Zorin OS / Mint SSH | ⏳ setup.sh bekleniyor (scripts/serve_setup.sh) |
| Gemini CLI bayrakları (`-p`) | ⏳ Zorin'de `--help` ile doğrulanacak |
| Çift alkış gerçek mikrofonda | ⏳ (varsayılan kapalı) |
| Edge TTS (Emel) hoparlörde, ilk ses ~1,5 sn | ✅ |
| Tarayıcı numaralı öğeler + kasadan şifre + select (yerel sayfa) | ✅ |
| Ödeme/kart/hesap kapısı, click_on, save_secret→.env (pytest, 49) | ✅ |
| Gemini ajan görevi (araçlı) / ses tanıma / görme | ✅ ~3 sn / ~1,5 sn / ~2,4 sn |
| Uyandırma 0,35 + alkış 0,3 gerçek mikrofonda (kayıttan) | ✅ yakalandı; uygulamada kullanıcı denemesi ⏳ |
| click_on gerçek tıklama / gerçek sitede alışveriş ve API anahtarı | ⏳ |

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



## 014 (28.10.2026)
Günlük bulut sınırı (300), ikinci Gemini anahtarı (gemini-2), gemini-yedek, mini Jarvis kısayolu ('<'+'z'). 51 test geçti. Ayrıntı: yenilikler/014.

## 015 (28.10.2026)
Ses tanıma: örnek cümle ipucu kaldırıldı (sessizlikte uyduruluyor, sahte Zorin test komutu), karışık Türkçe/İngilizce talimatı, sessizlik kapısı, 2. anahtara geçiş. 53 test. Ayrıntı: yenilikler/015.

## 016 (28.10.2026)
'hey jarvis' → "Sizi dinliyorum.", alkış → belirgin ses; gürültü kapısı speechy() (gürültüde uydurma API/.env komutu), ipucundan genel kelimeler çıkarıldı. 54 test. Ayrıntı: yenilikler/016.

## 017 (28.10.2026)
Ses tanıma zinciri (Gemini 3 model × 2 anahtar → Groq → Mac apple_stt → whisper), Mac ikinci kulak ile uydurma komut reddi, kendi sesini yok sayma, mikrofon 33→80 ve yumuşak kesme, Groq gpt-oss-120b. 57 test. Ayrıntı: yenilikler/017.

## 018 (28.10.2026)
Takılınca sorar: ajan talimatında açık ask_user kuralları, kodda 2 başarısızlıktan sonra sor notu, sahte 'yaptım' yasağı. 58 test. Ayrıntı: yenilikler/018.

## 019 (29.10.2026)
Küçültünce alttaki Jarvis çubuğu (dock: küre, dalga, son cevap, mikrofon/durdur/büyüt/gizle); ana pencere premium cila (ışıklı kenar, avatarlı mesaj, kopyala, odak parlaması). Ayrıntı: yenilikler/019.

## 020 (29.10.2026)
İkinci kulak uygulama içinde gerçek sözleri atıyordu → kanıt şartı; Silero VAD kapısı; Gemini'ye ad listesi yok. 60 test. Ayrıntı: yenilikler/020.

## 021 (29.10.2026)
JARVIS.app'e konuşma tanıma izni + yeniden imza (scripts/app_izinleri.sh); Mac ikinci kulağı uygulama içinde. Ayrıntı: yenilikler/021.

## 022 (29.10.2026)
Ses seçimi belirgin + tıklayınca önizleme, tek önizleme motoru, çökme kaydı (crash.log), uygulama simgesi paket içinde. Ayrıntı: yenilikler/022.

## 023 (29.10.2026)
Groq'a 2 model daha, 6 ücretsiz sağlayıcı anahtar bekliyor, scripts/beyin_kontrol.py; ses Emel'e alındı, yabancı aksanlı sesler etiketlendi. Ayrıntı: yenilikler/023.

## 024 (29.10.2026)
OpenRouter: nemotron-3-ultra (araç çağrısı ✓) + gemma-4-31b (sık meşgul). Ayrıntı: yenilikler/024.

## 025 (29.10.2026)
Bağlı olmayan Zorin/Mint'ten söz edilmez (iş Mac'te; adı söylendiyse sorar), Mac ikinci kulağı boşken veto yok, 120 sn
kayıt, yankı ayıklama, süre günlüğü; drag_on/find_on_screen/pointer/unity araçları, uygulama kullanma talimatı, sınırlar
yükseltildi. 61 test. Ayrıntı: yenilikler/025.

## 026 (29.10.2026)
Aşama 1: Erişilebilirlik ağacıyla ekranı okuma (ui_read/ui_click/ui_type/ui_menu), görsel model yedek. Ayrıntı: yenilikler/026.

## 027 (29.10.2026)
Aşama 2: görev sürerken dinleme; 'dur' durdurur, diğer sözler çalışan göreve iletilir; tell_user ile plan/durum. Ayrıntı: yenilikler/027.
