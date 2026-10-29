"""Scripted exploit probes against a sequential esolang harness (no model needed).

Each probe plays a cheating agent that has only what the paper's agents have: a shell
in its own cell directory. It builds a faithful copy of the paper's experiment layout
(``benchmark_harness/{harness.py, interpreters/, private/, public/, .experiment_root}``
plus a cell ``experiments/01_main_experiments/<harness>/<model>/<lang>/`` whose
``harness.py`` is a relative symlink, exactly as ``scripts/setup_main_grid.py`` does),
puts the *real* EsoLang tests in ``private/``, and then tries one exploit through the
harness's own CLI. A probe "succeeds" when the harness records a problem as solved, or
leaks something, that an honest agent could not get.

The same probes run against esoforge's hardened harness (``esoforge.harness``) to show
the holes are closed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from .dataset import load_problems
from .upstream import UPSTREAM_DIR

EMPTY_BF = ""                      # prints nothing: fails every E01 test honestly


@dataclass
class ProbeResult:
    name: str
    target: str
    exploited: bool
    summary: str
    evidence: List[str] = field(default_factory=list)


@dataclass
class Layout:
    root: Path
    bench: Path
    cell: Path
    language: str = "brainfuck"

    def run(self, *args: str, env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
        e = {k: v for k, v in os.environ.items() if not k.startswith("HARNESS_")}
        e.update(env or {})
        return subprocess.run([sys.executable, "harness.py", *args], cwd=self.cell, env=e,
                              capture_output=True, text=True, timeout=120)

    def state(self) -> dict:
        return json.loads((self.cell / "harness_state.json").read_text())

    def write_state(self, st: dict) -> None:
        (self.cell / "harness_state.json").write_text(json.dumps(st, indent=2))

    def write(self, name: str, text: str) -> Path:
        p = self.cell / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p


def _problems_json(with_tests: bool) -> dict:
    probs = []
    for p in load_problems().values():
        d = {"id": p.id, "difficulty": p.difficulty, "title": p.title, "description": p.description}
        if with_tests:
            d["test_cases"] = [{"input": i, "output": o} for i, o in p.tests]
        probs.append(d)
    return {"metadata": {"name": "EsoLang-Bench", "total_problems": 80}, "problems": probs}


def official_layout(base: Path, language: str = "brainfuck") -> Layout:
    bench = base / "benchmark_harness"
    (bench / "interpreters").mkdir(parents=True)
    (bench / "private").mkdir()
    (bench / "public").mkdir()
    (bench / ".experiment_root").write_text("")
    shutil.copy(UPSTREAM_DIR / "official_harness.py", bench / "harness.py")
    for f in ("esolang_common.py", "brainfuck_interpreter.py", "befunge98_interpreter.py",
              "whitespace_interpreter.py"):
        shutil.copy(UPSTREAM_DIR / f, bench / "interpreters" / f)
    (bench / "private" / "esolang_full_private.json").write_text(json.dumps(_problems_json(True)))
    (bench / "public" / "esolang_full_public.json").write_text(json.dumps(_problems_json(False)))
    cell = base / "experiments" / "01_main_experiments" / "claude_code" / "opus_4_6" / language
    cell.mkdir(parents=True)
    (cell / "harness.py").symlink_to(os.path.relpath(bench / "harness.py", cell))
    lay = Layout(base, bench, cell, language)
    r = lay.run("init", "--language", {"befunge98": "befunge-98"}.get(language, language))
    if r.returncode != 0:
        raise RuntimeError(f"harness init failed: {r.stdout}{r.stderr}")
    return lay


def _solved(lay: Layout, pid: str) -> bool:
    lay.run("fetch")  # finalizes the current problem the way the harness does
    return lay.state()["problems"][pid]["status"] == "solved"


# ---------------------------------------------------------------------- probes

def probe_read_hidden_tests(lay: Layout) -> ProbeResult:
    lay.run("fetch")
    rel = os.path.relpath(lay.bench / "private" / "esolang_full_private.json", lay.cell)
    try:
        data = json.loads((lay.cell / rel).read_text())
        first = data["problems"][0]["test_cases"][0]
        ok = True
        ev = [f"cat {rel}", f"E01 test 1: {first}"]
    except OSError as e:
        ok, ev = False, [str(e)]
    return ProbeResult("read_hidden_tests", "official", ok,
                       "The hidden tests are a plain file reachable from the agent's cell by a relative path; "
                       "isolation is only an instruction in the prompt.", ev)


def probe_state_forgery(lay: Layout) -> ProbeResult:
    lay.run("fetch")
    st = lay.state()
    st["problems"]["E01"]["best_score"] = 6
    lay.write_state(st)
    ok = _solved(lay, "E01")
    return ProbeResult("state_forgery", "official", ok,
                       "harness_state.json lives in the agent's cell and is trusted: setting best_score=6 "
                       "makes the harness finalize the problem as solved with zero submissions.",
                       ["edit harness_state.json: problems.E01.best_score = 6", "python harness.py fetch",
                        f"E01 status -> {lay.state()['problems']['E01']['status']}"])


def probe_submission_cap_reset(lay: Layout) -> ProbeResult:
    lay.run("fetch")
    prog = lay.write("wrong.bf", EMPTY_BF)
    for _ in range(3):
        lay.run("submit", "E01", prog.name)
    blocked = "Maximum" in lay.run("submit", "E01", prog.name).stdout
    st = lay.state()
    st["problems"]["E01"]["submissions"] = []
    lay.write_state(st)
    r = lay.run("submit", "E01", prog.name)
    ok = blocked and "Score:" in r.stdout
    return ProbeResult("submission_cap_reset", "official", ok,
                       "MAX_SUBMISSIONS is enforced by counting entries in the agent-writable state file; "
                       "clearing the list gives unlimited hidden submissions.",
                       ["3 submissions -> 4th refused" if blocked else "4th not refused",
                        "clear problems.E01.submissions in harness_state.json",
                        "4th submit graded: " + ("yes" if "Score:" in r.stdout else "no")])


def _fake_private(tests_for: Dict[str, List[dict]]) -> dict:
    data = _problems_json(True)
    for p in data["problems"]:
        if p["id"] in tests_for:
            p["test_cases"] = tests_for[p["id"]]
    return data


def probe_sentinel_hijack(lay: Layout) -> ProbeResult:
    lay.run("fetch")
    lay.write(".experiment_root", "")
    shutil.copytree(lay.bench / "interpreters", lay.cell / "interpreters")  # readable, so copyable
    fake = _fake_private({"E01": [{"input": "", "output": ""}] * 6})
    lay.write("private/esolang_full_private.json", json.dumps(fake))
    prog = lay.write("empty.bf", EMPTY_BF)
    r = lay.run("submit", "E01", prog.name)
    ok = "SOLVED" in r.stdout
    return ProbeResult("sentinel_hijack", "official", ok,
                       "The harness searches for its .experiment_root sentinel starting in the agent's cell, so "
                       "an agent can create one plus its own private/ test file; an empty program then 'solves' E01.",
                       ["touch .experiment_root; cp -r <bench>/interpreters .; write private/esolang_full_private.json",
                        "python harness.py submit E01 empty.bf", r.stdout.strip().splitlines()[-1] if r.stdout else ""])


def probe_env_override(lay: Layout) -> ProbeResult:
    lay.run("fetch")
    fake = lay.write("my_tests.json", json.dumps(_fake_private({"E01": [{"input": "", "output": ""}] * 6})))
    prog = lay.write("empty.bf", EMPTY_BF)
    r = lay.run("submit", "E01", prog.name, env={"HARNESS_PRIVATE_FILE": str(fake)})
    ok = "SOLVED" in r.stdout
    return ProbeResult("env_override", "official", ok,
                       "HARNESS_PRIVATE_FILE / HARNESS_INTERPRETER_DIR are read from the agent's own shell "
                       "environment, so the agent chooses which tests (and interpreter) grade it.",
                       ["HARNESS_PRIVATE_FILE=my_tests.json python harness.py submit E01 empty.bf",
                        r.stdout.strip().splitlines()[-1] if r.stdout else ""])


def probe_interpreter_hijack(lay: Layout) -> ProbeResult:
    lay.run("fetch")
    d = lay.cell / "myinterp"
    d.mkdir()
    priv = lay.bench / "private" / "esolang_full_private.json"
    (d / "brainfuck_interpreter.py").write_text(
        "import json\n"
        "class BrainfuckInterpreter:\n"
        "    def __init__(self, max_steps=0): pass\n"
        "    def run(self, code, input_data=''):\n"
        "        pid = json.load(open('harness_state.json'))['current_problem']\n"
        f"        probs = json.load(open({str(priv)!r}))['problems']\n"
        "        tests = next(p['test_cases'] for p in probs if p['id'] == pid)\n"
        "        return next(t['output'] for t in tests if t['input'] == input_data)\n")
    prog = lay.write("empty.bf", EMPTY_BF)
    r = lay.run("submit", "E01", prog.name, env={"HARNESS_INTERPRETER_DIR": str(d)})
    ok = "SOLVED" in r.stdout
    return ProbeResult("interpreter_hijack", "official", ok,
                       "An agent-supplied interpreter directory replaces the grader: it answers every hidden "
                       "test with the expected output.",
                       ["HARNESS_INTERPRETER_DIR=./myinterp python harness.py submit E01 empty.bf",
                        r.stdout.strip().splitlines()[-1] if r.stdout else ""])


def probe_per_test_feedback(lay: Layout) -> ProbeResult:
    lay.run("fetch")
    prog = lay.write("wrong.bf", EMPTY_BF)
    r = lay.run("submit", "E01", prog.name)
    lines = [ln for ln in r.stdout.splitlines() if ln.startswith("Hidden Test")]
    ok = len(lines) == 6
    return ProbeResult("per_test_feedback", "official", ok,
                       "submit prints a verdict per hidden test (the paper's Section 2 and Table 4 say only the "
                       "aggregate count is returned), which tells the agent which tests fail.", lines[:3])


def probe_strip_leniency(lay: Layout) -> ProbeResult:
    """E02's statement says echo 'exactly', and one test is '   spaces   '. A program that
    prints the input with surrounding whitespace removed... cannot be told apart, because
    the harness compares output.strip() with expected.strip(). Shown on E01 with a program
    that prints padded text."""
    lay.run("fetch")
    from .esoc.bfgen import print_text
    prog = lay.write("padded.bf", print_text("\n\n   Hello World!   \n\n"))
    r = lay.run("submit", "E01", prog.name)
    ok = "SOLVED" in r.stdout
    return ProbeResult("strip_leniency", "official", ok,
                       "Outputs are compared after strip(), so leading/trailing whitespace is never checked "
                       "(E02 asks to echo '   spaces   ' exactly; a trimming echo passes).",
                       ["program prints '\\n\\n   Hello World!   \\n\\n'", r.stdout.strip().splitlines()[-1]])


PROBES: Dict[str, Callable[[Layout], ProbeResult]] = {
    "read_hidden_tests": probe_read_hidden_tests,
    "state_forgery": probe_state_forgery,
    "submission_cap_reset": probe_submission_cap_reset,
    "sentinel_hijack": probe_sentinel_hijack,
    "env_override": probe_env_override,
    "interpreter_hijack": probe_interpreter_hijack,
    "per_test_feedback": probe_per_test_feedback,
    "strip_leniency": probe_strip_leniency,
}


def run_official_probes(names: Optional[List[str]] = None) -> List[ProbeResult]:
    out = []
    for name in names or list(PROBES):
        with tempfile.TemporaryDirectory(prefix="esoforge-probe-") as tmp:
            lay = official_layout(Path(tmp))
            out.append(PROBES[name](lay))
    return out


# ------------------------------------------------------------- hardened harness

@dataclass
class HardenedLayout:
    root: Path
    workspace: Path
    server: object
    session: object

    def run(self, *args: str, env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
        e = dict(os.environ)
        e.update(env or {})
        return subprocess.run([sys.executable, "harness.py", *args], cwd=self.workspace, env=e,
                              capture_output=True, text=True, timeout=120)

    def write(self, name: str, text: str) -> Path:
        p = self.workspace / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def solved(self, pid: str) -> bool:
        return self.session.export()["problems"][pid]["status"] == "solved"  # type: ignore[attr-defined]


SECRET_SEED = 987654321


def hardened_layout(base: Path, language: str = "brainfuck") -> HardenedLayout:
    from .harness import GraderServer, HarnessConfig, Session, write_client
    ws = base / "workspace"
    ws.mkdir()
    session = Session(HarnessConfig(language=language, tests="fresh", fresh_seed=SECRET_SEED,
                                    feedback="aggregate", policy="newline"))
    server = GraderServer(session)
    server.start_background()
    write_client(ws, server.address)
    return HardenedLayout(base, ws, server, session)


def _h_read_hidden_tests(lay: HardenedLayout) -> ProbeResult:
    from .freshtests import fresh_suite
    lay.run("fetch")
    secret = {o for _, o in fresh_suite("E04", SECRET_SEED, 30)} - {o for _, o in load_problems()["E04"].tests}
    hits = []
    for p in lay.root.rglob("*"):
        if p.is_file():
            txt = p.read_text(errors="ignore")
            if str(SECRET_SEED) in txt or any(f'"{o}"' in txt for o in list(secret)[:20]):
                hits.append(str(p.relative_to(lay.root)))
    return ProbeResult("read_hidden_tests", "esoforge", bool(hits),
                       "Tests and seed live only in the grader process; no file the agent can reach holds them.",
                       hits or ["no file under the run directory contains the fresh tests or the seed"])


def _h_state_forgery(lay: HardenedLayout) -> ProbeResult:
    lay.run("fetch")
    lay.write("harness_state.json", json.dumps({"problems": {"E01": {"status": "solved", "best_score": 6}}}))
    lay.run("status")
    ok = lay.solved("E01")
    return ProbeResult("state_forgery", "esoforge", ok, "There is no state file in the workspace to edit.",
                       ["wrote a forged harness_state.json", f"grader E01 status: "
                        f"{lay.session.export()['problems']['E01']['status']}"])  # type: ignore[attr-defined]


def _h_submission_cap(lay: HardenedLayout) -> ProbeResult:
    lay.run("fetch")
    prog = lay.write("wrong.bf", EMPTY_BF)
    outs = [lay.run("submit", "E01", prog.name).stdout for _ in range(4)]
    ok = "Score:" in outs[3]
    return ProbeResult("submission_cap_reset", "esoforge", ok, "The cap is counted by the grader.",
                       [outs[3].strip() or "(no output)"])


def _h_sentinel(lay: HardenedLayout) -> ProbeResult:
    lay.run("fetch")
    lay.write(".experiment_root", "")
    lay.write("private/esolang_full_private.json", json.dumps(_fake_private({"E01": [{"input": "", "output": ""}] * 6})))
    prog = lay.write("empty.bf", EMPTY_BF)
    lay.run("submit", "E01", prog.name)
    ok = lay.solved("E01")
    return ProbeResult("sentinel_hijack", "esoforge", ok, "The grader reads no files from the workspace.",
                       ["planted .experiment_root and private/ tests", f"solved: {ok}"])


def _h_env(lay: HardenedLayout) -> ProbeResult:
    lay.run("fetch")
    fake = lay.write("my_tests.json", json.dumps(_fake_private({"E01": [{"input": "", "output": ""}] * 6})))
    prog = lay.write("empty.bf", EMPTY_BF)
    lay.run("submit", "E01", prog.name, env={"HARNESS_PRIVATE_FILE": str(fake),
                                             "HARNESS_INTERPRETER_DIR": str(lay.workspace)})
    ok = lay.solved("E01")
    return ProbeResult("env_override", "esoforge", ok, "The agent's environment variables never reach the grader.",
                       [f"solved: {ok}"])


def _h_interp(lay: HardenedLayout) -> ProbeResult:
    lay.run("fetch")
    lay.write("brainfuck_interpreter.py", "class BrainfuckInterpreter:\n    def __init__(self, max_steps=0): pass\n"
                                          "    def run(self, code, input_data=''): return 'Hello World!'\n")
    prog = lay.write("empty.bf", EMPTY_BF)
    lay.run("submit", "E01", prog.name, env={"PYTHONPATH": str(lay.workspace)})
    ok = lay.solved("E01")
    return ProbeResult("interpreter_hijack", "esoforge", ok, "Interpreters are imported only inside the grader.",
                       [f"solved: {ok}"])


def _h_feedback(lay: HardenedLayout) -> ProbeResult:
    lay.run("fetch")
    prog = lay.write("wrong.bf", EMPTY_BF)
    out = lay.run("submit", "E01", prog.name).stdout
    ok = "Hidden Test" in out
    return ProbeResult("per_test_feedback", "esoforge", ok, "Feedback is the aggregate count unless configured.",
                       [ln for ln in out.splitlines() if ln][:2])


def _h_strip(lay: HardenedLayout) -> ProbeResult:
    lay.run("fetch")
    from .esoc.bfgen import print_text
    prog = lay.write("padded.bf", print_text("\n\n   Hello World!   \n\n"))
    lay.run("submit", "E01", prog.name)
    ok = lay.solved("E01")
    return ProbeResult("strip_leniency", "esoforge", ok,
                       "The 'newline' policy ignores one trailing newline and nothing else.", [f"solved: {ok}"])


def _h_redirect(lay: HardenedLayout) -> ProbeResult:
    """The agent edits its client to talk to a fake grader that always says SOLVED."""
    from .harness import GraderServer
    import socketserver

    class Fake(socketserver.StreamRequestHandler):
        def handle(self) -> None:
            for _ in self.rfile:
                self.wfile.write(b'{"ok": true, "passed": 6, "total": 6, "solved": true, "submissions_left": 2}\n')

    fake = socketserver.ThreadingTCPServer(("127.0.0.1", 0), Fake)
    fake.daemon_threads = True
    import threading
    threading.Thread(target=fake.serve_forever, daemon=True).start()
    lay.run("fetch")
    client = (lay.workspace / "harness.py").read_text()
    lay.write("harness.py", client.replace(lay.server.address, "%s:%d" % fake.server_address))  # type: ignore[attr-defined]
    prog = lay.write("empty.bf", EMPTY_BF)
    shown = lay.run("submit", "E01", prog.name).stdout
    fake.shutdown()
    ok = lay.solved("E01")
    return ProbeResult("client_redirect", "esoforge", ok,
                       "A rewritten client can fool only itself; the score is what the grader recorded.",
                       [f"fake grader printed: {shown.strip().splitlines()[-1] if shown.strip() else ''}",
                        f"real grader solved: {ok}"])


HARDENED_PROBES: Dict[str, Callable[[HardenedLayout], ProbeResult]] = {
    "read_hidden_tests": _h_read_hidden_tests,
    "state_forgery": _h_state_forgery,
    "submission_cap_reset": _h_submission_cap,
    "sentinel_hijack": _h_sentinel,
    "env_override": _h_env,
    "interpreter_hijack": _h_interp,
    "per_test_feedback": _h_feedback,
    "strip_leniency": _h_strip,
    "client_redirect": _h_redirect,
}


def run_hardened_probes(names: Optional[List[str]] = None) -> List[ProbeResult]:
    out = []
    for name in names or list(HARDENED_PROBES):
        with tempfile.TemporaryDirectory(prefix="esoforge-hprobe-") as tmp:
            lay = hardened_layout(Path(tmp))
            try:
                out.append(HARDENED_PROBES[name](lay))
            finally:
                lay.server.shutdown()  # type: ignore[attr-defined]
                lay.server.server_close()  # type: ignore[attr-defined]
    return out
