# 015 — Ses tanıma: uydurma cümle ve yabancı kelimeler
Kullanıcı: "Türkçe'yi yanlış anlıyor, içinde yabancı kelime geçince anlamıyor", "durduk yere 'Zorin OS için
bağlantı ayarı yok' diyor".

Sebep (app.log'dan):
- İpucunda örnek CÜMLELER vardı ("Jarvis, testleri çalıştır. Sesi otuz yap…"). Konuşma yok/gürültü olunca Gemini bu
  cümleyi aynen döndürüyordu → "testleri çalıştır" → Zorin'de test → "bağlantı ayarı yok". Kayıtta 6 kez.
- "Geçebilecek adlar: OBİS" ipucu, "API"yi "OBİS" diye duyurdu.

Yapılanlar (`voice/speech_to_text.py`):
- İpucu yalnız ad listesi (NAMES + settings voice.words); örnek cümle yok. Whisper yedeği de aynı listeyi kullanır.
- Yeni talimat (systemInstruction): Türkçe + İngilizce karışık; yabancı kelime özgün yazımla, ek kesme işaretiyle
  (API'sini, key'ini); çevirme/düzeltme yok; konuşma yoksa boş; adlar yalnız açıkça duyulursa.
- Sessiz kayıt (en yüksek 30 ms RMS < 0,005) modele hiç gönderilmez (boşta ad listesinden cümle uyduruyordu).
- `clean()`: model talimatı/listeyi geri yazarsa boş sayılır.
- Kota/ağ hatasında 2. anahtar (GEMINI_API_KEY_2) denenir; 2,3 GB'lık yerel whisper ancak sonra.

Ölçüm (Edge Emel ile 10 karışık cümle + gürültü + sessizlik, gemini-3.5-flash-lite):
- Eski: gürültüde uydurma Zorin cümlesi; "iyzico … sandbox secret key" → "İzi Jo panelinden soundboard seç red kiale V".
- Yeni: gürültü/sessizlik boş; API, .env, key'ini, screenshot'ları, OBİS, sandbox doğru. ~1,3 sn.
- gemini-3.5-flash biraz daha iyi ama ücretsiz kotası 6 istekte doldu (429) → lite kaldı.
Testler: 53 geçti.
