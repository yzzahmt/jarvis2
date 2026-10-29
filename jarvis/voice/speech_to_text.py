"""Türkçe konuşma tanıma — kaynak zinciri, biri biterse sıradaki (hiçbiri bitmez):
1. Gemini: her model ayrı kotadır → modeller × anahtarlar (~1 sn, en iyi Türkçe+İngilizce)
2. Groq Whisper (ücretsiz anahtar, ~0,6 sn)
3. Mac'in cihaz içi tanıması (data/bin/apple_stt; ücretsiz, internetsiz, kotasız, ~0,4 sn)
4. faster-whisper (yerel, 2,3 GB bellek; yalnızca hepsi yoksa yüklenir)
Ses kalıcı kaydedilmez (Mac tanıması için data/tmp'ye yazılıp hemen silinir)."""
import base64
import difflib
import io
import os
import re
import subprocess
import threading
import time
import wave

import httpx
import numpy as np

from ..text import fix_stt

# Yalnızca özel adların yazımı. Örnek CÜMLE ya da genel kelime (API, .env…) koyma: boş seste model bunlardan
# komut uyduruyordu ("testleri çalıştır" → Zorin, "env'deki API key'ini güncelle").
NAMES = "Jarvis, Zorin OS, Linux Mint, YouTube, Gemini, ChatGPT, Spotify, Trendyol, iyzico"
# Talimatta ÖRNEK KELİME de yok: "screenshot" örneğinden "screenshot'ı kaydet" uyduruldu (017).
PROMPT = """Sen bir konuşma yazıya dökücüsün. Kayıtta bir kişi bilgisayardaki asistanına Türkçe konuşuyor; Türkçenin içinde İngilizce kelimeler geçebilir.

Kurallar:
- Yalnızca kayıtta gerçekten söyleneni, söylendiği sırayla yaz. Çevirme, özetleme, düzeltme, cevap verme.
- İngilizce ve yabancı kelimeleri özgün yazımıyla yaz; Türkçe ekleri kesme işaretiyle bağla.
- Kısaltmaları büyük harfle yaz.
- Kayıtta anlaşılır konuşma yoksa (sessizlik, gürültü, nefes, müzik, uzaktaki TV/konuşma) hiçbir şey yazma, boş döndür. Asla tahmin edip cümle uydurma."""
# Gemini'ye ad listesi de verilmez: "Jarvis, Spotify'ı aç" listedeki iki addan uyduruldu (020). Liste yalnız Groq/Mac/whisper'a.
GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/{}:generateContent"
GROQ = "https://api.groq.com/openai/v1/audio/transcriptions"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
APPLE = os.path.join(ROOT, "data", "bin", "apple_stt")


def louder(audio: np.ndarray, rate=16000) -> np.ndarray:
    """Kısık kaydı yükselt (en yüksek 30 ms ~0,1 RMS; en çok 8 kat): kasmadan konuşulan ses de iyi tanınsın."""
    x = audio.astype(np.float32)
    n = rate * 3 // 100
    if len(x) < n:
        return audio
    peak = float(np.sqrt((x[: len(x) // n * n].reshape(-1, n) ** 2).mean(axis=1)).max()) / 32768.0
    g = min(8.0, 0.1 / peak) if peak > 0 else 1.0
    return audio if g <= 1.2 else np.clip(x * g, -32767, 32767).astype(np.int16)


def wav_bytes(audio: np.ndarray, rate=16000) -> bytes:
    x = audio if audio.dtype == np.int16 else (np.clip(audio, -1, 1) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(x.tobytes())
    return buf.getvalue()


def speechy(audio: np.ndarray, rate=16000) -> bool:
    """Kayıtta konuşma var mı: arka plan gürültüsünün belirgin üstünde, en az 120 ms kesintisiz ses.
    Ölçüm (28.10): konuşma 29-90 kare, beyaz/kahverengi gürültü 0, klavye tıkırtısı 1, çok kısık konuşma 5.
    Yoksa modele gönderilmez: boş/gürültülü seste ad listesinden komut uyduruyordu ("env'deki API key'ini güncelle")."""
    x = audio.astype(np.float32) / (32768.0 if audio.dtype == np.int16 else 1.0)
    n = rate * 3 // 100
    if len(x) < 4 * n:
        return False
    r = np.sqrt((x[: len(x) // n * n].reshape(-1, n) ** 2).mean(axis=1))
    on = r > max(2.5 * float(np.percentile(r, 20)), 0.006)
    run = best = 0
    for v in on:
        run = run + 1 if v else 0
        best = max(best, run)
    if best < 4:
        return False
    return vad_speech(x) >= 0.3


def vad_speech(x: np.ndarray) -> float:
    """Silero VAD (faster-whisper içinde, yerel, ~5 ms): kayıttaki insan konuşması süresi (sn).
    Ölçüm (29.10): konuşma 3,7-3,8 sn; beyaz/kahverengi gürültü, klavye, sessizlik 0. Yüklenemezse kapıyı geçer."""
    try:
        from faster_whisper.vad import VadOptions, get_speech_timestamps
    except Exception:
        return 99.0
    ts = get_speech_timestamps(x.astype(np.float32), VadOptions(threshold=0.5, min_speech_duration_ms=250))
    return sum(t["end"] - t["start"] for t in ts) / 16000


def _words(t: str) -> list[str]:
    return re.findall(r"\w+", (t or "").replace("I", "ı").replace("İ", "i").lower())


def agree(main: str, check: str) -> bool:
    """İkinci kulak (Mac tanıması) asıl metni doğruluyor mu: kelimelerinin en az dörtte biri (benzerlikle) orada.
    Mac İngilizce kelimeleri bozar ama Türkçe kelimeler tutar; uydurma cümlede ise hiç örtüşme olmaz."""
    a, b = _words(main), _words(check)
    if not a:
        return True
    if not b:
        return False
    hit = sum(1 for w in a if any(difflib.SequenceMatcher(None, w, x).ratio() >= 0.75 for x in b))
    return hit >= 1 and hit / len(a) >= 0.25


def clean(t: str) -> str:
    """Model talimatı/ad listesini geri yazarsa (konuşma yokken olur) boş say."""
    t = t.strip().strip('"\u201c\u201d').strip()
    if not t or "yazıya dökücü" in t or t.count(",") >= 6 and "Zorin OS" in t:
        return ""
    return t


class STT:
    def __init__(self, model="small", root=None, words=(), cloud_model="gemini-3.5-flash-lite", cloud=True,
                 cloud_models=None):
        self.model_name, self.root = model, root
        self.cloud = cloud
        self.cloud_models = list(cloud_models or [cloud_model])
        self.words = list(words)
        self.hint = ", ".join(self.words + [NAMES])                          # kişisel kelimeler önce
        self.m = None
        self.lock = threading.Lock()
        self.allow = lambda: True          # günlük bulut sınırı (ses döngüsü bağlar)
        self.used = lambda name="gemini-stt": None   # bulut isteği sayacı
        self.until: dict[str, float] = {}  # kotası dolan kaynak → ne zamana kadar atlanır
        self.apple = None
        self.apple_ok = False              # Mac tanıması bu oturumda en az bir kez metin döndürdü mü (veto hakkı)
        self.apple_err = ""
        self.last = ""                     # son kullanılan kaynak (durum için)
        self.rejected = ""                 # ikinci kulağın reddettiği son metin (günlük için)

    @staticmethod
    def _keys():
        return [k for k in (os.environ.get("GEMINI_API_KEY", ""), os.environ.get("GEMINI_API_KEY_2", "")) if k]

    @classmethod
    def _key(cls):
        return (cls._keys() or [""])[0]

    def _skip(self, name):
        return self.until.get(name, 0) > time.time()

    def _cool(self, name, status):
        self.until[name] = time.time() + (600 if status == 429 else 60)   # kota: 10 dk, yoğunluk/ağ: 1 dk

    def _local(self):
        with self.lock:
            if self.m is None:
                from faster_whisper import WhisperModel
                self.m = WhisperModel(self.model_name, device="cpu", compute_type="int8", download_root=self.root)
        return self.m

    def _gemini(self, audio) -> str | None:
        if not (self.cloud and self._keys() and self.allow()):
            return None
        body = {"systemInstruction": {"parts": [{"text": PROMPT}]},
                "contents": [{"parts": [{"inline_data": {
                    "mime_type": "audio/wav", "data": base64.b64encode(wav_bytes(audio)).decode()}}]}],
                "generationConfig": {"temperature": 0, "thinkingConfig": {"thinkingLevel": "minimal"}}}
        tmo = 10 + len(audio) / 16000 / 4  # uzun konuşma (1-2 dk) daha uzun sürer; 10 sn'de kesilip boşa gidiyordu
        for model in self.cloud_models:    # her model ayrı kota; her birinde iki anahtar
            for i, key in enumerate(self._keys()):
                name = f"{model}#{i + 1}"
                if self._skip(name):
                    continue
                self.used()
                try:
                    r = httpx.post(GEMINI.format(model), params={"key": key}, timeout=tmo, json=body)
                    if r.status_code != 200:
                        self._cool(name, r.status_code)
                        continue
                    parts = r.json()["candidates"][0].get("content", {}).get("parts", [])
                    self.last = f"gemini {model}"
                    return clean(" ".join(p.get("text", "") for p in parts))
                except (httpx.HTTPError, KeyError, IndexError, ValueError):
                    self._cool(name, 0)
        return None

    def _groq(self, audio) -> str | None:
        key = os.environ.get("GROQ_API_KEY", "")
        if not (self.cloud and key and self.allow()) or self._skip("groq"):
            return None
        self.used("groq-stt")
        try:
            r = httpx.post(GROQ, headers={"Authorization": f"Bearer {key}"}, timeout=10 + len(audio) / 64000,
                           files={"file": ("ses.wav", wav_bytes(audio), "audio/wav")},
                           data={"model": "whisper-large-v3-turbo", "language": "tr", "temperature": "0",
                                 "prompt": self.hint})
            if r.status_code != 200:
                self._cool("groq", r.status_code)
                return None
            self.last = "groq whisper"
            return clean(r.json().get("text", ""))
        except (httpx.HTTPError, ValueError):
            self._cool("groq", 0)
            return None

    def _apple(self, audio) -> str | None:
        """Mac'in cihaz içi tanıması: kalıcı yardımcı süreç, stdin'e wav yolu, stdout'tan tek satır metin."""
        if self.apple is False or not os.path.exists(APPLE) or self._skip("apple"):
            return None
        tmp = os.path.join(ROOT, "data", "tmp", f"stt-{os.getpid()}.wav")
        try:
            with self.lock:
                if self.apple is None or self.apple.poll() is not None:
                    self.apple = subprocess.Popen([APPLE, self.hint], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                                  text=True, bufsize=1)
                    first = self.apple.stdout.readline().strip()
                    if first != "hazır":         # izin yok / Türkçe yok: bu oturumda bir daha deneme
                        self.apple.kill()
                        self.apple = False
                        return None
                os.makedirs(os.path.dirname(tmp), exist_ok=True)
                with open(tmp, "wb") as f:
                    f.write(wav_bytes(audio))
                self.apple.stdin.write(tmp + "\n")
                self.apple.stdin.flush()
                out = self.apple.stdout.readline()
            if out.startswith("!"):            # tanıma çalışmadı (izin/bağlam): "boş" değil, bilinmiyor → veto yok
                self.apple_err = out[1:].strip()
                return None
            out = clean(out)
            if out:
                self.apple_ok = True
            self.last = "mac"
            return out
        except (OSError, ValueError):
            self._cool("apple", 0)
            return None
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass

    def _whisper(self, audio) -> str:
        x = audio.astype(np.float32) / (32768.0 if audio.dtype == np.int16 else 1.0)
        segs, _ = self._local().transcribe(x, language="tr", beam_size=5, vad_filter=True, temperature=0.0,
                                           initial_prompt=self.hint, condition_on_previous_text=False,
                                           no_speech_threshold=0.6, log_prob_threshold=-1.0)
        self.last = "yerel whisper"
        return " ".join(s.text.strip() for s in segs).strip()

    def transcribe(self, audio: np.ndarray) -> str:
        if not speechy(audio):             # sessiz/gürültülü kayıtta model ad listesinden komut uyduruyor; hiç sorma
            return ""
        audio = louder(audio)
        # İkinci kulak: Mac tanıması paralel çalışır (kotasız, ~0,4 sn). Bulut ipucundan cümle uydurabilir,
        # Mac uydurmaz → Mac bir şey duymadıysa ya da örtüşmüyorsa metin atılır (kendi kendine komut olmasın).
        check: dict = {}
        th = threading.Thread(target=lambda: check.update(t=self._apple(audio)), daemon=True)
        th.start()
        t = None
        for src in (self._gemini, self._groq):
            t = src(audio)
            if t is not None:
                break
        th.join(1.5 if t else 4)           # bulut cevap verdiyse Mac'i uzun bekleme (yavaşlık)
        mac = check.get("t")
        if t is None:
            t = mac if mac is not None else self._whisper(audio)
        elif mac and t and not agree(t, mac):
            # Yalnız Mac BİR ŞEY duyup tamamen farklıysa veto (uzaktaki TV/konuşma). Mac boş döndüyse veto yok:
            # 29.10'da uygulama içinde boş dönüp "Naber, nasılsın?" gibi gerçek sözleri atıyordu. Uydurmaya karşı
            # asıl koruma Silero VAD (speechy).
            self.rejected = f"{t!r} (Mac duydu: {mac!r})"
            return ""
        t = fix_stt(t)
        return re.sub(r"^\s*(hey|hay|hi)?[ ,]*jarvis[.,!? ]*", "", t, flags=re.I).strip()   # uyandırma sözü komut değil


def record_utterance(frames, rate=16000, start_timeout=6.0, silence=1.0, max_len=120.0, thresh=None, stats=None,
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
        quiet = quiet + dur if level < 0.6 * th else 0.0   # başladıktan sonra daha düşük eşik: yumuşak sesler kesilmesin
        if quiet >= silence or sum(len(g) for g in got) / rate >= max_len:
            break
    return np.concatenate(got) if got else None
