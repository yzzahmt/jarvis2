from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

CONFIG_DIR = Path.home() / ".jarvis"
CONFIG_PATH = CONFIG_DIR / "config.json"


class VoiceSettings(BaseModel):
    engine: Literal["piper", "elevenlabs"] = "piper"
    voice_id: str = "en_US-lessac-medium"
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: str = "Xb7hH8MSUJpSbSDYk0k2"  # "Alice" — natural multilingual female voice


class WakeWordSettings(BaseModel):
    enabled: bool = True
    keyword: str = "hey_jarvis"
    sensitivity: float = 0.5


class ClapSettings(BaseModel):
    enabled: bool = True
    claps_required: int = 2
    window_ms: int = 600


class SttSettings(BaseModel):
    engine: Literal["mlx_whisper", "faster_whisper"] = "mlx_whisper"
    model: str = "large-v3-turbo"
    language: str = "auto"


class LlmSettings(BaseModel):
    provider: Literal["ollama", "cloud"] = "ollama"
    ollama_model: str = "qwen2.5:7b-instruct"
    ollama_host: str = "http://127.0.0.1:11434"
    cloud_provider: Optional[Literal["groq"]] = None
    cloud_api_key: Optional[str] = None
    cloud_model: Optional[str] = None


class SystemSettings(BaseModel):
    confirm_before_open: bool = False


class DevicesSettings(BaseModel):
    # Windows PC reached over SSH for cross-device file transfer. Requires
    # OpenSSH Server enabled on the Windows side (Settings > Apps > Optional
    # Features > OpenSSH Server) and a key or password set up once by hand.
    windows_host: Optional[str] = None
    windows_user: Optional[str] = None
    windows_ssh_key_path: Optional[str] = None


class JarvisConfig(BaseModel):
    version: int = 1
    voice: VoiceSettings = Field(default_factory=VoiceSettings)
    theme: Literal["cyberpunk", "premium", "modern"] = "cyberpunk"
    input_mode: Literal["voice", "text"] = "voice"
    wake_word: WakeWordSettings = Field(default_factory=WakeWordSettings)
    clap_trigger: ClapSettings = Field(default_factory=ClapSettings)
    stt: SttSettings = Field(default_factory=SttSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)
    system: SystemSettings = Field(default_factory=SystemSettings)
    devices: DevicesSettings = Field(default_factory=DevicesSettings)


def load_config() -> JarvisConfig:
    if not CONFIG_PATH.exists():
        cfg = JarvisConfig()
        save_config(cfg)
        return cfg
    data = json.loads(CONFIG_PATH.read_text())
    return JarvisConfig.model_validate(data)


def save_config(cfg: JarvisConfig) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg.model_dump(), indent=2, ensure_ascii=False))


def update_config(partial: dict) -> JarvisConfig:
    cfg = load_config()
    merged = cfg.model_dump()
    _deep_merge(merged, partial)
    new_cfg = JarvisConfig.model_validate(merged)
    save_config(new_cfg)
    return new_cfg


def _deep_merge(base: dict, updates: dict) -> None:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
