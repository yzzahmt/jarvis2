"""Bilgisayar ajanları: Mac için yerel, Linux makineleri için SSH. Ajanlarda sunucu/port açılmaz."""
import os
import shlex
import socket
import subprocess
import threading
import time
from dataclasses import dataclass

from .. import config


@dataclass
class Result:
    ok: bool
    out: str = ""
    err: str = ""
    code: int = 0


def _exec(argv, timeout, stop: threading.Event | None) -> Result:
    try:
        p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                             stdin=subprocess.DEVNULL)
    except OSError as e:
        return Result(False, err=str(e), code=-1)
    end = time.time() + timeout
    while p.poll() is None:
        if (stop and stop.is_set()) or time.time() > end:
            p.kill()
            out, err = p.communicate()
            why = "durduruldu" if stop and stop.is_set() else f"zaman aşımı ({timeout} sn)"
            return Result(False, out, (err + "\n" + why).strip(), -9)
        time.sleep(0.1)
    out, err = p.communicate()
    return Result(p.returncode == 0, out, err, p.returncode)


class LocalAgent:
    local, configured = True, True

    def __init__(self, name="mac", cfg=None):
        self.name, self.cfg = name, cfg or {}
        self.python = str(config.HOME / ".venv/bin/python")
        self.browser = str(config.HOME / "jarvis/automation/browser.py")
        self.os = "darwin"

    def online(self) -> bool:
        return True

    def run(self, cmd: str, timeout=60, stop=None) -> Result:
        return _exec(["/bin/bash", "-c", cmd], timeout, stop)


class SSHAgent:
    local = False

    def __init__(self, name: str, cfg: dict):
        self.name, self.cfg = name, cfg
        self.host, self.user, self.port = cfg.get("host"), cfg.get("user"), int(cfg.get("port", 22))
        self.key = os.path.expanduser(cfg.get("key", "~/.ssh/jarvis_ed25519"))
        self.configured = bool(self.host and self.user)
        home = cfg.get("agent_dir", "~/jarvis-agent")
        self.python = cfg.get("python", f"{home}/.venv/bin/python")
        self.browser = f"{home}/browser.py"
        self.os = "linux"

    def online(self, timeout=2.0) -> bool:
        if not self.configured:
            return False
        try:
            with socket.create_connection((self.host, self.port), timeout=timeout):
                return True
        except OSError:
            return False

    def ssh_argv(self, remote: str) -> list[str]:
        return ["ssh", "-i", self.key, "-p", str(self.port), "-o", "BatchMode=yes",
                "-o", "ConnectTimeout=5", "-o", "StrictHostKeyChecking=accept-new",
                "-o", "ServerAliveInterval=15", f"{self.user}@{self.host}", remote]

    def run(self, cmd: str, timeout=60, stop=None) -> Result:
        # Uzak kabuk fish/zsh olabilir; komutu her zaman bash'e ver.
        cmd = 'export PATH="$HOME/.local/bin:$HOME/.local/node/bin:$PATH"; ' + cmd   # gemini-cli ve Node (Zorin) ~/.local altında
        return _exec(self.ssh_argv("bash -lc " + shlex.quote(cmd)), timeout, stop)

    def copy(self, local: str, remote: str, timeout=60) -> Result:
        return _exec(["scp", "-i", self.key, "-P", str(self.port), "-o", "BatchMode=yes",
                      local, f"{self.user}@{self.host}:{remote}"], timeout, None)


def build_agents(machines: dict) -> dict:
    return {n: (LocalAgent(n, c) if (c or {}).get("local") else SSHAgent(n, c or {}))
            for n, c in machines.items()}


def qpath(p: str) -> str:
    """Kabuk için güvenli yol; baştaki ~ uzak makinede de genişler."""
    if p == "~":
        return '"$HOME"'
    if p.startswith("~/"):
        return '"$HOME"/' + shlex.quote(p[2:])
    return shlex.quote(p)
