"""Gösterip öğretme: kullanıcı bir işi bir kez kendisi yapar, Jarvis tıklamaları (hangi uygulamada, hangi düğme),
sürüklemeleri, yazıları ve kısayolları kaydeder; sonra benzer istekte bu yolu örnek alıp uyarlar.
Kayıt ayrı süreçte çalışır (python -m jarvis.agent.teach <dosya>): pynput klavye dinleyicisi arayüz sürecinin
arka iş parçacığında macOS'ta çöküyordu; kendi sürecinde ana iş parçacığındadır. Şifre alanına yazılanlar kaydedilmez."""
import json
import os
import signal
import subprocess
import sys
import time

from .. import config

SKIP_APPS = {"python", "python3", "jarvis"}      # Jarvis'in kendi penceresine yapılanlar örnek değil


def _describe(x, y) -> tuple[str, str]:
    """(uygulama, öğe tarifi) — tıklanan noktadaki Erişilebilirlik öğesi."""
    try:
        import ApplicationServices as A
        from ..automation import ax
        app = (ax.find_app("") or ("?", 0))[0]
        err, el = A.AXUIElementCopyElementAtPosition(A.AXUIElementCreateSystemWide(), float(x), float(y), None)
        if err != 0 or el is None:
            return app, ""
        role = ax._get(el, "AXRole") or ""
        if role == "AXSecureTextField":
            return app, "şifre alanı"
        lab = ax._label(el)
        if not lab:                                   # etiketsiz öğe: üst öğenin adı
            par = ax._get(el, "AXParent")
            lab = ax._label(par) if par is not None else ""
        return app, f"{ax.ROLES.get(role, role.replace('AX', '').lower())} '{lab}'" if lab else ax.ROLES.get(role, "")
    except Exception:
        return "?", ""


def record(path):
    """Olayları path'e JSON satırları olarak yazar; SIGTERM ile durur."""
    from pynput import keyboard, mouse
    out = open(path, "a", encoding="utf-8")
    state = {"down": None, "text": "", "app": "", "secure": False, "last_click": (0, 0, 0)}
    mods = set()

    def emit(**e):
        if e.get("app", "").lower() in SKIP_APPS:
            return
        e["t"] = round(time.time(), 2)
        out.write(json.dumps(e, ensure_ascii=False) + "\n")
        out.flush()

    def flush_text():
        if state["text"]:
            emit(kind="type", app=state["app"], text="•••" if state["secure"] else state["text"])
            state["text"] = ""

    def on_click(x, y, button, pressed):
        if pressed:
            flush_text()
            state["down"] = (x, y, time.time())
            return
        if not state["down"]:
            return
        x0, y0, _ = state["down"]
        state["down"] = None
        app, what = _describe(x0, y0)
        state["app"], state["secure"] = app, what == "şifre alanı"
        b = "right" if button == mouse.Button.right else "left"
        if abs(x - x0) + abs(y - y0) > 12:
            _, to = _describe(x, y)
            emit(kind="drag", app=app, what=what, to=to, x=int(x0), y=int(y0), to_x=int(x), to_y=int(y))
            return
        lx, ly, lt = state["last_click"]
        state["last_click"] = (x, y, time.time())
        if abs(x - lx) + abs(y - ly) < 6 and time.time() - lt < 0.4:
            emit(kind="double", app=app, what=what, x=int(x), y=int(y))
        else:
            emit(kind="click", app=app, what=what, button=b, x=int(x), y=int(y))

    def on_scroll(x, y, dx, dy):
        app, what = _describe(x, y)
        emit(kind="scroll", app=app, what=what, amount=-int(dy))

    K = keyboard.Key
    MODS = {K.cmd: "cmd", K.cmd_r: "cmd", K.ctrl: "ctrl", K.ctrl_r: "ctrl", K.alt: "alt", K.alt_r: "alt",
            K.shift: "shift", K.shift_r: "shift"}
    SPECIAL = {K.enter: "enter", K.tab: "tab", K.esc: "esc", K.backspace: "backspace", K.delete: "delete",
               K.up: "up", K.down: "down", K.left: "left", K.right: "right", K.space: "space"}

    def on_press(key):
        if key in MODS:
            mods.add(MODS[key])
            return
        if mods - {"shift"}:                          # kısayol
            flush_text()
            name = SPECIAL.get(key) or getattr(key, "char", None) or str(key).replace("Key.", "")
            emit(kind="keys", app=state["app"], keys="+".join(sorted(mods) + [str(name).lower()]))
            return
        if key == K.space:
            state["text"] += " "
        elif key == K.backspace and state["text"]:
            state["text"] = state["text"][:-1]
        elif key in SPECIAL:
            flush_text()
            emit(kind="keys", app=state["app"], keys=SPECIAL[key])
        elif getattr(key, "char", None):
            state["text"] += key.char

    def on_release(key):
        if key in MODS:
            mods.discard(MODS[key])

    def stop(*_):
        flush_text()
        out.close()
        os._exit(0)

    signal.signal(signal.SIGTERM, stop)
    with mouse.Listener(on_click=on_click, on_scroll=on_scroll), \
            keyboard.Listener(on_press=on_press, on_release=on_release) as kl:
        kl.join()


def steps_text(events: list[dict]) -> list[str]:
    """Olayları okunur adımlara çevirir (arka arkaya kaydırmalar birleşir)."""
    out, prev = [], None
    for e in events:
        k, app = e.get("kind"), e.get("app", "")
        where = f" ({app})" if app and app != (prev or {}).get("app") else ""
        what = e.get("what") or f"({e.get('x')},{e.get('y')}) noktası"
        if k == "scroll" and prev and prev.get("kind") == "scroll" and prev.get("what") == e.get("what"):
            prev["amount"] = prev.get("amount", 0) + e.get("amount", 0)
            out[-1] = f"{what} üzerinde kaydır ({prev['amount']})"
            continue
        if k == "click":
            out.append(f"{what}{' sağ' if e.get('button') == 'right' else ''} tıkla{where}")
        elif k == "double":
            if out and out[-1].startswith(what):
                out.pop()
            out.append(f"{what} çift tıkla{where}")
        elif k == "drag":
            out.append(f"{what} → {e.get('to') or 'hedef'} sürükle ({e['x']},{e['y']}→{e['to_x']},{e['to_y']}){where}")
        elif k == "type":
            out.append(f"yaz: \"{e['text']}\"{where}")
        elif k == "keys":
            out.append(f"tuş: {e['keys']}{where}")
        elif k == "scroll":
            out.append(f"{what} üzerinde kaydır ({e.get('amount')})")
        prev = e
    return out


class Recorder:
    def __init__(self, name: str):
        self.name = name
        self.path = config.path(f"data/tmp/ogret-{int(time.time())}.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        py = str(config.HOME / ".venv/bin/python")
        self.proc = subprocess.Popen([py if os.path.exists(py) else sys.executable, "-m", "jarvis.agent.teach",
                                      str(self.path)], cwd=str(config.HOME),
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop(self) -> list[str]:
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        try:
            events = [json.loads(ln) for ln in self.path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        except OSError:
            events = []
        finally:
            self.path.unlink(missing_ok=True)
        return steps_text(events)


if __name__ == "__main__":
    record(sys.argv[1])
