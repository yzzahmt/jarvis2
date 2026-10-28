import pytest

from jarvis.agent import loop, tools as T
from jarvis.agent.skills import MacroFailed, Skills
from jarvis.agents.base import Result
from jarvis.automation.session import BrowserSession
from jarvis.controller.budget import Budget, BudgetExceeded
from jarvis.controller.task_manager import DONE, FAILED
from jarvis.llm import Reply, ToolCall
from jarvis.memory.db import DB
from tests.conftest import MACHINES, FakeAgent, FakeLLM

MACROS = """
macros:
  - name: hatırla
    triggers: ["(?P<k>\\\\w+) notunu (?P<v>.+) yap"]
    steps:
      - {tool: remember, args: {key: "{k}", value: "{v}"}}
    say: "{k} kaydedildi."
  - name: bozuk
    triggers: ["bozuk makro"]
    steps:
      - {tool: yok_boyle_arac, args: {}}
"""


class ScriptLLM(FakeLLM):
    """Sırayla verilen araç çağrılarını yapar, bitince son cevabı söyler."""

    def __init__(self, script, final="Bitti.", intent=None):
        super().__init__(intent or {"intent": "agent", "args": {"task": "dosyaları listele"}, "machine": "mac"})
        self.script, self.final, self.seen = list(script), final, []

    def chat_tools(self, messages, tools, model=None, max_tokens=800):
        self.seen.append([dict(m) for m in messages])
        if self.script:
            name, args = self.script.pop(0)
            return Reply("", [ToolCall(name, args)], 5)
        return Reply(self.final, [], 5)

    def assistant_msg(self, rep):
        return {"role": "assistant", "content": rep.content, "tool_calls": [c.name for c in rep.calls]}

    def tool_msg(self, call, content):
        return {"role": "tool", "content": content, "tool_name": call.name}


def ctx(db, agents=None, ask=lambda q: "", budget=None):
    return loop.Ctx(db=db, agents=agents or {}, machines=MACHINES, coder=None, budget=budget,
                    browser=lambda: None, vision=lambda q, f: "")


@pytest.fixture
def db(tmp_path):
    return DB(tmp_path / "a.db")


def test_loop_runs_tools_and_answers(db):
    llm = ScriptLLM([("remember", {"key": "renk", "value": "mavi"})], final="Kaydettim.")
    ans, steps = loop.run("rengimi hatırla", ctx(db), llm, Budget())
    assert ans == "Kaydettim." and steps == [{"tool": "remember", "args": {"key": "renk", "value": "mavi"},
                                              "ok": True, "denied": False}]
    assert db.recall("renk") == "mavi"
    assert llm.seen[1][-1]["role"] == "tool"          # araç sonucu modele döndü


def test_confirm_denied_and_danger_blocked(db):
    mac = FakeAgent()
    c = ctx(db, {"mac": mac})
    c.ask = lambda q: "hayır"
    res, ran = T.call(c, "shell", {"command": "rm -rf ~/x"})
    assert not ran and res.startswith("KULLANICI REDDETTİ") and mac.calls == []
    c.ask = lambda q: "evet"
    res, _ = T.call(c, "shell", {"command": "rm -rf /"})
    assert "REDDEDİLDİ" in res and mac.calls == []
    res, ran = T.call(c, "shell", {"command": "ls ~"})   # güvenli: sormadan çalışır
    assert ran and mac.calls == ["ls ~"]
    assert not T.shell_risk({"command": "ls ~/Downloads/*.pdf | wc -l"})
    for bad in ["ls | sh", "ls; rm x", "ls > a.txt", "cat $(echo x)", "ls | xargs rm"]:
        assert T.shell_risk({"command": bad}), bad


def test_list_dir_counts(db, tmp_path):
    assert T.call(ctx(db), "list_dir", {"path": str(tmp_path / "yok")})[0] == "klasör yok"
    (tmp_path / "bos").mkdir()
    assert "0 öğe" in T.call(ctx(db), "list_dir", {"path": str(tmp_path / "bos")})[0]
    (tmp_path / "bos" / "a.pdf").write_text("x")
    assert T.call(ctx(db), "list_dir", {"path": str(tmp_path / "bos")})[0].startswith("toplam 1 öğe")


def test_loop_is_bounded(db):
    llm = ScriptLLM([("recall", {"query": "x"})] * 50)
    with pytest.raises(BudgetExceeded):
        loop.run("sonsuz", ctx(db), llm, Budget(max_agent_turns=5))
    llm = ScriptLLM([("yok_arac", {})] * 50)           # aynı hata tekrarı da durur
    with pytest.raises(BudgetExceeded, match="düzeltme"):
        loop.run("hata", ctx(db), llm, Budget(max_agent_turns=50, max_auto_fixes=2))


def test_skill_saved_and_hinted(db):
    sk = Skills(db)
    assert sk.save("masaüstündeki pdf dosyalarını listele", [{"tool": "list_dir", "args": {"path": "~/Desktop"}, "ok": True}], "3 pdf")
    assert not sk.save("x", [{"tool": "shell", "args": {}, "ok": False}], "")   # başarısız adım saklanmaz
    assert not sk.save("giriş", [{"tool": "browser", "args": {"text": "şifre 1234"}, "ok": True}], "")  # gizli bilgi
    assert not sk.save("sil", [{"tool": "list_dir", "args": {}, "ok": True},
                               {"tool": "shell", "args": {}, "ok": False, "denied": True}], "")
    h = sk.hint("masaüstündeki pdf dosyalarını göster")
    assert "list_dir" in h and "~/Desktop" in h
    assert sk.hint("hava nasıl") == ""
    sk.save("masaüstündeki pdf dosyalarını listele", [{"tool": "list_dir", "args": {"path": "~/Desktop"}, "ok": True}], "")
    assert sk.similar("masaüstündeki pdf dosyalarını listele")[0]["uses"] == 2


def test_macro_match_and_run(db, tmp_path):
    p = tmp_path / "m.yaml"
    p.write_text(MACROS, encoding="utf-8")
    sk = Skills(db, p)
    m, v = sk.match("Alışveriş notunu süt al yap.")
    assert m["name"] == "hatırla" and v == {"k": "alışveriş", "v": "süt al"}
    assert sk.run_macro(ctx(db), m, v, Budget()) == "alışveriş kaydedildi."
    assert db.recall("alışveriş") == "süt al"
    assert sk.match("başka bir şey")[0] is None
    with pytest.raises(MacroFailed):
        sk.run_macro(ctx(db), sk.match("bozuk makro")[0], {}, Budget())


def test_ask_ai_code_needs_confirm_and_stays_in_project(db):
    zorin = FakeAgent(handler=lambda c: Result(True, "düzeltildi", "", 0))
    asked = []
    c = ctx(db, {"zorin": zorin}, budget=Budget())
    from jarvis.adapters.coder import Coder
    c.coder = Coder({"order": ["gemini"]})
    c.ask = lambda q: asked.append(q) or "evet"
    res, ran = T.call(c, "ask_ai", {"prompt": "oyundaki hatayı düzelt", "workdir": "tarih"})
    assert ran and "gemini" in res and asked
    assert any("/projeler/tarih && gemini -p" in x for x in zorin.calls)
    res, _ = T.call(c, "ask_ai", {"prompt": "x", "workdir": "~/projeler/../.ssh"})
    assert "REDDEDİLDİ" in res


def test_ai_chat_unknown_site_no_browser(tmp_path):
    s = BrowserSession(tmp_path)
    assert "bilinmeyen" in s.do("ai_chat", site="xyz", text="merhaba")
    assert s.pw is None                              # tarayıcı açılmadı


def test_core_agent_and_macro(make, tmp_path):
    llm = ScriptLLM([("remember", {"key": "proje", "value": "tarih"})], final="Not aldım.",
                    intent={"intent": "agent", "args": {"task": "projemin tarih olduğunu not et"}, "machine": "mac"})
    j = make(llm=llm)
    assert j.handle("projemin tarih olduğunu not et") == "Not aldım."
    t = j.tm.list(1)[0]
    assert t["status"] == DONE and "remember" in t["tools"]
    assert j.skills.similar("projemin tarih olduğunu not et")       # beceri kaydedildi
    # makro modelsiz çalışır
    p = tmp_path / "m.yaml"
    p.write_text(MACROS, encoding="utf-8")
    j.skills = Skills(j.db, p)
    calls = llm.calls
    assert j.handle("renk notunu mavi yap") == "renk kaydedildi."
    assert llm.calls == calls and j.db.recall("renk") == "mavi"
    assert "durdu" in j.handle("bozuk makro") and j.tm.list(1)[0]["status"] == FAILED


def test_core_agent_budget_stops(make):
    llm = ScriptLLM([("recall", {"query": "x"})] * 100)
    j = make(llm=llm)
    j.agent_cfg = {"max_turns": 4}
    assert j.handle("bir şeyler yap").startswith("Durdum")
    assert j.tm.list(1)[0]["status"] == FAILED


def test_brains_failover_and_cooldown(monkeypatch):
    from jarvis import brains as B
    from jarvis.llm import LLMError
    calls = []

    def fake(self, body):
        calls.append(self.name)
        if self.name == "a":
            raise LLMError("kota", 429)
        return {"content": "<think>x</think>Merhaba"}

    monkeypatch.setattr(B.OpenAICompat, "_post", fake)
    monkeypatch.setenv("K", "1")
    br = B.Brains([{"name": "a", "base_url": "https://a", "model": "m", "api_key_env": "K"},
                   {"name": "b", "base_url": "https://b", "model": "m", "api_key_env": "YOK"},   # anahtar yok: atlanır
                   {"name": "yerel", "base_url": "http://127.0.0.1:11434/v1", "model": "q"}])
    assert br.chat([{"role": "user", "content": "selam"}]) == "Merhaba" and calls == ["a", "yerel"]
    assert br.chat([]) == "Merhaba" and calls[-1] == "yerel" and calls.count("a") == 1   # a soğumada
    assert [s["wait_s"] > 0 for s in br.status()] == [True, False, False]


def test_two_failures_tell_agent_to_ask(db):
    # 018: takıldığında kafasına göre sürdürmesin; iki başarısız adımdan sonra kodda "kullanıcıya sor" notu
    llm = ScriptLLM([("yok_boyle_arac", {"a": 1}), ("yok_boyle_arac2", {"b": 2})], final="Sordum.")
    loop.run("bir şey yap", ctx(db), llm, Budget())
    last_tool = [m for m in llm.seen[-1] if m["role"] == "tool"]
    assert "SİSTEM" not in last_tool[0]["content"] and "ask_user" in last_tool[1]["content"]
    assert "Kafana göre iş yapma" in loop.SYSTEM and "yaptım deme" in loop.SYSTEM
