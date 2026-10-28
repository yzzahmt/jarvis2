# 017 — Ses kaynakları hiç bitmesin, mikrofon, asla kendi kendine komut yok
Kullanıcı: "Gemini hakkımız bitecek, başka ses kaynağı/sistem yap, Groq ekle", "mikrofon sesimi anlamıyor,
kendimi kasıyorum", "gene kendi kendine komut veriyor, asla vermesin".

Ses tanıma zinciri (`voice/speech_to_text.py`), biri bitince sıradaki; kotası dolan 10 dk (ağ/yoğunluk 1 dk) atlanır:
1. Gemini — `voice.stt_cloud_models` [3.5-flash-lite, flash-lite-latest, 3.1-flash-lite] × 2 anahtar (her model ayrı kota)
2. Groq whisper-large-v3-turbo (GROQ_API_KEY, ücretsiz katman, ~0,6 sn)
3. Mac'in cihaz içi Türkçe tanıması: `tools/apple_stt/stt.swift` → `data/bin/apple_stt` (scripts/build_apple_stt.sh;
   jarvis.sh yoksa derler). Kotasız, internetsiz, ~0,4 sn. İlk çalışmada "Konuşma Tanıma" izni ister.
4. faster-whisper (yerel 2,3 GB) — yalnız hepsi yoksa.
Ölçüm: Gemini en iyi; Groq iyi (İngilizce biraz bozuk); Mac Türkçede iyi, İngilizcede zayıf ("commit"→"Kbid").

Beyinler (`settings.yaml brains`): gemini-lite / gemini-lite-2 (flash-lite-latest), gemini-yedek-2 eklendi;
Groq modeli llama-3.3-70b kaldırılmıştı → openai/gpt-oss-120b. (gemini-2.5-flash-lite 404, 3.6/3.7-flash 503/takılma.)

Mikrofon: macOS giriş seviyesi 33'tü (konuşma tepe 0,01 ≈ gürültü) → 80 yapıldı. Kayıt: başladıktan sonra kesme eşiği
%60 (yumuşak sesler kesilmez), bitiş sessizliği 0,9 → 1,2 sn; kısık ses yazıya dökülmeden yükseltilir (`louder`, en çok 8×).

Asla kendi kendine komut (app.log: "screenshot'ı kaydet." — talimattaki örnek kelimeden uyduruldu):
- Talimatta örnek kelime/cümle YOK.
- İkinci kulak: Mac tanıması paralelde çalışır; Mac hiçbir şey duymadıysa ya da kelimelerin ¼'ü bile örtüşmüyorsa
  (`agree`) metin atılır, günlüğe "yok sayıldı (uydurma olabilir)" yazılır. 11 gerçek cümlede yanlış ret yok, gecikme aynı.
- Kendi sesi: duyulan metnin %70'i Jarvis'in son 20 sn'de söylediğindeyse atılır (`heard_self`).
- jarvis.sh'te bu oturumda eklenen satırdaki eksik tırnak (başlatmayı bozuyordu) düzeltildi.
Testler: 57.
