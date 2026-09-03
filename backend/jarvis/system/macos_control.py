from __future__ import annotations

import subprocess

from jarvis.utils.logging import get_logger

log = get_logger("system.macos")


def open_app(app_name: str) -> str:
    result = subprocess.run(
        ["open", "-a", app_name], capture_output=True, text=True, timeout=15
    )
    if result.returncode != 0:
        raise RuntimeError(f"couldn't open '{app_name}': {result.stderr.strip() or 'not found'}")
    return f"Opened {app_name}"


def open_url(url: str) -> str:
    result = subprocess.run(["open", url], capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        raise RuntimeError(f"couldn't open URL: {result.stderr.strip()}")
    return f"Opened {url}"


# Narrow, explicit AppleScript actions — kept out of the LLM tool registry for
# Phase 1 (not requested there yet), but available for a future settings-panel
# "quick actions" feature or Phase 2 without touching system-level code again.
def set_volume(level: int) -> str:
    level = max(0, min(100, level))
    subprocess.run(["osascript", "-e", f"set volume output volume {level}"], check=True, timeout=10)
    return f"Volume set to {level}"


def lock_screen() -> str:
    subprocess.run(
        [
            "osascript",
            "-e",
            'tell application "System Events" to keystroke "q" using {control down, command down}',
        ],
        check=True,
        timeout=10,
    )
    return "Screen locked"
