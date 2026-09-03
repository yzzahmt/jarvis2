from __future__ import annotations

from typing import Callable

import numpy as np
import sounddevice as sd

from jarvis.utils.audio_utils import FRAME_SAMPLES, SAMPLE_RATE
from jarvis.utils.logging import get_logger

log = get_logger("audio.capture")

FrameCallback = Callable[[np.ndarray], None]


class AudioCapture:
    """Single mic producer, fanned out to many subscribers (wake word, clap, VAD/recorder).

    Opening the mic device once and sharing frames avoids multiple concurrent
    PortAudio streams, which is both more reliable and asks for mic permission
    only once.
    """

    def __init__(self) -> None:
        self._subscribers: list[FrameCallback] = []
        self._stream: sd.InputStream | None = None

    def subscribe(self, callback: FrameCallback) -> None:
        self._subscribers.append(callback)

    def unsubscribe(self, callback: FrameCallback) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def _on_audio(self, indata: np.ndarray, frames: int, time_info, status) -> None:
        if status:
            log.debug("stream status: %s", status)
        frame = indata[:, 0].copy()
        for cb in list(self._subscribers):
            try:
                cb(frame)
            except Exception:
                log.exception("subscriber raised while handling audio frame")

    def start(self) -> None:
        if self._stream is not None:
            return
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            blocksize=FRAME_SAMPLES,
            callback=self._on_audio,
        )
        self._stream.start()
        log.info("audio capture started (%d Hz, %d-sample frames)", SAMPLE_RATE, FRAME_SAMPLES)

    def stop(self) -> None:
        if self._stream is None:
            return
        self._stream.stop()
        self._stream.close()
        self._stream = None
        log.info("audio capture stopped")


audio_capture = AudioCapture()
