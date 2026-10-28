"""Sesli döngü: UYKU (yalnızca hafif uyandırma) <-> AKTİF (dinle, anla, yanıtla).
Bileşenler bağımsız: uyandırma kelimesi, alkış veya kısayol çökerse diğerleri çalışır.
Mikrofon yoksa metin moduna düşer. Ses verisi diske/buluta gitmez."""
import itertools
import queue
import sys
import threading
import time
from collections import deque

import numpy as np

from .. import config
from ..core import Jarvis
from ..text import norm

RATE, FRAME = 16000, 1280


def _rms(f) -> float:
    return float(np.sqrt(np.mean((f.astype(np.float32) / 32768.0) ** 2)))


def chime(freqs=(880, 1320), dur=0.07, vol=0.18):
    """'Dinliyorum' sesi: kısa, yumuşak tonlar (konuşmadan anında; sounddevice ile, gecikmesiz)."""
    try:
        import sounddevice as sd
        sr = 24000
        t = np.arange(int(sr * dur)) / sr
        env = np.sin(np.pi * t / t[-1]) ** 2
        tone = np.concatenate([np.sin(2 * np.pi * f * t) * env for f in freqs]) * vol
        sd.play(tone.astype(np.float32), sr)
    except Exception:
        pass


def clap_chime():
    """Alkışla uyanınca: kısa sesten daha belirgin, yükselen üç ton (~0,4 sn)."""
    chime((660, 880, 1320), dur=0.12, vol=0.35)
WARM = ["Sizi dinliyorum.", "Dinliyorum, ne yapmamı istersin?", "Bir süredir komut gelmedi, uyku moduna geçiyorum.", "Tamam.",
        "Görevi durdurdum.", "Tamam, iptal ettim."]


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


class NoUI:
    """Arayüz yokken boş kancalar (arayüz: jarvis/ui/app.py)."""
    def state(self, s): pass
    def message(self, role, text): pass
    def ask(self, question, listen=None): return listen(question) if listen else ""


class VoiceLoop:
    def __init__(self, j=None, ui=None, hotkeys=True):
        self.s = config.load("settings")
        v = self.s.get("voice", {})
        self.v = v
        self.j = j or Jarvis(self.s)
        self.ui = ui or NoUI()
        from .text_to_speech import TTS
        self.tts = TTS.from_settings(v, config.path("data"))
        self.tts.warm(WARM)
        self.wake_evt = threading.Event()
        self.preroll: list = []         # söze girilince kaydedilen ilk kareler
        self.mic = Mic()
        self.ww = self.clap = None
        try:
            from .wakeword import WakeWord
            self.ww = WakeWord(v.get("wake_word", "hey_jarvis"), v.get("wake_threshold", 0.5))
        except Exception as e:
            status(f"Uyandırma kelimesi devre dışı: {e}")
        if v.get("clap_enabled"):
            from .clap_detector import ClapDetector
            self.clap = ClapDetector(peak=v.get("clap_peak", 0.3), max_gap=v.get("clap_max_gap", 1.0))
        if hotkeys:                # arayüzde kapalı: pynput arka iş parçacığında macOS'ta çöküyor
            self._hotkeys(v)
        from .speech_to_text import STT
        self.stt = STT(v.get("stt_model", "small"), str(config.path("data/hf")), v.get("words") or [],
                       v.get("stt_cloud_model", "gemini-3.5-flash-lite"), v.get("stt_cloud", True),
                       v.get("stt_cloud_models"))
        if self.j.brains:
            self.stt.allow, self.stt.used = self.j.brains.can_cloud, lambda name="gemini-stt": self.j.brains.note(name)
        status("Konuşma tanıma: " + ("Gemini (bulut), yedek yerel" if STT._key() and v.get("stt_cloud", True) else "yerel model"))
        threading.Thread(target=self._warm_llm, daemon=True).start()

    def _warm_llm(self):
        if self.j.brains and self.j.brains.ready() and any(b.is_cloud for b in self.j.brains.ready()):
            return                 # bulut beyin var: yerel modeli boşuna belleğe yükleme
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

    def heard_self(self, text) -> bool:
        """Duyulan metin Jarvis'in son 20 sn'de söylediğinin parçası mı (hoparlörden mikrofona yankı)."""
        said, at = getattr(self, "said", ("", 0))
        if not said or time.time() - at > 20:
            return False
        from .speech_to_text import _words
        a, b = _words(text), set(_words(said))
        return bool(a) and sum(w in b for w in a) / len(a) >= 0.7

    def say(self, text, interruptible=True):
        """Konuşur. Kullanıcı söze girerse (ChatGPT gibi) hemen susar; söylediğinin başı self.preroll'da kalır."""
        self.ui.state("speaking")
        self.said = (text, time.time())    # kendi sesini komut sanmasın (heard_self)
        self.mic.drain()
        self.tts.speak(text, block=False)
        pre = self._watch(interruptible and self.v.get("barge_in", True))
        self.ui.state("idle")
        if pre:
            self.preroll = pre
        else:
            time.sleep(0.2)
            self.mic.drain()       # kendi sesini komut sanmasın
        if self.ww:
            self.ww.reset()
        return bool(pre)

    def _watch(self, barge):
        """Konuşma bitene kadar mikrofonu izler. Mikrofondaki ses, hoparlöre verilen sesin yankısından belirgin
        şekilde yüksekse (ya da 'hey jarvis' denirse) kullanıcı konuşuyordur: sustur, son kareleri döndür."""
        ring = deque(maxlen=8)               # ~0,64 sn: sözün başı kaybolmasın
        # 28.10 ölçümü (MacBook hoparlör %31, mikrofon %33): yankı = çalınan sesin %3'ü (en çok %9).
        # Yankı oranının ÜST zarfı izlenir; eşik = 1,5 × beklenen yankı + 0,008. Kayıtta kendi sesiyle hiç
        # tetiklenmedi, üstüne eklenen 0,025+ konuşmayı her yerde ~0,3 sn'de yakaladı.
        gain, hot, t0 = self.v.get("echo_gain", 0.06), 0, time.time()
        k, floor = self.v.get("barge_k", 1.5), self.v.get("barge_floor", 0.008)
        while self.tts.speaking.is_set():
            try:
                f = self.mic.q.get(timeout=0.1)
            except queue.Empty:
                continue
            if not barge:
                continue
            ring.append(f)
            lvl, play = _rms(f), self.tts.echo_level()
            woke = bool(play is None and self.ww and self.ww.feed(f))   # kendi sesindeki 'Jarvis' kesmesin
            if play is None or time.time() - t0 < 0.4:                  # yerel ses / ilk an: enerjiyle kesme yok
                hot = 0
            elif lvl > k * gain * play + floor:
                hot += 1
            else:
                hot = 0
                if play > 0.01:
                    gain = max(0.97 * gain, min(lvl / play, 0.15), 0.03)   # yankı oranının üst zarfı
            if hot >= 4 or woke:             # ~0,3 sn süren konuşma
                self.tts.stop()
                status("SÖZÜM KESİLDİ — dinliyorum")
                return list(ring)
        return None

    def _take_preroll(self):
        pre, self.preroll = self.preroll, []
        return pre

    def ask(self, question):
        return self.ui.ask(question, listen=self.listen_answer)

    def listen_answer(self, question):
        """Soruyu söyle, tek cümlelik cevabı dinle (cevap yoksa "" -> onay verilmemiş sayılır)."""
        from .speech_to_text import record_utterance
        self.say(question)
        self.ui.state("listening")
        audio = record_utterance(self.mic.frames(), RATE, start_timeout=10, preroll=self._take_preroll())
        ans = self.stt.transcribe(audio) if audio is not None else ""
        status(f"sen> {ans}")
        return ans

    def sleep_mode(self):
        status("UYKU — 'hey jarvis', kısayol" + (" veya çift alkış" if self.clap else "") + " ile uyanır")
        self.ui.state("sleep")
        self.wake_src = "key"                    # kısayol/arayüz; kelime ve alkış aşağıda değiştirir
        silent, warned = 0, False
        for f in self.mic.frames(timeout=0.2):
            if self.wake_evt.is_set():
                break
            if not self.mic.enabled.is_set():
                continue
            silent = 0 if f.any() else silent + 1
            if silent > 125 and not warned:      # ~10 sn tam sıfır: mikrofon izni yok / aygıt kapalı
                warned = True
                msg = ("Mikrofondan hiç ses gelmiyor. Sistem Ayarları > Gizlilik ve Güvenlik > Mikrofon'da "
                       "JARVIS'e izin ver, sonra Jarvis'i yeniden aç.")
                status(msg)
                self.ui.message("jarvis-interim", msg)
            if self.ww and self.ww.feed(f):
                self.wake_src = "word"
                break
            if self.clap and self.clap.feed(f):
                self.wake_src = "clap"
                break
        self.wake_evt.clear()

    def active_mode(self):
        status("AKTİF — dinliyorum")
        greet = self.j.handle("uyan")
        base = "Dinliyorum, ne yapmamı istersin?"
        extra = greet.replace(base, "").strip()
        src = getattr(self, "wake_src", "key")
        reply = self.v.get("wake_reply", "Sizi dinliyorum.")
        if src == "word" and reply and not extra:
            self.ui.message("jarvis", reply)
            self.say(reply)                  # söze girersen susar, sözün kaybolmaz (preroll)
        elif src == "clap" and not extra:
            clap_chime()
            self.ui.message("jarvis-interim", "Dinliyorum…")
            time.sleep(0.45)
            self.mic.drain()
        elif self.v.get("wake_chime", True) and not extra:
            chime()                          # konuşmadan anında dinlemeye geç (önceden ~2,5 sn selamlama vardı)
            self.ui.message("jarvis-interim", "Dinliyorum…")
            time.sleep(0.15)
            self.mic.drain()
        else:
            self.ui.message("jarvis", greet)
            self.say(greet)
        from .speech_to_text import record_utterance
        idle_until = time.time() + self.v.get("idle_sleep_s", 60)
        while True:
            if time.time() > idle_until:
                self.j.handle("uyu")
                self.say("Bir süredir komut gelmedi, uyku moduna geçiyorum.")
                return
            self.ui.state("listening")
            st: dict = {}
            audio = record_utterance(self.mic.frames(), RATE, start_timeout=8, stats=st, preroll=self._take_preroll())
            if audio is None:
                status(f"duyulmadı (en yüksek seviye {st.get('peak')}, eşik {st.get('th')})")
                continue
            self.ui.state("thinking")
            text = self.stt.transcribe(audio)
            if self.stt.rejected:
                status(f"yok sayıldı (uydurma olabilir): {self.stt.rejected}")
                self.stt.rejected = ""
            if not text or len(norm(text)) < 2:
                continue
            if self.heard_self(text):
                status(f"yok sayıldı (kendi sesi): {text}")
                continue
            status(f"sen> {text}")
            self.ui.message("user", text)
            idle_until = time.time() + self.v.get("idle_sleep_s", 60)
            reply = self.j.handle(text, say=self.say, ask=self.ask)
            self.ui.message("jarvis", reply)
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
