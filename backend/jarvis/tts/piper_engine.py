from __future__ import annotations

import io
import wave

import numpy as np
import sounddevice as sd

from jarvis.tts.voices import ensure_voice
from jarvis.utils.logging import get_logger

log = get_logger("tts.piper")


class PiperEngine:
    def __init__(self, voice_id: str) -> None:
        self.voice_id = voice_id
        self._voice = None
        self._load(voice_id)

    def _load(self, voice_id: str) -> None:
        from piper.voice import PiperVoice

        onnx_path, json_path = ensure_voice(voice_id)
        self._voice = PiperVoice.load(str(onnx_path), config_path=str(json_path))
        self.voice_id = voice_id
        log.info("piper voice loaded: %s", voice_id)

    def set_voice(self, voice_id: str) -> None:
        if voice_id != self.voice_id:
            self._load(voice_id)

    def _synthesize_pcm(self, text: str) -> tuple[np.ndarray, int]:
        """Returns (int16 mono PCM samples, sample_rate). piper-tts yields one
        AudioChunk per sentence; join them with a small breath-like pause so
        multi-sentence replies have a natural human cadence instead of running
        sentences together back-to-back."""
        chunks = list(self._voice.synthesize(text))
        if not chunks:
            return np.zeros(0, dtype=np.int16), 22050
        sample_rate = chunks[0].sample_rate
        pause = np.zeros(int(sample_rate * 0.22), dtype=np.int16)
        parts: list[np.ndarray] = []
        for i, c in enumerate(chunks):
            if i > 0:
                parts.append(pause)
            parts.append(c.audio_int16_array)
        audio = np.concatenate(parts)
        return audio, sample_rate

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
        """Blocking: synthesizes and plays through the default output device."""
        audio, sample_rate = self._synthesize_pcm(text)
        if audio.size == 0:
            return
        sd.play(audio, samplerate=sample_rate, blocking=True)
