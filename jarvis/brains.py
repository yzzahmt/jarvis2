"""Çoklu beyin: birden fazla ücretsiz yapay zekâ sırayla denenir, kota/hata alan soğumaya alınır.
Hepsi OpenAI uyumlu biçim konuşur (yerel Ollama dahil, /v1), bu yüzden bir görevin ortasında bile
sağlayıcı değişebilir. Hepsi tükenirse yerel model çalışır; Jarvis hiç takılmaz. Claude kullanılmaz."""
import threading
import time

from .llm import LLMError, OpenAICompat

COOL = {429: 600, 402: 3600, 401: None, 403: None}   # sn; None = bu oturumda kapalı


class Brains:
    def __init__(self, cfgs: list[dict], db=None):
        self.all = [OpenAICompat(c) for c in cfgs]
        self.until: dict[str, float] = {}
        self.db = db
        self.lock = threading.Lock()
        self.last_model = None
        self.last_tokens = None

    @property
    def is_cloud(self):
        return any(b.is_cloud for b in self.ready())

    @property
    def model(self):
        return self.last_model

    def ready(self):
        now = time.time()
        return [b for b in self.all if b.available() and self.until.get(b.name, 0) <= now]

    def status(self) -> list[dict]:
        now = time.time()
        return [{"name": b.name, "model": b.model, "key": b.available(),
                 "wait_s": max(0, int(self.until.get(b.name, 0) - now))} for b in self.all]

    def _cool(self, b, e: LLMError):
        sec = COOL.get(e.status, 120) if e.status else 60      # zaman aşımı / ağ hatası: kısa bekleme
        if e.retry_after:
            sec = max(sec or 0, e.retry_after)
        with self.lock:
            self.until[b.name] = float("inf") if sec is None else time.time() + sec

    def _try(self, fn_name, *a, **k):
        errors = []
        for b in self.ready():
            try:
                out = getattr(b, fn_name)(*a, **k)
                self.last_model, self.last_tokens = f"{b.name}:{b.model}", b.last_tokens
                self._count(b)
                return out
            except LLMError as e:
                errors.append(f"{b.name}: {str(e)[:80]}")
                self._cool(b, e)
        raise LLMError("Hiçbir yapay zekâ yanıt vermedi: " + "; ".join(errors or ["hiçbiri ayarlı değil"]))

    def _count(self, b):
        if self.db is not None:
            day = time.strftime("%Y-%m-%d")
            k = f"kullanim:{day}:{b.name}"
            try:
                self.db.remember(k, (self.db.recall(k) or 0) + 1, kind="usage")
            except Exception:
                pass

    def chat_tools(self, messages, tools, model=None, max_tokens=1200):
        return self._try("chat_tools", messages, tools, max_tokens=max_tokens)

    def chat(self, messages, max_tokens=400):
        return self._try("chat", messages, max_tokens=max_tokens)

    # mesaj biçimi tüm sağlayıcılarda aynı
    def assistant_msg(self, rep):
        return OpenAICompat.assistant_msg(None, rep)

    def tool_msg(self, call, content):
        return OpenAICompat.tool_msg(None, call, content)
