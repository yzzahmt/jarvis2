import os
from pathlib import Path

import yaml

HOME = Path(os.environ.get("JARVIS_HOME", Path(__file__).resolve().parents[1]))


def load(name: str) -> dict:
    with open(HOME / "config" / f"{name}.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def path(rel: str) -> Path:
    p = Path(os.path.expanduser(rel))
    return p if p.is_absolute() else HOME / p


def load_env():
    """Jarvis/.env (git dışı) içindeki API anahtarlarını ortam değişkenine yükler; var olanı ezmez."""
    f = HOME / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                v = v.split(" #")[0].strip().strip('"')
                if v:
                    os.environ.setdefault(k.strip(), v)
