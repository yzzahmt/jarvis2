"""Çift alkış algılama (yalnızca numpy). Diğer ses bileşenlerinden bağımsız."""
import time

import numpy as np


class ClapDetector:
    def __init__(self, rate=16000, peak=0.5, ratio=6.0, min_gap=0.15, max_gap=0.8, quiet_after=0.3):
        self.rate, self.peak, self.ratio = rate, peak, ratio
        self.min_gap, self.max_gap, self.quiet_after = min_gap, max_gap, quiet_after
        self.bg = 0.01          # arka plan gürültü seviyesi (uyarlanır)
        self.claps: list[float] = []
        self.t = 0.0

    def feed(self, frame: np.ndarray, now: float | None = None) -> bool:
        """frame: int16 veya float32 mono. Çift alkışta True."""
        x = frame.astype(np.float32) / (32768.0 if frame.dtype == np.int16 else 1.0)
        self.t = now if now is not None else self.t + len(x) / self.rate
        # 10 ms'lik pencerelerde kısa, keskin tepe ara
        win = max(1, self.rate // 100)
        rms = np.sqrt(np.mean(x[: len(x) // win * win].reshape(-1, win) ** 2, axis=1)) if len(x) >= win else np.array([0.0])
        top = float(rms.max())
        hit = top > self.peak * 0.3 and np.abs(x).max() > self.peak and top > self.bg * self.ratio
        if hit and (not self.claps or self.t - self.claps[-1] >= self.min_gap):
            self.claps.append(self.t)
        elif not hit:
            self.bg = 0.95 * self.bg + 0.05 * float(np.median(rms))
        self.claps = [c for c in self.claps if self.t - c <= self.max_gap + self.quiet_after]
        if len(self.claps) == 2 and self.min_gap <= self.claps[1] - self.claps[0] <= self.max_gap \
                and self.t - self.claps[1] >= self.quiet_after:
            self.claps.clear()
            return True
        if len(self.claps) > 2:   # alkış dizisi / müzik: çift alkış sayma
            self.claps = self.claps[-1:]
        return False
