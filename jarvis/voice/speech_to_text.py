"""Türkçe konuşma tanıma: faster-whisper (yerel). Ses diske kaydedilmez."""
import numpy as np

HINT = "Jarvis, CachyOS, Linux Mint, YouTube, Mac, test, proje."


class STT:
    def __init__(self, model="small", root=None):
        from faster_whisper import WhisperModel
        self.m = WhisperModel(model, device="cpu", compute_type="int8", download_root=root)

    def transcribe(self, audio: np.ndarray) -> str:
        x = audio.astype(np.float32) / (32768.0 if audio.dtype == np.int16 else 1.0)
        segs, _ = self.m.transcribe(x, language="tr", beam_size=1, vad_filter=True,
                                    initial_prompt=HINT, condition_on_previous_text=False)
        return " ".join(s.text.strip() for s in segs).strip()


def record_utterance(frames, rate=16000, start_timeout=6.0, silence=0.9, max_len=15.0, thresh=None):
    """frames: int16 çerçeve üreteci. Konuşma başlayıp sessizlikle bitince sesi döndürür; yoksa None."""
    got, heard, quiet, total, noise = [], False, 0.0, 0.0, []
    for f in frames:
        if f is None:
            return None
        dur = len(f) / rate
        total += dur
        level = float(np.sqrt(np.mean((f.astype(np.float32) / 32768.0) ** 2)))
        if not heard:
            noise.append(level)
            th = thresh or max(0.01, 3 * float(np.median(noise[-25:])))
            if level > th and total > 0.25:
                heard = True
                got.append(f)
            elif total > start_timeout:
                return None
            continue
        got.append(f)
        quiet = quiet + dur if level < th else 0.0
        if quiet >= silence or sum(len(g) for g in got) / rate >= max_len:
            break
    return np.concatenate(got) if got else None
