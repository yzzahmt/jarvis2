"""Görünür, kalıcı tarayıcı oturumu (girişler data/browser-profile'da kalır).
Playwright tek iş parçacığında çalışmalı; tüm çağrılar özel bir işçiye gönderilir."""
import re
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

from .browser import _walk

# site: (adres, giriş kutusu seçicisi, yanıt seçicisi). Site arayüzü değişirse yalnızca burası güncellenir.
AI_SITES = {
    "gemini": ("https://gemini.google.com/app", "rich-textarea [contenteditable=true], div[contenteditable=true]",
               "message-content"),
    "chatgpt": ("https://chatgpt.com/", "#prompt-textarea", "[data-message-author-role=assistant]"),
}


class BrowserSession:
    def __init__(self, profile_dir):
        self.profile = str(profile_dir)
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="browser")
        self.pw = self.ctx = self.page = None

    def do(self, action, timeout=90, **a) -> str:
        if action == "ai_chat" and a.get("site") not in AI_SITES:
            return f"bilinmeyen yapay zekâ sitesi: {a.get('site')} (bilinenler: {', '.join(AI_SITES)})"
        return self.pool.submit(self._do, action, wait=timeout - 10, **a).result(timeout=timeout)

    def _ensure(self):
        if self.page and not self.page.is_closed():
            return
        from playwright.sync_api import sync_playwright
        self.pw = self.pw or sync_playwright().start()
        if self.ctx is None or not self.ctx.pages:
            self.ctx = self.pw.chromium.launch_persistent_context(self.profile, headless=False, locale="tr-TR",
                                                                  viewport=None, args=["--start-maximized"])
        self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()

    def _summary(self, n=2500):
        p = self.page
        txt = re.sub(r"\s+", " ", p.inner_text("body", timeout=5000))[:n]
        links = p.eval_on_selector_all("a, button, [role=button]",
                                       "els => els.filter(e => e.offsetParent).slice(0, 40)"
                                       ".map(e => (e.innerText || e.getAttribute('aria-label') || '').trim().slice(0, 40))"
                                       ".filter(Boolean)")
        return f"[{p.title()}] {p.url}\nMETİN: {txt}\nTIKLANABİLİR: {' | '.join(dict.fromkeys(links))}"

    def _ai_chat(self, site, prompt, wait):
        """Tarayıcıdaki yapay zekâ sohbetine yazar, yanıt metni durulunca döndürür (oturum kullanıcınındır)."""
        url, box_sel, ans_sel = AI_SITES[site]
        p = self.page
        if urllib.parse.urlparse(p.url).netloc != urllib.parse.urlparse(url).netloc:
            p.goto(url, wait_until="domcontentloaded", timeout=30000)
        box = p.locator(box_sel).first
        try:
            box.wait_for(state="visible", timeout=15000)
        except Exception:
            return f"{site} sohbet kutusu bulunamadı; tarayıcıda oturum açman gerekebilir."
        before = p.locator(ans_sel).count()
        box.click()
        box.fill(prompt)
        p.keyboard.press("Enter")
        end, last, stable = time.time() + wait, "", 0
        while time.time() < end:
            p.wait_for_timeout(1500)
            ans = p.locator(ans_sel)
            if ans.count() <= before:
                continue
            cur = ans.last.inner_text(timeout=5000).strip()
            stable = stable + 1 if cur and cur == last else 0
            last = cur
            if stable >= 2:
                return f"[{site}] {last}"
        return f"[{site}] {last} ...[yanıt tamamlanmadı]" if last else f"{site} yanıt vermedi"

    def _do(self, action, url=None, text=None, label=None, key=None, query=None, site=None, wait=80, **_):
        self._ensure()
        p = self.page
        if action == "goto":
            if not url:
                return "url gerekli"
            p.goto(url if url.startswith("http") else "https://" + url, wait_until="domcontentloaded", timeout=30000)
            p.wait_for_timeout(1200)
            return self._summary(1500)
        if action == "read":
            return self._summary()
        if action == "click":
            loc = p.get_by_role("link", name=text).or_(p.get_by_role("button", name=text)).or_(p.get_by_text(text))
            loc.first.click(timeout=6000)
            p.wait_for_timeout(1200)
            return "tıklandı. " + self._summary(800)
        if action == "fill":
            loc = p.get_by_label(label).or_(p.get_by_placeholder(label)).or_(p.get_by_role("searchbox"))
            loc.first.fill(text or "", timeout=6000)
            return "yazıldı"
        if action == "press":
            p.keyboard.press(key or "Enter")
            p.wait_for_timeout(1200)
            return "basıldı. " + self._summary(800)
        if action == "youtube":
            p.goto("https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query or text or ""),
                   wait_until="domcontentloaded", timeout=30000)
            found = []
            _walk(p.evaluate("() => window.ytInitialData || null") or {}, found)
            seen, out = set(), []
            for vid, title in found:
                if vid not in seen and title:
                    seen.add(vid)
                    out.append(f"{len(out) + 1}. {title} | https://www.youtube.com/watch?v={vid}")
            return "\n".join(out[:6]) or "sonuç yok"
        if action == "ai_chat":
            return self._ai_chat(site, text or query or "", wait)
        return f"bilinmeyen eylem: {action}"
