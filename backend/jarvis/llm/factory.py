from __future__ import annotations

from jarvis.config import LlmSettings
from jarvis.llm.client import LLMClient
from jarvis.utils.logging import get_logger

log = get_logger("llm.factory")


def build_llm_client(cfg: LlmSettings) -> LLMClient:
    if cfg.provider == "cloud" and cfg.cloud_provider and cfg.cloud_api_key:
        from jarvis.llm.cloud_client import build_cloud_client

        log.info("using cloud LLM provider: %s", cfg.cloud_provider)
        return build_cloud_client(cfg.cloud_provider, cfg.cloud_api_key, cfg.cloud_model)

    from jarvis.llm.ollama_client import OllamaClient

    log.info("using local Ollama model: %s", cfg.ollama_model)
    return OllamaClient(cfg.ollama_model, host=cfg.ollama_host)
