"""Mikrofonsuz ses doğrulaması: Piper(TR) -> Whisper(TR) ve 'hey jarvis' -> openWakeWord."""
import subprocess
import sys
import time
import wave

import numpy as np

sys.path.insert(0, ".")
from jarvis import config  # noqa: E402

TMP = config.path("data/tmp")
ok = True


def load16k(path):
    out = TMP / "16k.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(path), "-ar", "16000", "-ac", "1", str(out)], check=True)
    with wave.open(str(out)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16)


from piper import PiperVoice  # noqa: E402
v = PiperVoice.load(str(config.path("data/tts/tr_TR-dfki-medium.onnx")))
cümle = "Zorin OS bilgisayarında testleri çalıştır"
with wave.open(str(TMP / "tts.wav"), "wb") as w:
    v.synthesize_wav(cümle, w)
from jarvis.voice.speech_to_text import STT  # noqa: E402
t = time.time()
stt = STT("small", str(config.path("data/hf")))
heard = stt.transcribe(load16k(TMP / "tts.wav"))
print(f"STT ({time.time() - t:.1f} sn): '{heard}'")
ok &= "test" in heard.lower()

subprocess.run(["say", "-v", "Samantha", "-o", str(TMP / "hj.aiff"), "Hey Jarvis"], check=True)
a = np.concatenate([np.zeros(16000, np.int16), load16k(TMP / "hj.aiff"), np.zeros(16000, np.int16)])
from jarvis.voice.wakeword import WakeWord  # noqa: E402
ww = WakeWord()
hit = any(ww.feed(a[i:i + 1280]) for i in range(0, len(a) - 1280, 1280))
ww.reset()
z = np.random.default_rng(0).normal(0, 300, 16000 * 5).astype(np.int16)
false = any(ww.feed(z[i:i + 1280]) for i in range(0, len(z) - 1280, 1280))
print("Uyandırma 'hey jarvis':", hit, "| gürültüde yanlış uyanma:", false)
ok &= hit and not false
for f in TMP.glob("*.wav"):
    f.unlink()
print("SONUÇ:", "BAŞARILI" if ok else "BAŞARISIZ")
sys.exit(0 if ok else 1)
