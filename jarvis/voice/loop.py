"""Sesli döngü: UYKU (yalnızca hafif uyandırma) <-> AKTİF (dinle, anla, yanıtla).
Bileşenler bağımsız: uyandırma kelimesi, alkış veya kısayol çökerse diğerleri çalışır.
Mikrofon yoksa metin moduna düşer. Ses verisi diske/buluta gitmez."""
import queue
import sys
import threading
import time

import numpy as np

from .. import config
from ..core import Jarvis
from ..text import norm

RATE, FRAME = 16000, 1280


class Mic:
    def __init__(self):
        import sounddevice as sd
        self.q: queue.Queue = queue.Queue(maxsize=400)
        self.enabled = threading.Event()
        self.enabled.set()
        self.stream = sd.InputStream(samplerate=RATE, channels=1, dtype="int16", blocksize=FRAME,
                                     callback=self._cb)
        self.stream.start()

    def _cb(self, data, frames, t, status):
        if self.enabled.is_set():
            try:
                self.q.put_nowait(data[:, 0].copy())
            except queue.Full:
                pass

    def frames(self, timeout=1.0):
        while True:
            try:
                yield self.q.get(timeout=timeout)
            except queue.Empty:
                yield np.zeros(FRAME, dtype=np.int16)

    def drain(self):
        while not self.q.empty():
            self.q.get_nowait()

    def toggle(self) -> bool:
        if self.enabled.is_set():
            self.enabled.clear()
            self.drain()
        else:
            self.enabled.set()
        return self.enabled.is_set()


def status(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


class VoiceLoop:
    def __init__(self):
        self.s = config.load("settings")
        v = self.s.get("voice", {})
        self.v = v
        self.j = Jarvis(self.s)
        from .text_to_speech import TTS
        self.tts = TTS(v.get("tts", "piper"), config.path(f"data/tts/{v.get('piper_voice')}.onnx"),
                       v.get("say_voice", "Yelda"), config.path("data/tmp"))
        self.wake_evt = threading.Event()
        self.mic = Mic()
        self.ww = self.clap = None
        try:
            from .wakeword import WakeWord
            self.ww = WakeWord(v.get("wake_word", "hey_jarvis"), v.get("wake_threshold", 0.5))
        except Exception as e:
            status(f"Uyandırma kelimesi devre dışı: {e}")
        if v.get("clap_enabled"):
            from .clap_detector import ClapDetector
            self.clap = ClapDetector()
        self._hotkeys(v)
        status("Konuşma tanıma modeli yükleniyor...")
        from .speech_to_text import STT
        self.stt = STT(v.get("stt_model", "small"), str(config.path("data/hf")))
        threading.Thread(target=self._warm_llm, daemon=True).start()

    def _warm_llm(self):
        try:
            self.j.llm.chat([{"role": "user", "content": "merhaba"}], max_tokens=1)
        except Exception:
            pass

    def _hotkeys(self, v):
        try:
            from pynput import keyboard
            keys = {v.get("hotkey", "<cmd>+<shift>+j"): self._hk_wake,
                    v.get("mute_hotkey", "<cmd>+<shift>+m"): self._hk_mute}
            keyboard.GlobalHotKeys(keys).start()
        except Exception as e:  # macOS Erişilebilirlik izni gerekebilir
            status(f"Klavye kısayolu devre dışı: {e}")

    def _hk_wake(self):
        self.tts.stop()            # konuşurken basılırsa sözü keser
        self.wake_evt.set()

    def _hk_mute(self):
        on = self.mic.toggle()
        status("MİKROFON AÇIK" if on else "MİKROFON KAPALI (yalnızca kısayolla uyanır)")

    def say(self, text):
        self.tts.speak(text)
        time.sleep(0.25)
        self.mic.drain()           # kendi sesini komut sanmasın
        if self.ww:
            self.ww.reset()

    def sleep_mode(self):
        status("UYKU — 'hey jarvis', kısayol" + (" veya çift alkış" if self.clap else "") + " ile uyanır")
        for f in self.mic.frames(timeout=0.2):
            if self.wake_evt.is_set():
                break
            if not self.mic.enabled.is_set():
                continue
            if (self.ww and self.ww.feed(f)) or (self.clap and self.clap.feed(f)):
                break
        self.wake_evt.clear()

    def active_mode(self):
        status("AKTİF — dinliyorum")
        self.say(self.j.handle("uyan"))
        from .speech_to_text import record_utterance
        idle_until = time.time() + self.v.get("idle_sleep_s", 60)
        while True:
            if time.time() > idle_until:
                self.j.handle("uyu")
                self.say("Bir süredir komut gelmedi, uyku moduna geçiyorum.")
                return
            audio = record_utterance(self.mic.frames(), RATE, start_timeout=8)
            if audio is None:
                continue
            text = self.stt.transcribe(audio)
            if not text or len(norm(text)) < 2:
                continue
            status(f"sen> {text}")
            idle_until = time.time() + self.v.get("idle_sleep_s", 60)
            reply = self.j.handle(text, say=self.say)
            self.say(reply)
            if not self.j.awake:
                return

    def run(self):
        while True:
            self.sleep_mode()
            self.active_mode()


def main():
    try:
        loop = VoiceLoop()
    except Exception as e:
        status(f"Ses başlatılamadı ({e}); metin moduna geçiyorum.")
        sys.argv = sys.argv[:1]
        from ..__main__ import main as text_main
        return text_main()
    try:
        loop.run()
    except KeyboardInterrupt:
        status("Kapatılıyor.")
