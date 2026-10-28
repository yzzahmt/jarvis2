"""Türkçe konuşma tanıma. Önce Gemini (bulut, ~1 sn, Mac'i yormaz), yoksa/olmazsa faster-whisper (yerel).
Yerel model yalnızca gerektiğinde yüklenir (2,3 GB bellek, HDD'den ~40 sn). Ses diske kaydedilmez."""
import base64
import io
import os
import re
import threading
import wave

import httpx
import numpy as np

from ..text import fix_stt

# Bağlam ipucu: model bu kelimeleri ve Türkçe komut tarzını daha iyi tanır
HINT = ("Jarvis, Zorin OS, Linux Mint, YouTube, Mac, Gemini, Safari, Spotify. "
        "Jarvis, testleri çalıştır. Sesi otuz yap. İndirilenler klasöründe kaç PDF var? Uygulamayı aç, müziği durdur.")
GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"


def wav_bytes(audio: np.ndarray, rate=16000) -> bytes:
    x = audio if audio.dtype == np.int16 else (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(x.tobytes())
    return buf.getvalue()


class STT:
    def __init__(self, model="small", root=None, words=(), cloud_model="gemini-3.5-flash-lite", cloud=True):
        self.model_name, self.root = model, root
        self.cloud_model, self.cloud = cloud_model, cloud
        self.words = list(words)
        self.hint = (", ".join(self.words) + ". " if self.words else "") + HINT   # kişisel kelimeler önce
        self.m = None
        self.lock = threading.Lock()
        self.allow = lambda: True          # günlük bulut sınırı (ses döngüsü bağlar)
        self.used = lambda: None           # bulut isteği sayacı
        if not self._key():
            self._local()                  # bulut yoksa hemen yükle (ilk komut beklemesin)

    @staticmethod
    def _key():
        return os.environ.get("GEMINI_API_KEY", "")

    def _local(self):
        with self.lock:
            if self.m is None:
                from faster_whisper import WhisperModel
                self.m = WhisperModel(self.model_name, device="cpu", compute_type="int8", download_root=self.root)
        return self.m

    def _gemini(self, audio) -> str | None:
        if not (self.cloud and self._key() and self.allow()):
            return None
        self.used()
        prompt = ("Bu Türkçe ses kaydını kelimesi kelimesine yazıya dök. Yalnızca söyleneni yaz; konuşma yoksa boş bırak. "
                  "Geçebilecek özel adlar: " + self.hint)
        try:
            r = httpx.post(GEMINI.format(self.cloud_model), params={"key": self._key()}, timeout=10, json={
                "contents": [{"parts": [{"text": prompt}, {"inline_data": {
                    "mime_type": "audio/wav", "data": base64.b64encode(wav_bytes(audio)).decode()}}]}],
                "generationConfig": {"temperature": 0, "thinkingConfig": {"thinkingLevel": "minimal"}}})
            if r.status_code != 200:
                return None
            parts = r.json()["candidates"][0].get("content", {}).get("parts", [])
            return " ".join(p.get("text", "") for p in parts).strip()
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            return None

    def _whisper(self, audio) -> str:
        x = audio.astype(np.float32) / (32768.0 if audio.dtype == np.int16 else 1.0)
        segs, _ = self._local().transcribe(x, language="tr", beam_size=5, vad_filter=True, temperature=0.0,
                                           initial_prompt=self.hint, condition_on_previous_text=False,
                                           no_speech_threshold=0.6, log_prob_threshold=-1.0)
        return " ".join(s.text.strip() for s in segs).strip()

    def transcribe(self, audio: np.ndarray) -> str:
        t = self._gemini(audio)
        if t is None:                      # internet/kota yok: yerel
            t = self._whisper(audio)
        t = fix_stt(t)
        return re.sub(r"^\s*(hey|hay|hi)?[ ,]*jarvis[.,!? ]*", "", t, flags=re.I).strip()   # uyandırma sözü komut değil


def record_utterance(frames, rate=16000, start_timeout=6.0, silence=0.9, max_len=20.0, thresh=None, stats=None,
                     preroll=()):
    """frames: int16 çerçeve üreteci. Konuşma başlayıp sessizlikle bitince sesi döndürür; yoksa None.
    preroll: söze girilen anın son karelerİ (konuşmanın başı kaybolmasın) — varsa konuşma başlamış sayılır.
    stats: verilirse en yüksek seviye ve eşik yazılır (duyulmadı günlüğü için)."""
    got, heard, quiet, total, noise = list(preroll), bool(preroll), 0.0, 0.0, []
    th = thresh or 0.012
    peak = 0.0
    for f in frames:
        if f is None:
            return None
        dur = len(f) / rate
        total += dur
        level = float(np.sqrt(np.mean((f.astype(np.float32) / 32768.0) ** 2)))
        peak = max(peak, level)
        if stats is not None:
            stats.update(peak=round(peak, 4), th=round(th, 4))
        if not heard:
            noise.append(level)
            th = thresh or max(0.007, 2.5 * float(np.median(noise[-25:])))   # kısık mikrofonda da duysun
            if level > th and total > 0.25:
                heard = True
                got.append(f)
            elif total > start_timeout:
                return None
            continue
        got.append(f)
        quiet = quiet + dur if level < th else 0.0
        if quiet >= silence or sum(len(g) for g in got) / rate >= max_len:
            break
    return np.concatenate(got) if got else None
