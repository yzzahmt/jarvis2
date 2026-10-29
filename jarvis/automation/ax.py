"""Ekranı OKUMA: macOS Erişilebilirlik (AX) ağacı. Uygulamanın düğme, menü, alan, sekme… listesini adı ve konumuyla
verir; tıklama/yazma doğrudan öğeye yapılır (ekran görüntüsü + görsel model tahmininden 5-10 kat hızlı, ıskalamaz).
Bazı uygulamalar (oyun motorları, bazı video düzenleyiciler) ağacı zayıf verir: o zaman click_on/look_screen yedek.
İzin: Sistem Ayarları > Gizlilik ve Güvenlik > Erişilebilirlik > JARVIS (ve Terminal)."""
import time

ROLES = {"AXButton": "düğme", "AXCheckBox": "onay kutusu", "AXRadioButton": "seçenek", "AXTextField": "metin alanı",
         "AXTextArea": "metin alanı", "AXSearchField": "arama alanı", "AXComboBox": "açılır alan",
         "AXPopUpButton": "açılır menü", "AXMenuButton": "menü düğmesi", "AXSlider": "kaydırıcı",
         "AXIncrementor": "sayaç", "AXTab": "sekme", "AXTabGroup": "sekmeler", "AXLink": "bağlantı",
         "AXCell": "hücre", "AXRow": "satır", "AXDisclosureTriangle": "aç/kapa", "AXImage": "görsel",
         "AXStaticText": "yazı", "AXColorWell": "renk", "AXSegmentedControl": "bölmeli düğme", "AXToolbar": "araç çubuğu"}
CLICKABLE = set(ROLES) - {"AXStaticText", "AXImage", "AXTabGroup", "AXToolbar"}

_cache: dict[int, object] = {}       # son okumadaki öğeler: id → AXUIElement


def _ax():
    import ApplicationServices as A
    return A


def trusted() -> bool:
    try:
        return bool(_ax().AXIsProcessTrusted())
    except Exception:
        return False


def _get(el, attr):
    err, v = _ax().AXUIElementCopyAttributeValue(el, attr, None)
    return v if err == 0 else None


def _point(el, attr, kind):
    A = _ax()
    v = _get(el, attr)
    if v is None:
        return None
    ok, p = A.AXValueGetValue(v, kind, None)
    return p if ok else None


def _frame(el):
    A = _ax()
    p, s = _point(el, "AXPosition", A.kAXValueCGPointType), _point(el, "AXSize", A.kAXValueCGSizeType)
    if p is None or s is None:
        return None
    return int(p.x), int(p.y), int(s.width), int(s.height)


def _label(el) -> str:
    for a in ("AXTitle", "AXDescription", "AXValue", "AXHelp", "AXPlaceholderValue", "AXIdentifier"):
        v = _get(el, a)
        if isinstance(v, str) and v.strip():
            return v.strip().replace("\n", " ")[:60]
        if isinstance(v, (int, float)) and not isinstance(v, bool) and a == "AXValue":
            return str(v)
    t = _get(el, "AXTitleUIElement")
    return _label(t) if t is not None else ""


def running_apps() -> list[tuple[str, int]]:
    from AppKit import NSWorkspace
    return [(a.localizedName() or "", a.processIdentifier()) for a in NSWorkspace.sharedWorkspace().runningApplications()
            if a.activationPolicy() == 0]


def find_app(name: str = ""):
    """Ada göre çalışan uygulama (boşsa öndeki). (ad, pid) ya da None."""
    from AppKit import NSWorkspace
    if not name:
        a = NSWorkspace.sharedWorkspace().frontmostApplication()
        return (a.localizedName(), a.processIdentifier()) if a else None
    n = name.lower().replace(".app", "").strip()
    apps = running_apps()
    for exact in (True, False):
        for an, pid in apps:
            if (an.lower() == n) if exact else (n in an.lower() or an.lower() in n):
                return an, pid
    return None


def activate(pid):
    from AppKit import NSRunningApplication
    a = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
    if a:
        a.activateWithOptions_(1 << 1)    # NSApplicationActivateIgnoringOtherApps
        time.sleep(0.3)


def read(app: str = "", query: str = "", limit: int = 120) -> str:
    """Öndeki (ya da adı verilen) uygulamanın penceresindeki öğeleri numaralı listeler. query: yalnız eşleşenler."""
    if not trusted():
        return "Erişilebilirlik izni yok: Sistem Ayarları > Gizlilik ve Güvenlik > Erişilebilirlik > JARVIS'i aç."
    found = find_app(app)
    if not found:
        return f"'{app}' çalışmıyor; önce open_app ile aç."
    name, pid = found
    root = _ax().AXUIElementCreateApplication(pid)
    win = _get(root, "AXFocusedWindow") or (list(_get(root, "AXWindows") or []) or [None])[0]
    if win is None:
        return f"{name}: açık pencere yok."
    _cache.clear()
    wf = _frame(win) or (0, 0, 10 ** 5, 10 ** 5)
    inside = lambda f: wf[0] - 2 <= f[0] + f[2] // 2 <= wf[0] + wf[2] and wf[1] - 2 <= f[1] + f[3] // 2 <= wf[1] + wf[3]  # noqa: E731
    q = (query or "").lower()
    out, queue, seen, deadline = [], [(win, 0)], 0, time.time() + 4
    while queue and len(out) < limit and time.time() < deadline:
        el, depth = queue.pop(0)
        seen += 1
        role = _get(el, "AXRole") or ""
        if role in ROLES:
            lab = _label(el)
            fr = _frame(el)
            keep = lab or role in CLICKABLE - {"AXRow", "AXCell"}   # etiketsiz satır/hücre: içindeki öğe zaten listelenir
            if fr and fr[2] > 0 and fr[3] > 0 and keep and inside(fr) and (not q or q in lab.lower()):
                i = len(_cache) + 1
                _cache[i] = el
                en = "" if _get(el, "AXEnabled") is not False else " (pasif)"
                out.append(f"[{i}] {ROLES[role]} '{lab}' @({fr[0] + fr[2] // 2},{fr[1] + fr[3] // 2}) "
                           f"{fr[2]}x{fr[3]}{en}")
        if depth < 25:
            queue.extend((c, depth + 1) for c in (_get(el, "AXChildren") or []))
    title = _get(win, "AXTitle") or ""
    if not out:
        return (f"{name} '{title}': okunabilir öğe yok (uygulama erişilebilirlik bilgisi vermiyor) — "
                "look_screen/click_on/find_on_screen kullan.")
    return f"{name} — pencere '{title}' ({seen} öğe tarandı):\n" + "\n".join(out)


def _el(i):
    el = _cache.get(int(i))
    if el is None:
        raise LookupError(f"{i} numaralı öğe yok; önce ui_read ile yeniden oku")
    return el


def press(i, button="left") -> str:
    from ..agent.tools import _mouse_click
    el = _el(i)
    if button == "left" and _ax().AXUIElementPerformAction(el, "AXPress") == 0:
        time.sleep(0.3)
        return "basıldı"
    fr = _frame(el)                        # AXPress yoksa (hücre, görsel) ya da sağ/çift tık: merkezine fareyle
    if not fr:
        return "öğenin konumu yok"
    _mouse_click(fr[0] + fr[2] / 2, fr[1] + fr[3] / 2, button)
    time.sleep(0.3)
    return "tıklandı"


def set_value(i, text) -> str:
    A = _ax()
    el = _el(i)
    A.AXUIElementSetAttributeValue(el, "AXFocused", True)
    if A.AXUIElementSetAttributeValue(el, "AXValue", text) == 0 and _get(el, "AXValue") == text:
        return "yazıldı"
    from ..agent.tools import _kb, _mouse_click
    fr = _frame(el)
    if fr:
        _mouse_click(fr[0] + fr[2] / 2, fr[1] + fr[3] / 2)
    kb, Key = _kb()
    with kb.pressed(Key.cmd):
        kb.press("a")
        kb.release("a")
    kb.type(text)
    return "yazıldı (klavyeyle)"


def menu(app: str, path: str) -> str:
    """Menü çubuğundan seçim: 'Dosya > Dışa Aktar > Video'. Adlar kısmi ve büyük/küçük harf duyarsız eşleşir."""
    if not trusted():
        return "Erişilebilirlik izni yok."
    found = find_app(app)
    if not found:
        return f"'{app}' çalışmıyor."
    name, pid = found
    activate(pid)
    A = _ax()
    cur = _get(A.AXUIElementCreateApplication(pid), "AXMenuBar")
    parts = [p.strip().lower() for p in path.replace("→", ">").split(">") if p.strip()]
    for n, want in enumerate(parts):
        items = _get(cur, "AXChildren") or []
        if items and (_get(items[0], "AXRole") == "AXMenu"):
            items = _get(items[0], "AXChildren") or []
        titles = [(_get(it, "AXTitle") or "") for it in items]
        hit = next((it for it, t in zip(items, titles) if t.lower() == want), None) or \
            next((it for it, t in zip(items, titles) if want in t.lower()), None)
        if hit is None:
            have = ", ".join(t for t in titles if t)[:400]
            return f"'{want}' menüde yok. Mevcut: {have}"
        A.AXUIElementPerformAction(hit, "AXPress")
        time.sleep(0.25)
        cur = hit
    return f"{name}: {path} seçildi"
