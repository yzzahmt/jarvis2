# 022 — Ses seçimi görünmüyordu, tıklayınca önizleme, ayarlarda çökme
Kullanıcı: "ayarlar butonuna bastığım anda Jarvis çöktü"; "tıkladığımız ses kısa bir şey konuşsun"; "hangisini
seçtiğimizi göstermiyor ve ses seçmiyor".
- Seçim aslında ayara yazılıyordu ama işaret (ince çerçeve) silikti, liste kayınca görünmüyordu, panel yarı saydamdı.
  Şimdi: onay dairesi + mavi zemin + "Seçili"; tıklayınca anında işaretlenir; panel opak (--sheet);
  beyinler küçük etiketler (kullanılan mavi çerçeveli, kota dolan turuncu).
- Satıra tıklamak = seç + "Merhaba, ben <ad>. Sesim böyle, beğendin mi?"; ▶ = seçmeden dinle (çalarken mavi).
- Çökme yeniden üretilemedi (ayarlar defalarca açıldı, ses seçildi; çökmedi). Çökmeden önce önizleme 2 kez çalmıştı:
  her tıklamada yeni TTS motoru + Jarvis'in sesiyle üst üste. Artık tek önizleme motoru, önce diğer sesler susar.
- Çökme kaydı: faulthandler + iş parçacığı hataları → data/logs/crash.log; pencere kapanınca çağıran yığın app.log'a.
- JARVIS.app simgesi: 021'deki xattr temizliği Finder'ın özel simgesini silmişti → assets/jarvis.png'den
  applet.icns üretilip paketin içine kondu, CFBundleIconName silindi (scripts/app_izinleri.sh bunu da yapar).
