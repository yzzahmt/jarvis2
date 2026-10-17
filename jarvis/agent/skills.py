"""Beceri belleği ve makrolar.
Beceri: başarıyla biten ajan görevinin adımları SQLite'ta saklanır; benzer istek gelince modele
örnek olarak verilir (körü körüne tekrar oynatılmaz, model yine doğrular).
Makro: config/macros.yaml'daki sabit adım listesi; modelsiz çalışır, onay kuralları aynen geçerli."""
import hashlib
import json
import re
from pathlib import Path

import yaml

from ..text import norm
from . import tools as T

class MacroFailed(Exception):
    pass


STOP = {"bir", "bu", "şu", "ve", "ile", "için", "de", "da", "mi", "mı", "bana", "beni", "lütfen", "jarvis"}


def words(text: str) -> set[str]:
    return {w for w in re.findall(r"\w+", norm(text)) if len(w) > 2 and w not in STOP}


class Skills:
    def __init__(self, db, macros_path=None, min_score=0.5):
        self.db = db
        self.min_score = min_score
        self.macros = []
        if macros_path and Path(macros_path).exists():
            self.macros = (yaml.safe_load(Path(macros_path).read_text(encoding="utf-8")) or {}).get("macros", [])

    # ---------------- beceri belleği ----------------
    def save(self, task: str, steps: list, answer: str) -> bool:
        ok = [{"tool": s["tool"], "args": s["args"]} for s in steps if s.get("ok")]
        if not ok or any(s.get("denied") for s in steps):   # kullanıcı bir adımı reddettiyse örnek olmaz
            return False
        key = "beceri:" + hashlib.sha1(" ".join(sorted(words(task))).encode()).hexdigest()[:12]
        old = self.db.recall(key) or {}
        try:
            self.db.remember(key, {"task": task, "steps": ok[:15], "answer": answer[:200],
                                   "uses": old.get("uses", 0) + 1}, kind="skill")
        except ValueError:      # adımlarda gizli bilgi var -> saklanmaz
            return False
        return True

    def similar(self, task: str, k=2) -> list[dict]:
        w = words(task)
        if not w:
            return []
        scored = []
        for m in self.db.memories("skill"):
            sw = words(m["value"]["task"])
            score = len(w & sw) / len(w | sw) if sw else 0
            if score >= self.min_score:
                scored.append((score, m["value"]))
        return [v for _, v in sorted(scored, key=lambda x: -x[0])[:k]]

    def hint(self, task: str) -> str:
        sk = self.similar(task)
        if not sk:
            return ""
        lines = ["Daha önce benzer görevleri şu adımlarla başardın (örnek; koşullar değişmiş olabilir, doğrula):"]
        for s in sk:
            steps = "; ".join(f"{x['tool']}({json.dumps(x['args'], ensure_ascii=False)[:120]})" for x in s["steps"])
            lines.append(f"- \"{s['task']}\": {steps}")
        return "\n".join(lines)

    # ---------------- makrolar ----------------
    def match(self, text: str):
        t = norm(text).strip(" .'")
        for m in self.macros:
            for trig in m.get("triggers", []):
                r = re.fullmatch(trig, t)
                if r:
                    return m, {k: v.strip() for k, v in r.groupdict().items() if v}
        return None, {}

    def run_macro(self, ctx, macro: dict, vars: dict, budget) -> str:
        last = ""
        for step in macro.get("steps", []):
            budget.turn()
            if ctx.stop is not None and ctx.stop.is_set():
                return "Makro durduruldu."
            args = {k: v.format(**vars) if isinstance(v, str) else v for k, v in (step.get("args") or {}).items()}
            ctx.progress(step["tool"], args)
            res, ran = T.call(ctx, step["tool"], args)
            if not ran:
                raise MacroFailed(f"{macro['name']} makrosu '{step['tool']}' adımında durdu: {res[:150]}")
            if T.TOOLS[step["tool"]].info:
                last = res
        return macro.get("say", "").format(**vars) or T.clip(last, 300) or "Tamam."
