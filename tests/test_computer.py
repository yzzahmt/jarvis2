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
