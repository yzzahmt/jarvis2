"""Çoklu beyin: birden fazla ücretsiz yapay zekâ sırayla denenir, kota/hata alan soğumaya alınır.
Hepsi OpenAI uyumlu biçim konuşur (yerel Ollama dahil, /v1), bu yüzden bir görevin ortasında bile
sağlayıcı değişebilir. Hepsi tükenirse yerel model çalışır; Jarvis hiç takılmaz. Claude kullanılmaz."""
import threading
import time

from .llm import LLMError, OpenAICompat

COOL = {429: 600, 402: 3600, 401: None, 403: None, 400: 30}   # sn; None = bu oturumda kapalı; 400 = istek hatası, kısa


class Brains:
    def __init__(self, cfgs: list[dict], db=None, daily_cap=0):
        self.all = [OpenAICompat(c) for c in cfgs]
        self.daily_cap = daily_cap          # günlük bulut çağrısı üst sınırı (0 = sınırsız); dolunca yalnız yerel
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

    def today(self) -> int:
        """Bugünkü bulut çağrısı sayısı (tüm sağlayıcılar)."""
        if self.db is None:
            return 0
        pre = f"kullanim:{time.strftime('%Y-%m-%d')}:"
        local = {b.name for b in self.all if not b.is_cloud}
        return sum(int(m["value"] or 0) for m in self.db.memories("usage")
                   if m["key"].startswith(pre) and m["key"][len(pre):] not in local)

    def can_cloud(self) -> bool:
        return not self.daily_cap or self.today() < self.daily_cap

    def note(self, name):
        """Brains dışından yapılan bulut isteğini say (ör. ses tanıma)."""
        self._count(type("B", (), {"name": name})())

    def ready(self):
        now = time.time()
        if not self.can_cloud():                                   # günlük sınır doldu: yalnızca yerel
            return [b for b in self.all if not b.is_cloud and b.available()]
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

    def _try(self, fn_name, *a, only=None, strong=False, **k):
        errors = []
        order = self.ready()
        if strong:          # güçlü beyinler önce, sonra hızlı/lite olanlar (sıra korunur)
            order = sorted(order, key=lambda b: not getattr(b, "strong", False))
        else:               # sohbet/yönlendirme: güçlüler en sona (hız + kotaları ajan işlerine kalsın)
            order = sorted(order, key=lambda b: getattr(b, "strong", False))
        for b in filter(only or bool, order):
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
        return self._try("chat_tools", messages, tools, max_tokens=max_tokens, strong=True)

    def chat(self, messages, max_tokens=400):
        return self._try("chat", messages, max_tokens=max_tokens)

    def json(self, messages, max_tokens=200):
        return self._try("json", messages, max_tokens=max_tokens)

    def can_see(self) -> bool:
        return any(b.sees for b in self.ready())

    def vision(self, question, image_path):
        return self._try("vision", question, image_path, only=lambda b: b.sees, strong=True)

    # mesaj biçimi tüm sağlayıcılarda aynı
    def assistant_msg(self, rep):
        return OpenAICompat.assistant_msg(None, rep)

    def tool_msg(self, call, content):
        return OpenAICompat.tool_msg(None, call, content)
