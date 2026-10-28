"""JARVIS masaüstü arayüzü (python -m jarvis app). Terminal gerekmez.
Ana pencere: web/index.html (pywebview, port açılmaz; JS <-> Python köprüsü).
Alt çubuk: iş hangi bilgisayarda yapılıyorsa orada (overlays.py)."""
import faulthandler
import json
import logging
import os
import re
import threading
import time
import traceback
from pathlib import Path

import webview

from .. import config
from ..core import NAMES, Jarvis
from .labels import KINDS, step_label, step_machine
from .overlays import Bars

log = logging.getLogger("jarvis.ui")
WEB = Path(__file__).with_name("web")


class Api:
    """JS tarafı window.pywebview.api.* ile bunları çağırır (alt çizgili adlar dışarı açılmaz)."""

    def __init__(self, app):
        self._app = app

    def send(self, text):
        self._app.submit(text)

    def answer(self, text):
        self._app.answer(text)

    def mic(self):
        return self._app.mic()

    def stop(self):
        self._app.submit("dur", show=False)

    def machines(self):
        return self._app.machines()

    def set_speak(self, on):
        self._app.speak = bool(on)

    def hello(self):
        return self._app.hello()

    def minimize(self):
        self._app.dock(True)            # macOS Dock'a değil, ekranın altındaki Jarvis çubuğuna küçülür

    def settings(self):
        return self._app.settings()

    def set_voice(self, voice):
        return self._app.set_voice(voice)

    def preview_voice(self, voice):
        self._app.preview_voice(voice)

    def set_key(self, key):
        return self._app.set_key(key)

    def quit(self):
        self._app.quit()

    def expand(self):
        self._app.set_mini(False)

    def hide(self):
        self._app.dock(True)


class BarApi:
    """Alttaki çubuğun (dock) düğmeleri."""

    def __init__(self, app):
        self._app = app

    def expand(self):
        self._app.dock(False)

    def mic(self):
        return self._app.mic()

    def stop(self):
        self._app.submit("dur", show=False)

    def close(self):
        self._app.hide()


class App:
    def __init__(self):
        self.s = config.load("settings")
        self.j = Jarvis(self.s)
        self.j.on_progress = self.on_step
        self.j.on_event = self.on_event
        self.voice = None
        self.voice_msg = "Ses yükleniyor…"
        self.speak = self.s.get("ui", {}).get("speak", True)
        self.task_machine = "mac"
        self.task_title = "JARVIS"
        self.pending_ask = None            # (id, Event, [cevap])
        self.ready, self.buffer = False, []
        self.win = webview.create_window(
            "JARVIS", str(WEB / "index.html"), js_api=Api(self), width=440, height=720, min_size=(380, 560),
            frameless=True, easy_drag=False, vibrancy=True, transparent=True, background_color="#000000")
        self.bar_win = self._bar_window()
        self.bars = Bars(self.j.agents, self.bar_win)
        self.docked, self.last_line = False, ""
        self._preview, self._preview_lock = None, threading.Lock()
        self.win.events.loaded += self._loaded
        try:                                     # ⌘M / sarı düğme: Dock'a değil alttaki çubuğa
            self.win.events.minimized += lambda: threading.Thread(target=self.dock, args=(True,), daemon=True).start()
        except Exception:
            pass
        self.win.events.closed += lambda: self.quit()

    def _bar_window(self):
        try:
            sc = webview.screens[0]
            w, h = 580, 84
            x, y = sc.x + (sc.width - w) // 2, sc.y + sc.height - h - 96
        except Exception:
            w, h, x, y = 580, 84, None, None
        return webview.create_window("JARVIS çubuk", str(WEB / "overlay.html"), js_api=BarApi(self),
                                     width=w, height=h, x=x, y=y,
                                     frameless=True, easy_drag=False, on_top=True, transparent=True,
                                     hidden=True, focus=False, resizable=False, background_color="#000000")

    # ---------------- Python -> arayüz ----------------
    def _loaded(self):
        self.ready = True
        for ev, d in self.buffer:
            self._js(ev, d)
        self.buffer = []

    def _js(self, ev, d):
        self.win.evaluate_js(f"jarvis.on({json.dumps(ev)}, {json.dumps(d, ensure_ascii=False)})")

    def push(self, ev, **d):
        if not self.ready:
            self.buffer.append((ev, d))
            return
        try:
            self._js(ev, d)
        except Exception:
            pass

    # VoiceLoop arayüz kancaları
    def state(self, s):
        if self.docked:
            self._dock_msg({"t": "state", "state": s})
        elif s == "listening" and getattr(self, "_last_state", "") == "sleep":
            try:                       # "hey jarvis" ya da çift alkışla uyanınca pencere öne gelir
                self.win.restore()
                self.win.show()
            except Exception:
                pass
        self._last_state = s
        self.push("state", state=s)

    def message(self, role, text):
        self.push("msg", role=role, text=text)
        if role != "jarvis-interim":
            self.last_line = text
        if self.docked:
            self._dock_msg({"t": "msg", "role": role, "text": text})

    # ---------------- alttaki çubuk (dock) ----------------
    def _dock_msg(self, msg):
        lb = self.bars.local
        if lb:
            self.bars.q.put((lb, msg))

    def dock(self, on=True):
        """Küçültünce ana pencere gizlenir, altta Jarvis çubuğu kalır (dinleme/cevap orada görünür)."""
        lb = self.bars.local
        if lb is None:
            return self.win.minimize() if on else None
        self.docked = lb.docked = on
        if on:
            self.visible = False
            try:
                self.win.hide()
            except Exception:
                pass
            self._dock_msg({"t": "dock", "state": getattr(self, "_last_state", "idle"), "text": self.last_line})
        else:
            self._dock_msg({"t": "hide"})
            self.set_mini(False)
            self.win.restore()
            self.win.show()
            self.visible = True
            try:
                from AppKit import NSApplication
                NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
            except Exception:
                pass

    def ask(self, question, listen=None):
        """Onay/soru kartı gösterir; cevap düğmeden, yazıdan ya da (sesli komutsa) sesten gelir."""
        ev, box, qid = threading.Event(), [], str(time.time())
        self.pending_ask = (qid, ev, box)
        self.push("ask", id=qid, question=question)
        self.bars.step(self.task_machine, "Onay bekleniyor: " + question[:60], self.task_title)
        if listen is not None:
            threading.Thread(target=lambda: self._voice_answer(qid, listen, question), daemon=True).start()
        else:
            threading.Thread(target=self.say, args=(question,), daemon=True).start()
        ev.wait(timeout=180)
        self.pending_ask = None
        self.push("ask_done", id=qid)
        return box[0] if box else ""

    def _voice_answer(self, qid, listen, question):
        ans = listen(question)
        if ans and self.pending_ask and self.pending_ask[0] == qid:
            self.message("user", ans)
            self.answer(ans)

    # Jarvis çekirdek kancaları
    def on_event(self, ev, d):
        if ev == "task_start":
            self.task_machine = d["machine"]
            self.task_title = KINDS.get(d["kind"], "Çalışıyorum") + " · " + NAMES.get(d["machine"], d["machine"])
            self.push("task_start", title=self.task_title, request=d["request"], machine=d["machine"])
            self.bars.show(d["machine"], self.task_title, d["request"][:80])
        elif ev == "task_end":
            self.push("task_end", ok=d["ok"], text=d["text"])
            self.bars.done(d["ok"], d["text"][:90])

    def on_step(self, name, args):
        text = step_label(name, args)
        self.push("step", text=text, tool=name)
        self.bars.step(step_machine(name, args, self.task_machine), text, self.task_title)

    # ---------------- arayüz -> Python ----------------
    def hello(self):
        return {"machines": self.machines(), "voice": self.voice_msg, "speak": self.speak,
                "hotkey": self.s.get("voice", {}).get("hotkey", "<cmd>+<shift>+j").replace("<", "").replace(">", "")}

    VOICES = [("en-US-AvaMultilingualNeural", "Ava", "sıcak, kadın"),
              ("en-US-AndrewMultilingualNeural", "Andrew", "sakin, erkek"),
              ("en-US-EmmaMultilingualNeural", "Emma", "neşeli, kadın"),
              ("en-US-BrianMultilingualNeural", "Brian", "rahat, erkek"),
              ("tr-TR-EmelNeural", "Emel", "yerli, kadın")]

    def settings(self):
        b = self.j.brains
        return {"voice": self.s.get("voice", {}).get("edge_voice", ""),
                "voices": [{"id": v, "name": n, "desc": d} for v, n, d in self.VOICES],
                "brains": b.status() if b else [], "active": getattr(b, "last_model", None) or "",
                "gemini": bool(os.environ.get("GEMINI_API_KEY")),
                "today": b.today() if b else 0, "cap": getattr(b, "daily_cap", 0)}

    def _tts_objs(self):
        return [t for t in (getattr(self, "tts", None), getattr(self.voice, "tts", None)) if t]

    def set_voice(self, voice):
        if voice not in {v for v, _, _ in self.VOICES}:
            return False
        f = config.path("config/settings.yaml")
        txt = re.sub(r"(?m)^(\s*edge_voice:\s*)\S+", lambda m: m.group(1) + voice, f.read_text(encoding="utf-8"))
        f.write_text(txt, encoding="utf-8")
        self.s.setdefault("voice", {})["edge_voice"] = voice
        for t in self._tts_objs():
            t.edge_voice = voice
        return True

    def preview_voice(self, voice):
        """Sesin kısa önizlemesi. Tek önizleme motoru; önce Jarvis'in konuşması ve önceki önizleme susar
        (her tıklamada yeni motor + üst üste çalan sesler 29.10'da çökmeyle aynı anda görüldü)."""
        from ..voice.text_to_speech import TTS
        name = next((n for v, n, _ in self.VOICES if v == voice), "Jarvis")
        for t in self._tts_objs():
            t.stop()
        with self._preview_lock:
            if self._preview is None:
                self._preview = TTS.from_settings({**self.s.get("voice", {}), "edge_voice": voice}, config.path("data"))
            self._preview.stop()
            self._preview.edge_voice = voice
            self._preview.speak(f"Merhaba, ben {name}. Sesim böyle, beğendin mi?", block=False)

    def set_key(self, key):
        """Gemini anahtarını .env'e yazar ve beyinleri yeniden kurar (yeniden başlatmadan)."""
        key = (key or "").strip()
        if not re.match(r"^[\w.-]{20,120}$", key):     # eski AIza…, yeni AQ.… biçimi
            return "Anahtar geçersiz görünüyor."
        from .. import secrets
        from ..brains import Brains
        secrets.write_env(str(config.path(".env")), "GEMINI_API_KEY", key)
        os.environ["GEMINI_API_KEY"] = key
        self.j.brains = Brains(self.s["brains"], self.j.db, self.s.get("budget", {}).get("max_cloud_calls_per_day", 0))
        try:
            g = self.j.brains.all[0]                      # ilk sıradaki Gemini   # yalnız Gemini'yi dene (yerele düşmesin)
            g.chat([{"role": "user", "content": "Sadece 'tamam' yaz."}], max_tokens=10)
            return "ok"
        except Exception as e:
            return f"Kaydedildi ama Gemini yanıt vermedi: {str(e)[:120]}"

    def machines(self):
        out = []
        for n, a in self.j.agents.items():
            st = "off" if not a.configured else ("on" if a.online() else "down")
            out.append({"id": n, "name": NAMES.get(n, n), "state": st})
        return out

    def answer(self, text):
        if self.pending_ask:
            _, ev, box = self.pending_ask
            box.append(text)
            ev.set()

    def submit(self, text, show=True):
        text = (text or "").strip()
        if not text:
            return
        if self.pending_ask:                     # açık soru varsa yazılan cevap sayılır
            self.message("user", text)
            return self.answer(text)
        if show:
            self.message("user", text)
        threading.Thread(target=self._run, args=(text,), daemon=True).start()

    def _run(self, text):
        if self.j.lock.locked() and text != "dur":
            self.message("jarvis", "Şu an bir görev çalışıyor. Durdurmak için 'dur' yaz ya da kare düğmeye bas.")
            return
        self.state("thinking")
        reply = self.j.handle(text, say=lambda m: self.message("jarvis-interim", m), ask=self.ask)
        self.message("jarvis", reply)
        self.say(reply)
        self.state("idle" if self.j.awake or not self.voice else "sleep")

    def say(self, text):
        """Sesli cevap: mikrofon yoksa da konuşur (yankı engeli için varsa ses döngüsünün say'i)."""
        if not self.speak or not text:
            return
        if self.voice:
            return self.voice.say(text)
        try:
            if not hasattr(self, "tts"):
                from ..voice.text_to_speech import TTS
                v = self.s.get("voice", {})
                self.tts = TTS.from_settings(v, config.path("data"))
            self.state("speaking")
            self.tts.speak(text)
        except Exception:
            pass
        self.state("idle")

    def mic(self):
        if not self.voice:
            return self.voice_msg
        self.voice.tts.stop()
        self.voice.wake_evt.set()
        return ""

    # ---------------- ses ----------------
    def _start_voice(self):
        try:
            from ..voice.loop import VoiceLoop
            self.voice = VoiceLoop(j=self.j, ui=self, hotkeys=False)
            self.voice_msg = ""
            self.push("voice", ok=True, text="")
            self.voice.run()
        except Exception as e:      # mikrofon/izin yoksa arayüz yazıyla çalışmaya devam eder
            self.voice = None
            self.voice_msg = f"Ses kullanılamıyor: {e}"[:160]
            self.push("voice", ok=False, text=self.voice_msg)
            self.state("idle")

    def _bg(self):
        threading.Thread(target=self._start_voice, daemon=True).start()
        while True:                  # bilgisayar kartlarını tazele
            time.sleep(30)
            self.push("machines", list=self.machines())

    def quit(self):
        log.warning("çıkış: %s", "".join(traceback.format_stack(limit=6)[:-1]).replace("\n", " | ")[-600:])
        self.bars.close()
        for w in list(webview.windows):
            try:
                w.destroy()
            except Exception:
                pass

    # ---------------- küçük pencere (ChatGPT gibi, ekranın altında) ----------------
    MINI = (600, 230)
    FULL = (440, 720)

    def _screen(self):
        try:
            sc = webview.screens[0]
            return sc.x, sc.y, sc.width, sc.height
        except Exception:
            return 0, 0, 1512, 982

    def set_mini(self, on):
        x0, y0, sw, sh = self._screen()
        self.mini = on
        w, h = self.MINI if on else self.FULL
        self.win.resize(w, h)
        if on:
            self.win.move(x0 + (sw - w) // 2, y0 + sh - h - 70)
        else:
            self.win.move(x0 + (sw - w) // 2, y0 + max(40, (sh - h) // 2))
        self.push("mini", on=on)

    def hide(self):
        """Tamamen gizle (çubuk da); kısayol ya da 'hey jarvis' geri getirir."""
        self.visible = False
        if self.docked:
            self.docked = self.bars.local.docked = False
            self._dock_msg({"t": "hide"})
        self.win.hide()

    def toggle_mini(self):
        """Kısayol: gizliyse altta küçük pencereyi aç ve dinlemeye başla; açıksa gizle."""
        if getattr(self, "visible", True) and getattr(self, "mini", False):
            return self.hide()
        if self.docked:
            self.docked = self.bars.local.docked = False
            self._dock_msg({"t": "hide"})
        self.set_mini(True)
        self.win.show()
        self.visible = True
        try:
            from AppKit import NSApplication
            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        except Exception:
            pass
        self.push("focus")
        if self.voice:
            self.voice.tts.stop()
            self.voice.wake_evt.set()

    def run(self):
        _brand()                     # AppKit ana iş parçacığında
        _hotkey(self, self.s.get("voice", {}).get("quick_keys", "<+z"))
        webview.start(self._bg, debug=False)
        os._exit(0)                  # pencere kapandı: tarayıcı/ses iş parçacıkları süreci asılı tutmasın


def _hotkey(app, keys="<+z"):
    """Genel kısayol (varsayılan '<' + 'Z' birlikte). macOS NSEvent izleyicisi: ana iş parçacığında kurulur,
    Erişilebilirlik izni ister. Tuşlar diğer uygulamaya da gider (macOS izleyicisi engelleyemez)."""
    try:
        from AppKit import NSEvent
    except Exception:
        return
    a, b = [k.strip().lower() for k in keys.split("+")]
    down, last = set(), [0.0]
    KEYDOWN, KEYUP = 1 << 10, 1 << 11
    ISO = {10: "<", 50: "<"}           # ISO tuşu (Türkçe klavyede Z'nin solundaki '<'), bazı klavyelerde 50

    def name(ev):
        ch = (ev.charactersIgnoringModifiers() or "").lower()
        return ISO.get(ev.keyCode(), ch) if ev.keyCode() in ISO else ch

    def handle(ev):
        try:
            n = name(ev)
            if ev.type() == 10:                      # NSEventTypeKeyDown
                if n in (a, b):
                    other = b if n == a else a
                    if other in down and time.time() - last[0] > 0.6:
                        last[0] = time.time()
                        threading.Thread(target=app.toggle_mini, daemon=True).start()
                    down.add(n)
            else:
                down.discard(n)
        except Exception:
            pass
        return ev

    NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(KEYDOWN | KEYUP, handle)
    NSEvent.addLocalMonitorForEventsMatchingMask_handler_(KEYDOWN | KEYUP, handle)


def _brand():
    """Dock'ta 'Python' yerine JARVIS adı ve simgesi."""
    try:
        from AppKit import NSApplication, NSBundle, NSImage
        info = NSBundle.mainBundle().infoDictionary()
        info["CFBundleName"] = "JARVIS"
        icon = config.path("assets/jarvis.png")
        if icon.exists():
            NSApplication.sharedApplication().setApplicationIconImage_(
                NSImage.alloc().initWithContentsOfFile_(str(icon)))
    except Exception:
        pass


def main():
    # Çökme kaydı: Python'un yakalayamadığı (yerel) çökmeler ve iş parçacığı hataları data/logs/crash.log'a
    crash = open(config.path("data/logs/crash.log"), "a", buffering=1)
    crash.write(f"\n=== başlangıç {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    faulthandler.enable(file=crash, all_threads=True)
    threading.excepthook = lambda a: crash.write(
        f"[{time.strftime('%H:%M:%S')}] iş parçacığı hatası: {''.join(traceback.format_exception(a.exc_type, a.exc_value, a.exc_traceback))}")
    App().run()
