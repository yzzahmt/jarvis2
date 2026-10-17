"""JARVIS çekirdeği: metin komutu -> niyet -> görev -> sonuç. Ses ve API bunu kullanır."""
import datetime as dt
import json
import re
import threading
from dataclasses import asdict

from . import config
from .adapters.coder import Coder
from .agents.base import build_agents, qpath
from .controller.budget import Budget, BudgetExceeded
from .controller.permissions import Permissions
from .controller.router import Intent, route, route_llm
from .controller.task_manager import CONFIRM, DONE, FAILED, PENDING, RUNNING, TaskManager
from .llm import LLMError, Ollama
from .memory.db import DB
from .text import norm


class TaskError(Exception):
    pass


INSTANT = {"time", "date", "sleep", "wake", "status", "stop", "remember", "recall", "tasks", "chat"}
DEDUPE = {"run_tests", "code"}   # aynı görev kısa sürede tekrar gelirse onay sor
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül",
         "Ekim", "Kasım", "Aralık"]
NAMES = {"mac": "Mac", "cachyos": "CachyOS", "mint": "Linux Mint"}
TEST_CMD = ("set -o pipefail; if [ -f pyproject.toml ] || [ -f pytest.ini ] || [ -d tests ]; then "
            "(python -m pytest -q 2>&1 || python3 -m pytest -q 2>&1) | tail -n 40; "
            "elif [ -f package.json ]; then npm test 2>&1 | tail -n 40; else echo JARVIS_NO_TESTS; exit 3; fi")


class Jarvis:
    def __init__(self, settings=None, machines=None, db_path=None, llm=None, agents=None):
        self.s = settings or config.load("settings")
        self.machines = machines if machines is not None else config.load("machines")
        self.db = DB(db_path or config.path(self.s.get("db_path", "data/jarvis.db")))
        self.tm = TaskManager(self.db, self.s.get("budget", {}).get("dedupe_hours", 24))
        self.perms = Permissions(self.s.get("permissions", {}))
        self.llm = llm or Ollama(self.s.get("llm", {}))
        self.agents = agents if agents is not None else build_agents(self.machines)
        self.coder = Coder(self.s.get("coder", {}))
        self.awake = False
        self.pending: tuple[str, Intent] | None = None
        self.lock = threading.Lock()
        self.recovered = self.tm.recover()

    # ---------------- giriş noktası ----------------
    def handle(self, text: str, say=lambda msg: None) -> str:
        t = norm(text)
        if re.fullmatch(r"(jarvis )?(dur|durdur|iptal|görevi durdur)", t):
            return self.do_stop(None)          # çalışan görevi kilit beklemeden durdur
        with self.lock:
            return self._handle(text, t, say)

    def _handle(self, text, t, say):
        if self.pending:
            tid, intent = self.pending
            if re.match(r"^(evet|onaylıyorum|onayla|tamam|olur|yap)\b", t):
                self.pending = None
                return self._run(tid, intent, say)
            self.pending = None
            self.tm.stop(tid)
            if re.match(r"^(hayır|iptal|vazgeç|yapma)\b", t):
                return "Tamam, iptal ettim."
        intent = route(text, self.machines)
        if intent is None:
            try:
                intent = route_llm(text, self.llm)
            except LLMError:
                return "Bunu anlayamadım ve yerel model yanıt vermedi. Daha kısa söyler misin?"
        if intent.name == "chat":
            intent.args.setdefault("text", text)
        if intent.name in INSTANT:
            return getattr(self, "do_" + intent.name)(intent)
        return self._task(text, intent, say)

    def _task(self, text, intent: Intent, say):
        agent = self.agents.get(intent.machine)
        nm = NAMES.get(intent.machine, intent.machine)
        if agent is None or not agent.configured:
            return f"{nm} için bağlantı ayarı yok. config/machines.yaml dosyasını doldurmalıyız."
        if (busy := self.tm.busy(intent.machine)):
            return f"{nm} bilgisayarında zaten bir görev çalışıyor ({busy}). 'Dur' diyerek durdurabilirsin."
        cats = self.perms.needs_confirm(intent.name, text)
        prev = self.tm.recent_done(text, intent.machine) if intent.name in DEDUPE else None
        task = self.tm.create(text, asdict(intent), intent.machine, plan=intent.name,
                              tools=[intent.name], permissions=cats,
                              status=CONFIRM if (cats or prev) else PENDING)
        if not agent.online():
            self.tm.finish(task["id"], FAILED, error="çevrimdışı")
            return f"{nm} bilgisayarına ulaşamıyorum, çevrimdışı görünüyor. Görevi çalıştırmadım."
        if prev:
            self.pending = (task["id"], intent)
            return f"Bu görev kısa süre önce tamamlandı: {prev['result'][:150]}. Yine de tekrar çalıştırayım mı?"
        if cats:
            self.pending = (task["id"], intent)
            return f"Bu işlem onay gerektiriyor ({', '.join(cats)}). Onaylıyor musun?"
        return self._run(task["id"], intent, say)

    def _run(self, tid, intent: Intent, say):
        b = Budget.from_cfg(self.s.get("budget", {}))
        if intent.source == "yerel-model":   # yerel (ücretsiz) model tokenları; bulut değil
            b.add_tokens(self.llm.last_tokens)
        self.tm.start(tid, model=self.llm.last_model if intent.source == "yerel-model" else "kural")
        try:
            msg = getattr(self, "do_" + intent.name)(intent, tid=tid, budget=b, say=say)
            if self.tm.stopped(tid):
                return "Görev durduruldu."
            self.tm.finish(tid, DONE, msg, budget=b)
            return msg
        except (BudgetExceeded, TaskError) as e:
            self.tm.finish(tid, FAILED, error=str(e), budget=b)
            return f"Durdum: {e}"
        except Exception as e:  # beklenmeyen hata da kaydedilir, tekrar denenmez
            self.tm.finish(tid, FAILED, error=f"{type(e).__name__}: {e}", budget=b)
            return f"Beklenmeyen bir hata oldu: {e}"

    # ---------------- anlık komutlar (görev kaydı yok) ----------------
    def do_time(self, i):
        return f"Saat {dt.datetime.now():%H:%M}."

    def do_date(self, i):
        d = dt.date.today()
        return f"Bugün {d.day} {AYLAR[d.month - 1]} {d.year}, {GUNLER[d.weekday()]}."

    def do_sleep(self, i):
        self.awake = False
        return "Uyku moduna geçiyorum."

    def do_wake(self, i):
        self.awake = True
        extra = ""
        if self.recovered:
            extra = f" Not: son kapanışta {len(self.recovered)} görev yarım kaldı, durduruldu olarak işaretledim."
            self.recovered = []
        return "Dinliyorum, ne yapmamı istersin?" + extra

    def do_status(self, i):
        parts = ["yerel model " + ("hazır" if self.llm.up() else "kapalı")]
        for n, a in self.agents.items():
            st = "ayarlanmadı" if not a.configured else ("çevrimiçi" if a.online() else "çevrimdışı")
            parts.append(f"{NAMES.get(n, n)} {st}")
        out = ", ".join(parts)
        return out[0].upper() + out[1:] + "."

    def do_stop(self, i):
        running = self.tm.list(50, RUNNING) + self.tm.list(50, CONFIRM)
        self.pending = None
        n = sum(self.tm.stop(t["id"]) for t in running)
        return "Görevi durdurdum." if n else "Çalışan bir görev yok."

    def do_remember(self, i):
        try:
            self.db.remember(i.args["key"], i.args["value"], kind="user")
        except ValueError as e:
            return str(e) + "."
        return "Tamam, hatırlayacağım."

    def do_recall(self, i):
        v = self.db.recall(i.args["key"])
        return f"{i.args['key']}: {v}." if v is not None else "Bununla ilgili bir kaydım yok."

    def do_tasks(self, i):
        ts = self.tm.list(3)
        if not ts:
            return "Henüz görev yok."
        return " ".join(f"{t['request'][:40]} — {t['status']}." for t in ts)

    def do_chat(self, i):
        if i.args.get("reply"):
            return i.args["reply"]
        try:
            return self.llm.chat([{"role": "system", "content": "Sen JARVIS'sin. Türkçe, en fazla iki kısa cümleyle yanıt ver."},
                                  {"role": "user", "content": i.args.get("text", "")}], max_tokens=120)
        except LLMError:
            return "Yerel model şu an yanıt vermiyor."

    # ---------------- görevler ----------------
    def _agent(self, i):
        return self.agents[i.machine]

    def _sh(self, i, cmd, tid, budget, timeout=60):
        budget.turn()
        r = self._agent(i).run(cmd, timeout=min(timeout, budget.max_task_seconds), stop=self.tm.stop_flags.get(tid))
        return r

    def do_open_app(self, i, tid, budget, say):
        app = self.perms.app(i.args.get("app", ""))
        if not app:
            raise TaskError(f"'{i.args.get('app')}' izin verilen uygulamalar listesinde değil")
        a = self._agent(i)
        cmd = (f"open -a {qpath(app)}" if a.os == "darwin"
               else f"DISPLAY=${{DISPLAY:-:0}} setsid -f {qpath(app.lower().replace(' ', '-'))} >/dev/null 2>&1")
        r = self._sh(i, cmd, tid, budget, 20)
        if not r.ok:
            raise TaskError(f"{app} açılamadı: {r.err.strip()[:200]}")
        return f"{app} açıldı."

    def _browser(self, i, args, tid, budget, timeout=90):
        a = self._agent(i)
        r = self._sh(i, f"{qpath(a.python)} {qpath(a.browser)} " + " ".join(qpath(x) for x in args),
                     tid, budget, timeout)
        try:
            d = json.loads(r.out.strip().splitlines()[-1])
        except (ValueError, IndexError):
            raise TaskError("Tarayıcı aracı yanıt vermedi: " + (r.err or r.out).strip()[-200:])
        if not d.get("ok"):
            raise TaskError("Tarayıcı hatası: " + str(d.get("error", "sonuç yok"))[:200])
        return d

    def do_open_url(self, i, tid, budget, say):
        self._browser(i, ["open", i.args["url"]], tid, budget, 20)
        return "Sayfayı açtım."

    def do_youtube(self, i, tid, budget, say):
        q = i.args.get("query", "").strip()
        if not q:
            self._browser(i, ["open", "https://www.youtube.com"], tid, budget, 20)
            return "YouTube'u açtım."
        say(f"{NAMES.get(i.machine)} bilgisayarında aramayı başlatıyorum.")
        d = self._browser(i, ["youtube", q], tid, budget)
        res = d["results"]
        self.db.remember("son_youtube", {"machine": i.machine, "results": res}, kind="state")
        top = " ".join(f"{n}: {r['title'][:60]}." for n, r in enumerate(res[:3], 1))
        return f"{len(res)} sonuç buldum. {top} Hangisini açayım?"

    def do_pick_result(self, i, tid, budget, say):
        last = self.db.recall("son_youtube") or {}
        res = last.get("results", [])
        k = i.args.get("index", 1)
        if not 1 <= k <= len(res):
            raise TaskError("Seçilecek bir arama sonucu yok")
        i.machine = last.get("machine", i.machine)
        self._browser(i, ["open", res[k - 1]["url"]], tid, budget, 20)
        return f"Açıyorum: {res[k - 1]['title'][:80]}."

    def _project_dir(self, i):
        base = (self.machines.get(i.machine) or {}).get("project_dir", "~/projeler")
        name = i.args.get("project") or self.db.recall(f"proje:{i.machine}")
        if not name:
            raise TaskError("Hangi proje? Örnek: 'tarih projesinin testlerini çalıştır'")
        name = self.db.recall(f"proje:{name}") or name
        if "/" in name and not name.startswith(base.rstrip("/") + "/"):
            raise TaskError("Proje izin verilen klasörün dışında")
        if ".." in name:
            raise TaskError("Geçersiz proje yolu")
        return name if "/" in name else f"{base.rstrip('/')}/{name}"

    def _tests(self, i, d, tid, budget):
        r = self._sh(i, f"cd {qpath(d)} && {TEST_CMD}", tid, budget, 600)
        if "JARVIS_NO_TESTS" in r.out:
            raise TaskError("Bu projede test bulamadım")
        if r.code == 1 and "No such file" in r.err + r.out:
            raise TaskError(f"Klasör bulunamadı: {d}")
        return r

    @staticmethod
    def _summary(out: str) -> str:
        m = re.findall(r"=+ (.+?) in [\d.]+s", out)
        return m[-1] if m else out.strip().splitlines()[-1][:120] if out.strip() else "çıktı yok"

    def do_run_tests(self, i, tid, budget, say):
        d = self._project_dir(i)
        say("Projeyi kontrol ediyorum. Testleri çalıştırıp sonucu bildireceğim.")
        r = self._tests(i, d, tid, budget)
        self.db.remember(f"proje:{i.machine}", i.args.get("project") or d, kind="project")
        return ("Testler başarılı: " if r.ok else "Testlerde hata var: ") + self._summary(r.out) + "."

    def do_code(self, i, tid, budget, say):
        d = self._project_dir(i) if (i.args.get("project") or self.db.recall(f"proje:{i.machine}")) \
            else (self.machines.get(i.machine) or {}).get("project_dir", "~/projeler")
        say("Kodlama ajanını başlatıyorum.")
        tool, r = self.coder.run(self._agent(i), d, i.args["task"], "", budget, self.tm.stop_flags.get(tid))
        if tool is None:
            raise TaskError("Hedef makinede kodlama ajanı (gemini veya aider) kurulu değil")
        self.tm.update(tid, model=tool)
        if not r.ok:
            raise TaskError(f"{tool} başarısız: {(r.err or r.out).strip()[-200:]}")
        try:
            t = self._tests(i, d, tid, budget)
        except TaskError:
            return f"{tool} görevi bitirdi. Test bulunmadığı için doğrulayamadım."
        while not t.ok:                      # aynı hata için en fazla max_auto_fixes deneme
            budget.fix_attempt(t.out)
            say("Testler başarısız, bir düzeltme deniyorum.")
            tool, r = self.coder.run(self._agent(i), d, "Başarısız testleri düzelt.", budget.clip(t.out[-3000:]),
                                     budget, self.tm.stop_flags.get(tid))
            t = self._tests(i, d, tid, budget)
        return f"{tool} görevi bitirdi, testler geçti: {self._summary(t.out)}."
