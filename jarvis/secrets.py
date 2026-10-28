"""Gizli bilgiler (site şifreleri, API anahtarları) macOS Anahtar Zinciri'nde, hizmet adı "jarvis".
Yapay zekâ modeli değerleri ASLA görmez: yalnızca adlarını bilir; tarayıcı aracı değeri doğrudan alana yazar
veya sayfadan alıp doğrudan dosyaya kaydeder. Ekleme: python -m jarvis secret set <ad>"""
import getpass
import re
import subprocess
import sys
from pathlib import Path

SERVICE = "jarvis"
NAME = re.compile(r"^[\w.@:-]{1,80}$")


def _sec(*args, input=None):
    return subprocess.run(["security", *args], capture_output=True, text=True, input=input, timeout=15)


def get(name: str) -> str | None:
    if not NAME.match(name or ""):
        return None
    r = _sec("find-generic-password", "-s", SERVICE, "-a", name, "-w")
    return r.stdout.rstrip("\n") if r.returncode == 0 else None


def put(name: str, value: str) -> bool:
    if not NAME.match(name or "") or not value:
        return False
    return _sec("add-generic-password", "-U", "-s", SERVICE, "-a", name, "-w", value).returncode == 0


def delete(name: str) -> bool:
    return _sec("delete-generic-password", "-s", SERVICE, "-a", name).returncode == 0


def names() -> list[str]:
    """Kayıtlı adlar (değerler değil)."""
    out = _sec("dump-keychain").stdout
    found = []
    for item in out.split("keychain: ")[1:]:          # her kayıt ayrı blok; alan sırası sabit değil
        f = dict(re.findall(r'"(svce|acct)"<blob>="([^"]*)"', item))
        if f.get("svce") == SERVICE and f.get("acct"):
            found.append(f["acct"])
    return sorted(dict.fromkeys(found))


def mask(v: str) -> str:
    return (v[:4] + "…" + v[-2:]) if len(v) > 10 else "…"


def write_env(path: str, var: str, value: str) -> str:
    """Değeri bir .env dosyasına VAR=değer olarak yazar (varsa günceller). Dönen metin değeri içermez."""
    if not re.match(r"^[A-Z_][A-Z0-9_]*$", var):
        return "geçersiz değişken adı (BÜYÜK_HARF_ALT_ÇİZGİ olmalı)"
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = p.read_text().splitlines() if p.exists() else []
    lines = [l for l in lines if not re.match(rf"^\s*{var}\s*=", l)] + [f"{var}={value}"]
    p.write_text("\n".join(lines) + "\n")
    gi = p.parent / ".gitignore"
    if (p.parent / ".git").exists() and p.name not in (gi.read_text() if gi.exists() else ""):
        with gi.open("a") as f:
            f.write(f"\n{p.name}\n")
    return f"{var} → {p} yazıldı ({mask(value)})"


def cli(argv):
    """python -m jarvis secret set|del|list [ad]"""
    cmd, name = (argv + ["", ""])[:2]
    if cmd == "set" and name:
        v = getpass.getpass(f"{name} değeri (görünmez): ")
        print("kaydedildi" if put(name, v) else "kaydedilemedi")
    elif cmd == "del" and name:
        print("silindi" if delete(name) else "bulunamadı")
    elif cmd == "list":
        print("\n".join(names()) or "(boş)")
    else:
        print("kullanım: python -m jarvis secret set <ad> | del <ad> | list\n"
              "ad örnekleri: trendyol.com:email, trendyol.com:sifre, iyzico.com:email")
        sys.exit(1)
