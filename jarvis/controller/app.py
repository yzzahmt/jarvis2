"""Yerel kontrol API'si (yalnızca 127.0.0.1)."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from ..core import Jarvis


class Cmd(BaseModel):
    text: str


class Mem(BaseModel):
    value: object
    kind: str = "user"


def create_app(j: Jarvis | None = None) -> FastAPI:
    app = FastAPI(title="JARVIS")
    app.state.j = j = j or Jarvis()

    @app.get("/health")
    def health():
        return {"llm": j.llm.up(), "machines": {n: (a.configured and a.online()) for n, a in j.agents.items()}}

    @app.post("/command")
    def command(c: Cmd):
        return {"reply": j.handle(c.text)}

    @app.get("/tasks")
    def tasks(limit: int = 20, status: str | None = None):
        return j.tm.list(limit, status)

    @app.get("/tasks/{tid}")
    def task(tid: str):
        return j.tm.get(tid) or _404()

    @app.post("/tasks/{tid}/stop")
    def stop(tid: str):
        return {"stopped": j.tm.stop(tid)}

    @app.get("/memory")
    def memory(kind: str | None = None):
        return j.db.memories(kind)

    @app.put("/memory/{key}")
    def put(key: str, m: Mem):
        try:
            j.db.remember(key, m.value, m.kind)
        except ValueError as e:
            raise HTTPException(400, str(e))
        return {"ok": True}

    @app.delete("/memory/{key}")
    def forget(key: str):
        j.db.forget(key)
        return {"ok": True}

    return app


def _404():
    raise HTTPException(404, "yok")
