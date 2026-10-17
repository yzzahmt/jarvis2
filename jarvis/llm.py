import json
import re

import httpx


class LLMError(Exception):
    pass


class Ollama:
    """Yerel model istemcisi. Bulut yok; model başarısızsa yedek modele geçer."""

    def __init__(self, cfg: dict):
        self.url = cfg.get("url", "http://127.0.0.1:11434").rstrip("/")
        self.models = [cfg.get("model", "qwen3:4b"), *cfg.get("fallback_models", [])]
        self.timeout = cfg.get("timeout_s", 90)
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
            body = {"model": m, "messages": messages, "stream": False, "think": False,
                    "options": {"temperature": 0.2, "num_predict": max_tokens}}
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
