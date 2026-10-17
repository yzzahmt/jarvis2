#!/usr/bin/env python3
"""Bağımsız tarayıcı aracı (Mac'te ve Linux Mint ajanında aynı dosya).
Kullanım: browser.py youtube "sorgu" | browser.py open URL
Çıktı: tek satır JSON."""
import json
import os
import platform
import subprocess
import sys
import urllib.parse


def open_url(url: str) -> dict:
    if not url.startswith(("http://", "https://")):
        return {"ok": False, "error": "Yalnızca http(s) adresleri açılır"}
    if platform.system() == "Darwin":
        cmd = ["open", url]
    else:
        os.environ.setdefault("DISPLAY", ":0")
        cmd = ["xdg-open", url]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    return {"ok": True, "url": url}


def youtube_search(query: str, n: int = 5) -> dict:
    from playwright.sync_api import sync_playwright

    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(locale="tr-TR")
        pg.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:  # çerez onay sayfası çıkarsa
            pg.click("button:has-text('Tümünü reddet'), button:has-text('Reject all')", timeout=3000)
        except Exception:
            pass
        pg.wait_for_selector("ytd-video-renderer a#video-title", timeout=20000)
        items = pg.eval_on_selector_all(
            "ytd-video-renderer a#video-title",
            f"els => els.slice(0,{n}).map(e => ({{title: (e.title || e.textContent).trim(), url: e.href}}))")
        b.close()
    return {"ok": bool(items), "results": items, "search_url": url}


def main(argv):
    try:
        if len(argv) >= 2 and argv[0] == "youtube":
            r = youtube_search(" ".join(argv[1:]))
        elif len(argv) == 2 and argv[0] == "open":
            r = open_url(argv[1])
        else:
            r = {"ok": False, "error": "kullanım: youtube SORGU | open URL"}
    except Exception as e:  # sonuç her zaman JSON
        r = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    print(json.dumps(r, ensure_ascii=False))
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
