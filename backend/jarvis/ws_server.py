from __future__ import annotations

import time
import uuid
from typing import Any, Awaitable, Callable

from fastapi import WebSocket, WebSocketDisconnect

from jarvis.state import event_bus
from jarvis.utils.logging import get_logger

log = get_logger("ws")

ClientHandler = Callable[[str, dict], Awaitable[None]]


class ConnectionManager:
    def __init__(self) -> None:
        self._sockets: set[WebSocket] = set()
        self._client_handlers: dict[str, ClientHandler] = {}
        event_bus.subscribe(self._on_bus_event)

    def register_handler(self, msg_type: str, handler: ClientHandler) -> None:
        self._client_handlers[msg_type] = handler

    async def _on_bus_event(self, msg_type: str, payload: dict) -> None:
        await self.broadcast(msg_type, payload)

    async def broadcast(self, msg_type: str, payload: dict[str, Any]) -> None:
        envelope = {
            "type": msg_type,
            "id": str(uuid.uuid4()),
            "ts": int(time.time() * 1000),
            "payload": payload,
        }
        dead: list[WebSocket] = []
        for ws in list(self._sockets):
            try:
                await ws.send_json(envelope)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._sockets.discard(ws)

    async def handle_connection(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._sockets.add(websocket)
        log.info("client connected (%d total)", len(self._sockets))
        try:
            await self.broadcast("state_changed", {"state": event_bus.state.value})
            while True:
                data = await websocket.receive_json()
                msg_type = data.get("type")
                payload = data.get("payload", {})
                handler = self._client_handlers.get(msg_type)
                if handler is None:
                    log.warning("no handler registered for message type %s", msg_type)
                    continue
                await handler(msg_type, payload)
        except WebSocketDisconnect:
            pass
        finally:
            self._sockets.discard(websocket)
            log.info("client disconnected (%d total)", len(self._sockets))


manager = ConnectionManager()
