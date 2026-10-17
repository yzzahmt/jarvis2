"""Uyandırma kelimesi: openWakeWord 'hey jarvis' (yerel, CPU'da hafif, ONNX)."""
import numpy as np


class WakeWord:
    FRAME = 1280  # 80 ms @ 16 kHz

    def __init__(self, name="hey_jarvis", threshold=0.5):
        from openwakeword.model import Model
        self.name, self.threshold = name, threshold
        self.model = Model(wakeword_models=[name], inference_framework="onnx")

    def feed(self, frame: np.ndarray) -> bool:
        scores = self.model.predict(frame.astype(np.int16))
        return max(scores.values()) >= self.threshold

    def reset(self):
        self.model.reset()
