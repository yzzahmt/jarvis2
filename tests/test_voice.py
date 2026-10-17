import numpy as np

from jarvis.voice.clap_detector import ClapDetector

R, F = 16000, 1280


def _clap():
    x = np.zeros(F, np.float32)
    x[100:400] = np.random.default_rng(0).uniform(-0.9, 0.9, 300) * np.exp(-np.arange(300) / 60)
    return x


def _run(seq):
    d, hits = ClapDetector(), 0
    rng = np.random.default_rng(1)
    for kind in seq:
        f = _clap() if kind == "c" else rng.normal(0, 0.003, F).astype(np.float32)
        hits += d.feed(f)
    return hits


def test_double_clap():
    assert _run("....." + "c" + "..." + "c" + "......") == 1


def test_single_and_many_claps_ignored():
    assert _run("....." + "c" + "..........") == 0
    assert _run("....." + "c.c.c.c.c" + "......") == 0


def test_quiet_never_triggers():
    assert _run("." * 100) == 0


def test_speakable_and_stt_fixes():
    from jarvis.text import fix_stt, speakable
    assert speakable("Kara delikler **çöker** 🌌✨ bkz. https://x.com/a") == "Kara delikler çöker bkz. bağlantı"
    assert speakable("👍") == ""
    assert fix_stt("Carvis kaçı os'ta testleri çalıştır") == "Jarvis CachyOS'ta testleri çalıştır"
