# 014 — Günlük bulut sınırı, 2. Gemini anahtarı, mini Jarvis
(013'ten sonra yapıldı; oturum bağlantısı kopunca not düşülememişti, 28.10 23:40'ta tamamlandı.)
- Günlük bulut sınırı: `budget.max_cloud_calls_per_day: 300` (`brains.py` `daily_cap`, `today()`); sayaç
  SQLite'ta `kullanim:YYYY-AA-GG:<beyin>`. Dolunca yalnız yerel model. Arayüz durumunda "bugün / sınır" görünür.
  Gemini ile yazıya dökme de bu sayaca işlenir (`voice/loop.py`, `brains.note("gemini-stt")`).
- Beyin sırası: gemini (3.5-flash-lite) → gemini-yedek (gemini-flash-latest) → gemini-2 (`GEMINI_API_KEY_2`,
  ikinci ücretsiz anahtar = kota iki katı) → groq → cerebras → openrouter → yerel qwen3:4b. İki anahtar da 200 döndü.
- Mini Jarvis: `voice.quick_keys: "<+z"` → birlikte basınca altta küçük pencere açılır/kapanır (yalnız son iki
  mesaj; `ui/app.py` `toggle_mini/set_mini`, `index.html` `body.mini`).
- Test: Gemini thought_signature gidiş-dönüşü + günlük sınırda yerele düşme. Toplam 51 geçti.
