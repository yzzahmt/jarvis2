"""JARVIS masaüstü arayüzü (python -m jarvis app). Terminal gerekmez.
Ana pencere: web/index.html (pywebview, port açılmaz; JS <-> Python köprüsü).
Alt çubuk: iş hangi bilgisayarda yapılıyorsa orada (overlays.py)."""
import json
import threading
import time
from pathlib import Path

import webview

from .. import config
from ..core import NAMES, Jarvis
from .labels import KINDS, step_label, step_machine
from .overlays import Bars

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
        self._app.win.minimize()

    def quit(self):
        self._app.quit()


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
        self.win.events.loaded += self._loaded
        self.win.events.closed += lambda: self.quit()

    def _bar_window(self):
        try:
            sc = webview.screens[0]
            w, h = 520, 76
            x, y = sc.x + (sc.width - w) // 2, sc.y + sc.height - h - 96
        except Exception:
            w, h, x, y = 520, 76, None, None
        return webview.create_window("JARVIS çubuk", str(WEB / "overlay.html"), width=w, height=h, x=x, y=y,
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
        if s == "listening" and getattr(self, "_last_state", "") == "sleep":
            try:                       # "hey jarvis" ya da çift alkışla uyanınca pencere öne gelir
                self.win.restore()
                self.win.show()
            except Exception:
                pass
        self._last_state = s
        self.push("state", state=s)

    def message(self, role, text):
        self.push("msg", role=role, text=text)

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
        self.bars.close()
        for w in list(webview.windows):
            try:
                w.destroy()
            except Exception:
                pass

    def run(self):
        _brand()                     # AppKit ana iş parçacığında
        webview.start(self._bg, debug=False)


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
    App().run()
