from __future__ import annotations

import time
from collections import deque
from typing import Callable

import numpy as np

from jarvis.utils.audio_utils import int16_to_float32, rms
from jarvis.utils.logging import get_logger

log = get_logger("audio.clap")

# Tuned for a 30ms frame cadence. A clap is a short, sharp energy transient well
# above the recent noise floor; sustained loud sound (speech, music) shouldn't
# keep re-triggering because the floor slowly adapts upward except during spikes.
SPIKE_RATIO = 7.0
MIN_ABS_RMS = 0.09
REFRACTORY_S = 0.15
FLOOR_ALPHA = 0.02  # slow adaptation


class ClapDetector:
    def __init__(
        self,
        claps_required: int = 2,
        window_ms: int = 600,
        on_detected: Callable[[], None] | None = None,
    ) -> None:
        self.claps_required = claps_required
        self.window_ms = window_ms
        self.on_detected = on_detected
        self.enabled = True

        self._floor = MIN_ABS_RMS
        self._last_spike_t = 0.0
        self._clap_times: deque[float] = deque()

    def configure(self, claps_required: int | None = None, window_ms: int | None = None, enabled: bool | None = None) -> None:
        if claps_required is not None:
            self.claps_required = claps_required
        if window_ms is not None:
            self.window_ms = window_ms
        if enabled is not None:
            self.enabled = enabled

    def process_frame(self, frame_int16: np.ndarray) -> None:
        if not self.enabled:
            return
        level = rms(int16_to_float32(frame_int16))
        now = time.monotonic()
        threshold = max(self._floor * SPIKE_RATIO, MIN_ABS_RMS)

        is_spike = level > threshold and (now - self._last_spike_t) > REFRACTORY_S
        if is_spike:
            self._last_spike_t = now
            self._register_clap(now)
        else:
            # Only adapt the floor outside of spikes so a single clap doesn't
            # permanently raise the threshold.
            self._floor = (1 - FLOOR_ALPHA) * self._floor + FLOOR_ALPHA * level

    def _register_clap(self, now: float) -> None:
        self._clap_times.append(now)
        window_s = self.window_ms / 1000.0
        while self._clap_times and now - self._clap_times[0] > window_s:
            self._clap_times.popleft()

        if len(self._clap_times) >= self.claps_required:
            self._clap_times.clear()
            log.info("clap sequence detected")
            if self.on_detected:
                self.on_detected()
