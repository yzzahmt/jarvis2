# 018 — Takıldığında sorsun, kafasına göre iş yapmasın
Kullanıcı: "Jarvis takıldığı yerde bana sorsun, kafasına göre iş yapmasın; hangisini/nasıl yapayım diye sorsun".
- `agent/loop.py` SYSTEM: "Belirsizse ask_user" tek satırı yerine açık kurallar — istek birden çok anlama geliyorsa
  ilk adımdan önce; birden çok uygun seçenekte kendin seçme, 2-3'ünü söyleyip sor; söylenmeyeni varsayma (marka,
  boyut, fiyat, klasör); bir yol olmadı/beklenmedik ekran → dur, ne denediğini söyle, sor. Basit tek anlamlı işte sorma.
  "Yapmadığın şeyi yaptım deme" (app.log'da API anahtarını almadan "aldım, kasama kaydettim" demişti).
- Kodda (model atlayamaz): üst üste 2 başarısız adımda araç sonucuna "[SİSTEM: … ask_user ile sor]" eklenir;
  ask_user ya da başarılı adım sayacı sıfırlar.
- `core.py` CHAT_SYSTEM: sohbette hiçbir iş yapmadığını bilir; "açtım/aldım/kaydettim" demez, belirsizse kısa soru.
Testler: 58.
