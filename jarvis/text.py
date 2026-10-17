import re


def norm(s: str) -> str:
    """Türkçe uyumlu küçük harf + boşluk sadeleştirme."""
    s = s.replace("I", "ı").replace("İ", "i").lower()
    s = re.sub(r"[^\w\s:'./-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


SECRET = re.compile(r"(parola|şifre|sifre|password|passwd|token|api[_ ]?key|secret|BEGIN [A-Z ]*PRIVATE KEY)", re.I)


def looks_secret(s: str) -> bool:
    return bool(SECRET.search(s or ""))
