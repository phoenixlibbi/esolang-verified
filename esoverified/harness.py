"""A hardened sequential harness: the paper's protocol, enforced instead of requested.

Architecture: a grader **server** owns the tests, the session state and every limit;
the agent only gets a **client** (``harness.py`` in its workspace) that sends
``fetch / run / submit / status / skip`` requests. Nothing the grader trusts lives in
the workspace, and the client reads no configuration that can change what is graded.
In the Docker/Harbor packaging the server runs as root and the agent as an
unprivileged user, so the tests and state files are not even readable.

Protocol (same as the paper unless configured): fixed forward order, a problem is
finalized when one submission passes every test or the submission cap is reached,
finalized problems are never revisited, unlimited local runs.

Knobs (``HarnessConfig``): test source (official 6 or a seeded fresh suite),
submission cap, local-run budget, feedback granularity (``aggregate`` | ``per_test``),
output comparison policy, interpreter dialect and step cap, problem subset.
"""

from __future__ import annotations

import json
import socket
import socketserver
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import EXTENSIONS, canonical_language
from .dataset import get_problem, problem_ids
from .freshtests import fresh_suite
from .grading import grade_program
from .interp import run as interp_run
from .interp.common import DEFAULT_MAX_STEPS

Test = Tuple[str, str]


@dataclass
class HarnessConfig:
    language: str = "brainfuck"
    problems: List[str] = field(default_factory=list)       # empty = all 80 in benchmark order
    tests: str = "official"                                  # official | fresh | impossible
    fresh_seed: int = 0
    fresh_random: int = 30
    max_submissions: int = 3
    run_budget: Optional[int] = None                         # local runs per problem; None = unlimited
    feedback: str = "aggregate"                              # aggregate | per_test
    policy: str = "official"                                 # official | exact | newline
    dialect: str = "official"
    max_steps: int = DEFAULT_MAX_STEPS
    max_program_bytes: int = 2_000_000

    def __post_init__(self) -> None:
        self.language = canonical_language(self.language)
        self.problems = [p.upper() for p in self.problems] or problem_ids()
        if self.feedback not in ("aggregate", "per_test"):
            raise ValueError("feedback must be 'aggregate' or 'per_test'")
        if self.tests not in ("official", "fresh", "impossible"):
            raise ValueError("tests must be 'official', 'fresh' or 'impossible'")
        if self.max_submissions < 1:
            raise ValueError("max_submissions must be >= 1")


@dataclass
class ProblemState:
    status: str = "pending"          # pending, active, solved, failed, skipped
    submissions: List[Dict[str, object]] = field(default_factory=list)
    runs: int = 0
    best: int = 0
    fetched_at: Optional[float] = None
    finished_at: Optional[float] = None


class Session:
    """All grading logic. Thread-safe; owned by the server process."""

    def __init__(self, config: HarnessConfig, log_path: Optional[Path] = None) -> None:
        self.config = config
        self.state: Dict[str, ProblemState] = {pid: ProblemState() for pid in config.problems}
        self.index = 0
        self.current: Optional[str] = None
        self.events: List[Dict[str, object]] = []
        self.log_path = log_path
        self._lock = threading.Lock()
        self._tests: Dict[str, List[Test]] = {}

    # -------------------------------------------------------------- internals
    def tests_for(self, pid: str) -> List[Test]:
        if pid not in self._tests:
            c = self.config
            if c.tests == "official":
                t = list(get_problem(pid).tests)
            elif c.tests == "fresh":
                t = fresh_suite(pid, c.fresh_seed, c.fresh_random)
            else:
                from .impossible import impossible_tests
                t = impossible_tests(pid, c.fresh_seed)
            self._tests[pid] = t
        return self._tests[pid]

    def _log(self, event: str, **data: object) -> None:
        rec = {"t": time.time(), "event": event, **data}
        self.events.append(rec)
        if self.log_path:
            with self.log_path.open("a") as f:
                f.write(json.dumps(rec) + "\n")

    def _finalize_current(self) -> None:
        if self.current is None:
            return
        st = self.state[self.current]
        if st.status == "active":
            st.status = "failed" if st.submissions else "skipped"
            st.finished_at = time.time()
            self._log("finalize", pid=self.current, status=st.status)

    # -------------------------------------------------------------- commands
    def fetch(self) -> Dict[str, object]:
        with self._lock:
            if self.current is not None and self.state[self.current].status == "active":
                st = self.state[self.current]
                if len(st.submissions) < self.config.max_submissions:
                    return {"ok": False, "error": f"{self.current} is still active with "
                            f"{self.config.max_submissions - len(st.submissions)} submissions left; "
                            "use skip to give up on it"}
            self._finalize_current()
            if self.index >= len(self.config.problems):
                self.current = None
                return {"ok": True, "done": True, "message": "All problems have been completed."}
            pid = self.config.problems[self.index]
            self.index += 1
            self.current = pid
            st = self.state[pid]
            st.status, st.fetched_at = "active", time.time()
            p = get_problem(pid)
            self._log("fetch", pid=pid)
            return {"ok": True, "done": False, "id": pid, "title": p.title, "difficulty": p.difficulty,
                    "description": p.description, "max_submissions": self.config.max_submissions,
                    "run_budget": self.config.run_budget}

    def run(self, code: str, input_data: str = "") -> Dict[str, object]:
        with self._lock:
            if len(code.encode()) > self.config.max_program_bytes:
                return {"ok": False, "error": "program too large"}
            if self.current is not None and self.config.run_budget is not None:
                st = self.state[self.current]
                if st.runs >= self.config.run_budget:
                    return {"ok": False, "error": f"local run budget ({self.config.run_budget}) used up"}
                st.runs += 1
            self._log("run", pid=self.current, bytes=len(code))
        r = interp_run(self.config.language, code, input_data, dialect=self.config.dialect,
                       max_steps=self.config.max_steps)
        return {"ok": True, "output": r.output, "error": r.error}

    def submit(self, pid: str, code: str) -> Dict[str, object]:
        pid = pid.upper()
        with self._lock:
            if pid != self.current or self.state[pid].status != "active":
                return {"ok": False, "error": f"{pid} is not the active problem"}
            st = self.state[pid]
            if len(st.submissions) >= self.config.max_submissions:
                return {"ok": False, "error": "no submissions left"}
            if len(code.encode()) > self.config.max_program_bytes:
                return {"ok": False, "error": "program too large"}
            g = grade_program(self.config.language, code, self.tests_for(pid), policy=self.config.policy,
                              dialect=self.config.dialect, max_steps=self.config.max_steps)
            st.submissions.append({"passed": g.passed, "total": g.total, "bytes": len(code), "t": time.time(),
                                   "statuses": [r.status for r in g.results]})
            st.best = max(st.best, g.passed)
            if g.solved:
                st.status, st.finished_at = "solved", time.time()
            elif len(st.submissions) >= self.config.max_submissions:
                st.status, st.finished_at = "failed", time.time()
            self._log("submit", pid=pid, passed=g.passed, total=g.total, attempt=len(st.submissions))
            reply: Dict[str, object] = {"ok": True, "passed": g.passed, "total": g.total, "solved": g.solved,
                                        "submissions_left": self.config.max_submissions - len(st.submissions)}
            if self.config.feedback == "per_test":
                reply["per_test"] = [r.status for r in g.results]
            return reply

    def skip(self) -> Dict[str, object]:
        with self._lock:
            if self.current is None or self.state[self.current].status != "active":
                return {"ok": False, "error": "no active problem"}
            st = self.state[self.current]
            st.status, st.finished_at = "skipped", time.time()
            self._log("skip", pid=self.current)
            return {"ok": True, "skipped": self.current}

    def status(self) -> Dict[str, object]:
        with self._lock:
            counts: Dict[str, int] = {}
            for st in self.state.values():
                counts[st.status] = counts.get(st.status, 0) + 1
            return {"ok": True, "language": self.config.language, "current": self.current,
                    "solved": counts.get("solved", 0), "total": len(self.state), "counts": counts}

    def export(self) -> Dict[str, object]:
        with self._lock:
            cfg = asdict(self.config)
            return {"config": cfg, "solved": sum(s.status == "solved" for s in self.state.values()),
                    "total": len(self.state),
                    "problems": {pid: asdict(st) for pid, st in self.state.items()}, "events": self.events}

    def handle(self, req: Dict[str, object]) -> Dict[str, object]:
        cmd = req.get("cmd")
        try:
            if cmd == "fetch":
                return self.fetch()
            if cmd == "run":
                return self.run(str(req.get("code", "")), str(req.get("input", "")))
            if cmd == "submit":
                return self.submit(str(req.get("id", "")), str(req.get("code", "")))
            if cmd == "skip":
                return self.skip()
            if cmd == "status":
                return self.status()
        except Exception as e:  # never let a malformed request crash the grader
            return {"ok": False, "error": f"{type(e).__name__}: {e}"}
        return {"ok": False, "error": f"unknown command {cmd!r}"}


# ------------------------------------------------------------------ transport

class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:  # one JSON request per line
        for line in self.rfile:
            try:
                req = json.loads(line)
                resp = self.server.session.handle(req)  # type: ignore[attr-defined]
            except json.JSONDecodeError:
                resp = {"ok": False, "error": "bad json"}
            self.wfile.write((json.dumps(resp) + "\n").encode())


class GraderServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, session: Session, host: str = "127.0.0.1", port: int = 0) -> None:
        super().__init__((host, port), _Handler)
        self.session = session

    @property
    def address(self) -> str:
        h, p = self.server_address[:2]
        return f"{h}:{p}"

    def start_background(self) -> threading.Thread:
        t = threading.Thread(target=self.serve_forever, daemon=True)
        t.start()
        return t


def request(address: str, payload: Dict[str, object], timeout: float = 600.0) -> Dict[str, object]:
    host, port = address.rsplit(":", 1)
    with socket.create_connection((host, int(port)), timeout=timeout) as s:
        f = s.makefile("rwb")
        f.write((json.dumps(payload) + "\n").encode())
        f.flush()
        return json.loads(f.readline())


# ------------------------------------------------------------------ agent client

CLIENT_TEMPLATE = '''#!/usr/bin/env python3
"""Agent-side client for the esoverified grader. Usage:
  python harness.py fetch | status | skip
  python harness.py run <file> --input "..."
  python harness.py submit <PROBLEM_ID> <file>
Grading happens in a separate grader process; nothing here affects the score.
"""
import json, socket, sys

ADDRESS = "{address}"


def call(payload):
    host, port = ADDRESS.rsplit(":", 1)
    with socket.create_connection((host, int(port)), timeout=600) as s:
        f = s.makefile("rwb")
        f.write((json.dumps(payload) + "\\n").encode()); f.flush()
        return json.loads(f.readline())


def main(argv):
    if not argv:
        print(__doc__); return 2
    cmd = argv[0]
    if cmd in ("fetch", "status", "skip"):
        r = call({{"cmd": cmd}})
    elif cmd == "run" and len(argv) >= 2:
        inp = argv[argv.index("--input") + 1] if "--input" in argv else ""
        r = call({{"cmd": "run", "code": open(argv[1]).read(), "input": inp}})
    elif cmd == "submit" and len(argv) >= 3:
        r = call({{"cmd": "submit", "id": argv[1], "code": open(argv[2]).read()}})
    else:
        print(__doc__); return 2
    if not r.get("ok"):
        print("ERROR: " + str(r.get("error"))); return 1
    if cmd == "fetch":
        if r.get("done"):
            print(r["message"]); return 0
        print("=" * 60); print("Problem %s: %s" % (r["id"], r["title"])); print("Difficulty: " + r["difficulty"])
        print("=" * 60); print(); print(r["description"]); print()
        print("Max hidden submissions: %d" % r["max_submissions"])
    elif cmd == "run":
        print("RUNTIME ERROR: " + r["error"] if r.get("error") else "OUTPUT: " + repr(r["output"]))
    elif cmd == "submit":
        for i, s in enumerate(r.get("per_test", []), 1):
            print("Hidden Test %d: %s" % (i, s))
        print("Score: %d/%d" % (r["passed"], r["total"]))
        print("SOLVED!" if r["solved"] else "Submissions remaining: %d" % r["submissions_left"])
    else:
        print(json.dumps(r, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''


def write_client(workspace: Path, address: str) -> Path:
    p = workspace / "harness.py"
    p.write_text(CLIENT_TEMPLATE.format(address=address))
    return p


def language_card(language: str) -> str:
    from .cards import card_for
    return card_for(canonical_language(language))


def extension(language: str) -> str:
    return EXTENSIONS[canonical_language(language)]
