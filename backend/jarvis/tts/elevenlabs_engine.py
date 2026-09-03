from __future__ import annotations

import io
import subprocess
import wave

import httpx
import numpy as np
import sounddevice as sd

from jarvis.utils.logging import get_logger

log = get_logger("tts.elevenlabs")

API_BASE = "https://api.elevenlabs.io/v1/text-to-speech"
MODEL_ID = "eleven_multilingual_v2"  # handles Turkish (and any language) with any voice
OUTPUT_SR = 22050


class ElevenLabsEngine:
    """Cloud TTS via ElevenLabs. Same speak()/synthesize_wav_bytes()/set_voice()
    surface as PiperEngine so the orchestrator can swap between them freely."""

    def __init__(self, api_key: str, voice_id: str) -> None:
        if not api_key:
            raise ValueError(
                "ElevenLabs TTS needs an API key — set it in Settings > Ses (TTS) first."
            )
        self.api_key = api_key
        self.voice_id = voice_id

    def set_voice(self, voice_id: str) -> None:
        self.voice_id = voice_id

    def _synthesize_pcm(self, text: str) -> tuple[np.ndarray, int]:
        resp = httpx.post(
            f"{API_BASE}/{self.voice_id}",
            headers={"xi-api-key": self.api_key, "accept": "audio/mpeg"},
            json={
                "text": text,
                "model_id": MODEL_ID,
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            },
            timeout=30,
        )
        resp.raise_for_status()

        # ElevenLabs returns mp3; decode to the same PCM shape Piper produces.
        proc = subprocess.run(
            ["ffmpeg", "-i", "pipe:0", "-f", "s16le", "-ar", str(OUTPUT_SR), "-ac", "1", "pipe:1"],
            input=resp.content,
            capture_output=True,
            timeout=30,
            check=True,
        )
        audio = np.frombuffer(proc.stdout, dtype=np.int16)
        return audio, OUTPUT_SR

    def synthesize_wav_bytes(self, text: str) -> bytes:
        audio, sample_rate = self._synthesize_pcm(text)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio.tobytes())
        return buf.getvalue()

    def speak(self, text: str) -> None:
        audio, sample_rate = self._synthesize_pcm(text)
        if audio.size == 0:
            return
        sd.play(audio, samplerate=sample_rate, blocking=True)
