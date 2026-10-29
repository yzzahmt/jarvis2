# 027 — Aşama 2: Görev sürerken konuşma, yön değiştirme, plan bildirme

- Sesli komut artık arka planda çalışır (VoiceLoop.run_task); bu sırada mikrofon dinlemeye devam eder.
  * "dur / iptal / vazgeç / bırak" → görev hemen durur.
  * Başka her söz (ör. "mavi değil kırmızı olsun", "şu klibi de ekle") → Jarvis.tell → inbox → ajan bir sonraki
    turda "[Görev sürerken kullanıcı şunu dedi]" mesajını görür ve planını günceller. Jarvis "Tamam, bunu da hesaba
    katıyorum." der.
  * Jarvis konuşurken (söze girme hâlâ çalışır) ya da görev soru sorarken (answering) dinleyici mikrofonu bırakır.
- Arayüz: görev sürerken yazılan mesaj da aynı şekilde göreve iletilir ("şu an görev çalışıyor" engeli kalktı).
- Yeni araç tell_user: cevap beklemeden kısa sesli bilgi. Talimat: 3+ adımlı işte başta planı tek cümleyle söyle,
  büyük aşamalarda durum bildir.
Testler: 65.
