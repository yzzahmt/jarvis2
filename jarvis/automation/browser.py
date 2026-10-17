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


def _walk(o, out):
    """ytInitialData içinden video kimliği + başlık topla (eski ve yeni YouTube düzeni)."""
    if isinstance(o, dict):
        vr = o.get("videoRenderer")
        if isinstance(vr, dict) and vr.get("videoId"):
            runs = (vr.get("title") or {}).get("runs") or [{}]
            out.append((vr["videoId"], runs[0].get("text", "")))
        lv = o.get("lockupViewModel")
        if isinstance(lv, dict) and lv.get("contentType", "").endswith("VIDEO") and lv.get("contentId"):
            t = (((lv.get("metadata") or {}).get("lockupMetadataViewModel") or {}).get("title") or {}).get("content", "")
            out.append((lv["contentId"], t))
        for v in o.values():
            _walk(v, out)
    elif isinstance(o, list):
        for v in o:
            _walk(v, out)


def youtube_search(query: str, n: int = 5) -> dict:
    from playwright.sync_api import sync_playwright

    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(locale="tr-TR")
        pg.goto(url, wait_until="domcontentloaded", timeout=30000)
        if "consent." in pg.url:  # çerez onay sayfası: reddet
            try:
                pg.click("button:has-text('Tümünü reddet'), button:has-text('Reject all')", timeout=5000)
                pg.wait_for_load_state("domcontentloaded")
            except Exception:
                pass
        data = pg.evaluate("() => window.ytInitialData || null")
        b.close()
    found, seen, items = [], set(), []
    _walk(data or {}, found)
    for vid, title in found:
        if vid not in seen and title:
            seen.add(vid)
            items.append({"title": title, "url": f"https://www.youtube.com/watch?v={vid}"})
    return {"ok": bool(items), "results": items[:n], "search_url": url,
            **({} if items else {"error": "sonuç bulunamadı"})}


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
