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
    assert fix_stt("Carvis sorin o es'ta testleri çalıştır") == "Jarvis Zorin OS'ta testleri çalıştır"


def test_stt_no_example_sentences_in_hint():
    # Örnek cümle ipucu, sessizlikte "testleri çalıştır" diye uydurulup Zorin'e gidiyordu (015)
    from jarvis.voice import speech_to_text as S
    st = S.STT.__new__(S.STT)
    st.words = ["OBİS"]
    assert "çalıştır" not in S.NAMES and "?" not in S.NAMES
    assert S.clean('"Bana API anahtarını al."') == "Bana API anahtarını al."
    assert S.clean("Sen bir konuşma yazıya dökücüsün.") == ""
    assert S.clean("Jarvis, Zorin OS, Linux Mint, YouTube, Gemini, ChatGPT, Spotify") == ""
    assert "API" not in S.NAMES and "env" not in S.NAMES


def test_stt_skips_silence():
    import numpy as np
    from jarvis.voice import speech_to_text as S
    st = S.STT.__new__(S.STT)
    st._gemini = st._whisper = lambda a: (_ for _ in ()).throw(AssertionError("sessizlikte model çağrıldı"))
    assert st.transcribe(np.zeros(24000, np.int16)) == ""


def test_stt_speech_gate(monkeypatch):
    import numpy as np
    from jarvis.voice import speech_to_text as S
    speechy = S.speechy
    rng, sr = np.random.default_rng(0), 16000
    noise = rng.normal(0, 0.01 * 32768, sr * 2)
    clicks = rng.normal(0, 0.005 * 32768, sr * 2)
    for i in range(0, sr * 2, 2500):
        clicks[i:i + 200] += rng.normal(0, 0.15 * 32768, 200)
    t = np.arange(sr) / sr
    voice = np.concatenate([noise[:sr // 2], noise[:sr] + 0.1 * 32768 * np.sin(2 * np.pi * 220 * t), noise[:sr // 2]])
    assert not speechy(noise.astype(np.int16)) and not speechy(clicks.astype(np.int16))
    monkeypatch.setattr(S, "vad_speech", lambda x: 1.0)        # sinüs insan sesi değil; enerji kısmını dene
    assert speechy(voice.astype(np.int16))


def test_stt_source_chain(monkeypatch):
    # Gemini/Groq yoksa Mac tanımasına, o da yoksa yerel whisper'a düşer (hiçbir kaynak bitince durmaz)
    import numpy as np
    from jarvis.voice import speech_to_text as S
    monkeypatch.setattr(S, "speechy", lambda a: True)
    st = S.STT.__new__(S.STT)
    st._gemini = st._groq = lambda a: None
    st._apple = lambda a: "Safari'yi aç"
    st._whisper = lambda a: (_ for _ in ()).throw(AssertionError("yerele gerek yoktu"))
    assert st.transcribe(np.ones(16000, np.int16)) == "Safari'yi aç"
    st._apple = lambda a: None
    st._whisper = lambda a: "yerel"
    assert st.transcribe(np.ones(16000, np.int16)) == "yerel"


def test_record_keeps_soft_tail():
    # Başladıktan sonra eşiğin altındaki yumuşak sesler (eşiğin %60'ı üstü) cümleyi kesmez
    import numpy as np
    from jarvis.voice.speech_to_text import record_utterance
    fr = lambda lvl, n: [np.full(480, int(lvl * 32768), np.int16)] * n
    frames = iter(fr(0.001, 20) + fr(0.05, 20) + fr(0.008, 40) + fr(0.0, 60))
    a = record_utterance(frames, thresh=0.01)
    assert a is not None and len(a) >= 480 * 60


def test_second_ear_rejects_invented_text(monkeypatch):
    # 017: Gemini "screenshot'ı kaydet" uydurdu; Mac tanıması bir şey duymadıysa/örtüşmüyorsa atılır
    import numpy as np
    from jarvis.voice import speech_to_text as S
    monkeypatch.setattr(S, "speechy", lambda a: True)
    st = S.STT.__new__(S.STT)
    st.rejected, st.apple_ok = "", True
    st._groq = lambda a: None
    st._gemini = lambda a: "screenshot'ı kaydet."
    for mac in ("", "evet evet tamam"):
        st._apple = lambda a, m=mac: m
        assert st.transcribe(np.ones(16000, np.int16)) == "" and st.rejected
    st._gemini = lambda a: "ChatGPT API key'ini kopyala ve .env dosyasına yapıştır."
    st._apple = lambda a: "Çetin Apikini kopyala veen dosyasına yapıştır"     # gerçek Mac çıktısı (İngilizce bozuk)
    assert st.transcribe(np.ones(16000, np.int16)).startswith("ChatGPT")
    assert S.agree("İziço panelinden sandbox secret key'i al", "Easyce panelinden Sound for Secret Kia Alevi")
    assert "screenshot" not in S.PROMPT and "API" not in S.PROMPT.split("Kısaltmaları")[0]


def test_second_ear_without_proof_does_not_veto(monkeypatch):
    # Mac tanıması bu oturumda hiç çalışmadıysa (uygulama içinde hep boş) gerçek sözleri atmasın
    import numpy as np
    from jarvis.voice import speech_to_text as S
    monkeypatch.setattr(S, "speechy", lambda a: True)
    st = S.STT.__new__(S.STT)
    st.rejected, st.apple_ok = "", False
    st._groq = lambda a: None
    st._gemini = lambda a: "Naber, nasılsın?"
    st._apple = lambda a: ""
    assert st.transcribe(np.ones(16000, np.int16)) == "Naber, nasılsın?" and not st.rejected


def test_vad_rejects_noise_and_no_names_to_gemini():
    import numpy as np
    from jarvis.voice import speech_to_text as S
    noise = np.random.default_rng(2).normal(0, 0.03, 32000).astype(np.float32)
    assert S.vad_speech(noise) < 0.3
    assert "Spotify" not in S.PROMPT and "Jarvis" not in S.PROMPT
