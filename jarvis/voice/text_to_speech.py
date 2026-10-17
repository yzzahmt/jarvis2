"""Türkçe sesli yanıt: Piper (yerel). Yedek: macOS 'say' / Linux 'espeak-ng'. Kesilebilir."""
import platform
import shutil
import subprocess
import threading
import uuid
import wave
from pathlib import Path

from ..text import speakable


class TTS:
    def __init__(self, engine="piper", voice_path=None, say_voice="Yelda", tmp="/tmp"):
        self.engine, self.say_voice, self.tmp = engine, say_voice, Path(tmp)
        self.voice = None
        self.proc: subprocess.Popen | None = None
        self.speaking = threading.Event()
        if engine == "piper" and voice_path and Path(voice_path).exists():
            try:
                from piper import PiperVoice
                self.voice = PiperVoice.load(str(voice_path))
            except Exception:
                self.voice = None   # yedeğe düş

    def _cmd(self, text):
        if self.voice:
            wav = self.tmp / f"tts-{uuid.uuid4().hex[:8]}.wav"
            with wave.open(str(wav), "wb") as w:
                self.voice.synthesize_wav(text, w)
            player = ["afplay"] if platform.system() == "Darwin" else ["aplay", "-q"]
            return player + [str(wav)], wav
        if platform.system() == "Darwin":
            return ["say", "-v", self.say_voice, text], None
        if shutil.which("espeak-ng"):
            return ["espeak-ng", "-v", "tr", text], None
        return None, None

    def speak(self, text: str, block=True):
        print("jarvis>", text, flush=True)
        text = speakable(text)
        if not text:
            return
        cmd, wav = self._cmd(text)
        if not cmd:
            return
        self.speaking.set()
        try:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if block:
                self.proc.wait()
        finally:
            if block:
                self.speaking.clear()
                if wav:
                    wav.unlink(missing_ok=True)

    def stop(self):
        """Konuşmayı kes (kullanıcı araya girdiğinde)."""
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
        self.speaking.clear()
