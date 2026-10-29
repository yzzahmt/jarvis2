# 028 — Aşama 4: Uygulamaların kendi yolu — video (ffmpeg) ve Blender

## video aracı (jarvis/agent/media.py)
ffmpeg: venv'e imageio-ffmpeg (arm64 ikili, HDD'de; brew yok). İşlemler: info, overlay (resim/video, x,y merkez oranı
0-1, width oranı, start-end), text (Türkçe yazı, Arial Unicode), cut (aralığı tutar), remove (aralığı siler), concat
(farklı boyutları eşitler), audio (müzik ekle / değiştir, gecikme, ses düzeyi), speed, frame (karenin png'si), convert.
Asıl dosyaya asla yazmaz: yanına <ad>_jarvis-<iş>.mp4 (varsa -2, -3…). Hepsi test videosuyla denendi; overlay
pikselden doğrulanan testle korunuyor.

## pointer(inside=...)
"Gösterdiğim yere" → imlecin video önizlemesindeki oranı (x,y) → doğrudan video overlay'e verilir.

## look_image
Render, video karesi, indirilen resim: görsel modele sorar (sonucu kontrol için).

## blender aracı
Blender 5.2.3 (arm64) data/apps/Blender.app'e kurulacak (DMG indi: data/apps/indir/blender.dmg; bağlama adımına
otomatik ortamda izin verilmedi, kullanıcı tek komutla kuracak). Arka planda bpy betiği; file/save/render;
jarvis_render() otomatik kamera+ışık ile önizleme png'si → look_image ile bakılır. print('JARVIS: ...') çıktısı döner.

## Talimat
Kesin video işleri video aracıyla, CapCut'a özgü işler CapCut'ta. 3B: blender'da parça parça kur + render'a bak;
gerçekçi model → hazır ücretsiz model + Blender'da kullanıcının istediği değişiklikler → FBX/GLB → unity import.
Testler: 66.
