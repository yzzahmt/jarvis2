from __future__ import annotations

import numpy as np

from jarvis.stt.engine import STTEngine, TranscriptionResult
from jarvis.utils.audio_utils import int16_to_float32
from jarvis.utils.logging import get_logger

log = get_logger("stt.faster_whisper")


class FasterWhisperEngine(STTEngine):
    """Unused on macOS in Phase 1 (CPU-only, slower than mlx-whisper on Apple
    Silicon) — kept ready as the Windows-port STT backend for a later phase,
    since CTranslate2 has no MLX equivalent there."""

    def __init__(self, model: str = "medium") -> None:
        from faster_whisper import WhisperModel

        self._model = WhisperModel(model, device="cpu", compute_type="int8")
        log.info("faster-whisper ready (%s, cpu)", model)

    def transcribe(self, pcm_int16: np.ndarray, language: str = "auto") -> TranscriptionResult:
        audio = int16_to_float32(pcm_int16)
        segments, info = self._model.transcribe(
            audio, language=None if language == "auto" else language
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        return TranscriptionResult(text=text, language=info.language)
