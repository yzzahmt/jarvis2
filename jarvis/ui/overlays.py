"""Alt çubuklar: iş hangi bilgisayarda yapılıyorsa o ekranda görünür.
Mac: pywebview penceresi (overlay.html). Linux: SSH ile açılan tk programı (remote_overlay.py), stdin'den beslenir."""
import base64
import json
import queue
import subprocess
import threading
from pathlib import Path

SCRIPT = Path(__file__).with_name("remote_overlay.py")
REMOTE_CMD = ('mkdir -p ~/jarvis-agent && echo {b64} | base64 -d > ~/jarvis-agent/overlay.py && '
              'export DISPLAY="${{DISPLAY:-:0}}"; XA=$(ls /run/user/$(id -u)/xauth_* 2>/dev/null | head -1); '
              'export XAUTHORITY="${{XAUTHORITY:-${{XA:-$HOME/.Xauthority}}}}"; exec python3 ~/jarvis-agent/overlay.py')


class RemoteBar:
    """Uzak makinedeki çubuğa açık bir SSH oturumu; mesajlar JSON satırı olarak yazılır."""

    def __init__(self, agent):
        self.agent, self.p, self.lock = agent, None, threading.Lock()

    def _alive(self):
        return self.p is not None and self.p.poll() is None

    def send(self, msg: dict):
        with self.lock:
            if not self._alive():
                if not (getattr(self.agent, "configured", False) and hasattr(self.agent, "ssh_argv")):
                    return False
                cmd = REMOTE_CMD.format(b64=base64.b64encode(SCRIPT.read_bytes()).decode())
                self.p = subprocess.Popen(self.agent.ssh_argv(cmd), stdin=subprocess.PIPE,
                                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
            try:
                self.p.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
                self.p.stdin.flush()
                return True
            except (BrokenPipeError, OSError):
                self.p = None
                return False

    def close(self):
        if self._alive():
            self.p.stdin.close()
            self.p.terminate()


class LocalBar:
    """Mac'teki çubuk: gizli başlayan, odak çalmayan, her zaman üstte şeffaf pencere."""

    def __init__(self, window):
        self.w, self.hide_timer = window, None

    def send(self, msg: dict):
        t = msg.get("t")
        if self.hide_timer:
            self.hide_timer.cancel()
            self.hide_timer = None
        if t == "show":
            self.w.show()
        self.w.evaluate_js(f"bar.on({json.dumps(msg, ensure_ascii=False)})")
        if t == "done":
            self.hide_timer = threading.Timer(5, self.w.hide)
            self.hide_timer.start()
        elif t == "hide":
            self.w.hide()
        return True

    def close(self):
        pass


class Bars:
    def __init__(self, agents, local_window=None):
        self.agents, self.bars = agents, {}
        self.local = LocalBar(local_window) if local_window else None
        self.shown: set[str] = set()
        self.q: queue.Queue = queue.Queue()      # tek işçi: mesaj sırası korunur, SSH açılışı görevi bekletmez
        threading.Thread(target=self._work, daemon=True).start()

    def _bar(self, machine):
        a = self.agents.get(machine)
        if a is None:
            return None
        if getattr(a, "local", False):
            return self.local
        return self.bars.setdefault(machine, RemoteBar(a))

    def send(self, machine, msg):
        b = self._bar(machine)
        if b is None:
            return
        self.q.put((b, msg))

    def _work(self):
        while True:
            b, msg = self.q.get()
            try:
                b.send(msg)
            except Exception:      # çubuk hatası görevi etkilemez
                pass

    def show(self, machine, title, text=""):
        self.shown.add(machine)
        self.send(machine, {"t": "show", "title": title, "text": text})

    def step(self, machine, text, title):
        if machine not in self.shown:
            self.show(machine, title, text)
        else:
            self.send(machine, {"t": "step", "text": text})

    def done(self, ok, text):
        for m in self.shown:
            self.send(m, {"t": "done", "ok": ok, "text": text})
        self.shown = set()

    def close(self):
        for b in self.bars.values():
            b.close()
