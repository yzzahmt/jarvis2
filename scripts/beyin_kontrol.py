"""Beyin zincirini dener: anahtarı olan her sağlayıcıda modelin var olup olmadığına ve kısa bir cevaba bakar.
Kullanım: source scripts/env.sh && python scripts/beyin_kontrol.py   (anahtarlar yazdırılmaz)"""
import os
import sys
import time

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from jarvis import config  # noqa: E402

for line in open(config.path(".env"), encoding="utf-8"):
    k, _, v = line.partition("=")
    if k.strip() and v.strip() and not k.startswith("#"):
        os.environ.setdefault(k.strip(), v.split("#")[0].strip())

for b in config.load("settings")["brains"]:
    env = b.get("api_key_env")
    key = os.environ.get(env, "") if env else "yerel"
    if not key:
        print(f"  –  {b['name']:12s} anahtar yok ({env})")
        continue
    h = {"Authorization": f"Bearer {key}"} if env else {}
    t = time.time()
    try:
        r = httpx.post(b["base_url"] + "/chat/completions", headers=h, timeout=30, json={
            "model": b["model"], "max_tokens": 20, "messages": [{"role": "user", "content": "Tek kelimeyle selam ver."}]})
        ok = r.status_code == 200
        msg = r.json()["choices"][0]["message"].get("content", "")[:30] if ok else r.text[:90].replace("\n", " ")
    except Exception as e:  # ağ / yerel model kapalı
        ok, msg = False, str(e)[:90]
    print(f"  {'✓' if ok else '✕'}  {b['name']:12s} {b['model']:38s} {time.time() - t:4.1f}s  {msg}")
