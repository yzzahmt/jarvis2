# 016 — Uyanma cevabı, alkış sesi, gürültüde uydurma komut
Kullanıcı: "hey jarvis ile uyanınca 'sizi dinliyorum' desin, alkışla uyanınca bir ses çıkarsın";
"durduk yere 'API anahtarını güncelleyelim' deyip duruyor".

Uyanma (`voice/loop.py`): uyanma kaynağı tutulur (`wake_src`: word / clap / key).
- "hey jarvis" → "Sizi dinliyorum." der (`voice.wake_reply`, açılışta önbelleğe alınır; söze girilirse susar).
- Çift alkış → `clap_chime()`: yükselen üç ton, kısayoldaki kısa sesten belirgin (~0,4 sn).
- Kısayol → eski kısa iki ton.

Uydurma komut (`voice/speech_to_text.py`): 015'ten sonra app.log'da kullanıcının söylemediği
"env dosyasındaki API key'ini günceller misin?" çıktı. Gürültülü kayıtta model ad listesindeki ".env, API"den uyduruyordu
(015'teki sessizlik kapısı yalnız tam sessizliği yakalıyordu).
- `speechy()`: 30 ms karelerde arka plan (20. yüzdelik) ×2,5'in üstünde en az 4 kare (120 ms) kesintisiz ses yoksa
  modele gönderilmez. Ölçüm: konuşma 29-90 kare; beyaz/kahverengi gürültü 0; klavye 1; çok kısık konuşma 5.
- NAMES'ten genel kelimeler (API, .env, PDF, sandbox, Mac, Safari, Finder) çıkarıldı; yalnız özel adlar.
- Canlı: gürültülerin hepsi boş; kısık konuşma doğru. Testler: 54.
