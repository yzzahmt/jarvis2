"""Türkçe sesli yanıt. Öncelik: Edge sinir ağı sesi (ücretsiz, anahtarsız, internet ister; insana yakın).
Yedek: Piper (yerel) → macOS 'say' / Linux 'espeak-ng'. Cümle cümle üretilir: ilk cümle hazır olunca çalmaya başlar,
o çalarken sonraki üretilir. Kesilebilir."""
import platform
import queue
import re
import shutil
import subprocess
import threading
import time
import uuid
import wave
from pathlib import Path

from ..text import speakable

PLAYER = ["afplay"] if platform.system() == "Darwin" else ["mpg123", "-q"]


def sentences(text: str, min_len=40) -> list[str]:
    """Cümlelere böl; çok kısa parçaları birleştir (her parça ayrı istek, gereksiz bekleme olmasın)."""
    parts, cur = [], ""
    for s in re.split(r"(?<=[.!?…])\s+", text.strip()):
        cur = f"{cur} {s}".strip()
        if len(cur) >= min_len:
            parts.append(cur)
            cur = ""
    if cur:
        parts.append(cur)
    return parts


class TTS:
    def __init__(self, engine="edge", voice_path=None, say_voice="Yelda", tmp="/tmp",
                 edge_voice="tr-TR-EmelNeural", edge_rate="+0%", edge_pitch="+0Hz"):
        self.engine, self.say_voice, self.tmp = engine, say_voice, Path(tmp)
        self.edge_voice, self.edge_rate, self.edge_pitch = edge_voice, edge_rate, edge_pitch
        self.voice = None
        self.proc: subprocess.Popen | None = None
        self.speaking = threading.Event()
        self.cancel = threading.Event()
        self.edge_ok = engine == "edge"
        if engine in ("piper", "edge") and voice_path and Path(voice_path).exists():
            try:
                from piper import PiperVoice
                self.voice = PiperVoice.load(str(voice_path))
            except Exception:
                self.voice = None   # yedeğe düş

    @classmethod
    def from_settings(cls, v: dict, data_dir: Path):
        return cls(v.get("tts", "edge"), data_dir / f"tts/{v.get('piper_voice')}.onnx", v.get("say_voice", "Yelda"),
                   data_dir / "tmp", v.get("edge_voice", "en-US-AvaMultilingualNeural"), v.get("edge_rate", "+0%"),
                   v.get("edge_pitch", "+0Hz"))

    # ---- üretim ----
    def _edge(self, text) -> Path | None:
        if not self.edge_ok:
            return None
        import asyncio
        import edge_tts
        f = self.tmp / f"tts-{uuid.uuid4().hex[:8]}.mp3"
        for attempt in range(3):          # servis ara sıra boş döner; hemen robot sese düşme
            try:
                asyncio.run(asyncio.wait_for(edge_tts.Communicate(text, self.edge_voice, rate=self.edge_rate,
                                                                  pitch=self.edge_pitch).save(str(f)), 12))
                if f.exists() and f.stat().st_size:
                    self.edge_fails = 0
                    return f
            except Exception:
                pass
            if self.cancel.is_set():
                break
            time.sleep(0.6 * (attempt + 1))
        f.unlink(missing_ok=True)
        self.edge_fails = getattr(self, "edge_fails", 0) + 1
        if self.edge_fails >= 3:          # üst üste 3 cümle olmadı: internet yok say, 2 dk yerel ses
            self.edge_ok, self.edge_fails = False, 0
            t = threading.Timer(120, lambda: setattr(self, "edge_ok", True))
            t.daemon = True
            t.start()
        return None

    def _cmd(self, text):
        f = self._edge(text)
        if f:
            return PLAYER + [str(f)], f
        if self.voice:
            wav = self.tmp / f"tts-{uuid.uuid4().hex[:8]}.wav"
            with wave.open(str(wav), "wb") as w:
                self.voice.synthesize_wav(text, w)
            return (["afplay"] if platform.system() == "Darwin" else ["aplay", "-q"]) + [str(wav)], wav
        if platform.system() == "Darwin":
            return ["say", "-v", self.say_voice, text], None
        if shutil.which("espeak-ng"):
            return ["espeak-ng", "-v", "tr", text], None
        return None, None

    # ---- çalma ----
    def _pipeline(self, parts):
        q: queue.Queue = queue.Queue(maxsize=2)

        def produce():
            for p in parts:
                if self.cancel.is_set():
                    break
                q.put(self._cmd(p))
            q.put(None)

        threading.Thread(target=produce, daemon=True).start()
        try:
            while (item := q.get()) is not None:
                cmd, f = item
                try:
                    if cmd and not self.cancel.is_set():
                        self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        self.proc.wait()
                finally:
                    if f:
                        f.unlink(missing_ok=True)
        finally:
            self.speaking.clear()

    def speak(self, text: str, block=True):
        print("jarvis>", text, flush=True)
        text = speakable(text)
        if not text:
            return
        self.cancel.clear()
        self.speaking.set()
        parts = sentences(text)
        if block:
            self._pipeline(parts)
        else:
            threading.Thread(target=self._pipeline, args=(parts,), daemon=True).start()

    def stop(self):
        """Konuşmayı kes (kullanıcı araya girdiğinde)."""
        self.cancel.set()
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
        self.speaking.clear()
