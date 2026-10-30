# 035 — Kendi sesine cevap, söz kesme, yarıda kesme (30.10.2026)

Günlük (19:02-19:13): Jarvis konuşurken kendi sesiyle "SÖZÜM KESİLDİ" oldu, görev durdu, yankıyı "Kalite" diye
duyup cevap verdi; kullanıcının cümlesi düşünürken verdiği arada kesildi ("…yani gerçek").
Sebep: yankı oranı (echo_gain 0,06) mikrofon %33'te ölçülmüştü; giriş seviyesi 80'e çıkınca yankı eşiği aştı.
- _watch: her konuşmanın ilk 0,8 sn'si yalnız yankı oranını ölçer; kesmek için ~0,55 sn kesintisiz ses (7 kare).
- heard_self: 1-2 kelimelik metin, Jarvis'in az önce söylediği kelimelerin başıysa atılır.
- Bitiş sessizliği 1,0 → 1,8 sn (settings voice.end_silence); cümle "ama/yani/gibi/ve/…" ya da virgülle bitiyorsa
  dinlemeye devam edilir ve metinler birleştirilir (en çok 3 kez).
73 test.
