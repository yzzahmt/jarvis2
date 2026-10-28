"""Araç adımlarını kullanıcıya gösterilecek kısa Türkçe cümleye çevirir (ana pencere ve alt çubuk ortak)."""


def _a(args, k, n=50):
    return str(args.get(k, ""))[:n]


LABELS = {
    "shell": lambda a: "Komut çalıştırılıyor: " + _a(a, "command"),
    "list_dir": lambda a: "Klasöre bakılıyor: " + _a(a, "path"),
    "read_file": lambda a: "Dosya okunuyor: " + _a(a, "path"),
    "write_file": lambda a: "Dosya yazılıyor: " + _a(a, "path"),
    "find_files": lambda a: "Dosya aranıyor: " + _a(a, "name"),
    "open_app": lambda a: _a(a, "app") + " açılıyor",
    "open_url": lambda a: "Sayfa açılıyor: " + _a(a, "url"),
    "applescript": lambda a: "Uygulama kontrol ediliyor",
    "set_volume": lambda a: f"Ses %{_a(a, 'level')} yapılıyor",
    "look_screen": lambda a: "Ekrana bakılıyor",
    "type_text": lambda a: "Yazı yazılıyor",
    "press_keys": lambda a: "Tuşlara basılıyor: " + _a(a, "keys"),
    "click": lambda a: "Tıklanıyor",
    "web_search": lambda a: "İnternette aranıyor: " + _a(a, "query"),
    "fetch_url": lambda a: "Sayfa okunuyor",
    "browser": lambda a: {"goto": "Siteye gidiliyor", "read": "Sayfa okunuyor", "click": "Tıklanıyor: " + _a(a, "text", 30),
                          "fill": "Form dolduruluyor", "press": "Tuşa basılıyor",
                          "youtube": "YouTube'da aranıyor: " + _a(a, "query", 40)}.get(a.get("action"), "Tarayıcı"),
    "ask_ai": lambda a: {"gemini": "Gemini'ye soruluyor", "chatgpt": "ChatGPT'ye soruluyor"}.get(
        a.get("target"), "Kodlama ajanı çalışıyor"),
    "remember": lambda a: "Hafızaya kaydediliyor",
    "recall": lambda a: "Hafızaya bakılıyor",
    "ask_user": lambda a: "Sana soruyorum",
}

KINDS = {"open_app": "Uygulama açılıyor", "open_url": "Sayfa açılıyor", "youtube": "YouTube'da aranıyor",
         "pick_result": "Video açılıyor", "run_tests": "Testler çalışıyor", "code": "Kod yazılıyor",
         "agent": "Çalışıyorum", "macro": "Makro çalışıyor"}


def step_label(name: str, args: dict) -> str:
    f = LABELS.get(name)
    try:
        return f(args) if f else name
    except Exception:
        return name


def step_machine(name: str, args: dict, default: str) -> str:
    """Adım hangi bilgisayarda çalışıyor (alt çubuk orada gösterilir)."""
    if args.get("machine"):
        return args["machine"]
    if name == "ask_ai" and args.get("target", "kod") == "kod":
        return "zorin"
    return default
