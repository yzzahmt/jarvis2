import os
from pathlib import Path

# Eylem türü -> onay gerekir mi (settings.permissions.confirm listesine göre)
SENSITIVE_WORDS = {
    "delete": ["sil", "kaldır", "rm ", "temizle"],
    "install": ["yükle", "kur ", "install", "pip ", "brew ", "pacman", "apt "],
    "system": ["sistem ayar", "sudo", "kapat", "yeniden başlat", "reboot", "shutdown"],
    "account": ["hesab", "satın al", "ödeme", "giriş yap"],
    "external": ["gönder", "paylaş", "mail", "e-posta", "yükle internete"],
}


class Permissions:
    def __init__(self, cfg: dict):
        self.confirm = set(cfg.get("confirm", []))
        self.dirs = [Path(os.path.expanduser(d)).resolve() for d in cfg.get("allowed_dirs", [])]
        self.apps = {a.lower(): a for a in cfg.get("allowed_apps", [])}

    def sensitive(self, text: str) -> list[str]:
        t = text.lower()
        return [k for k, ws in SENSITIVE_WORDS.items() if k in self.confirm and any(w in t for w in ws)]

    def needs_confirm(self, intent: str, text: str) -> list[str]:
        cats = self.sensitive(text)
        if intent in ("code", "shell") and "shell" in self.confirm:
            cats.append("shell")
        return sorted(set(cats))

    def dir_ok(self, p: str) -> bool:
        rp = Path(os.path.expanduser(p)).resolve()
        return any(rp == d or d in rp.parents for d in self.dirs)

    def app(self, name: str) -> str | None:
        n = name.lower().strip()
        return self.apps.get(n) or next((v for k, v in self.apps.items() if k.startswith(n) or n.startswith(k)), None)
