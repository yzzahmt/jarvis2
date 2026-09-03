from __future__ import annotations

import threading
from pathlib import Path

from jarvis.utils.logging import get_logger

log = get_logger("browser.controller")

PROFILE_DIR = Path.home() / ".jarvis" / "browser_profile"

# A dedicated Chromium profile, separate from the user's real browser: it has
# no saved passwords, payment methods or logged-in sessions. That's a
# deliberate safety backstop for the shopping tools — even if a click lands
# somewhere unexpected, there's no stored payment info for it to reach.
# It's a real, visible (headed) window so the user can watch it work and
# step in at any point.


class BrowserController:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._playwright = None
        self._context = None

    def _ensure_started(self):
        if self._context is not None:
            return self._context
        with self._lock:
            if self._context is not None:
                return self._context
            from playwright.sync_api import sync_playwright

            PROFILE_DIR.mkdir(parents=True, exist_ok=True)
            self._playwright = sync_playwright().start()
            self._context = self._playwright.chromium.launch_persistent_context(
                str(PROFILE_DIR),
                headless=False,
                viewport={"width": 1280, "height": 900},
            )
            log.info("browser context started (profile=%s)", PROFILE_DIR)
        return self._context

    def new_page(self):
        ctx = self._ensure_started()
        page = ctx.new_page()
        page.bring_to_front()
        return page


controller = BrowserController()
