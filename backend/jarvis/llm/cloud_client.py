from __future__ import annotations

import json
import uuid

import httpx

from jarvis.llm.client import ChatResponse, LLMClient, ToolCall
from jarvis.utils.logging import get_logger

log = get_logger("llm.cloud")


class GroqClient(LLMClient):
    """OpenAI-compatible endpoint — free-tier API key from console.groq.com."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile") -> None:
        self.api_key = api_key
        self.model = model
        self._url = "https://api.groq.com/openai/v1/chat/completions"

    def chat(self, messages: list[dict], tools: list[dict]) -> ChatResponse:
        body = {"model": self.model, "messages": messages}
        if tools:
            body["tools"] = tools
        resp = httpx.post(
            self._url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=body,
            timeout=60,
        )
        resp.raise_for_status()
        message = resp.json()["choices"][0]["message"]
        raw_tool_calls = message.get("tool_calls") or []
        tool_calls = [
            ToolCall(
                id=tc.get("id") or str(uuid.uuid4()),
                name=tc["function"]["name"],
                arguments=json.loads(tc["function"]["arguments"] or "{}"),
            )
            for tc in raw_tool_calls
        ]
        return ChatResponse(content=message.get("content"), tool_calls=tool_calls)


class GeminiClient(LLMClient):
    """Free-tier API key from aistudio.google.com. Translates our OpenAI-ish
    message/tool shape into Gemini's contents/functionDeclarations schema."""

    def __init__(self, api_key: str, model: str = "gemini-2.0-flash") -> None:
        self.api_key = api_key
        self.model = model

    def chat(self, messages: list[dict], tools: list[dict]) -> ChatResponse:
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        contents = []
        for m in messages:
            if m["role"] == "system":
                continue
            if m["role"] == "tool":
                contents.append(
                    {
                        "role": "function",
                        "parts": [
                            {
                                "functionResponse": {
                                    "name": m.get("name", "tool"),
                                    "response": {"result": m["content"]},
                                }
                            }
                        ],
                    }
                )
            elif m["role"] == "assistant":
                contents.append({"role": "model", "parts": [{"text": m.get("content") or ""}]})
            else:
                contents.append({"role": "user", "parts": [{"text": m.get("content") or ""}]})

        body: dict = {"contents": contents}
        if system_parts:
            body["systemInstruction"] = {"parts": [{"text": "\n".join(system_parts)}]}
        if tools:
            body["tools"] = [
                {
                    "functionDeclarations": [
                        {
                            "name": t["function"]["name"],
                            "description": t["function"].get("description", ""),
                            "parameters": t["function"].get("parameters", {}),
                        }
                        for t in tools
                    ]
                }
            ]

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        resp = httpx.post(url, json=body, timeout=60)
        resp.raise_for_status()
        candidate = resp.json()["candidates"][0]
        parts = candidate.get("content", {}).get("parts", [])

        text_chunks = [p["text"] for p in parts if "text" in p]
        tool_calls = [
            ToolCall(id=str(uuid.uuid4()), name=p["functionCall"]["name"], arguments=p["functionCall"].get("args", {}))
            for p in parts
            if "functionCall" in p
        ]
        content = "\n".join(text_chunks).strip() or None
        return ChatResponse(content=content, tool_calls=tool_calls)


def build_cloud_client(provider: str, api_key: str, model: str | None) -> LLMClient:
    if provider == "groq":
        return GroqClient(api_key, model or "llama-3.3-70b-versatile")
    if provider == "gemini":
        return GeminiClient(api_key, model or "gemini-2.0-flash")
    raise ValueError(f"unknown cloud provider '{provider}'")
