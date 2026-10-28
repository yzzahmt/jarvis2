"""Görünür, kalıcı tarayıcı oturumu (girişler data/browser-profile'da kalır).
Playwright tek iş parçacığında çalışmalı; tüm çağrılar özel bir işçiye gönderilir.
Sayfa modele numaralı öğe listesi olarak verilir ([12] button "Sepete ekle"); model numarayla tıklar/yazar.
Gizli değerler (şifre, API anahtarı) modelden geçmez: Anahtar Zinciri → alan, sayfa/pano → dosya."""
import re
import subprocess
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

from .. import secrets
from .browser import _walk

# site: (adres, giriş kutusu seçicisi, yanıt seçicisi). Site arayüzü değişirse yalnızca burası güncellenir.
AI_SITES = {
    "gemini": ("https://gemini.google.com/app", "rich-textarea [contenteditable=true], div[contenteditable=true]",
               "message-content"),
    "chatgpt": ("https://chatgpt.com/", "#prompt-textarea", "[data-message-author-role=assistant]"),
}

# Görünür etkileşimli öğeleri numaralar (data-jid) ve kısa tanım döndürür. Şifre alanlarının değeri gönderilmez.
MARK_JS = r"""(max) => {
  document.querySelectorAll('[data-jid]').forEach(e => e.removeAttribute('data-jid'));
  const sel = 'a[href],button,input:not([type=hidden]),select,textarea,summary,[role=button],[role=link],[role=checkbox],' +
              '[role=radio],[role=tab],[role=menuitem],[role=option],[role=switch],[role=combobox],[contenteditable=true],[onclick]';
  const vh = innerHeight, out = [];
  let n = 0;
  for (const e of document.querySelectorAll(sel)) {
    const r = e.getBoundingClientRect(), st = getComputedStyle(e);
    if (r.width < 4 || r.height < 4 || st.visibility === 'hidden' || st.display === 'none' || +st.opacity === 0) continue;
    if (r.bottom < -vh * 0.5 || r.top > vh * 2) continue;          // ekranın çok uzağındakiler değil
    const tag = e.tagName.toLowerCase(), type = (e.getAttribute('type') || '').toLowerCase();
    let label = (e.getAttribute('aria-label') || e.innerText || e.getAttribute('placeholder') || e.getAttribute('title') ||
                 e.getAttribute('name') || e.getAttribute('alt') || (e.querySelector('img') || {}).alt || '').trim();
    if (!label && e.id) { const l = document.querySelector(`label[for="${CSS.escape(e.id)}"]`); if (l) label = l.innerText.trim(); }
    if (!label && tag === 'input' && ['submit', 'button'].includes(type)) label = e.value;
    label = label.replace(/\s+/g, ' ').slice(0, 60);
    let val = '';
    if (['input', 'textarea'].includes(tag) && !['submit', 'button', 'checkbox', 'radio'].includes(type))
      val = type === 'password' ? (e.value ? '••••' : '') : (e.value || '').slice(0, 40);
    if (tag === 'select') val = (e.options[e.selectedIndex] || {}).text || '';
    if (['checkbox', 'radio'].includes(type)) val = e.checked ? '✓' : '☐';
    if (!label && !val && tag === 'a') continue;
    e.setAttribute('data-jid', ++n);
    out.push(`[${n}] ${tag}${type ? '[' + type + ']' : ''} "${label}"${val ? ' =' + val : ''}${r.top > vh ? ' ↓' : ''}`);
    if (n >= max) break;
  }
  return out;
}"""

PAY = re.compile(r"(satın al|siparişi (onayla|tamamla|ver)|ödemeyi? (yap|tamamla|onayla)|^öde\b|alışverişi tamamla|"
                 r"place order|complete (order|purchase)|pay now|buy now|confirm (payment|purchase)|abone ol|subscribe)", re.I)
ACCOUNT = re.compile(r"(hesap oluştur|kayıt ol|üye ol|sign ?up|create (an )?account|register)", re.I)
CHECKOUT_URL = re.compile(r"(checkout|odeme|ödeme|payment|siparis-?onay|order-?review)", re.I)
MONEY = re.compile(r"(?:₺\s?[\d.,]+|[\d.,]+\s?(?:TL|₺|USD|\$|EUR|€))")


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
        if self.ctx is not None and self.ctx.pages:
            if not self.page or self.page.is_closed():
                self.page = self.ctx.pages[-1]
            return
        from playwright.sync_api import sync_playwright
        self.pw = self.pw or sync_playwright().start()
        self.ctx = self.pw.chromium.launch_persistent_context(
            self.profile, headless=False, locale="tr-TR", viewport=None,
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
            ignore_default_args=["--enable-automation"])
        self.ctx.on("page", self._new_page)            # yeni sekme/açılır pencere açılınca ona geç
        self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()

    def _new_page(self, p):
        self.page = p

    def _settle(self, ms=1200):
        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=8000)
        except Exception:
            pass
        self.page.wait_for_timeout(ms)

    # ---- sayfayı modele anlat ----
    def _summary(self, n=1500, max_el=70):
        p = self.page
        try:
            txt = re.sub(r"\s+", " ", p.inner_text("body", timeout=5000))[:n]
        except Exception:
            txt = ""
        try:
            els = p.evaluate(MARK_JS, max_el)
        except Exception:
            els = []
        tabs = len(self.ctx.pages) if self.ctx else 1
        return (f"[{p.title()[:80]}] {p.url[:150]}" + (f" (sekme {tabs})" if tabs > 1 else "") +
                f"\nMETİN: {txt}\nÖĞELER (numarayla kullan, ↓ = aşağıda):\n" + "\n".join(els))

    def _el(self, id):
        loc = self.page.locator(f'[data-jid="{int(id)}"]')
        if not loc.count():
            raise LookupError(f"[{id}] bulunamadı — sayfa değişmiş olabilir, önce look yap")
        return loc.first

    def label(self, id=None, text=None) -> str:
        """Tıklanacak öğenin görünen adı (onay denetimi için)."""
        return self.pool.submit(self._label, id, text).result(timeout=20)

    def _label(self, id, text):
        if text:
            return text
        if id is None or self.page is None:
            return ""
        try:
            e = self._el(id)
            return (e.get_attribute("aria-label") or e.inner_text(timeout=2000) or e.get_attribute("value") or "").strip()
        except Exception:
            return ""

    def checkout_info(self) -> tuple[bool, str]:
        """(ödeme sayfası mı, sayfadaki tutarlar) — onay sorusunda kullanıcıya gösterilir."""
        def f():
            if self.page is None:
                return False, ""
            try:
                body = self.page.inner_text("body", timeout=4000)
            except Exception:
                body = ""
            amounts = list(dict.fromkeys(MONEY.findall(body)))[-4:]
            return bool(CHECKOUT_URL.search(self.page.url)), ", ".join(amounts)
        return self.pool.submit(f).result(timeout=20)

    def screenshot(self, path) -> str:
        def f():
            self._ensure()
            self.page.screenshot(path=str(path))
            return str(path)
        return self.pool.submit(f).result(timeout=30)

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

    def _target(self, id, text):
        if id is not None and str(id).strip().isdigit():
            return self._el(id)
        if not text:
            raise LookupError("id veya text gerekli")
        p = self.page
        return (p.get_by_role("button", name=text).or_(p.get_by_role("link", name=text))
                .or_(p.get_by_text(text, exact=False))).first

    def _secret_value(self, id, source):
        if source == "clipboard":
            return subprocess.run(["pbpaste"], capture_output=True, text=True).stdout.strip()
        e = self._el(id)
        tag = e.evaluate("e => e.tagName.toLowerCase()")
        v = e.input_value() if tag in ("input", "textarea") else e.inner_text()
        return (v or e.get_attribute("value") or "").strip()

    def _do(self, action, url=None, text=None, label=None, key=None, query=None, site=None, wait=80, id=None,
            option=None, direction=None, secret=None, source=None, env_file=None, var=None, index=None, **_):
        self._ensure()
        p = self.page
        if action == "goto":
            if not url:
                return "url gerekli"
            p.goto(url if "://" in url else "https://" + url, wait_until="domcontentloaded", timeout=30000)
            self._settle()
            return self._summary()
        if action in ("read", "look"):
            return self._summary(3000 if action == "read" else 1500)
        if action == "click":
            self._target(id, text).click(timeout=8000)
            self._settle()
            return "tıklandı. " + self._summary(800)
        if action in ("type", "fill"):
            e = self._el(id) if id is not None else p.get_by_label(label).or_(p.get_by_placeholder(label)).first
            e.fill(text or "", timeout=8000)
            if key:
                e.press(key)
                self._settle()
                return "yazıldı ve basıldı. " + self._summary(800)
            return "yazıldı"
        if action == "fill_secret":
            v = secrets.get(secret or "")
            if v is None:
                return (f"'{secret}' kasada yok. Kullanıcıdan Terminal'de 'python -m jarvis secret set {secret}' "
                        f"ile eklemesini iste ya da tarayıcıda kendisi girsin. Kayıtlılar: {', '.join(secrets.names())}")
            self._el(id).fill(v, timeout=8000)
            return f"[{id}] alanına '{secret}' yazıldı (değer gizli)"
        if action == "save_secret":
            v = self._secret_value(id, source)
            if len(v) < 8 or " " in v.strip():
                return f"değer anahtar gibi görünmüyor ({len(v)} karakter). Önce anahtarı göster/kopyala, sonra tekrar dene."
            out = []
            if secret:
                out.append(f"kasaya '{secret}' kaydedildi" if secrets.put(secret, v) else "kasaya yazılamadı")
            if env_file and var:
                out.append(secrets.write_env(env_file, var, v))
            return "; ".join(out) or "secret veya env_file+var gerekli"
        if action == "select":
            self._el(id).select_option(label=option, timeout=8000)
            return f"seçildi: {option}"
        if action == "press":
            p.keyboard.press(key or "Enter")
            self._settle()
            return "basıldı. " + self._summary(800)
        if action == "scroll":
            p.mouse.wheel(0, -700 if direction == "up" else 700)
            p.wait_for_timeout(600)
            return self._summary(600)
        if action == "back":
            p.go_back(timeout=15000)
            self._settle()
            return self._summary(800)
        if action == "tabs":
            pages = self.ctx.pages
            if index is not None and 0 <= int(index) < len(pages):
                self.page = pages[int(index)]
                self.page.bring_to_front()
                return self._summary(800)
            return "\n".join(f"{i}: {x.title()[:60]} {x.url[:80]}" for i, x in enumerate(pages))
        if action == "wait":
            p.wait_for_timeout(min(int(float(text or 3) * 1000), 30000))
            return self._summary(800)
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
