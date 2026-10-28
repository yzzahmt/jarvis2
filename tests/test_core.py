import json

import pytest

from jarvis.agents.base import Result, qpath
from jarvis.controller.budget import Budget, BudgetExceeded
from jarvis.controller.router import route
from jarvis.controller.task_manager import DONE, FAILED, RUNNING, STOPPED
from tests.conftest import MACHINES, FakeAgent, FakeLLM


@pytest.mark.parametrize("text,name,machine", [
    ("Jarvis, uyan", "wake", "mac"),
    ("saat kaç", "time", "mac"),
    ("uyku moduna geç", "sleep", "mac"),
    ("bilgisayarlar çevrimiçi mi", "status", "mac"),
    ("Linux Mint bilgisayarında YouTube'u aç ve lofi müzik videosunu bul", "youtube", "mint"),
    ("Zorin OS bilgisayarında tarih projesinin testlerini çalıştır", "run_tests", "zorin"),
    ("Safari'yi aç", "open_app", "mac"),
    ("ikinci videoyu aç", "pick_result", "mint"),
    ("github.com aç", "open_url", "mac"),
])
def test_rules(text, name, machine):
    i = route(text, MACHINES)
    assert i and i.name == name and i.machine == machine


def test_youtube_query_and_project():
    assert route("Linux Mint bilgisayarında YouTube'u aç ve lofi müzik videosunu bul", MACHINES).args["query"] == "lofi müzik"
    assert route("zorin'de tarih projesinin testlerini çalıştır", MACHINES).args["project"] == "tarih"
    assert route("Safari'yi aç", MACHINES).args["app"] == "safari"


def test_simple_commands_no_llm(make):
    llm = FakeLLM()
    j = make(llm=llm)
    for t in ["saat kaç", "bugün ayın kaçı", "Jarvis uyan", "bilgisayarlar çevrimiçi mi", "uyu"]:
        j.handle(t)
    assert llm.calls == 0


def test_unknown_goes_to_local_llm(make):
    llm = FakeLLM()
    assert make(llm=llm).handle("nasılsın bugün") == "Merhaba!" and llm.calls == 1


def test_budget_limits():
    b = Budget(max_agent_turns=2, max_auto_fixes=2, max_cloud_calls_per_task=0)
    b.turn(); b.turn()
    with pytest.raises(BudgetExceeded):
        b.turn()
    with pytest.raises(BudgetExceeded):
        b.cloud()
    b.fix_attempt("E1"); b.fix_attempt("E1")
    with pytest.raises(BudgetExceeded):
        b.fix_attempt("E1")
    assert b.tokens is None  # ölçülmeden rakam yok


def test_open_app_records_task(make):
    j = make()
    assert j.handle("Safari'yi aç") == "Safari açıldı."
    t = j.tm.list(1)[0]
    assert t["status"] == DONE and t["machine"] == "mac" and "open -a" in j.agents["mac"].calls[0]


def test_disallowed_app(make):
    j = make()
    assert "izin verilen" in j.handle("Steam'i aç")
    assert j.tm.list(1)[0]["status"] == FAILED


def test_offline_machine(make):
    j = make(agents={"mac": FakeAgent(), "zorin": FakeAgent(online=False), "mint": FakeAgent()})
    assert "çevrimdışı" in j.handle("zorin tarih projesinin testlerini çalıştır")
    assert j.tm.list(1)[0]["status"] == FAILED


def test_sensitive_needs_confirm(make):
    j = make()
    r = j.handle("zorin'de eski log dosyalarını sil, kodu düzelt")
    assert "onay" in r.lower() and j.agents["zorin"].calls == []
    assert "iptal" in j.handle("hayır").lower()
    assert j.tm.list(1)[0]["status"] == STOPPED


def test_run_tests_and_dedupe(make):
    out = "..F\n==== 1 failed, 2 passed in 0.1s ===="
    zorin = FakeAgent(handler=lambda c: Result(False, out, "", 1))
    j = make(agents={"mac": FakeAgent(), "zorin": zorin, "mint": FakeAgent()})
    r = j.handle("zorin tarih projesinin testlerini çalıştır")
    assert "1 failed, 2 passed" in r and '"$HOME"/' in zorin.calls[0]
    assert "tekrar" in j.handle("zorin tarih projesinin testlerini çalıştır")
    assert len(zorin.calls) == 1   # ikinci kez onaysız çalışmadı


def test_fix_loop_is_bounded(make):
    def h(c):
        if "command -v gemini" in c or "gemini -p" in c:
            return Result(True)
        return Result(False, "==== 1 failed in 0.1s ====", "", 1)
    zorin = FakeAgent(handler=h)
    j = make(agents={"mac": FakeAgent(), "zorin": zorin, "mint": FakeAgent()})
    j.db.remember("proje:zorin", "tarih", kind="project")
    r = j.handle("zorin'de login fonksiyonundaki hatayı düzelt")
    assert "düzeltme denendi" in r
    assert sum("gemini -p" in c for c in zorin.calls) == 3   # ilk + 2 düzeltme


def test_youtube_flow(make):
    res = [{"title": f"Video {n}", "url": f"https://youtu.be/{n}"} for n in range(5)]
    mint = FakeAgent(handler=lambda c: Result(True, json.dumps({"ok": True, "results": res})))
    j = make(agents={"mac": FakeAgent(), "zorin": FakeAgent(), "mint": mint})
    assert "Hangisini" in j.handle("mint'te youtube'da lofi ara")
    assert "Video 1" in j.handle("ikinci videoyu aç") and "youtu.be/1" in mint.calls[-1]


def test_memory_and_secrets(make):
    j = make()
    j.handle("hatırla: proje tarih = /Volumes/HDD/projeler/tarih")
    assert "tarih" in j.handle("proje tarih neydi")
    assert "kaydedilmez" in j.handle("hatırla: wifi şifre = 1234")


def test_restart_recovers(make, tmp_path):
    j = make(db="r.db")
    t = j.tm.create("x", {}, "mac")
    j.tm.start(t["id"])
    j2 = make(db="r.db")
    assert j2.tm.get(t["id"])["status"] == STOPPED and len(j2.recovered) == 1
    assert j2.tm.list(5)[0]["request"] == "x"   # geçmiş korunuyor


def test_qpath():
    assert qpath("~/a b") == "\"$HOME\"/'a b'"


def test_music_goes_to_youtube_and_aliases():
    from jarvis.controller.permissions import Permissions
    i = route("biraz caz müziği açsana", MACHINES)
    assert i.name == "youtube" and "caz" in i.args["query"]
    p = Permissions({"allowed_apps": ["Notes"], "app_aliases": {"notlar": "Notes"}})
    assert p.app("notlar") == "Notes" and p.app("steam") is None
