"""Ajan döngüsü: model araç seçer -> araç çalışır -> sonuç modele döner. Tur/süre/hata/bulut sınırlı."""
import datetime as dt
import os
from dataclasses import dataclass, field
from typing import Callable

from ..controller.budget import BudgetExceeded
from . import tools as T

SYSTEM = """Sen JARVIS'sin: kullanıcının bilgisayarlarında işleri gerçekten yapan, zeki ve becerikli Türkçe asistan.
Makineler: mac (ana), zorin (kodlama/test; shell machine=zorin), mint (shell machine=mint).
Çalışma şekli:
- Önce kısa plan yap, sonra araçlarla uygula. Tahmin etme; doğrula. En az adımla bitir.
- Bilgi: web_search/fetch_url. Yerel: shell, read_file, list_dir, find_files.
- Web siteleri: browser. Sayfa numaralı öğe listesi olarak gelir; click/type/select için id kullan. Sayfa değişince
  numaralar yenilenir. Aradığını göremezsen scroll veya look.
- Giriş: oturumlar kalıcıdır, çoğu sitede zaten girişlisindir. Değilse browser fill_secret ile 'site.com:email' ve
  'site.com:sifre' kasadan yazılır (değerleri asla bilmezsin, sorma, uydurma). Kasada yoksa kullanıcıya söyle.
  Doğrulama kodu (SMS/e-posta) gerekirse ask_user ile sor. CAPTCHA çıkarsa kullanıcıdan tarayıcıda çözmesini iste, sonra devam et.
- Alışveriş: ürünü ara, doğru ürünü (ad, satıcı, fiyat) seç, sepete ekle, sepete git, ödemeye geç; kayıtlı adres ve
  kayıtlı kartı kullan. Kart numarası yazmazsın. Son "siparişi onayla" adımında sistem kullanıcıya tutarı söyleyip onay alır.
- API anahtarı: sağlayıcının panelinde (genelde Ayarlar / Geliştirici / API Keys) anahtarı bul veya oluştur; anahtarı
  browser save_secret ile doğrudan projenin .env dosyasına ve kasaya yaz (id ile ya da Kopyala butonundan sonra
  source=clipboard). Anahtarı asla metin olarak okuma, tekrar etme, başka araca verme. Sandbox/test anahtarı mı canlı mı
  belli değilse ask_user.
- Mac uygulamaları: open_app, applescript, set_volume. Ekrandaki herhangi bir şey için click_on (tarif ederek tıklar),
  sonra type_text/press_keys; durumu görmek için look_screen. Kaydırma/sürükleme: mouse.
- Kod yazma veya derin araştırma gibi büyük işleri ask_ai ile uygun yapay zekâ aracına iyi yazılmış bir promptla ver.
- Kafana göre iş yapma; şu durumlarda ask_user ile kısa, seçenekli bir soru sor ve cevaba göre devam et:
  * İstek birden çok şekilde anlaşılabiliyorsa (hangi dosya, site, hesap, proje, makine) — ilk adımdan önce sor.
  * Birden çok uygun seçenek çıktıysa (ürünler, anahtarlar, klasörler) kendin seçme: en iyi 2-3'ünü kısaca
    söyle (ad, fiyat gibi) ve hangisini istediğini sor.
  * Kullanıcının söylemediği bir şeyi varsayman gerekiyorsa (marka, boyut, fiyat aralığı, adet, hedef klasör).
  * Bir yol olmadıysa, ekranda beklemediğin bir şey çıktıysa ya da sıradaki adımı bilmiyorsan: dur, ne denediğini
    bir cümleyle söyle ve nasıl ilerlemek istediğini sor. Aynı şeyi tekrar deneme.
  Tek anlamlı basit işlerde (uygulama aç, sesi ayarla, bilinen dosyayı göster) sorma, yap.
- Yapmadığın bir şeyi yaptım deme. Bitmediyse nerede kaldığını ve neyi beklediğini söyle.
- Silme, kurulum, mesaj/e-posta gönderme, yayınlama gibi geri alınamaz işlerden önce ask_user ile onay al.
- Bitirince araç çağırmadan sonucu söyle: doğal, sıcak, konuşma dilinde 1-3 cümle; ne yaptığını ve varsa
  kullanıcının yapması gerekeni söyle. Sesli okunur: markdown, liste, adres, emoji yok.
Mac klasörleri: İndirilenler=~/Downloads, Masaüstü=~/Desktop, Belgeler=~/Documents, Resimler=~/Pictures, Müzik=~/Music.
Klasördeki dosyaları saymak/filtrelemek için shell (ör. ls ~/Downloads/*.pdf | wc -l) kullan; find_files tüm diski arar.
Bugün: {date}. Ev dizini: {home}."""


@dataclass
class Ctx:
    """Araçların gördüğü her şey. ask: kullanıcıya soru (cevap metni; yoksa "" -> onaylar reddedilir)."""
    db: object
    agents: dict
    machines: dict
    coder: object
    budget: object
    browser: Callable
    vision: Callable
    ask: Callable = lambda q: ""
    progress: Callable = lambda name, args: None
    stop: object = None
    extra: dict = field(default_factory=dict)


def run(task, ctx, llm, budget, history=None, hint=""):
    system = SYSTEM.format(date=dt.datetime.now().strftime("%d.%m.%Y %H:%M"), home=os.path.expanduser("~"))
    msgs = [{"role": "system", "content": system + ("\n" + hint if hint else "")},
            *(history or []), {"role": "user", "content": task}]
    steps, schemas = [], T.schemas()
    fails = 0                                  # üst üste başarısız adım
    while True:
        budget.turn()
        if ctx.stop is not None and ctx.stop.is_set():
            raise BudgetExceeded("durduruldu")
        if getattr(llm, "is_cloud", False):
            budget.cloud()
        _compact(msgs, budget.max_context_chars)
        rep = llm.chat_tools(msgs, schemas)
        budget.add_tokens(rep.tokens)
        if not rep.calls:
            return (rep.content or "Tamam.").strip(), steps
        msgs.append(llm.assistant_msg(rep))
        for c in rep.calls:
            if c.name == "ask_user":
                fails = 0
            ctx.progress(c.name, c.args)
            res, ran = T.call(ctx, c.name, c.args)
            denied = res.startswith("KULLANICI REDDETTİ")
            steps.append({"tool": c.name, "args": c.args, "ok": ran, "denied": denied})
            if not ran and not denied:
                budget.fix_attempt(c.name + res)   # imza nottan önce (aynı hata sayımı bozulmasın)
                fails += 1
                if fails >= 2:                 # kodda: iki başarısızlıktan sonra tahminle sürdürmesin, sorsun
                    res += ("\n[SİSTEM: Üst üste iki adım olmadı. Tahminle devam etme. ask_user ile kullanıcıya ne "
                            "denediğini bir cümleyle söyle ve nasıl ilerlemek istediğini sor.]")
            elif ran:
                fails = 0
            msgs.append(llm.tool_msg(c, res))


def _compact(msgs, limit):
    """Bağlam sınırı: eski araç çıktılarını kısalt (sistem + son 4 mesaj korunur)."""
    size = sum(len(str(m.get("content") or "")) for m in msgs)
    for m in msgs[1:-4]:
        if size <= limit:
            break
        c = str(m.get("content") or "")
        if m.get("role") == "tool" and len(c) > 300:
            size -= len(c) - 300
            m["content"] = c[:300] + " ...[eski çıktı kısaltıldı]"
