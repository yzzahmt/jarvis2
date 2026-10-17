import json
import sqlite3
import threading
import time
from pathlib import Path

from ..text import looks_secret

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks(
  id TEXT PRIMARY KEY, fingerprint TEXT, request TEXT, intent TEXT, plan TEXT,
  machine TEXT, tools TEXT, permissions TEXT, status TEXT, model TEXT,
  created REAL, started REAL, finished REAL,
  turns INTEGER DEFAULT 0, retries INTEGER DEFAULT 0, cloud_calls INTEGER DEFAULT 0,
  tokens INTEGER,            -- NULL = ölçülemedi
  result TEXT, error TEXT);
CREATE INDEX IF NOT EXISTS ix_fp ON tasks(fingerprint, status);
CREATE TABLE IF NOT EXISTS memory(
  key TEXT PRIMARY KEY, value TEXT, kind TEXT, updated REAL);
"""


class DB:
    def __init__(self, path: str | Path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.c = sqlite3.connect(str(path), check_same_thread=False)
        self.c.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        self.c.executescript(SCHEMA)

    def q(self, sql, args=()):
        with self.lock:
            return [dict(r) for r in self.c.execute(sql, args).fetchall()]

    def x(self, sql, args=()):
        with self.lock:
            self.c.execute(sql, args)
            self.c.commit()

    # --- kalıcı hafıza (tercihler, projeler, özetler) ---
    def remember(self, key: str, value, kind: str = "pref", allow_secret=False):
        v = json.dumps(value, ensure_ascii=False)
        if not allow_secret and (looks_secret(key) or looks_secret(v)):
            raise ValueError("Gizli bilgi hafızaya kaydedilmez")
        self.x("INSERT OR REPLACE INTO memory VALUES(?,?,?,?)", (key, v, kind, time.time()))

    def recall(self, key: str, default=None):
        r = self.q("SELECT value FROM memory WHERE key=?", (key,))
        return json.loads(r[0]["value"]) if r else default

    def memories(self, kind: str | None = None):
        rows = self.q("SELECT * FROM memory" + (" WHERE kind=?" if kind else "") + " ORDER BY key",
                      (kind,) if kind else ())
        return [{**r, "value": json.loads(r["value"])} for r in rows]

    def forget(self, key: str):
        self.x("DELETE FROM memory WHERE key=?", (key,))
