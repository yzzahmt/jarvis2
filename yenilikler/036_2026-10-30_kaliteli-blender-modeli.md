# 036 — Blender'da kaliteli, görünür model (30.10.2026)

Sorun: Jarvis Blender arayüzünü kullanmadı. Arka planda bpy çalıştırdı ve önceki basit test arabasını yeniden yaptı.
- Kaydedilen araba becerisi (beceri:f38c11319a9e) DB'den silindi. Jarvis aynı test arabasını bu yüzden tekrarlıyordu.
- Arka plan `blender` aracı (bpy) ajandan gizli. Yalnız istekte "arka planda / hızlıca / görmeme gerek yok" geçerse açılır.
  Gizliyken çağrılırsa "görünür çalış (blender_ui)" cevabı döner. blender_ui hep açık.
- Kaliteli model akışı: önce ücretsiz hazır model (Sketchfab downloadable, Poly Haven, BlenderKit). En iyi 2-3'ü
  ask_user ile sorulur, seçilen indirilir, Blender'da görünür açılıp düzenlenir. Hiçbiri beğenilmezse sıfırdan, insan
  gibi modellenir: blokaj → halka kesim/extrude + mirror → subdivision → tekerlek, cam, far → iç mekân (koltuk,
  direksiyon, H vites, 3 pedal) → malzeme, ışık, render. Her parçadan sonra look_screen ile bakılır, kötüyse cmd+z.
- Sınırlar: ajan 400 tur / 4500 sn (75 dk), bulutta görev başına 400 çağrı (günlük 600 aynı).
73 test.
