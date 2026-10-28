"""Ajan araçları. Her araç: ad, açıklama, parametre şeması, risk.
risk: "safe" (sormadan), "confirm" (kullanıcı onayı), veya args'a göre karar veren fonksiyon."""
import html
import json
import os
import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx

from .. import config

MAX_OUT = 2500
TOOLS: dict[str, "Tool"] = {}


@dataclass
class Tool:
    name: str
    desc: str
    params: dict
    fn: Callable
    risk: object = "safe"   # "safe" | "confirm" | callable(args)->bool(onay gerekir)
    info: bool = True       # sonuç bilgi mi (tekrar oynatmada özetlenir)

    def schema(self):
        req = [k for k, v in self.params.items() if not v.get("optional")]
        props = {k: {kk: vv for kk, vv in v.items() if kk != "optional"} for k, v in self.params.items()}
        return {"type": "function", "function": {"name": self.name, "description": self.desc,
                "parameters": {"type": "object", "properties": props, "required": req}}}

    def needs_confirm(self, args) -> bool:
        return self.risk(args) if callable(self.risk) else self.risk == "confirm"


def tool(tool_name, desc, risk="safe", info=True, **params):
    def deco(fn):
        TOOLS[tool_name] = Tool(tool_name, desc, params, fn, risk, info)
        return fn
    return deco


S = lambda d, **k: {"type": "string", "description": d, **k}  # noqa: E731
I = lambda d, **k: {"type": "integer", "description": d, **k}  # noqa: E731


def clip(s: str, n=MAX_OUT) -> str:
    s = s.strip()
    return s if len(s) <= n else s[: n // 2] + "\n...[kısaltıldı]...\n" + s[-n // 2:]


# ---------------- kabuk ----------------
SAFE_CMD = re.compile(
    r"^\s*(ls|pwd|cat|head|tail|wc|df|du|ps|top -l 1|uptime|whoami|which|date|cal|echo|find|grep|rg|mdfind|"
    r"sw_vers|uname|system_profiler|pmset -g|ioreg|networksetup -get|ifconfig|ipconfig getifaddr|ping -c|"
    r"defaults read|git (status|log|diff|branch|show)|python3? --version|node -v|ollama list|brew list|"
    r"pgrep|lsof -i|osascript -e 'output volume|stat|file|tree|nproc|free|lsblk|ip a|hostnamectl|ss -)\b")
DANGER = re.compile(r"(rm\s+-rf?\s+[/~]\s*$|mkfs|dd\s+if=|:\(\)\{|>\s*/dev/sd|chmod\s+-R\s+777\s+/|curl[^|]*\|\s*(ba)?sh)")


SAFE_PIPE = re.compile(r"^\s*(wc|sort|uniq|head|tail|grep|cut|tr|awk '[^']*'|sed -n)\b")


def shell_risk(a) -> bool:
    """Onay gerekir mi: yalnızca bilinen okuma komutları ve aralarındaki | borusu onaysızdır."""
    cmd = a.get("command", "").replace("2>&1", "").replace("2>/dev/null", "")
    if re.search(r"[;&`$]|>\s*\S|\(", cmd):
        return True
    first, *rest = cmd.split("|")
    return not SAFE_CMD.match(first) or not all(SAFE_PIPE.match(p) for p in rest)


@tool("shell", "Bir bilgisayarda kabuk komutu çalıştırır (macOS: zsh/bash, Linux: bash). Çıktıyı döndürür.",
      risk=shell_risk, command=S("komut"), machine=S("mac|cachyos|mint (varsayılan mac)", optional=True))
def t_shell(ctx, command, machine="mac"):
    if DANGER.search(command):
        return "REDDEDİLDİ: tehlikeli komut"
    a = ctx.agents.get(machine)
    if not a or not a.configured:
        return f"{machine} bağlı değil"
    if not a.online():
        return f"{machine} çevrimdışı"
    r = a.run(command, timeout=120, stop=ctx.stop)
    return clip(f"[çıkış {r.code}]\n{r.out}\n{r.err}")


# ---------------- dosyalar ----------------
def _p(path):
    return Path(os.path.expanduser(path)).resolve()


@tool("list_dir", "Klasör içeriğini listeler.", path=S("klasör yolu"))
def t_ls(ctx, path):
    p = _p(path)
    if not p.is_dir():
        return "klasör yok"
    items = sorted((x for x in p.iterdir() if not x.name.startswith(".")), key=lambda x: (not x.is_dir(), x.name.lower()))
    if not items:
        return "klasör boş (0 öğe)"
    head = f"toplam {len(items)} öğe ({sum(x.is_dir() for x in items)} klasör)\n"
    return clip(head + "\n".join(("📁 " if x.is_dir() else "") + x.name for x in items[:200]))


@tool("read_file", "Metin dosyası okur (ilk kısmı).", path=S("dosya yolu"))
def t_read(ctx, path):
    p = _p(path)
    if not p.is_file():
        return "dosya yok"
    return clip(p.read_text(errors="replace")[:20000])


def write_risk(a):
    p = _p(a.get("path", ""))
    return p.exists() or not any(str(p).startswith(str(_p(d))) for d in ctx_allowed())


def ctx_allowed():
    return config.load("settings").get("permissions", {}).get("allowed_dirs", [])


@tool("write_file", "Dosyaya metin yazar (yeni dosya; var olanın üzerine yazmak onay ister).", risk=write_risk, info=False,
      path=S("dosya yolu"), content=S("içerik"))
def t_write(ctx, path, content):
    p = _p(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"yazıldı: {p} ({len(content)} karakter)"


@tool("find_files", "Mac'te Spotlight ile dosya/klasör arar (ada göre). Toplam sayıyı da verir.",
      name=S("aranan ad parçası"), folder=S("yalnızca bu klasörde ara, ör. ~/Downloads", optional=True))
def t_find(ctx, name, folder=""):
    cmd = ["mdfind", "-name", name] + (["-onlyin", str(_p(folder))] if folder else [])
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    lines = [l for l in r.stdout.splitlines() if "/Library/" not in l]
    return clip(f"toplam {len(lines)} sonuç\n" + "\n".join(lines[:30])) if lines else "bulunamadı"


# ---------------- uygulamalar / macOS ----------------
@tool("open_app", "Mac'te uygulama açar.", info=False, app=S("uygulama adı (ör. Safari, Notes, Music)"))
def t_open_app(ctx, app):
    r = subprocess.run(["open", "-a", app], capture_output=True, text=True)
    return "açıldı" if r.returncode == 0 else f"açılamadı: {r.stderr.strip()}"


@tool("open_url", "Varsayılan tarayıcıda adres açar (Mac).", info=False, url=S("http(s) adresi"))
def t_open_url(ctx, url):
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    subprocess.run(["open", url])
    return "açıldı"


SAFE_AS = re.compile(r"^\s*(tell application \"[\w ]+\" to (activate|quit|play|pause|playpause|next track|previous track|"
                     r"get name of current track)|set volume output volume \d+|output volume of \(get volume settings\)|"
                     r"display notification )", re.I)


@tool("applescript", "macOS'ta AppleScript çalıştırır (uygulama kontrolü: Müzik, Finder, Takvim, Hatırlatıcılar, Notlar, ses vb.).",
      risk=lambda a: not SAFE_AS.match(a.get("script", "")), script=S("AppleScript kodu"))
def t_as(ctx, script):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=30)
    return clip(r.stdout or r.stderr or "tamam")


@tool("set_volume", "Mac ses seviyesini ayarlar.", info=False, level=I("0-100"))
def t_vol(ctx, level):
    subprocess.run(["osascript", "-e", f"set volume output volume {max(0, min(100, int(level)))}"])
    return f"ses {level}"


@tool("look_screen", "Mac ekranının görüntüsünü alır ve görsel modele soru sorar (ekranda ne var, buton nerede).",
      question=S("ekranla ilgili soru"))
def t_look(ctx, question):
    f = config.path("data/tmp/screen.png")
    subprocess.run(["screencapture", "-x", "-t", "png", str(f)], timeout=10)
    if not f.exists():
        return "ekran görüntüsü alınamadı (Ekran Kaydı izni gerekli)"
    subprocess.run(["sips", "-Z", "1280", str(f)], capture_output=True)
    try:
        return clip(ctx.vision(question, f))
    finally:
        f.unlink(missing_ok=True)


# ---------------- klavye / fare ----------------
def _kb():
    from pynput.keyboard import Controller, Key
    return Controller(), Key


@tool("type_text", "Etkin pencereye klavyeyle metin yazar.", info=False, text=S("yazılacak metin"))
def t_type(ctx, text):
    kb, _ = _kb()
    kb.type(text)
    return "yazıldı"


@tool("press_keys", "Tuş kombinasyonu basar, ör. 'cmd+space', 'enter', 'cmd+shift+n'.", info=False, keys=S("tuşlar"))
def t_keys(ctx, keys):
    kb, Key = _kb()
    names = {"cmd": Key.cmd, "ctrl": Key.ctrl, "alt": Key.alt, "option": Key.alt, "shift": Key.shift,
             "enter": Key.enter, "return": Key.enter, "tab": Key.tab, "esc": Key.esc, "space": Key.space,
             "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right, "backspace": Key.backspace,
             "delete": Key.delete}
    seq = [names.get(k.strip().lower(), k.strip()) for k in keys.split("+")]
    for k in seq:
        kb.press(k)
    for k in reversed(seq):
        kb.release(k)
    time.sleep(0.3)
    return "basıldı"


def _mouse_click(x, y, button="left", count=1):
    from pynput.mouse import Button, Controller
    m = Controller()
    m.position = (int(x), int(y))
    time.sleep(0.05)
    m.click({"right": Button.right}.get(button, Button.left), 2 if count == 2 or button == "double" else 1)


@tool("click", "Ekranda koordinata tıklar (nokta cinsinden). Genelde click_on daha güvenilirdir.", info=False,
      x=I("x"), y=I("y"), button=S("left|right|double", optional=True))
def t_click(ctx, x, y, button="left"):
    _mouse_click(x, y, button)
    return "tıklandı"


def _screen_size():
    r = subprocess.run(["osascript", "-e", 'tell application "Finder" to get bounds of window of desktop'],
                       capture_output=True, text=True, timeout=10)
    nums = [int(n) for n in re.findall(r"-?\d+", r.stdout)]
    return (nums[2], nums[3]) if len(nums) == 4 else (1512, 982)


BOX_Q = ('Bu ekran görüntüsünde şu öğeyi bul: "{t}". YALNIZCA JSON döndür: {{"box_2d": [ymin, xmin, ymax, xmax]}} '
         '(0-1000 arası normalize). Öğe yoksa {{"box_2d": null, "neden": "kısa açıklama"}}.')


@tool("click_on", "Mac ekranında TARİF EDİLEN öğeyi görerek bulur ve tıklar (herhangi bir uygulamada: buton, simge, menü, "
      "metin kutusu). Ör. target='Finder kenar çubuğunda İndirilenler', 'Spotify'da oynat butonu'. "
      "Tarayıcı sayfalarında browser aracını tercih et.", info=False,
      target=S("öğenin açık tarifi"), button=S("left|right|double", optional=True))
def t_click_on(ctx, target, button="left"):
    f = config.path("data/tmp/screen.png")
    f.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["screencapture", "-x", "-m", "-t", "png", str(f)], timeout=10)   # -m: ana ekran
    if not f.exists():
        return "ekran görüntüsü alınamadı (Sistem Ayarları > Gizlilik > Ekran Kaydı izni gerekli)"
    subprocess.run(["sips", "-Z", "1600", str(f)], capture_output=True)
    try:
        out = ctx.vision(BOX_Q.format(t=target), f)
    finally:
        f.unlink(missing_ok=True)
    m = re.search(r"\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]", out or "")
    if not m:
        return f"bulunamadı: {clip(out or 'görsel model yanıt vermedi', 200)}"
    y0, x0, y1, x1 = (int(v) for v in m.groups())
    w, h = _screen_size()
    x, y = (x0 + x1) / 2000 * w, (y0 + y1) / 2000 * h
    _mouse_click(x, y, button)
    time.sleep(0.4)
    return f"'{target}' tıklandı ({int(x)},{int(y)}). Sonucu doğrulamak için gerekirse look_screen."


@tool("mouse", "Fare: scroll (amount: + aşağı, - yukarı), move(x,y), drag(x,y → to_x,to_y).", info=False,
      action=S("scroll|move|drag"), amount=I("kaydırma adımı", optional=True), x=I("x", optional=True),
      y=I("y", optional=True), to_x=I("hedef x", optional=True), to_y=I("hedef y", optional=True))
def t_mouse(ctx, action, amount=5, x=None, y=None, to_x=None, to_y=None):
    from pynput.mouse import Button, Controller
    m = Controller()
    if x is not None and y is not None:
        m.position = (int(x), int(y))
    if action == "scroll":
        m.scroll(0, -int(amount))
    elif action == "drag" and to_x is not None and to_y is not None:
        m.press(Button.left)
        for i in range(1, 11):
            sx, sy = m.position
            m.position = (sx + (int(to_x) - sx) / (11 - i), sy + (int(to_y) - sy) / (11 - i))
            time.sleep(0.03)
        m.release(Button.left)
    return "tamam"


# ---------------- web ----------------
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/130 Safari/537.36"}


@tool("web_search", "İnternette arama yapar (DuckDuckGo, ücretsiz). Başlık, adres ve özet döndürür.", query=S("arama"))
def t_search(ctx, query):
    r = httpx.post("https://html.duckduckgo.com/html/", data={"q": query, "kl": "tr-tr"}, headers=UA, timeout=20)
    out = []
    for m in re.finditer(r'class="result__a" href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</', r.text, re.S):
        url, title, snip = m.groups()
        if "uddg=" in url:
            url = httpx.URL(html.unescape(url)).params.get("uddg", url)
        clean = lambda s: html.unescape(re.sub("<.*?>", "", s)).strip()  # noqa: E731
        out.append(f"- {clean(title)} | {url}\n  {clean(snip)}")
        if len(out) >= 6:
            break
    return clip("\n".join(out) or "sonuç yok")


@tool("fetch_url", "Bir web sayfasının metnini getirir.", url=S("adres"))
def t_fetch(ctx, url):
    r = httpx.get(url, headers=UA, timeout=20, follow_redirects=True)
    t = re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", r.text)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return clip(re.sub(r"\s+", " ", t), 4000)


# ---------------- tarayıcı (görünür, oturum korunur) ----------------
CARD = re.compile(r"(kart|card|cvv|cvc|iban)", re.I)
GO_ON = re.compile(r"(onayla|tamamla|devam|gönder|ilerle|continue|confirm|submit|next)", re.I)


def _env_risk(a):
    f = a.get("env_file")
    return bool(f) and not any(str(_p(f)).startswith(str(_p(d))) for d in ctx_allowed())


def _browser_guard(ctx, action, a) -> str | None:
    """Ödeme / hesap açma / kart bilgisi KODDA denetlenir (model atlayamaz). Onay yoksa ret metni döner."""
    from ..automation.session import ACCOUNT, PAY
    s = ctx.browser()
    q = None
    if action in ("type", "fill") and CARD.search(f"{a.get('label', '')} {s.label(a.get('id'))}"):
        return "REDDEDİLDİ: kart bilgisini Jarvis yazmaz. Sitedeki kayıtlı kartı seç ya da kullanıcı kendisi girsin."
    if action in ("click", "press") or (action in ("type", "fill") and a.get("key")):
        lbl = s.label(a.get("id"), a.get("text")) if action == "click" else a.get("key", "Enter")
        checkout, money = s.checkout_info()
        if PAY.search(lbl) or (checkout and (action != "click" or GO_ON.search(lbl))):
            q = f"Ödeme adımı: '{lbl[:40]}'" + (f". Sayfadaki tutarlar: {money}" if money else "") + ". Onaylıyor musun?"
        elif action == "click" and ACCOUNT.search(lbl):
            q = f"Yeni hesap oluşturulacak ('{lbl[:40]}'). Onaylıyor musun?"
    if q and not re.match(r"^\s*(evet|e|onay|onaylıyorum|tamam|olur|yap|yes|y)\b", (ctx.ask(q) or "").lower()):
        return "KULLANICI REDDETTİ — bu adımı yapma; kullanıcıya durumu söyle."
    return None


@tool("browser", "Görünür tarayıcı (oturumlar kalıcı). Sayfa numaralı öğe listesi olarak gelir; öğeyi id ile kullan. "
      "action: goto(url) | look (öğeleri yenile) | read (uzun metin) | click(id veya text) | type(id,text[,key=Enter]) | "
      "select(id,option) | scroll(direction=up|down) | back | tabs([index]) | wait(text=saniye) | press(key) | "
      "fill_secret(id,secret): kasadaki şifre/e-postayı alana yazar, değeri görmezsin, ad biçimi 'site.com:email', 'site.com:sifre' | "
      "save_secret(id veya source=clipboard, secret ve/veya env_file+var): API anahtarını sayfadan/panodan alıp kasaya ve/veya "
      "projenin .env dosyasına doğrudan yazar | youtube(query). Ödeme ve hesap açma adımlarında sistem kullanıcıya kendisi sorar.",
      risk=_env_risk, info=True,
      action=S("goto|look|read|click|type|select|scroll|back|tabs|wait|press|fill_secret|save_secret|youtube"),
      url=S("adres", optional=True), id=I("öğe numarası", optional=True),
      text=S("yazılacak metin / tıklanacak görünen metin", optional=True), label=S("alan etiketi (id yoksa)", optional=True),
      key=S("tuş, ör. Enter", optional=True), option=S("seçenek metni", optional=True),
      direction=S("up|down", optional=True), index=I("sekme sırası", optional=True),
      secret=S("kasa adı, ör. trendyol.com:sifre veya iyzico:api_key", optional=True),
      source=S("save_secret için: clipboard (Kopyala butonundan sonra)", optional=True),
      env_file=S(".env dosya yolu, ör. ~/projeler/magaza/.env", optional=True),
      var=S("değişken adı, ör. IYZICO_API_KEY", optional=True), query=S("YouTube araması", optional=True))
def t_browser(ctx, action, **a):
    denied = _browser_guard(ctx, action, a)
    if denied:
        return denied
    try:
        return ctx.browser().do(action, **a)
    except LookupError as e:
        return str(e)


# ---------------- başka yapay zekâya devretme ----------------
AI_WEB = ("gemini", "chatgpt")


@tool("ask_ai", "Büyük işi başka bir yapay zekâ aracına verir. target: kod (CachyOS'ta Gemini CLI/aider proje klasöründe "
      "kod yazar/düzeltir) | gemini | chatgpt (tarayıcıdaki sohbet: araştırma, uzun yazı, fikir). "
      "Bağlamı içeren, net ve iyi yazılmış bir prompt ver.",
      risk=lambda a: a.get("target", "kod") not in AI_WEB, prompt=S("prompt"),
      target=S("kod|gemini|chatgpt (varsayılan kod)", optional=True),
      machine=S("kod için makine (varsayılan cachyos)", optional=True),
      workdir=S("kod için proje klasörü (proje dizini altında)", optional=True))
def t_ask_ai(ctx, prompt, target="kod", machine="cachyos", workdir=""):
    if target in AI_WEB:
        return clip(ctx.browser().do("ai_chat", timeout=200, site=target, text=prompt), 4000)
    a = ctx.agents.get(machine)
    if not a or not a.configured:
        return f"{machine} bağlı değil"
    if not a.online():
        return f"{machine} çevrimdışı"
    base = (ctx.machines.get(machine) or {}).get("project_dir", "~/projeler").rstrip("/")
    d = workdir.rstrip("/") or base
    if not d.startswith(("/", "~")):
        d = f"{base}/{d}"
    if ".." in d or not (d == base or d.startswith(base + "/")):
        return "REDDEDİLDİ: klasör proje dizininin dışında"
    name, r = ctx.coder.run(a, d, prompt, "", ctx.budget, ctx.stop)
    if name is None:
        return f"{machine} makinesinde gemini veya aider kurulu değil"
    return clip(f"[{name}, çıkış {r.code}]\n{r.out}\n{r.err}", 4000)


# ---------------- hafıza / kullanıcı ----------------
@tool("remember", "Kalıcı hafızaya bilgi kaydeder (gizli bilgi değil).", info=False, key=S("anahtar"), value=S("değer"))
def t_remember(ctx, key, value):
    try:
        ctx.db.remember(key, value, kind="user")
        return "kaydedildi"
    except ValueError as e:
        return str(e)


@tool("recall", "Kalıcı hafızada arar.", query=S("anahtar kelime"))
def t_recall(ctx, query):
    q = query.lower()
    hits = [f"{m['key']}: {m['value']}" for m in ctx.db.memories() if q in m["key"].lower() or q in str(m["value"]).lower()]
    return clip("\n".join(hits[:20]) or "kayıt yok")


@tool("ask_user", "Kullanıcıya kısa bir açıklama sorusu sorar ve cevabı döndürür.", question=S("soru"))
def t_ask(ctx, question):
    return ctx.ask(question) or "(cevap yok)"


def schemas(names=None):
    return [t.schema() for n, t in TOOLS.items() if names is None or n in names]


def call(ctx, name, args) -> tuple[str, bool]:
    """(sonuç, çalıştı_mı). Onay gerekiyorsa kullanıcıya sorar."""
    t = TOOLS.get(name)
    if not t:
        return f"bilinmeyen araç: {name}", False
    if t.needs_confirm(args):
        ans = ctx.ask(f"Onay: {name} {json.dumps(args, ensure_ascii=False)[:200]} — yapayım mı?") or ""
        if not re.match(r"^\s*(evet|e|onay|tamam|olur|yap|yes|y)\b", ans.lower()):
            return "KULLANICI REDDETTİ — bu işlemi yapma, başka yol dene veya bitir.", False
    try:
        return str(t.fn(ctx, **args)), True
    except TypeError as e:
        return f"hatalı parametre: {e}", False
    except Exception as e:
        return f"hata: {type(e).__name__}: {e}"[:400], False
