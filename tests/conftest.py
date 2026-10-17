import pytest

from jarvis.agents.base import Result
from jarvis.core import Jarvis

MACHINES = {
    "mac": {"local": True},
    "cachyos": {"aliases": ["cachy", "cachyos"], "host": "x", "user": "u", "project_dir": "~/projeler"},
    "mint": {"aliases": ["mint", "linux mint"], "host": "y", "user": "u"},
}
SETTINGS = {
    "budget": {"max_agent_turns": 10, "max_auto_fixes": 2, "max_task_seconds": 60,
               "max_cloud_calls_per_task": 0, "dedupe_hours": 24},
    "permissions": {"confirm": ["delete", "install", "system", "account", "external"],
                    "allowed_apps": ["Safari", "Terminal"]},
}


class FakeAgent:
    configured, os, python, browser = True, "linux", "py", "browser.py"

    def __init__(self, online=True, handler=None):
        self._online, self.calls = online, []
        self.handler = handler or (lambda c: Result(True, "", "", 0))

    def online(self):
        return self._online

    def run(self, cmd, timeout=60, stop=None):
        self.calls.append(cmd)
        return self.handler(cmd)


class FakeLLM:
    def __init__(self, reply=None):
        self.last_tokens, self.last_model = 10, "fake"
        self.reply, self.calls = reply or {"intent": "chat", "reply": "Merhaba!"}, 0

    def up(self):
        return True

    def json(self, messages, max_tokens=200):
        self.calls += 1
        return self.reply

    def chat(self, messages, json_mode=False, max_tokens=300):
        self.calls += 1
        return "Merhaba!"


@pytest.fixture
def make(tmp_path):
    def _make(agents=None, llm=None, db="j.db"):
        mac = FakeAgent()
        mac.os = "darwin"
        ag = agents or {"mac": mac, "cachyos": FakeAgent(), "mint": FakeAgent()}
        return Jarvis(SETTINGS, MACHINES, tmp_path / db, llm or FakeLLM(), ag)
    return _make
