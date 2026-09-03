from __future__ import annotations

import time
from typing import Callable, Optional

import numpy as np
import webrtcvad

from jarvis.utils.audio_utils import FRAME_MS, SAMPLE_RATE
from jarvis.utils.logging import get_logger

log = get_logger("audio.vad")

SILENCE_TIMEOUT_MS = 900
MIN_SPEECH_MS = 250
MAX_UTTERANCE_S = 15.0
VAD_AGGRESSIVENESS = 3  # 0-3, higher = more aggressive about filtering non-speech


class UtteranceRecorder:
    """Buffers mic frames while `state == listening` and calls back with the full
    utterance once the user stops talking (or a max-duration safety cap hits).
    Calls back with `None` when the recording is discarded (too little speech),
    so the caller can still reset state out of `listening`."""

    def __init__(self, on_utterance_complete: Callable[[Optional[np.ndarray]], None]) -> None:
        self._vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
        self.on_utterance_complete = on_utterance_complete

        self._recording = False
        self._frames: list[np.ndarray] = []
        self._silence_ms = 0
        self._speech_ms = 0
        self._start_t = 0.0

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self) -> None:
        self._recording = True
        self._frames = []
        self._silence_ms = 0
        self._speech_ms = 0
        self._start_t = time.monotonic()
        log.info("utterance recording started")

    def stop(self, reason: str) -> None:
        if not self._recording:
            return
        self._recording = False
        audio = (
            np.concatenate(self._frames)
            if self._frames
            else np.zeros(0, dtype=np.int16)
        )
        log.info("utterance recording stopped (%s, %.2fs)", reason, audio.size / SAMPLE_RATE)
        if self._speech_ms >= MIN_SPEECH_MS:
            self.on_utterance_complete(audio)
        else:
            log.info("discarding utterance — too little speech detected")
            self.on_utterance_complete(None)

    def process_frame(self, frame_int16: np.ndarray) -> None:
        if not self._recording:
            return

        self._frames.append(frame_int16)
        is_speech = self._vad.is_speech(frame_int16.tobytes(), SAMPLE_RATE)
        if is_speech:
            self._speech_ms += FRAME_MS
            self._silence_ms = 0
        else:
            self._silence_ms += FRAME_MS

        elapsed = time.monotonic() - self._start_t
        if elapsed > MAX_UTTERANCE_S:
            self.stop("max_duration")
        elif self._speech_ms >= MIN_SPEECH_MS and self._silence_ms >= SILENCE_TIMEOUT_MS:
            self.stop("silence")
