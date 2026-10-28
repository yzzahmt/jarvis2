# 023 — Daha çok ücretsiz beyin, beyin kontrol betiği, doğal Türkçe ses
Kullanıcı: "bütün ücretsiz API'leri kullanalım, biri bitince diğerine geçsin"; "neden Fransız aksanıyla konuşuyor,
normal bir Türk gibi konuşsun".
- Zincir zaten kotası dolanı bekletip sıradakine geçiyor; kaynak eklendi:
  groq-2 (openai/gpt-oss-20b), groq-3 (qwen/qwen3.8-27b) — aynı Groq anahtarı, her model ayrı kota, araç çağrısı çalışıyor.
  Anahtar gelince devreye girecekler (yoksa atlanır): cerebras (gpt-oss-120b), mistral (mistral-small-latest),
  github (GitHub Models, openai/gpt-4.1-mini), sambanova, nvidia, openrouter. Model adları anahtar gelince doğrulanacak.
- scripts/beyin_kontrol.py: her beyni kısa istekle dener (✓/✕/anahtar yok, süre), anahtar yazdırmaz.
  29.10 sonuç: gemini ×2, gemini-lite ×2, groq ×3 ✓; gemini-flash-latest yoğunluk (503/zaman aşımı) → zincir atlar.
- Ses: test sırasında Ava seçilmişti (çok dilli İngilizce ses → Türkçeyi yabancı aksanla okur). Emel'e alındı.
  Listede Emel en üstte "Türkçe, doğal"; diğerleri "yabancı aksanlı". tr-TR-AhmetNeural hâlâ ses üretmiyor.
