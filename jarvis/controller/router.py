"""Komut yönlendirme: önce kurallar (0 token), anlaşılmazsa yerel model."""
import re
from dataclasses import dataclass, field

from ..text import norm

INTENTS = ["time", "date", "sleep", "wake", "status", "stop", "open_app", "open_url", "youtube",
           "pick_result", "run_tests", "code", "remember", "recall", "tasks", "chat"]


@dataclass
class Intent:
    name: str
    args: dict = field(default_factory=dict)
    machine: str = "mac"
    source: str = "kural"


def detect_machine(t: str, machines: dict, default="mac") -> str:
    for name, m in machines.items():
        for a in [name, *(m or {}).get("aliases", [])]:
            if re.search(rf"\b{re.escape(norm(a))}", t):
                return name
    if re.search(r"\b(mac|macbook|bu bilgisayar)", t):
        return "mac"
    return default


def _strip_machine(t: str, machines: dict) -> str:
    words = [norm(a) for n, m in machines.items() for a in [n, *(m or {}).get("aliases", [])]]
    for w in sorted(words, key=len, reverse=True):
        t = re.sub(rf"\b{re.escape(w)}\S*\s*(bilgisayar\S*)?", " ", t)
    return re.sub(r"\s+", " ", t).strip()


ORD = {"birinci": 1, "ilk": 1, "ikinci": 2, "üçüncü": 3, "dördüncü": 4, "beşinci": 5}


def route(text: str, machines: dict) -> Intent | None:
    t = norm(text)
    t = re.sub(r"^(hey )?jarvis\b[ ,]*", "", t)
    if not t:
        return Intent("wake")
    m = lambda d="mac": detect_machine(t, machines, d)  # noqa: E731

    if re.fullmatch(r"(uyan|uyandın mı|orada mısın|burada mısın)", t):
        return Intent("wake")
    if re.search(r"\b(uyu|uyku moduna|uykuya geç|iyi geceler|şimdilik bu kadar|görüşürüz)\b", t):
        return Intent("sleep")
    if re.fullmatch(r"(dur|durdur|iptal|vazgeç|iptal et|görevi durdur)", t):
        return Intent("stop")
    if re.search(r"\bsaat (kaç|ne)|\bsaati söyle", t):
        return Intent("time")
    if re.search(r"\b(bugün (günlerden ne|ayın kaçı|ne günü)|tarih (ne|nedir)$|bugünün tarihi)", t):
        return Intent("date")
    if re.search(r"(çevrimiçi|online|bağlı mı|açık mı|durum(u|unu)? (ne|söyle|nedir)|bilgisayarlar)", t) \
            and not re.search(r"\b(youtube|test)", t):
        return Intent("status")
    if re.search(r"\b(görevler|son görev|görev geçmiş)", t):
        return Intent("tasks")
    mm = re.match(r"^(?:(?:hey )?jarvis[, ]+)?(?:hatırla|aklında tut|kaydet)[: ]+(.+?)\s*(?:=| değeri | olarak )\s*(.+)$",
                  text.strip(), re.I)
    if mm:  # değer orijinal yazımıyla saklanır (yol, büyük harf)
        return Intent("remember", {"key": norm(mm.group(1)), "value": mm.group(2).strip()})
    mm = re.match(r"^(.+?) (neydi|ne idi|nerede)$", t)
    if mm and not re.search(r"youtube|saat", t):
        return Intent("recall", {"key": mm.group(1)})
    mm = re.search(r"\b(\d+|" + "|".join(ORD) + r")\.? (videoyu|sonucu|videoyı|olanı)", t)
    if mm:
        g = mm.group(1)
        return Intent("pick_result", {"index": int(g) if g.isdigit() else ORD[g]}, machine=m("mint"))
    if "youtube" in t or re.search(r"\b(şarkı|müzi[kğ]|video|klip)\S*\b.*\b(aç|çal|dinle|izle|oynat)", t):
        q = _strip_machine(t, machines)
        q = re.sub(r"youtube\S*\s*(aç)?\s*(ve)?", " ", q)
        q = re.sub(r"\b(videosunu|videoyu|videolarını|video)\b|\b(ara|bul|aç|göster|oynat)\b", " ", q)
        q = re.sub(r"\bşu\b", " ", q)
        return Intent("youtube", {"query": re.sub(r"\s+", " ", q).strip()}, machine=m("mint"))
    mm = re.search(r"(https?://\S+|\b[\w-]+\.(?:com|org|net|io|dev|ai|tr|com\.tr)\b\S*)", text, re.I)
    if mm and re.search(r"\b(aç|git|göster)", t):
        url = mm.group(1)
        return Intent("open_url", {"url": url if url.startswith("http") else "https://" + url}, machine=m())
    if re.search(r"\btest\S*\b.*\b(çalıştır|koş|başlat|yap)", t):
        proj = re.search(r"(\S+) (projesi|projesinin|projemin|klasör)", t)
        return Intent("run_tests", {"project": proj.group(1) if proj else None}, machine=m("cachyos"))
    if re.search(r"\b(kod|hata\S* düzelt|düzelt|refactor|fonksiyon|geliştir|bug)\b", t):
        return Intent("code", {"task": text}, machine=m("cachyos"))
    mm = re.match(r"^(.+?)(?:'?(?:yi|yı|yu|yü|i|ı|u|ü))?(?: uygulamasını| programını)? (aç|başlat)$", t)
    if mm:
        return Intent("open_app", {"app": _strip_machine(mm.group(1), machines)}, machine=m())
    return None


LLM_SYSTEM = (
    "Sen JARVIS adlı Türkçe asistanın komut ayrıştırıcısısın. Kullanıcı cümlesini şu JSON'a çevir: "
    '{"intent": <' + "|".join(INTENTS) + '>, "args": {...}, "machine": "mac|cachyos|mint", '
    '"reply": "<sadece intent chat ise kısa Türkçe yanıt>"}. '
    "args: youtube->{query}, open_app->{app}, open_url->{url}, run_tests->{project}, code->{task}. "
    "cachyos: kodlama/test makinesi, mint: tarayıcı/YouTube makinesi, varsayılan mac. "
    "Şarkı/müzik/video çalma veya izleme her zaman youtube'dur. open_app yalnızca uygulama adı içindir. Örnekler: "
    '"tarkanın son şarkısını çal" -> {"intent":"youtube","args":{"query":"tarkan son şarkı"},"machine":"mint"}; '
    '"oyunumdaki hatayı düzelt" -> {"intent":"code","args":{"task":"oyundaki hatayı düzelt"},"machine":"cachyos"}; '
    '"nasılsın" -> {"intent":"chat","args":{},"machine":"mac","reply":"İyiyim, teşekkürler."}. Sadece JSON yaz.')


def route_llm(text: str, llm) -> Intent:
    d = llm.json([{"role": "system", "content": LLM_SYSTEM}, {"role": "user", "content": text}])
    name = d.get("intent") if d.get("intent") in INTENTS else "chat"
    args = d.get("args") or {}
    if name == "chat" and d.get("reply"):
        args["reply"] = d["reply"]
    mach = d.get("machine") if d.get("machine") in ("mac", "cachyos", "mint") else "mac"
    return Intent(name, args, mach, source="yerel-model")
