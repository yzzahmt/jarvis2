"""Türkçe sesli yanıt. Öncelik: Edge sinir ağı sesi (ücretsiz, anahtarsız, internet ister; insana yakın).
Tüm cevap TEK istekle akış olarak üretilir ve parçalar geldikçe mpg123'e verilir: cümle arası boşluk olmaz.
Servis ilk sesi 2,5 sn'de vermezse bir kez daha denenir, olmazsa beklemeden Piper (yerel) → 'say' / espeak-ng.
Sık söylenen kısa cümleler önbellekte (data/tts-cache) tutulur, anında çalar. Kesilebilir."""
import asyncio
import hashlib
import platform
import queue
import re
import shutil
import subprocess
import threading
import time
import uuid
import wave
from collections import deque
from pathlib import Path

import numpy as np

from ..text import speakable

MAC = platform.system() == "Darwin"
FIRST_AUDIO_S = 2.5      # ilk ses bu sürede gelmezse servis yavaş sayılır
CACHE_MAX_CHARS = 80     # bu kadar kısa cevaplar önbelleğe alınır


def sentences(text: str, min_len=40) -> list[str]:
    """Cümlelere böl; çok kısa parçaları birleştir."""
    parts, cur = [], ""
    for s in re.split(r"(?<=[.!?…])\s+", text.strip()):
        cur = f"{cur} {s}".strip()
        if len(cur) >= min_len:
            parts.append(cur)
            cur = ""
    if cur:
        parts.append(cur)
    return parts


class Player:
    """mp3 baytlarını mpg123 ile ham sese çözer ve sounddevice ile çalar. Çalınan sesin seviyesini kaydeder:
    ses döngüsü mikrofondaki yankıyı bununla karşılaştırıp kullanıcının söze girdiğini anlar."""
    RATE = 24000

    def __init__(self, mpg123, cancel, levels):
        self.cancel, self.levels = cancel, levels
        self.proc = subprocess.Popen([mpg123, "-q", "-s", "-m", "-r", str(self.RATE), "-e", "s16", "-"],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.q: queue.Queue = queue.Queue()
        self.started = threading.Event()
        threading.Thread(target=self._writer, daemon=True).start()
        self.pt = threading.Thread(target=self._play, daemon=True)
        self.pt.start()

    def feed(self, b: bytes):
        self.q.put(b)

    def close(self):
        self.q.put(None)

    def _writer(self):
        while (b := self.q.get()) is not None and not self.cancel.is_set():
            try:
                self.proc.stdin.write(b)
                self.proc.stdin.flush()
            except OSError:
                break
        try:
            self.proc.stdin.close()
        except OSError:
            pass

    def _play(self):
        import sounddevice as sd
        try:
            with sd.OutputStream(samplerate=self.RATE, channels=1, dtype="int16", latency="low") as out:
                while not self.cancel.is_set():
                    b = self.proc.stdout.read(2400)          # 50 ms
                    if not b:
                        break
                    x = np.frombuffer(b[: len(b) // 2 * 2], np.int16)
                    self.levels.append((time.time(), float(np.sqrt(np.mean((x / 32768.0) ** 2))) if len(x) else 0.0))
                    self.started.set()
                    out.write(x)
                if self.cancel.is_set():
                    out.abort()
        finally:
            if self.proc.poll() is None:
                self.proc.kill()

    def wait(self):
        self.pt.join()


class TTS:
    def __init__(self, engine="edge", voice_path=None, say_voice="Yelda", tmp="/tmp",
                 edge_voice="en-US-AvaMultilingualNeural", edge_rate="+0%", edge_pitch="+0Hz", cache_dir=None):
        self.engine, self.say_voice, self.tmp = engine, say_voice, Path(tmp)
        self.edge_voice, self.edge_rate, self.edge_pitch = edge_voice, edge_rate, edge_pitch
        self.cache = Path(cache_dir) if cache_dir else None
        self.voice = None
        self.proc: subprocess.Popen | None = None
        self.speaking = threading.Event()
        self.cancel = threading.Event()
        self.lock = threading.Lock()                 # aynı anda tek konuşma
        self.levels: deque = deque(maxlen=400)        # (zaman, çalınan ses seviyesi) — söz kesme için
        self.live = False                            # şu an seviyesi bilinen sesle mi konuşuyor
        self.gen = 0                                 # konuşma numarası
        self.mpg123 = shutil.which("mpg123") or ("/opt/homebrew/bin/mpg123" if Path("/opt/homebrew/bin/mpg123").exists() else None)
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
                   v.get("edge_pitch", "+0Hz"), data_dir / "tts-cache")

    def echo_level(self, window=0.5):
        """Son 'window' sn'de hoparlöre verilen en yüksek seviye; seviyesi bilinmeyen sesle konuşuyorsa None."""
        if not self.live:
            return None
        now = time.time()
        return max((lv for t, lv in list(self.levels) if now - t <= window), default=0.0)

    # ---- çalma yardımcıları ----
    def _play(self, cmd, cancel) -> None:
        if cancel.is_set():
            return
        self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.proc.wait()

    def _cache_file(self, text) -> Path | None:
        if not self.cache or len(text) > CACHE_MAX_CHARS:
            return None
        h = hashlib.sha1(f"{self.edge_voice}|{self.edge_rate}|{self.edge_pitch}|{text}".encode()).hexdigest()[:16]
        return self.cache / f"{h}.mp3"

    # ---- Edge: tek istek, akış ----
    def _player_run(self, chunks, cancel) -> bytes:
        """chunks: bayt üreteci (async değil). Player ile çalar; çalınan tüm baytları döndürür."""
        pl = Player(self.mpg123, cancel, self.levels)
        self.proc, self.live = pl.proc, True
        got = bytearray()
        try:
            for c in chunks:
                got.extend(c)
                pl.feed(c)
            pl.close()
            pl.wait()
        finally:
            self.live = False
        return bytes(got)

    def _edge_stream(self, text, cancel) -> bool:
        """Sesi geldikçe çalar. Hiç ses gelmediyse False (yedeğe geçilir). Kısmen çaldıysa True."""
        if self.engine != "edge":
            return False
        import edge_tts
        cf = self._cache_file(text)
        if cf and cf.exists() and cf.stat().st_size:
            if self.mpg123:
                self._player_run([cf.read_bytes()], cancel)
            else:
                self._play(["afplay", str(cf)], cancel)
            return True
        for _ in range(2):
            q: queue.Queue = queue.Queue()

            async def run():
                it = edge_tts.Communicate(text, self.edge_voice, rate=self.edge_rate,
                                          pitch=self.edge_pitch).stream().__aiter__()
                first = True
                while not cancel.is_set():
                    try:
                        c = await asyncio.wait_for(it.__anext__(), FIRST_AUDIO_S if first else 10)
                    except StopAsyncIteration:
                        return
                    if c["type"] == "audio":
                        first = False
                        q.put(c["data"])

            def fetch():
                try:
                    asyncio.run(run())
                except Exception:
                    pass                              # zaman aşımı / bağlantı hatası
                q.put(None)

            threading.Thread(target=fetch, daemon=True).start()
            head = q.get()                            # ilk parça (ya da hiç)
            if head is None:
                if cancel.is_set():
                    return True
                continue

            def chunks():
                yield head
                while (c := q.get()) is not None:
                    yield c

            if self.mpg123:
                got = self._player_run(chunks(), cancel)
            else:                                     # mpg123 yoksa: dosyaya yazıp çal
                got = b"".join(chunks())
                f = self.tmp / f"tts-{uuid.uuid4().hex[:8]}.mp3"
                f.write_bytes(got)
                self._play(["afplay", str(f)], cancel)
                f.unlink(missing_ok=True)
            if cf and got and not cancel.is_set():
                cf.parent.mkdir(parents=True, exist_ok=True)
                cf.write_bytes(got)
            return True
        return False

    def _local(self, text, cancel):
        if self.voice:
            wav = self.tmp / f"tts-{uuid.uuid4().hex[:8]}.wav"
            with wave.open(str(wav), "wb") as w:
                self.voice.synthesize_wav(text, w)
            self._play((["afplay"] if MAC else ["aplay", "-q"]) + [str(wav)], cancel)
            wav.unlink(missing_ok=True)
        elif MAC:
            self._play(["say", "-v", self.say_voice, text], cancel)
        elif shutil.which("espeak-ng"):
            self._play(["espeak-ng", "-v", "tr", text], cancel)

    def _run(self, text, cancel, gen):
        try:
            with self.lock:
                if not cancel.is_set() and not self._edge_stream(text, cancel) and not cancel.is_set():
                    self._local(text, cancel)
        finally:
            if self.gen == gen:                      # eski (kesilmiş) konuşma yenisinin bayrağını indirmesin
                self.speaking.clear()

    def speak(self, text: str, block=True):
        print("jarvis>", text, flush=True)
        text = speakable(text)
        if not text:
            return
        self.stop()                                  # önceki konuşma varsa kes
        self.cancel = threading.Event()              # her konuşmanın kendi iptal bayrağı
        self.gen += 1
        self.speaking.set()
        if block:
            self._run(text, self.cancel, self.gen)
        else:
            threading.Thread(target=self._run, args=(text, self.cancel, self.gen), daemon=True).start()

    def warm(self, phrases):
        """Sık cümleleri arka planda önbelleğe al (sessizce)."""
        def go():
            import edge_tts
            for p in phrases:
                cf = self._cache_file(speakable(p))
                if not cf or cf.exists():
                    continue
                try:
                    cf.parent.mkdir(parents=True, exist_ok=True)
                    asyncio.run(asyncio.wait_for(edge_tts.Communicate(speakable(p), self.edge_voice, rate=self.edge_rate,
                                                                      pitch=self.edge_pitch).save(str(cf)), 15))
                except Exception:
                    cf.unlink(missing_ok=True)
        if self.engine == "edge" and self.cache:
            threading.Thread(target=go, daemon=True).start()

    def stop(self):
        """Konuşmayı kes (kullanıcı araya girdiğinde)."""
        self.cancel.set()
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
        self.speaking.clear()
