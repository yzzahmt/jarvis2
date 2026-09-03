from __future__ import annotations

import uuid

from jarvis.llm.client import ChatResponse, LLMClient, ToolCall
from jarvis.utils.logging import get_logger

log = get_logger("llm.ollama")


class OllamaClient(LLMClient):
    def __init__(self, model: str, host: str = "http://127.0.0.1:11434") -> None:
        import ollama

        self._client = ollama.Client(host=host)
        self.model = model

    def chat(self, messages: list[dict], tools: list[dict]) -> ChatResponse:
        response = self._client.chat(
            model=self.model,
            messages=messages,
            tools=tools or None,
        )
        message = response["message"]
        raw_tool_calls = message.get("tool_calls") or []
        tool_calls = [
            ToolCall(
                id=tc.get("id") or str(uuid.uuid4()),
                name=tc["function"]["name"],
                arguments=tc["function"]["arguments"] or {},
            )
            for tc in raw_tool_calls
        ]
        return ChatResponse(content=message.get("content") or None, tool_calls=tool_calls)
