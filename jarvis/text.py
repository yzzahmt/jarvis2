import re


def norm(s: str) -> str:
    """Türkçe uyumlu küçük harf + boşluk sadeleştirme."""
    s = s.replace("I", "ı").replace("İ", "i").lower()
    s = re.sub(r"[^\w\s:'./-]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


SECRET = re.compile(r"(parola|şifre|sifre|password|passwd|token|api[_ ]?key|secret|BEGIN [A-Z ]*PRIVATE KEY)", re.I)


def looks_secret(s: str) -> bool:
    return bool(SECRET.search(s or ""))


EMOJI = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF‍️←-⇿⌀-⏿⬀-⯿]")


def speakable(text: str) -> str:
    """Sesli okunacak metin: emoji, markdown işaretleri, kod ve bağlantılar ayıklanır."""
    t = EMOJI.sub("", text or "")
    t = re.sub(r"```.*?```", " kod bloğu ", t, flags=re.S)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)              # [metin](adres) -> metin
    t = re.sub(r"https?://\S+", "bağlantı", t)
    t = re.sub(r"[*_`#>|~]+", "", t)
    t = re.sub(r"^\s*[-•]\s+", "", t, flags=re.M)
    t = t.replace("✓", "").replace("✕", "")
    return re.sub(r"\s+", " ", t).strip()


# Whisper'ın sık yanlış duyduğu adlar
FIXES = [(re.compile(r"\b(c|ç|j|ş)[ae]r?v[iı]s+\b|\bjarvi[sz]\w*\b|\bcervis\b|\bçarviz\b", re.I), "Jarvis"),
         (re.compile(r"\b(zor[ıi]n|sor[ıi]n|zor in) ?(o ?es|os|oes)\b", re.I), "Zorin OS"),
         (re.compile(r"\byou ?tube|yutup|yutub\b", re.I), "YouTube")]


def fix_stt(text: str) -> str:
    for rx, rep in FIXES:
        text = rx.sub(rep, text)
    return text
