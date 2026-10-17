from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid

from ..memory.db import DB
from ..text import norm

PENDING, RUNNING, CONFIRM, DONE, FAILED, STOPPED = (
    "bekliyor", "calisiyor", "onay_bekliyor", "tamamlandi", "basarisiz", "durduruldu")
FINAL = {DONE, FAILED, STOPPED}


class TaskManager:
    def __init__(self, db: DB, dedupe_hours: float = 24):
        self.db, self.dedupe_s = db, dedupe_hours * 3600
        self.stop_flags: dict[str, threading.Event] = {}

    @staticmethod
    def fingerprint(request: str, machine: str) -> str:
        return hashlib.sha1(f"{machine}|{norm(request)}".encode()).hexdigest()

    def recent_done(self, request: str, machine: str):
        r = self.db.q("SELECT * FROM tasks WHERE fingerprint=? AND status=? AND finished>? "
                      "ORDER BY finished DESC LIMIT 1",
                      (self.fingerprint(request, machine), DONE, time.time() - self.dedupe_s))
        return r[0] if r else None

    def busy(self, machine: str):
        r = self.db.q("SELECT id FROM tasks WHERE machine=? AND status=?", (machine, RUNNING))
        return r[0]["id"] if r else None

    def create(self, request, intent, machine, plan="", tools=(), permissions=(), status=PENDING) -> dict:
        tid = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        self.db.x("INSERT INTO tasks(id,fingerprint,request,intent,plan,machine,tools,permissions,status,created)"
                  " VALUES(?,?,?,?,?,?,?,?,?,?)",
                  (tid, self.fingerprint(request, machine), request, json.dumps(intent, ensure_ascii=False),
                   plan, machine, ",".join(tools), ",".join(permissions), status, time.time()))
        self.stop_flags[tid] = threading.Event()
        return self.get(tid)

    def get(self, tid):
        r = self.db.q("SELECT * FROM tasks WHERE id=?", (tid,))
        return r[0] if r else None

    def list(self, limit=20, status=None):
        if status:
            return self.db.q("SELECT * FROM tasks WHERE status=? ORDER BY created DESC LIMIT ?", (status, limit))
        return self.db.q("SELECT * FROM tasks ORDER BY created DESC LIMIT ?", (limit,))

    def update(self, tid, **f):
        if f:
            self.db.x(f"UPDATE tasks SET {','.join(k + '=?' for k in f)} WHERE id=?", (*f.values(), tid))

    def start(self, tid, model="kural"):
        self.update(tid, status=RUNNING, started=time.time(), model=model)

    def finish(self, tid, status, result="", error=None, budget=None):
        extra = {}
        if budget is not None:
            extra = dict(turns=budget.turns, cloud_calls=budget.cloud_calls, tokens=budget.tokens,
                         retries=sum(max(0, n - 1) for n in budget.fixes.values()))
        self.update(tid, status=status, finished=time.time(), result=result[:4000], error=error, **extra)
        self.stop_flags.pop(tid, None)

    def stop(self, tid) -> bool:
        t = self.get(tid)
        if not t or t["status"] in FINAL:
            return False
        if tid in self.stop_flags:
            self.stop_flags[tid].set()
        self.finish(tid, STOPPED, error="Kullanıcı durdurdu")
        return True

    def stopped(self, tid) -> bool:
        ev = self.stop_flags.get(tid)
        return bool(ev and ev.is_set())

    def recover(self) -> list[dict]:
        """Yeniden başlatmada yarım kalan görevleri işaretle (otomatik tekrar YOK)."""
        stale = self.db.q("SELECT * FROM tasks WHERE status=?", (RUNNING,))
        for t in stale:
            self.update(t["id"], status=STOPPED, finished=time.time(), error="Sistem yeniden başlatıldı")
        return stale
