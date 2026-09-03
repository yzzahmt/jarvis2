from __future__ import annotations

import numpy as np

SAMPLE_RATE = 16000
FRAME_MS = 30
FRAME_SAMPLES = int(SAMPLE_RATE * FRAME_MS / 1000)


def int16_to_float32(pcm: np.ndarray) -> np.ndarray:
    return (pcm.astype(np.float32) / 32768.0).clip(-1.0, 1.0)


def float32_to_int16(pcm: np.ndarray) -> np.ndarray:
    return (pcm.clip(-1.0, 1.0) * 32767.0).astype(np.int16)


def rms(pcm_float32: np.ndarray) -> float:
    if pcm_float32.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(pcm_float32))))
