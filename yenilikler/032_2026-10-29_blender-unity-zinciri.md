# 032 — Blender kuruldu, Blender → Unity zinciri gerçek denemeden geçti

- Blender 5.2.3 LTS (arm64) → data/apps/Blender.app (912 MB, HDD). hdiutil'e otomatik ortamda izin olmadığı için DMG
  7-Zip ile açıldı (7zz geçici indirildi, sonra silindi). Kullanıcının komut çalıştırmasına gerek kalmadı.
- blender aracı denendi: gövde/kabin/4 teker/malzemeler 4,7 sn'de kuruldu, .blend kaydedildi, render alındı.
  Otomatik kamera artık zemini (düz, yüksekliksiz nesneler) kadraja katmıyor; koyu varsayılan dünya aydınlık stüdyo olur.
- Zincir: blender → FBX → unity create (HDD'de, 23 sn) → unity import (Assets/Imported/araba.fbx) → unity run
  (C#: yeni sahne, prefabı yerleştir, Assets/Araba.unity kaydet; 6 parça) → hepsi çıkış 0. Deneme projesi silindi.
- Unity günlük süzgeci: yalnız "error CSxxxx", "...Exception:", "Error", "JARVIS:" satırları; lisans uyarısı ve
  "ValidationExceptions.json" gibi dosya adları hata sayılmıyor.
- Test: Blender kuruluysa model kur + kaydet + render + hatalı kodda NameError döner. Testler: 71.
Hâlâ kullanıcıda: GitHub Models / Cerebras / Mistral / SambaNova / NVIDIA anahtarları (.env), Linux makineleri, izinler.
