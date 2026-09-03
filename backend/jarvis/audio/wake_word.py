from __future__ import annotations

import time
from typing import Callable

import numpy as np

from jarvis.utils.logging import get_logger

log = get_logger("audio.wake_word")

# openWakeWord's models are trained on 80ms (1280-sample) chunks at 16kHz.
CHUNK_SAMPLES = 1280
REFRACTORY_S = 2.0


class WakeWordDetector:
    """Wraps openWakeWord. Loads lazily so import/model-download failures don't
    crash the whole backend — wake-word detection degrades gracefully to
    "disabled" and the user still has push-to-talk / clap / typed input."""

    def __init__(
        self,
        keyword: str = "hey_jarvis",
        sensitivity: float = 0.5,
        on_detected: Callable[[], None] | None = None,
    ) -> None:
        self.keyword = keyword
        self.sensitivity = sensitivity
        self.on_detected = on_detected
        self.enabled = True
        self.available = False

        self._model = None
        self._buffer = np.zeros(0, dtype=np.int16)
        self._last_trigger_t = 0.0
        self._load_model()

    def _load_model(self) -> None:
        try:
            from openwakeword.model import Model

            self._model = Model(inference_framework="onnx")
            self.available = True
            log.info("openWakeWord loaded (watching for keyword containing '%s')", self.keyword)
        except Exception:
            log.exception(
                "failed to load openWakeWord — wake-word detection disabled, "
                "use push-to-talk or the clap trigger instead"
            )
            self._model = None
            self.available = False

    def configure(self, keyword: str | None = None, sensitivity: float | None = None, enabled: bool | None = None) -> None:
        if keyword is not None:
            self.keyword = keyword
        if sensitivity is not None:
            self.sensitivity = sensitivity
        if enabled is not None:
            self.enabled = enabled

    def process_frame(self, frame_int16: np.ndarray) -> None:
        if not self.enabled or not self.available or self._model is None:
            return

        self._buffer = np.concatenate([self._buffer, frame_int16])
        while self._buffer.size >= CHUNK_SAMPLES:
            chunk, self._buffer = self._buffer[:CHUNK_SAMPLES], self._buffer[CHUNK_SAMPLES:]
            self._predict(chunk)

    def _predict(self, chunk: np.ndarray) -> None:
        predictions = self._model.predict(chunk)
        now = time.monotonic()
        for model_name, score in predictions.items():
            if self.keyword.lower() not in model_name.lower():
                continue
            if score >= self.sensitivity and (now - self._last_trigger_t) > REFRACTORY_S:
                self._last_trigger_t = now
                log.info("wake word detected (%s: %.2f)", model_name, score)
                if self.on_detected:
                    self.on_detected()
