"""Linux ajan makinesinde ekranın altında çıkan küçük JARVIS çubuğu (tek dosya, yalnızca standart kütüphane + tk).
Mac bunu SSH ile ~/jarvis-agent/overlay.py olarak kopyalar ve stdin'den JSON satırları gönderir:
{"t":"show","title":..} {"t":"step","text":..} {"t":"done","ok":true,"text":..} {"t":"hide"}
stdin kapanınca (SSH bitince) kendiliğinden kapanır."""
import json
import math
import queue
import sys
import threading
import tkinter as tk

W, H, BOTTOM = 560, 64, 70
BG, FG, DIM = "#1c1c1e", "#f5f5f7", "#98989d"
COLORS = ["#64d2ff", "#5e5ce6", "#bf5af2", "#ff375f"]


def _mix(a, b, t):
    a, b = [int(a[i:i + 2], 16) for i in (1, 3, 5)], [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(int(x + (y - x) * t) for x, y in zip(a, b))


class Bar:
    def __init__(self):
        self.q = queue.Queue()
        self.r = tk.Tk()
        self.r.withdraw()
        self.r.overrideredirect(True)
        self.r.attributes("-topmost", True)
        try:
            self.r.attributes("-alpha", 0.94)
            self.r.attributes("-type", "notification")
        except tk.TclError:
            pass
        sw, sh = self.r.winfo_screenwidth(), self.r.winfo_screenheight()
        self.r.geometry(f"{W}x{H}+{(sw - W) // 2}+{sh - H - BOTTOM}")
        self.c = tk.Canvas(self.r, width=W, height=H, bg=BG, highlightthickness=0)
        self.c.pack()
        self.orb = [self.c.create_oval(0, 0, 0, 0, outline="", fill=COLORS[i]) for i in range(3)]
        self.title = self.c.create_text(64, 23, anchor="w", fill=FG, font=("Inter", 12, "bold"), text="JARVIS")
        self.sub = self.c.create_text(64, 43, anchor="w", fill=DIM, font=("Inter", 10), text="")
        self.t, self.busy, self.hide_at = 0.0, True, None
        threading.Thread(target=self._read, daemon=True).start()
        self._tick()

    def _read(self):
        for line in sys.stdin:
            try:
                self.q.put(json.loads(line))
            except ValueError:
                pass
        self.q.put({"t": "quit"})

    def _tick(self):
        while not self.q.empty():
            self._handle(self.q.get())
        self.t += 0.05 if self.busy else 0.015
        cx, cy = 32, H // 2
        for i, o in enumerate(self.orb):          # dönen, iç içe yumuşak renkler
            a = self.t * (1 + i * 0.4) + i * 2.1
            r = (15 - i * 3) * (1 + (0.12 if self.busy else 0.04) * math.sin(self.t * 3 + i))
            x, y = cx + math.cos(a) * (2 + i), cy + math.sin(a) * (2 + i)
            self.c.coords(o, x - r, y - r, x + r, y + r)
            self.c.itemconfig(o, fill=_mix(COLORS[i], COLORS[(i + 1) % 4], (math.sin(self.t + i) + 1) / 2))
        if self.hide_at is not None:
            self.hide_at -= 1
            if self.hide_at <= 0:
                self.hide_at = None
                self.r.withdraw()
        self.r.after(33, self._tick)

    def _handle(self, m):
        t = m.get("t")
        if t == "quit":
            self.r.destroy()
            sys.exit(0)
        if t == "show":
            self.busy, self.hide_at = True, None
            self.c.itemconfig(self.title, text=m.get("title", "JARVIS")[:60])
            self.c.itemconfig(self.sub, text=m.get("text", "")[:80], fill=DIM)
            self.r.deiconify()
            self.r.attributes("-topmost", True)
        elif t == "step":
            self.c.itemconfig(self.sub, text=m.get("text", "")[:80], fill=DIM)
        elif t == "done":
            self.busy = False
            self.c.itemconfig(self.sub, text=("✓ " if m.get("ok") else "✕ ") + m.get("text", "")[:78],
                              fill="#30d158" if m.get("ok") else "#ff453a")
            self.hide_at = 150                    # ~5 sn sonra gizle
        elif t == "hide":
            self.r.withdraw()


if __name__ == "__main__":
    Bar().r.mainloop()
