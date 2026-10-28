# 020 — Cevap verememe, uykuya geçmeme, kendi kendine cevap
Kullanıcı: "aşırı düşünüyor, basit şeye bile cevap veremiyor"; "konuşmazsam uyku moduna geçmiyor, kendi kendine cevaplıyor".

Sebep (app.log 00:03-00:04): 017'deki ikinci kulak (Mac tanıması) JARVIS.app içinde hep boş döndü → "Naber, nasılsın?"
dahil gerçek sözler "uydurma" diye atıldı. Mac tanıması uygulama içinde çalışmıyor: JARVIS.app Info.plist'inde
NSSpeechRecognitionUsageDescription yok (terminalden gerçek mikrofon kaydını doğru yazıyor). Eklemek uygulamanın
imzasını değiştirip mikrofon iznini sıfırlar → şimdilik yapılmadı.
Uyumama: uydurma cümle kabul edilince cevap verip uyku sayacını sıfırlıyordu.

Yapılanlar:
- apple_stt hatayı "!" ile bildirir (1110 = gerçekten konuşma yok); Python hatayı "boş" saymaz, günlüğe
  "Mac tanıması çalışmadı" yazar. Mac yalnız bu oturumda en az bir kez metin döndürdüyse (apple_ok) boşla veto eder.
- Silero VAD (faster-whisper içinde, yerel, ~5 ms): en az 0,3 sn insan konuşması yoksa ses hiç gönderilmez.
  Ölçüm: konuşma 3,7-3,8 sn; beyaz/kahverengi gürültü, klavye, sessizlik 0 sn.
- Gemini'ye ad listesi verilmiyor ("Jarvis, Spotify'ı aç" listedeki iki addan uyduruldu); talimata
  "uzaktaki TV/konuşma → boş" eklendi. Liste yalnız Groq/Mac/whisper'da.
Testler: 60.
