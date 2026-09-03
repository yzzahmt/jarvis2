from __future__ import annotations

import asyncio
from enum import Enum
from typing import Any, Awaitable, Callable, Optional


class AppState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


Listener = Callable[[str, dict], Awaitable[None]]


class EventBus:
    """Simple async pub/sub used to decouple audio/LLM workers from the WS layer."""

    def __init__(self) -> None:
        self._listeners: list[Listener] = []
        self._state = AppState.IDLE
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def unsubscribe(self, listener: Listener) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    @property
    def state(self) -> AppState:
        return self._state

    async def emit(self, msg_type: str, payload: dict[str, Any]) -> None:
        for listener in list(self._listeners):
            await listener(msg_type, payload)

    def emit_threadsafe(self, msg_type: str, payload: dict[str, Any]) -> None:
        """Called from non-async worker threads (audio callbacks, blocking model calls)."""
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(self.emit(msg_type, payload), self._loop)

    async def set_state(self, new_state: AppState) -> None:
        self._state = new_state
        await self.emit("state_changed", {"state": new_state.value})

    def set_state_threadsafe(self, new_state: AppState) -> None:
        self._state = new_state
        self.emit_threadsafe("state_changed", {"state": new_state.value})


event_bus = EventBus()
