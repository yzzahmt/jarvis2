# 012 — Gemini bağlandı, hız, uyandırma/alkış ayarı
Kullanıcı: "aşırı kasıyor, çalışmıyor", "hey jarvis ve 2 alkış ile uyanmıyor".
- **Sistem kasması:** Unity'nin sahipsiz C# derleyicisi (VBCSCompiler, PPID 1) 2 sa+ %100 CPU. Jarvis değil.
  Claude'un kapatma isteği izin sisteminde reddedildi → kullanıcı kapatacak (Etkinlik Monitörü / kill).
- **Gemini anahtarı** kullanıcının Google AI Studio hesabındaki mevcut ücretsiz anahtardan (…8ffw) alındı, değer
  ekrana basılmadan .env'e + Anahtar Zinciri'ne (gemini:api_key) yazıldı. Yeni biçim `AQ.…` (53 karakter);
  arayüz anahtar doğrulaması buna göre gevşetildi. Groq: hesap açma gerektiği için yapılmadı (gerek de kalmadı).
- **gemini-2.5-flash kaldırılmış (404)** → `gemini-3.5-flash-lite` (reasoning_effort minimal, ~1 sn) + yedek
  `gemini-flash-latest`. gemini-3.8-flash o an 503 (yoğun).
- **Gemini 3 araç çağrısı:** `thought_signature` (tool_calls[].extra_content) bir sonraki turda geri gönderilmezse 400 →
  beyin soğumaya giriyor, her şey yerel 4B'ye düşüyordu (görev 26 sn, İngilizce düşünce sızıntısı). `ToolCall.extra` ile
  geri gönderiliyor; 400 soğuması 120 → 30 sn. Ajan görevi artık ~3 sn, görme ~2,4 sn.
- **Ses tanıma Gemini'de** (`speech_to_text.py`, ~1,1-1,7 sn), yerel whisper large-v3-turbo yalnızca bulut olmazsa
  ve ilk ihtiyaçta yüklenir (açılışta 2,3 GB / ~40 sn tasarruf). Bulut varken yerel LLM ısıtılmıyor.
- **Uyandırma/alkış** canlı mikrofon ölçümüyle: kullanıcının "hey jarvis" puanı 0,37-0,62 → eşik 0,5 → 0,35;
  alkış tepeleri 0,35-0,61 ama dedektör 0,5 istiyordu → `clap_peak: 0.3`, `clap_max_gap: 1.0` (settings'ten okunuyor).
  Mikrofon ~10 sn tam sıfır verirse "Mikrofon izni yok" uyarısı. macOS giriş seviyesi %33 (düşük).
- Gemini TTS (gemini-3.8-flash-tts) denendi: çok doğal ama cümle başına ~5 sn → kullanıcı Ava'da kaldı.
- Testler: 50 geçti (yeni: thought_signature gidiş-dönüş).
