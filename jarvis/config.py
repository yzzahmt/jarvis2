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
