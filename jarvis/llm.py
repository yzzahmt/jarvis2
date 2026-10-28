import base64
import json
import os
import re
from dataclasses import dataclass, field

import httpx


@dataclass
class ToolCall:
    name: str
    args: dict
    id: str = ""


@dataclass
class Reply:
    content: str = ""
    calls: list = field(default_factory=list)
    tokens: int | None = None


class LLMError(Exception):
    def __init__(self, msg, status=None, retry_after=None):
        super().__init__(msg)
        self.status, self.retry_after = status, retry_after


THINK = re.compile(r"<think>.*?</think>", re.S)


class Ollama:
    """Yerel model istemcisi. Bulut yok; model başarısızsa yedek modele geçer."""

    def __init__(self, cfg: dict):
        self.url = cfg.get("url", "http://127.0.0.1:11434").rstrip("/")
        self.models = [cfg.get("model", "qwen3:4b"), *cfg.get("fallback_models", [])]
        self.timeout = cfg.get("timeout_s", 90)
        self.agent_model = cfg.get("agent_model", self.models[0])
        self.vision_model = cfg.get("vision_model", "gemma3:4b")
        self.keep_alive = cfg.get("keep_alive", "30m")
        self.num_ctx = cfg.get("num_ctx", 8192)   # tüm çağrılarda aynı olmalı; farklıysa Ollama modeli yeniden yükler
        self.last_model = None
        self.last_tokens = None

    def up(self) -> bool:
        try:
            return httpx.get(self.url + "/api/tags", timeout=2).status_code == 200
        except httpx.HTTPError:
            return False

    def installed(self) -> list[str]:
        try:
            return [m["name"] for m in httpx.get(self.url + "/api/tags", timeout=3).json().get("models", [])]
        except httpx.HTTPError:
            return []

    def chat(self, messages, json_mode=False, max_tokens=300) -> str:
        have = set(self.installed())
        errors = []
        for m in [m for m in self.models if m in have] or self.models:
            body = {"model": m, "messages": messages, "stream": False, "think": False, "keep_alive": self.keep_alive,
                    "options": {"temperature": 0.2, "num_predict": max_tokens, "num_ctx": self.num_ctx}}
            if json_mode:
                body["format"] = "json"
            try:
                r = httpx.post(self.url + "/api/chat", json=body, timeout=self.timeout)
                r.raise_for_status()
                d = r.json()
                self.last_model = m
                self.last_tokens = (d.get("prompt_eval_count") or 0) + (d.get("eval_count") or 0)
                return re.sub(r"<think>.*?</think>", "", d["message"]["content"], flags=re.S).strip()
            except (httpx.HTTPError, KeyError, ValueError) as e:
                errors.append(f"{m}: {e}")
        raise LLMError("Yerel model yanıt vermedi: " + "; ".join(errors))

    def json(self, messages, max_tokens=200) -> dict:
        out = self.chat(messages, json_mode=True, max_tokens=max_tokens)
        try:
            return json.loads(out)
        except ValueError:
            m = re.search(r"\{.*\}", out, re.S)
            if m:
                return json.loads(m.group(0))
            raise LLMError("Model geçerli JSON üretmedi")

    # ---- araç çağırma ----
    def chat_tools(self, messages, tools, model=None, max_tokens=800) -> Reply:
        body = {"model": model or self.agent_model, "messages": messages, "tools": tools, "stream": False,
                "keep_alive": self.keep_alive,
                "think": False, "options": {"temperature": 0.1, "num_predict": max_tokens, "num_ctx": self.num_ctx}}
        try:
            r = httpx.post(self.url + "/api/chat", json=body, timeout=self.timeout)
            r.raise_for_status()
        except httpx.HTTPError as e:
            raise LLMError(f"Yerel model hatası: {e}")
        d = r.json()
        m = d.get("message", {})
        calls = [ToolCall(c["function"]["name"], c["function"].get("arguments") or {})
                 for c in m.get("tool_calls") or []]
        self.last_model = body["model"]
        return Reply(re.sub(r"<think>.*?</think>", "", m.get("content", ""), flags=re.S).strip(), calls,
                     (d.get("prompt_eval_count") or 0) + (d.get("eval_count") or 0))

    def assistant_msg(self, rep: Reply) -> dict:
        return {"role": "assistant", "content": rep.content,
                "tool_calls": [{"function": {"name": c.name, "arguments": c.args}} for c in rep.calls]}

    def tool_msg(self, call: ToolCall, content: str) -> dict:
        return {"role": "tool", "content": content, "tool_name": call.name}

    def vision(self, question, image_path) -> str:
        img = base64.b64encode(open(image_path, "rb").read()).decode()
        body = {"model": self.vision_model, "stream": False, "messages": [
            {"role": "user", "content": question + " (Türkçe, kısa. Konum sorulursa piksel koordinatı ver.)",
             "images": [img]}], "options": {"num_predict": 300}}
        r = httpx.post(self.url + "/api/chat", json=body, timeout=self.timeout)
        r.raise_for_status()
        return r.json()["message"]["content"].strip()


class OpenAICompat:
    """OpenAI uyumlu uç: Gemini, Groq, OpenRouter, Cerebras ücretsiz katmanları veya yerel Ollama (/v1). Claude DEĞİL."""

    def __init__(self, cfg: dict):
        self.name = cfg.get("name") or cfg.get("model")
        self.base = (cfg.get("base_url") or "").rstrip("/")
        self.model = cfg.get("model")
        env = cfg.get("api_key_env")
        self.key = os.environ.get(env, "") if env else "yerel"
        self.is_cloud = not self.base.startswith(("http://127.0.0.1", "http://localhost"))
        self.timeout = cfg.get("timeout_s", 60)
        self.extra = cfg.get("extra") or {}
        self.sees = bool(cfg.get("vision"))
        self.last_model, self.last_tokens = self.model, None

    def available(self) -> bool:
        return bool(self.base and self.model and self.key)

    def _post(self, body):
        try:
            r = httpx.post(self.base + "/chat/completions", headers={"Authorization": f"Bearer {self.key}"},
                           json={"model": self.model, **self.extra, **body}, timeout=self.timeout)
        except httpx.HTTPError as e:
            raise LLMError(f"{self.name} bağlantı hatası: {e}")
        if r.status_code >= 400:
            ra = r.headers.get("retry-after")
            raise LLMError(f"{self.name} {r.status_code}: {r.text[:120]}", r.status_code,
                           int(float(ra)) if ra and ra.replace(".", "").isdigit() else None)
        d = r.json()
        self.last_tokens = (d.get("usage") or {}).get("total_tokens")
        try:
            return d["choices"][0]["message"]
        except (KeyError, IndexError):
            raise LLMError(f"{self.name}: boş yanıt", 500)

    def chat(self, messages, max_tokens=400) -> str:
        m = self._post({"messages": messages, "max_tokens": max_tokens, "temperature": 0.4})
        return THINK.sub("", m.get("content") or "").strip()

    def vision(self, question, image_path, max_tokens=400) -> str:
        if not self.sees:
            raise LLMError(f"{self.name}: görme yok", 400)
        img = base64.b64encode(open(image_path, "rb").read()).decode()
        m = self._post({"max_tokens": max_tokens, "temperature": 0, "messages": [{"role": "user", "content": [
            {"type": "text", "text": question},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img}"}}]}]})
        return THINK.sub("", m.get("content") or "").strip()

    def chat_tools(self, messages, tools, model=None, max_tokens=1200) -> Reply:
        m = self._post({"messages": messages, "tools": tools, "max_tokens": max_tokens, "temperature": 0.1})
        calls = []
        for c in m.get("tool_calls") or []:
            a = c["function"].get("arguments") or "{}"
            try:
                args = json.loads(a) if isinstance(a, str) else a
            except ValueError:
                args = {}
            calls.append(ToolCall(c["function"]["name"], args, c.get("id", "")))
        return Reply(THINK.sub("", m.get("content") or "").strip(), calls, self.last_tokens)

    def assistant_msg(self, rep: Reply) -> dict:
        return {"role": "assistant", "content": rep.content or "",
                "tool_calls": [{"id": c.id or f"c{i}", "type": "function",
                                "function": {"name": c.name, "arguments": json.dumps(c.args, ensure_ascii=False)}}
                               for i, c in enumerate(rep.calls)]}

    def tool_msg(self, call: ToolCall, content: str) -> dict:
        return {"role": "tool", "tool_call_id": call.id or "c0", "name": call.name, "content": content}
