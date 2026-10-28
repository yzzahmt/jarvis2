# 011 — Donma düzeltmesi, yeni arayüz, CachyOS → Zorin OS
**Donma (kullanıcı: "aşırı donuyor")** — teşhis: Python süreci pencere kapandıktan sonra `Py_FinalizeEx` →
`wait_for_thread_shutdown`'da asılı (tarayıcı işçisi vb. daemon olmayan iş parçacıkları); qwen3:8b 5,9 GB RAM'de,
boş bellek ~90 MB; Gemini anahtarı yok → her komut yerel 8B'ye (bir istek 1 dk 24 sn).
- `ui/app.py`: `webview.start` dönünce `os._exit(0)`.
- Yönlendirme önce bulut beyinle (`Brains.json`, `OpenAICompat.json` response_format json_object), olmazsa yerel.
- Yerel yedek qwen3:8b → **qwen3:4b** (2,5 GB), keep_alive 30m → 10m (settings + env.sh).
**Arayüz** (`ui/web/index.html`, `ui/app.py`):
- Ayarlar paneli (dişli): ses seçimi + dinle (Ava/Andrew/Emma/Brian/Emel; settings.yaml'a yazar, anında geçer),
  beyin durumu (anahtar yok / kota / kullanılıyor), **Gemini anahtarını yapıştırıp kaydetme** (.env + canlı yeniden kurulum + deneme).
- "Gemini anahtarı yok" şeridi, tıklanabilir örnek komutlar, kırmızı "ÖDEME ONAYI" kartı ("Onayla ve öde").
- Hata: herhangi bir tuş odağı ana kutuya çekiyordu (anahtar alanını bozardı) → yalnız INPUT dışındayken.
- Mock API ile ekran görüntüsü alındı, JS hatası yok.
**Zorin OS** (eski CachyOS makinesi): anahtar `zorin`, ad "Zorin OS", takma adlar zorin/zorin os/sorin/teknik; STT düzeltmesi
"sorin o es" → Zorin OS. `linux_agent_setup.sh` yalnız apt (Zorin/Mint): python3-tk, pytest, Node 22 LTS ~/.local/node
(Ubuntu'daki Node, Gemini CLI için eski), gemini-cli. Mac IP 192.168.1.31 → 192.168.1.23 olmuştu: betik `MAC_IP` alıyor,
yeni `scripts/serve_setup.sh` IP'yi bulup Linux'ta çalıştırılacak satırı yazıyor. `docs/ZORIN_SETUP.md` (CACHYOS_SETUP yerine).
SSH komutlarında PATH'e ~/.local/node/bin eklendi. Testler: 49 geçti.
