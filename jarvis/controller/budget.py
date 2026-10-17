import hashlib
import time
from dataclasses import dataclass, field


class BudgetExceeded(Exception):
    pass


@dataclass
class Budget:
    """Görev başına sınırlar. Token sayımı ayrı tutulur; ölçülemezse None kalır."""
    max_agent_turns: int = 10
    max_auto_fixes: int = 2
    max_task_seconds: int = 900
    max_context_chars: int = 20000
    max_cloud_calls_per_task: int = 0
    started: float = field(default_factory=time.time)
    turns: int = 0
    cloud_calls: int = 0
    tokens: int | None = None
    fixes: dict = field(default_factory=dict)

    @classmethod
    def from_cfg(cls, cfg: dict):
        keys = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in cfg.items() if k in keys})

    def check_time(self):
        if time.time() - self.started > self.max_task_seconds:
            raise BudgetExceeded(f"Süre sınırı aşıldı ({self.max_task_seconds} sn)")

    def turn(self):
        self.check_time()
        self.turns += 1
        if self.turns > self.max_agent_turns:
            raise BudgetExceeded(f"Ajan turu sınırı ({self.max_agent_turns})")

    def cloud(self):
        if self.cloud_calls >= self.max_cloud_calls_per_task:
            raise BudgetExceeded("Bulut çağrısı izni yok / sınır doldu")
        self.cloud_calls += 1

    def fix_attempt(self, error: str):
        sig = hashlib.sha1(error.strip()[-300:].encode()).hexdigest()[:12]
        self.fixes[sig] = self.fixes.get(sig, 0) + 1
        if self.fixes[sig] > self.max_auto_fixes:
            raise BudgetExceeded(f"Aynı hata için {self.max_auto_fixes} düzeltme denendi, duruyorum")

    def clip(self, text: str) -> str:
        return text if len(text) <= self.max_context_chars else text[-self.max_context_chars:]

    def add_tokens(self, n: int | None):
        if n is not None:
            self.tokens = (self.tokens or 0) + n
