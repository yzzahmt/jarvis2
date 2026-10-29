# 029 — Aşama 3: Bir kere göster, Jarvis öğrensin

- "Sana CapCut'ta altyazı eklemeyi göstereyim" / "beni izle" → kayıt başlar (ad: cümleden). Kullanıcı işi kendisi yapar.
- "Tamam bitti" → kayıt biter, adımlar saklanır (DB kind=demo). "Kaydı iptal et" → silinir.
- Kayıt sürerken başka komut çalışmaz (yanlışlıkla iş yapmasın); ses döngüsü uykuya geçmez.
- jarvis/agent/teach.py: kayıt AYRI SÜREÇTE (pynput klavye dinleyicisi arayüz sürecinde macOS'ta çöküyordu).
  Tıklama/çift tık/sağ tık/sürükleme/kaydırma + tıklanan öğenin Erişilebilirlik adı ve uygulaması, yazılan metin,
  kısayollar. Şifre alanına yazılan "•••"; gizli bilgiye benzeyen metin "(gizli metin)". Jarvis'in kendi penceresi atlanır.
- Benzer istek gelince (gösterimin adındaki kelimelerin %30+'ı istekte) ajana "KULLANICI SANA BUNU BİZZAT GÖSTERDİ"
  diye numaralı adımlar verilir; ui_read ile aynı öğeleri bulup değişen kısımları uyarlar.
- Canlı deneme: kayıt süreci Terminal'deki kaydırmayı "metin alanı 'kabuk' üzerinde kaydır (3)" olarak yakaladı.
İzin: klavye kaydı için Gizlilik > Giriş İzleme > JARVIS (ilk kayıtta macOS sorabilir). Testler: 68.
