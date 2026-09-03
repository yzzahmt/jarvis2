from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatResponse:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMClient(ABC):
    """Every provider (local Ollama, Gemini, Groq) implements this so
    tool_loop.py stays provider-agnostic — switching `llm.provider` in
    settings swaps the implementation, not the orchestration logic."""

    @abstractmethod
    def chat(self, messages: list[dict], tools: list[dict]) -> ChatResponse:
        raise NotImplementedError
