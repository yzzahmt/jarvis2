from __future__ import annotations

import asyncio
import threading
from contextlib import asynccontextmanager

import numpy as np
from fastapi import FastAPI, WebSocket

from jarvis.audio.capture import audio_capture
from jarvis.audio.clap_detector import ClapDetector
from jarvis.audio.vad import UtteranceRecorder
from jarvis.audio.wake_word import WakeWordDetector
from jarvis.config import load_config, update_config
from jarvis.llm.factory import build_llm_client
from jarvis.llm.tool_loop import JarvisAgent
from jarvis.state import AppState, event_bus
from jarvis.utils.audio_utils import int16_to_float32, rms
from jarvis.utils.logging import get_logger
from jarvis.ws_server import manager

log = get_logger("main")


class Orchestrator:
    """Wires audio capture -> wake/clap triggers -> VAD recording -> STT ->
    LLM tool loop -> TTS together, and exposes the handful of actions the
    WebSocket layer needs (push-to-talk, text input, settings, interrupt)."""

    def __init__(self) -> None:
        self.cfg = load_config()
        self.agent = JarvisAgent(build_llm_client(self.cfg.llm))
        self._stt_engine = None
        self._tts_engine = None
        self._lazy_lock = threading.Lock()

        self.recorder = UtteranceRecorder(self._on_utterance_complete)

        self.clap = ClapDetector(
            claps_required=self.cfg.clap_trigger.claps_required,
            window_ms=self.cfg.clap_trigger.window_ms,
            on_detected=lambda: self._trigger_wake("clap"),
        )
        self.clap.enabled = self.cfg.clap_trigger.enabled

        self.wake_word = WakeWordDetector(
            keyword=self.cfg.wake_word.keyword,
            sensitivity=self.cfg.wake_word.sensitivity,
            on_detected=lambda: self._trigger_wake("wake_word"),
        )
        self.wake_word.enabled = self.cfg.wake_word.enabled

        audio_capture.subscribe(self.clap.process_frame)
        audio_capture.subscribe(self.wake_word.process_frame)
        audio_capture.subscribe(self.recorder.process_frame)
        audio_capture.subscribe(self._emit_audio_level)

    # -- lazy model loading: STT/TTS models are slow to load, don't block startup --
    @property
    def stt_engine(self):
        if self._stt_engine is None:
            with self._lazy_lock:
                if self._stt_engine is None:
                    from jarvis.stt.mlx_whisper_engine import MlxWhisperEngine

                    self._stt_engine = MlxWhisperEngine(self.cfg.stt.model)
        return self._stt_engine

    @property
    def tts_engine(self):
        if self._tts_engine is None:
            with self._lazy_lock:
                if self._tts_engine is None:
                    self._tts_engine = self._build_tts_engine()
        return self._tts_engine

    def _build_tts_engine(self):
        if self.cfg.voice.engine == "elevenlabs":
            from jarvis.tts.elevenlabs_engine import ElevenLabsEngine

            return ElevenLabsEngine(
                self.cfg.voice.elevenlabs_api_key or "", self.cfg.voice.elevenlabs_voice_id
            )
        from jarvis.tts.piper_engine import PiperEngine

        return PiperEngine(self.cfg.voice.voice_id)

    def _emit_audio_level(self, frame: np.ndarray) -> None:
        if event_bus.state == AppState.LISTENING:
            event_bus.emit_threadsafe("audio_level", {"rms": rms(int16_to_float32(frame))})

    def _trigger_wake(self, source: str) -> None:
        if event_bus.state != AppState.IDLE:
            return
        event_bus.set_state_threadsafe(AppState.LISTENING)
        event_bus.emit_threadsafe("wake_triggered", {"source": source})
        self.recorder.start()

    def start_manual_listen(self) -> None:
        self._trigger_wake("manual")

    def stop_manual_listen(self) -> None:
        if self.recorder.is_recording:
            self.recorder.stop("manual_stop")

    def _on_utterance_complete(self, audio: np.ndarray | None) -> None:
        if audio is None:
            event_bus.set_state_threadsafe(AppState.IDLE)
            return
        threading.Thread(target=self._process_utterance, args=(audio,), daemon=True).start()

    def _process_utterance(self, audio: np.ndarray) -> None:
        event_bus.set_state_threadsafe(AppState.THINKING)
        try:
            result = self.stt_engine.transcribe(audio, language=self.cfg.stt.language)
            text = result.text.strip()
            lang = result.language
        except Exception:
            log.exception("STT failed")
            event_bus.emit_threadsafe(
                "error", {"code": "stt_failed", "message": "Konuşma anlaşılamadı, tekrar dener misin?"}
            )
            event_bus.set_state_threadsafe(AppState.IDLE)
            return

        if not text:
            event_bus.set_state_threadsafe(AppState.IDLE)
            return

        event_bus.emit_threadsafe("transcript_final", {"text": text, "lang": lang})
        self._respond_to_text(text)

    def handle_text_input(self, text: str) -> None:
        text = text.strip()
        if not text or event_bus.state != AppState.IDLE:
            return
        event_bus.set_state_threadsafe(AppState.THINKING)
        event_bus.emit_threadsafe("transcript_final", {"text": text, "lang": "text"})
        threading.Thread(target=self._respond_to_text, args=(text,), daemon=True).start()

    def _respond_to_text(self, text: str) -> None:
        try:
            reply = self.agent.handle_user_text(text)
        except Exception as exc:
            log.exception("LLM turn failed")
            event_bus.emit_threadsafe("error", {"code": "llm_failed", "message": str(exc)})
            event_bus.set_state_threadsafe(AppState.IDLE)
            return

        event_bus.emit_threadsafe("assistant_reply", {"text": reply, "used_tools": []})
        event_bus.set_state_threadsafe(AppState.SPEAKING)
        try:
            self.tts_engine.speak(reply)
        except Exception:
            log.exception("TTS failed")
        event_bus.set_state_threadsafe(AppState.IDLE)

    def interrupt(self) -> None:
        import sounddevice as sd

        sd.stop()
        event_bus.set_state_threadsafe(AppState.IDLE)

    def toggle_gesture_control(self) -> bool:
        from jarvis.vision.gesture_control import controller

        if controller.is_running:
            controller.stop()
            return False
        controller.start()
        return True

    def get_settings(self) -> dict:
        return self.cfg.model_dump()

    def set_settings(self, partial: dict) -> dict:
        prev_voice = self.cfg.voice
        self.cfg = update_config(partial)
        self.clap.configure(
            claps_required=self.cfg.clap_trigger.claps_required,
            window_ms=self.cfg.clap_trigger.window_ms,
            enabled=self.cfg.clap_trigger.enabled,
        )
        self.wake_word.configure(
            keyword=self.cfg.wake_word.keyword,
            sensitivity=self.cfg.wake_word.sensitivity,
            enabled=self.cfg.wake_word.enabled,
        )
        if self.cfg.voice.engine != prev_voice.engine:
            # switching engines (piper <-> elevenlabs) needs a fresh instance,
            # not just a voice swap — rebuild lazily on next use.
            self._tts_engine = None
        elif self._tts_engine is not None:
            active_voice_id = (
                self.cfg.voice.elevenlabs_voice_id
                if self.cfg.voice.engine == "elevenlabs"
                else self.cfg.voice.voice_id
            )
            self._tts_engine.set_voice(active_voice_id)
        self.agent.set_client(build_llm_client(self.cfg.llm))
        return self.cfg.model_dump()


orchestrator: Orchestrator | None = None


async def _on_push_to_talk_start(_type: str, _payload: dict) -> None:
    orchestrator.start_manual_listen()


async def _on_push_to_talk_stop(_type: str, _payload: dict) -> None:
    orchestrator.stop_manual_listen()


async def _on_text_input(_type: str, payload: dict) -> None:
    orchestrator.handle_text_input(payload.get("text", ""))


async def _on_settings_get(_type: str, _payload: dict) -> None:
    await manager.broadcast("settings_state", {"settings": orchestrator.get_settings()})


async def _on_settings_set(_type: str, payload: dict) -> None:
    settings = orchestrator.set_settings(payload.get("settings", {}))
    await manager.broadcast("settings_state", {"settings": settings})


async def _on_interrupt(_type: str, _payload: dict) -> None:
    orchestrator.interrupt()


async def _on_gesture_toggle(_type: str, _payload: dict) -> None:
    import asyncio

    active = await asyncio.to_thread(orchestrator.toggle_gesture_control)
    await manager.broadcast("gesture_state", {"active": active})


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global orchestrator
    event_bus.bind_loop(asyncio.get_running_loop())
    orchestrator = Orchestrator()

    manager.register_handler("push_to_talk_start", _on_push_to_talk_start)
    manager.register_handler("push_to_talk_stop", _on_push_to_talk_stop)
    manager.register_handler("text_input", _on_text_input)
    manager.register_handler("settings_get", _on_settings_get)
    manager.register_handler("settings_set", _on_settings_set)
    manager.register_handler("interrupt", _on_interrupt)
    manager.register_handler("gesture_toggle", _on_gesture_toggle)

    audio_capture.start()
    log.info("Jarvis backend ready")
    try:
        yield
    finally:
        audio_capture.stop()


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    await manager.handle_connection(websocket)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
