from __future__ import annotations

import numpy as np

from jarvis.stt.engine import STTEngine, TranscriptionResult
from jarvis.utils.audio_utils import int16_to_float32
from jarvis.utils.logging import get_logger

log = get_logger("stt.mlx_whisper")

MODEL_REPOS = {
    "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
    "medium": "mlx-community/whisper-medium-mlx",
    "small": "mlx-community/whisper-small-mlx",
}


class MlxWhisperEngine(STTEngine):
    """Apple Silicon default: uses MLX (GPU/unified memory) instead of the
    CPU-only CTranslate2 backend that faster-whisper relies on."""

    def __init__(self, model: str = "large-v3-turbo") -> None:
        self.repo = MODEL_REPOS.get(model, model)
        import mlx_whisper  # import here so a missing dep only breaks STT, not the whole backend

        self._mlx_whisper = mlx_whisper
        log.info("mlx-whisper ready (%s)", self.repo)

    def transcribe(self, pcm_int16: np.ndarray, language: str = "auto") -> TranscriptionResult:
        audio = int16_to_float32(pcm_int16)
        result = self._mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=self.repo,
            language=None if language == "auto" else language,
            fp16=True,
        )
        text = result.get("text", "").strip()
        detected_lang = result.get("language", "unknown")
        return TranscriptionResult(text=text, language=detected_lang)
