from __future__ import annotations

from pathlib import Path

import httpx

from jarvis.utils.logging import get_logger

log = get_logger("tts.voices")

VOICES_DIR = Path.home() / ".jarvis" / "voices"
HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"

# A handful of good starter voices spanning languages/genders for the "change
# voice" setting. voice_id -> (lang_dir, lang_country_dir, name, quality)
KNOWN_VOICES: dict[str, tuple[str, str, str, str]] = {
    "en_US-lessac-medium": ("en", "en_US", "lessac", "medium"),
    "en_US-amy-medium": ("en", "en_US", "amy", "medium"),
    "en_GB-alan-medium": ("en", "en_GB", "alan", "medium"),
    # "fahrettin"/"fettah" were pulled from the upstream repo — "dfki" (male)
    # is the only tr_TR voice piper-voices still ships as of 2026-09.
    "tr_TR-dfki-medium": ("tr", "tr_TR", "dfki", "medium"),
}


def _urls_for(voice_id: str) -> tuple[str, str]:
    lang, lang_country, name, quality = KNOWN_VOICES[voice_id]
    base = f"{HF_BASE}/{lang}/{lang_country}/{name}/{quality}/{voice_id}"
    return f"{base}.onnx", f"{base}.onnx.json"


def ensure_voice(voice_id: str) -> tuple[Path, Path]:
    """Downloads the voice model on first use, then reuses the local cache."""
    if voice_id not in KNOWN_VOICES:
        raise ValueError(f"unknown voice_id '{voice_id}' — add it to KNOWN_VOICES first")

    VOICES_DIR.mkdir(parents=True, exist_ok=True)
    onnx_path = VOICES_DIR / f"{voice_id}.onnx"
    json_path = VOICES_DIR / f"{voice_id}.onnx.json"

    if onnx_path.exists() and json_path.exists():
        return onnx_path, json_path

    onnx_url, json_url = _urls_for(voice_id)
    log.info("downloading voice model %s", voice_id)
    with httpx.Client(follow_redirects=True, timeout=120) as client:
        for url, dest in ((onnx_url, onnx_path), (json_url, json_path)):
            resp = client.get(url)
            resp.raise_for_status()
            dest.write_bytes(resp.content)
    log.info("voice model %s ready", voice_id)
    return onnx_path, json_path
