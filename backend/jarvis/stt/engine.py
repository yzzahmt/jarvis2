from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np


@dataclass
class TranscriptionResult:
    text: str
    language: str


class STTEngine(ABC):
    @abstractmethod
    def transcribe(self, pcm_int16: np.ndarray, language: str = "auto") -> TranscriptionResult:
        """pcm_int16 is mono 16kHz int16 audio."""
        raise NotImplementedError
