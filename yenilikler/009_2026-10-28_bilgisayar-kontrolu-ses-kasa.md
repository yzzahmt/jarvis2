# 009 — Tam bilgisayar kontrolü, doğal ses, gizli bilgi kasası
Hedef: kısayolla (Cmd+Shift+J) açılıp alışveriş, API anahtarı alma, uygulama kontrolü ve sohbet yapan Jarvis;
kullanırken Claude tokeni SIFIR (beyin: ücretsiz Gemini → Groq/Cerebras/OpenRouter → yerel qwen3:8b).

- **Ses** (`voice/text_to_speech.py`): Edge sinir ağı sesi `tr-TR-EmelNeural` (erkek: `tr-TR-AhmetNeural`), anahtarsız.
  Cümle cümle üretim + çalma (ilk ses ~1,5 sn). İnternet yoksa Piper → say; 5 dk sonra Edge yeniden denenir.
  `TTS.from_settings()` arayüz ve ses döngüsünde ortak. Kurulum: `edge-tts 7.3.1` (.venv, HDD).
- **Tarayıcı** (`automation/session.py`): sayfa numaralı öğe listesi (`[4] button "Sepete Ekle"`); yeni eylemler
  look, type(id,key), select, scroll, back, tabs, wait, fill_secret, save_secret. Yeni sekmeye otomatik geçer.
  Otomasyon bayrağı gizlendi (bazı siteler botu engelliyordu). `goto` artık file:// adresini bozmuyor.
- **Kasa** (`secrets.py`): macOS Anahtar Zinciri, hizmet "jarvis". Model değerleri hiç görmez.
  `python -m jarvis secret set trendyol.com:email` / `set trendyol.com:sifre` / `list` / `del`.
  `save_secret`: API anahtarını sayfadan veya panodan alıp kasaya ve/veya projenin `.env` dosyasına yazar
  (çıktıda maskeli; proje git ise `.env` .gitignore'a eklenir; izinli klasör dışı onay ister).
- **Güvenlik kapısı (kodda, model atlayamaz)**: "Siparişi onayla/Satın al/Öde…" tıklaması ve ödeme sayfasındaki
  devam/Enter → kullanıcıya sayfadaki tutarlarla sorulur; "Hesap oluştur/Kayıt ol" → sorulur; kart/CVV/IBAN alanına
  yazma tamamen yasak (sitede kayıtlı kart kullanılır).
- **Ekran** (`agent/tools.py`): `click_on(target)` ekran görüntüsünü görebilen beyne (Gemini) verir, kutu koordinatını
  alıp tıklar (sol/sağ/çift). `mouse` (scroll/move/drag). Görme: `Brains.vision` yalnızca `vision: true` beyinler,
  yoksa yerel gemma3.
- **Konuşma**: sohbet ve ajan talimatları doğal, konuşma dili Türkçesi; ajan alışveriş/giriş/API anahtarı akışlarını biliyor.
  Gemini için `reasoning_effort: none` (düşünme boş cevap üretmesin, hızlı olsun).
- Testler: 49 geçti (yeni `tests/test_computer.py`: ödeme/kart/hesap kapısı, .env yazımı, tarifle tıklama, görme, cümle bölme).
  Gerçek tarayıcıda numaralı öğe + kasadan şifre yazma + select denendi ✅. Edge sesi hoparlörde ✅.
- Bekleyen: `GEMINI_API_KEY` (.env) — gelmeden click_on ve Türkçe kalite yerel modelle sınırlı.
