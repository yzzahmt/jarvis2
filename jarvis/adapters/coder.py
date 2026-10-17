"""Kodlama ajanı adaptörü — Claude KULLANMAZ. Hedef makinede kurulu ilk aracı seçer.
gemini: Google Gemini CLI (ücretsiz katman, Google hesabıyla giriş)
aider:  hedef makinedeki yerel Ollama modeliyle (bulut yok)
Bayraklar hedef makinede `--help` ile doğrulanana kadar 'verified' False kalır."""
import shlex

from ..agents.base import qpath

TOOLS = {
    # Otomatik onay bayrağı (yolo/yes-always) bilerek kullanılmıyor.
    "gemini": lambda prompt, cfg: f"gemini -p {shlex.quote(prompt)}",
    "aider": lambda prompt, cfg: ("aider --no-auto-commits --no-stream --model "
                                  + shlex.quote("ollama_chat/" + cfg.get("aider_model", "qwen2.5-coder:7b"))
                                  + " --message " + shlex.quote(prompt)),
}


class Coder:
    def __init__(self, cfg: dict):
        self.order = cfg.get("order", list(TOOLS))
        self.timeout = cfg.get("timeout_s", 900)
        self.cfg = cfg

    def available(self, agent) -> str | None:
        for name in self.order:
            if name in TOOLS and agent.run(f"command -v {name}", timeout=10).ok:
                return name
        return None

    def prompt(self, task: str, context: str = "") -> str:
        p = ("Görev (kapsam dışına çıkma, sadece gerekli dosyaları oku, dosya silme/paket kurma yapma): "
             + task.strip())
        return p + ("\n\nİlgili çıktı:\n" + context if context else "")

    def run(self, agent, workdir: str, task: str, context: str, budget, stop=None):
        tool = self.available(agent)
        if not tool:
            return None, None
        budget.turn()
        cmd = f"cd {qpath(workdir)} && " + TOOLS[tool](budget.clip(self.prompt(task, context)), self.cfg)
        return tool, agent.run(cmd, timeout=min(self.timeout, budget.max_task_seconds), stop=stop)
