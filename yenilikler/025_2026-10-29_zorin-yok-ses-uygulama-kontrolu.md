# 025 — "Zorin bağlantısı yok" bitti, ses düzeltmeleri, her uygulamayı kullanma

Kullanıcı şikâyeti: yavaş; sesi yanlış/eksik anlıyor; konuşurken söze girince sözünü siliyor; Unity'de araba modeli
istedi → iki kez "Zorin OS için bağlantı ayarı yok" dedi; uzun konuşmaları anlamıyor; CapCut gibi uygulamalarda kurgu
yapabilmeli; "bu ana, gösterdiğim yere koy" gibi işaretli istekleri anlamalı.

## Makine yönlendirmesi
- Bağlı olmayan makineden (Zorin/Mint) artık hiç söz edilmez: kullanıcı makine adı söylemediyse iş sessizce Mac'te yapılır.
- Kullanıcı adını söylediyse ve bağlı değil/çevrimdışıysa: "Zorin OS henüz bağlı değil. Bu işi Mac'te yapmamı ister
  misin?" diye SORAR (evet → Mac, hayır → yapmaz).
- Mac'te gemini/aider yok → kod/test işleri genel ajana gider (kendisi yazar).
- Yönlendirici: machine varsayılan mac; uygulama kullanmak (Unity, Blender…) "agent", "code" değil.
- Ajan talimatında yalnız bağlı makineler listelenir. shell/ask_ai bağlı olmayan makinede Mac'e düşer.
- Mac proje klasörü: /Volumes/HDD/Projeler/Projeler (machines.yaml).

## Ses
- Mac ikinci kulağı BOŞ döndüğünde artık veto yok (günlükte "Naber, nasılsın?", "Spotify'ı aç" bu yüzden atılıyordu).
  Veto yalnız Mac bir şey duyup tamamen farklıysa. Asıl uydurma koruması Silero VAD.
- Mac tanıması bulut cevabından sonra en çok 1,5 sn beklenir (önce 4 sn) → daha hızlı.
- Kayıt üst sınırı 20 sn → 120 sn (uzun konuşmalar yarıda kesiliyordu); bulut tanıma zaman aşımı ses uzunluğuyla büyür.
- Bitiş sessizliği 1,2 → 1,0 sn.
- Söze girme: kaydın başındaki Jarvis yankısı kelime kelime atılır, kullanıcının sözü kalır (strip_self).
  "Kendi sesi" sayma eşiği sıkılaştı (en az 2 kelime, %80).
- Onay sorusunda kendi sesini cevap sanıp isteği iptal etmesin: yankı ise yok sayılır, tekrar dinler.
- Konuşma bitince hoparlör tamponu için 0,4 sn bekleyip mikrofonu boşaltır (0,2 kısaydı).
- "Sizi dinliyorum" kesilemez (kendi sesiyle "sözüm kesildi" olup yankıyı komut sanıyordu); diğer cevaplar söze girince susar.
- Günlükte her komutun süresi: "süre: anlama X sn (kaynak), cevap Y sn" → yavaşlık nereden, görülür.
- Bulut beyin zaman aşımı 60 → 25 sn (takılan sağlayıcıda bekleme yerine sıradakine geçer).

## Uygulama kontrolü
- Yeni araçlar: drag_on (tarif edilen öğeyi tarif edilen yere/kaydırmayla sürükler), find_on_screen (yer + kutu,
  tıklamadan), pointer (fare imlecinin yeri — konuşma bittiği andaki konum — ve altında ne olduğu).
- unity aracı: create (batch ile yeni proje), import (dosya/zip/klasör → Assets/Imported), run (JarvisRun.Run C# editör
  betiği; onay ister), open. Unity 6000.6.7f1 bulunuyor.
- Talimat: her uygulamayı kullanır, "yapamam" demez; arayüzü tanı → küçük adımlar → her adımda doğrula; kullanıcının
  her ayrıntısını ayrı adım yapar; CapCut kurgu akışı; gerçekçi 3B model fareyle çizilmez, ücretsiz hazır model bulunur
  ve seçenekler sorulur. "Buraya/gösterdiğim yere" = imleç, "bu ana" = oynatma çizgisi.
- Sınırlar: ajan turu 25 → 80, görev süresi 900 → 2400 sn, görev başı bulut 40 → 120, günlük bulut 300 → 600.

Testler: 61 geçiyor.
