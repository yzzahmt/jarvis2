# 034 — Görünür çalışma, mikrofon kapatma, HUD arayüz (30.10.2026)

Kullanıcı: "görevi arka planda değil, klavye-mouse'u eline alarak yapsın, ben de anlık göreyim"; "mikrofonu kapatma
tuşu olsun"; "daha şık, futuristik arayüz".

- Ajan talimatı: GÖRÜNÜR ÇALIŞ. Uygulama işleri uygulamanın kendi arayüzünde klavye/fareyle; arka plan araçları
  (blender bpy, unity batch, video ffmpeg) yalnız kullanıcı "arka planda" derse ya da arayüzde 2 denemede olmazsa.
  Blender kısayol rehberi talimatta (shift+a ara, s/g/r + eksen + sayı, tab, e, ctrl+r, ctrl+b, f3, konsol).
- Yeni araç blender_ui (media.py): open (HDD Blender'ını ekranda açar, pencereyi ekrana yayar) | viewport (fareyi
  3B görünüme götürür; kısayollar fare altındaki alana gider) | console (Scripting > Python Konsolu) | layout.
- press_keys boşlukla ayrılmış diziler basar ('s x 2 enter'); f1-f12, home/end/pageup eklendi; "cmd + s" düzelir.
- Fare artık ışınlanmaz: _glide ile görünür kayar (click, click_on, drag_on, mouse).
- Ekran aracı kullanılınca ana pencere alt çubuğa iner (App.SCREEN_TOOLS), adımlar çubukta canlı yazılır.
- Mikrofon kapatma: ana pencerede ve alt çubukta düğme (App.mute → Mic.toggle). Kapalıyken uyandırma/alkış da
  dinlenmez; konuş düğmesine basmak mikrofonu açar.
- Arayüz: koyu HUD teması (ızgara, tarama çizgisi, köşe çerçeveleri, ark reaktörü küre, mono yazı), çubuk da aynı.
- 72 test.
