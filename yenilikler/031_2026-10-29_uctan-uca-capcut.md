# 031 — Uçtan uca CapCut denemesi ve düzeltmeler

Gerçek deneme (metin): "CapCut'ı aç ve ana ekranında hangi düğmeler var, kısaca söyle".
İlk: 23,6 sn ve cevap "Tamam." / ikinci: 42,9 sn. Düzeltmelerden sonra: 13,2 sn, doğru ve doğal cevap.

- ui_read: odaktaki pencere boşsa diğer pencereler; AXManualAccessibility açılır (Electron/Chromium ağacı).
  CapCut (Chromium Embedded) ağacı zayıf → çoğu iş look_screen/click_on ile; bu beklenen yedek yol.
- open_app: pencere gelene kadar bekler (≤15 sn) ve öne getirir (önceden açılırken okuyup boş dönüyordu).
- Ajan sessiz bitirirse ("Tamam.") bir kez daha "sonucu söyle" ister.
- gemini-3.5-flash ücretsiz sınırı DAKİKADA 5 istek (proje+model başına). 429'da 10 dk değil Gemini'nin retryDelay'i
  kadar (~40 sn) beklenir (llm.py gövdeden okur). Görme hızlı modelde kalır (aynı kutu, 3 sn) → güçlü kota akıl
  yürütmeye.
Testler: 70.
