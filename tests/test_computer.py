"""Bilgisayar kontrolü: ödeme/kart/hesap kapısı, gizli anahtarın dosyaya yazılması, tarifle tıklama, görme, ses bölme."""
import pytest

from jarvis import secrets
from jarvis.agent import loop, tools as T
from jarvis.memory.db import DB
from jarvis.voice.text_to_speech import sentences
from tests.conftest import MACHINES


class FakeSession:
    def __init__(self, labels=None, checkout=(False, "")):
        self.labels, self.checkout, self.done = labels or {}, checkout, []

    def label(self, id=None, text=None):
        return text or self.labels.get(id, "")

    def checkout_info(self):
        return self.checkout

    def do(self, action, **a):
        self.done.append((action, a))
        return "ok"


def mk(tmp_path, sess, answer="", vision=lambda q, f: ""):
    asked = []

    def ask(q):
        asked.append(q)
        return answer
    c = loop.Ctx(db=DB(tmp_path / "a.db"), agents={}, machines=MACHINES, coder=None, budget=None,
                 browser=lambda: sess, vision=vision, ask=ask)
    return c, asked


@pytest.mark.parametrize("label", ["Siparişi Onayla", "Satın Al", "Place order"])
def test_payment_click_needs_user_yes(tmp_path, label):
    s = FakeSession({7: label}, (True, "1.249,90 TL"))
    c, asked = mk(tmp_path, s, answer="")
    res, ran = T.call(c, "browser", {"action": "click", "id": 7})
    assert "REDDETTİ" in res and not s.done and "1.249,90 TL" in asked[0]
    c, _ = mk(tmp_path, s, answer="evet")
    T.call(c, "browser", {"action": "click", "id": 7})
    assert s.done == [("click", {"id": 7})]


def test_normal_click_and_enter_on_checkout(tmp_path):
    s = FakeSession({1: "Sepete Ekle"})
    c, asked = mk(tmp_path, s)
    T.call(c, "browser", {"action": "click", "id": 1})
    assert s.done and not asked                      # sepete eklemek sorulmaz
    s2 = FakeSession(checkout=(True, ""))
    c, asked = mk(tmp_path, s2)
    assert "REDDETTİ" in T.call(c, "browser", {"action": "press", "key": "Enter"})[0] and asked


def test_card_never_typed_and_account_asks(tmp_path):
    s = FakeSession({3: "Kart Numarası", 4: "Hesap Oluştur"})
    c, asked = mk(tmp_path, s, answer="evet")
    assert "kart bilgisini Jarvis yazmaz" in T.call(c, "browser", {"action": "type", "id": 3, "text": "4111"})[0]
    T.call(c, "browser", {"action": "click", "id": 4})
    assert "hesap" in asked[0].lower() and s.done == [("click", {"id": 4})]


def test_env_outside_allowed_needs_confirm():
    t = T.TOOLS["browser"]
    assert t.needs_confirm({"action": "save_secret", "env_file": "/etc/x/.env", "var": "A"})
    assert not t.needs_confirm({"action": "save_secret", "env_file": "~/projeler/m/.env", "var": "A"})


def test_write_env_masks_and_updates(tmp_path):
    (tmp_path / ".git").mkdir()
    f = tmp_path / ".env"
    f.write_text("A=1\nIYZICO_API_KEY=eski\n")
    out = secrets.write_env(str(f), "IYZICO_API_KEY", "sandbox-abcdef123456")
    assert "abcdef123456" not in out and f.read_text() == "A=1\nIYZICO_API_KEY=sandbox-abcdef123456\n"
    assert ".env" in (tmp_path / ".gitignore").read_text()
    assert "geçersiz" in secrets.write_env(str(f), "kötü ad", "x")


def test_click_on_uses_vision_box(tmp_path, monkeypatch):
    clicks = []
    monkeypatch.setattr(T.subprocess, "run", lambda *a, **k: (tmp_path / "data/tmp").mkdir(parents=True, exist_ok=True)
                        or (tmp_path / "data/tmp/screen.png").write_bytes(b"x"))
    monkeypatch.setattr(T.config, "path", lambda rel: tmp_path / rel)
    monkeypatch.setattr(T, "_screen_size", lambda: (1000, 500))
    monkeypatch.setattr(T, "_mouse_click", lambda x, y, b="left": clicks.append((round(x), round(y), b)))
    c, _ = mk(tmp_path, None, vision=lambda q, f: '```json\n{"box_2d": [100, 200, 300, 400]}\n```')
    res, ran = T.call(c, "click_on", {"target": "kaydet butonu", "button": "double"})
    assert ran and clicks == [(300, 100, "double")]
    c, _ = mk(tmp_path, None, vision=lambda q, f: '{"box_2d": null, "neden": "yok"}')
    assert "bulunamadı" in T.call(c, "click_on", {"target": "x"})[0]


def test_brains_vision_only_seeing_brain(monkeypatch):
    from jarvis import brains as B
    used = []
    monkeypatch.setattr(B.OpenAICompat, "_post", lambda self, body: used.append(self.name) or {"content": "kutu"})
    monkeypatch.setenv("K", "1")
    br = B.Brains([{"name": "groq", "base_url": "https://g", "model": "m", "api_key_env": "K"},
                   {"name": "gemini", "base_url": "https://x", "model": "m", "api_key_env": "K", "vision": True}])
    assert br.can_see() and br.vision("ne var", __file__) == "kutu" and used == ["gemini"]


def test_sentences_merge_short():
    assert sentences("Tamam. Hallettim. Sepete ekledim, ödeme adımında onayını bekliyorum.") == \
        ["Tamam. Hallettim. Sepete ekledim, ödeme adımında onayını bekliyorum."]
    assert len(sentences("Bu birinci uzunca cümledir ve kırk karakteri geçer. Bu da ikinci uzunca cümledir tamam mı.")) == 2


def test_gemini_thought_signature_round_trip(monkeypatch):
    from jarvis.llm import OpenAICompat
    sig = {"google": {"thought_signature": "imza"}}
    monkeypatch.setattr(OpenAICompat, "_post", lambda self, body: {"content": "", "tool_calls": [
        {"id": "c1", "type": "function", "function": {"name": "shell", "arguments": "{}"}, "extra_content": sig}]})
    b = OpenAICompat({"name": "g", "base_url": "https://x", "model": "m", "api_key_env": "PATH"})
    rep = b.chat_tools([], [])
    assert b.assistant_msg(rep)["tool_calls"][0]["extra_content"] == sig


def test_daily_cloud_cap_falls_back_to_local(tmp_path, monkeypatch):
    import time
    from jarvis import brains as B
    from jarvis.memory.db import DB
    db = DB(tmp_path / "a.db")
    monkeypatch.setenv("K", "1")
    br = B.Brains([{"name": "g", "base_url": "https://g", "model": "m", "api_key_env": "K"},
                   {"name": "yerel", "base_url": "http://127.0.0.1:11434/v1", "model": "q"}], db, daily_cap=2)
    assert [b.name for b in br.ready()] == ["g", "yerel"]
    db.remember(f"kullanim:{time.strftime('%Y-%m-%d')}:g", 2, kind="usage")
    assert br.today() == 2 and [b.name for b in br.ready()] == ["yerel"]


def test_ui_tools_registered_and_preferred():
    # 026: uygulama içinde önce Erişilebilirlik ağacı (ui_read), görsel model yedek
    from jarvis.agent import loop, tools as T
    assert {"ui_read", "ui_click", "ui_type", "ui_menu"} <= set(T.TOOLS)
    assert loop.SYSTEM.index("ui_read") < loop.SYSTEM.index("click_on")


def test_ui_click_needs_fresh_read():
    from jarvis.automation import ax
    ax._cache.clear()
    import pytest
    with pytest.raises(LookupError):
        ax.press(5)


def test_video_overlay_lands_where_asked(tmp_path):
    # 028: "resmi 1. saniyede sağ üste koy" → ffmpeg; asıl dosyaya dokunmaz, kare doğru yerde kırmızı
    import subprocess
    import numpy as np
    from jarvis.agent import media as M
    F = M.ffmpeg()
    src, img = tmp_path / "v.mp4", tmp_path / "r.png"
    subprocess.run([F, "-loglevel", "error", "-f", "lavfi", "-i", "color=black:size=320x180:rate=10:duration=3", str(src)])
    subprocess.run([F, "-loglevel", "error", "-f", "lavfi", "-i", "color=red:size=50x50", "-frames:v", "1", str(img)])
    c = type("C", (), {"extra": {}})()
    r = M.t_video(c, "overlay", str(src), media=str(img), start="1", end="2", x=0.75, y=0.25, width=0.2)
    out = r.split("hazır: ")[1].split(" (")[0]
    assert out != str(src) and M.info(out)["sure"] == 3.0
    raw = subprocess.run([F, "-loglevel", "error", "-ss", "1.5", "-i", out, "-frames:v", "1", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
    px = np.frombuffer(raw, np.uint8).reshape(180, 320, 3)
    assert px[45, 240, 0] > 200 and px[45, 240, 1] < 60      # sağ üstte kırmızı
    assert px[135, 80, 0] < 30                                 # sol altta yok
    assert M._out(str(src), out, "ekli") != out                # üzerine yazmaz


def test_blender_builds_saves_renders(tmp_path):
    # 032: blender aracı (HDD'deki Blender) model kurar, .blend kaydeder, zemini kadraja almadan render eder
    import pytest
    from jarvis.agent import media as M
    if not M.BLENDER.exists():
        pytest.skip("Blender kurulu değil")
    code = ("bpy.ops.mesh.primitive_plane_add(size=50)\n"
            "print('JARVIS: nesne', len(bpy.data.objects))")
    r = M.t_blender(None, code, save=str(tmp_path / "a.blend"), render=str(tmp_path / "a.png"))
    assert "[çıkış 0]" in r and "JARVIS: nesne 4" in r
    assert (tmp_path / "a.blend").exists() and (tmp_path / "a.png").stat().st_size > 5000
    bad = M.t_blender(None, "olmayan_fonksiyon()")
    assert "çıkış 0" not in bad and "NameError" in bad


def test_visible_mode_keys_and_blender_ui(monkeypatch):
    # 033: tuş dizileri sırayla basılır, fare görünür kayar, Blender ayarları HDD'de, ajan görünür çalışır
    from jarvis.agent import loop, media as M, tools as T
    pressed = []

    class KB:
        def press(self, k): pressed.append(("+", k))
        def release(self, k): pressed.append(("-", k))
    monkeypatch.setattr(T, "_kb", lambda: (KB(), __import__("pynput.keyboard", fromlist=["Key"]).Key))
    monkeypatch.setattr(T.time, "sleep", lambda s: None)
    T.t_keys(None, "s x 2 enter")
    assert [k for d, k in pressed if d == "+"][:3] == ["s", "x", "2"]
    pressed.clear()
    T.t_keys(None, "cmd + s")
    assert len([1 for d, _ in pressed if d == "+"]) == 2          # tek kombinasyon
    assert "data/blender-user" in M._blender_env()["BLENDER_USER_RESOURCES"].replace("\\", "/")
    assert "blender_ui" in T.TOOLS and "GÖRÜNÜR ÇALIŞ" in loop.SYSTEM
    from jarvis.ui.labels import step_label
    assert step_label("blender_ui", {"action": "open"}) == "Blender açılıyor"
