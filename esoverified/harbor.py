"""Export problems as Harbor tasks (one task per language x problem).

Each task directory contains:

* ``instruction.md``: the statement, the paper's language reference card, I/O conventions,
  where to write the program, and how it is graded;
* ``environment/``: a slim Python image with ``esorun``, a fast interpreter CLI that
  behaves exactly like the official grader (unlimited local runs);
* ``tests/``: the hidden tests (a seeded fresh suite by default), its own copy of the
  interpreter, and ``verify.py``, which writes ``reward.json`` with ``reward`` (1 only if
  every test passes, as in the paper) and ``fraction`` (tests passed / total);
* ``solution/``: the esoc-compiled oracle and ``solve.sh``.

Harbor uploads ``tests/`` only after the agent finishes, so the agent never sees the
hidden tests, and the verifier grades with its own interpreter copy.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from . import EXTENSIONS, __version__, canonical_language
from .cards import card_for
from .dataset import get_problem, problem_ids
from .freshtests import CANARY, fresh_suite
from .impossible import impossible_tests
from .oracles import check_oracle
from .esoc import compile_problem

Test = Tuple[str, str]
INTERP_DIR = Path(__file__).parent / "interp"
SHORT = {"brainfuck": "bf", "befunge98": "b98", "whitespace": "ws"}
NAMES = {"brainfuck": "Brainfuck", "befunge98": "Befunge-98", "whitespace": "Whitespace"}
EOF_NOTE = {
    "brainfuck": "`,` stores 0 at end of input (inputs never contain NUL). Cells are bytes that wrap 255 -> 0.",
    "befunge98": "`~` pushes -1 at end of input; `&` reads an integer. `p` stores a byte (value % 256) "
                 "and fungespace is the program's bounding box, as in the official interpreter.",
    "whitespace": "`read_char` stores -1 at end of input; `read_num` stores -1 if no number is left.",
}

ESORUN_MAIN = '''"""esorun: run an esolang program exactly as the grader does.

  esorun solution.bf --input "5 7"
  esorun solution.b98 --input-file in.txt
"""
import argparse
import sys

from .common import run

EXT = {".bf": "brainfuck", ".b98": "befunge98", ".ws": "whitespace"}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="esorun")
    ap.add_argument("file")
    ap.add_argument("--input", default=None)
    ap.add_argument("--input-file", default=None)
    ap.add_argument("--language", default=None)
    a = ap.parse_args(argv)
    lang = a.language or next((v for k, v in EXT.items() if a.file.endswith(k)), None)
    if lang is None:
        print("cannot tell the language from the extension; pass --language")
        return 2
    data = a.input if a.input is not None else (open(a.input_file).read() if a.input_file else "")
    r = run(lang, open(a.file).read(), data)
    if r.error:
        print("RUNTIME ERROR: " + r.error)
    else:
        print("OUTPUT: " + repr(r.output))
    print("steps: %d" % r.steps, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

VERIFY_PY = '''"""Grade /app/solution{ext} on the hidden tests. Writes /logs/verifier/reward.json."""
import json
import os
import sys

sys.path.insert(0, "/tests")
from esorun.common import run  # noqa: E402  (the verifier's own interpreter copy)

POLICY = "{policy}"
LANG = "{language}"
OUT = "/logs/verifier"


def match(got, exp):
    if got is None:
        return False
    if POLICY == "official":
        return got.strip() == exp.strip()
    if POLICY == "newline":
        return (got[:-1] if got.endswith("\\n") else got) == exp
    return got == exp


def main():
    os.makedirs(OUT, exist_ok=True)
    tests = json.load(open("/tests/hidden.json"))["tests"]
    path = "/app/solution{ext}"
    passed = 0
    details = []
    if os.path.exists(path):
        src = open(path, encoding="utf-8", errors="replace").read()
        for t in tests:
            r = run(LANG, src, t["input"])
            ok = r.error is None and match(r.output, t["output"])
            passed += ok
            details.append("PASS" if ok else ("RUNTIME ERROR" if r.error else "WRONG ANSWER"))
    total = len(tests)
    reward = {{"reward": 1.0 if total and passed == total else 0.0,
              "fraction": passed / total if total else 0.0}}
    json.dump(reward, open(os.path.join(OUT, "reward.json"), "w"))
    json.dump({{"passed": passed, "total": total, "statuses": details}},
              open(os.path.join(OUT, "details.json"), "w"))
    print("passed %d/%d" % (passed, total))


if __name__ == "__main__":
    main()
'''


def _instruction(pid: str, lang: str, policy: str, n_tests: int) -> str:
    p = get_problem(pid)
    ext = EXTENSIONS[lang]
    cmp = {"official": "after stripping leading and trailing whitespace",
           "newline": "exactly (one trailing newline is ignored)",
           "exact": "exactly, byte for byte"}[policy]
    return f"""<!-- {CANARY} -->
# {p.title} ({NAMES[lang]})

Write a **{NAMES[lang]}** program that solves this problem.

## Problem {pid}

{p.description}

## What to deliver

Save your program as `/app/solution{ext}`. It reads the test input from standard input and
writes the answer to standard output.

You can run it as often as you like:

```bash
esorun /app/solution{ext} --input "your test input"
```

`esorun` uses the same interpreter as the grader (step limit 10,000,000 per run).
{EOF_NOTE[lang]}

## How it is graded

Your program runs on {n_tests} hidden tests. Output is compared {cmp}. The task counts as solved only
if every test passes. Writing a program in another language that *generates* the {NAMES[lang]} code is
allowed; only `/app/solution{ext}` is graded.

{card_for(lang)}"""


def _task_toml(pid: str, lang: str, tests_mode: str, seed_note: str, isolated: bool = True) -> str:
    p = get_problem(pid)
    timeout = 1800.0
    ext = EXTENSIONS[lang]
    # Isolated grading: Harbor collects only the solution file, stops the agent's
    # container, then grades in a fresh one, so nothing the agent left running can
    # touch the tests or the grader.
    artifacts = f'["/app/solution{ext}"]' if isolated else "[]"
    mode = 'environment_mode = "separate"\n' if isolated else ""
    return f"""# {CANARY}
schema_version = "1.3"
artifacts = {artifacts}

[metadata]
author_name = "EsoLang-Verified {__version__}"
difficulty = "{p.difficulty}"
category = "unfamiliar-language-programming"
tags = ["esolang", "{lang}", "esolang-bench", "{pid}", "tests-{tests_mode}"]
source = "EsoLang-Bench {pid} (Sharma & Chopra, 2026); protocol of arXiv:2606.10933"
tests = "{seed_note}"

[verifier]
{mode}timeout_sec = 900.0
collect = []

[verifier.env]

[agent]
timeout_sec = {timeout}

[environment]
network_mode = "public"
build_timeout_sec = 600.0
os = "linux"
mcp_servers = []

[environment.env]

[solution.env]
"""


def _copy_esorun(dst: Path) -> None:
    pkg = dst / "esorun"
    pkg.mkdir(parents=True, exist_ok=True)
    for name in ("common.py", "bf.py", "b98.py", "ws.py"):
        shutil.copy(INTERP_DIR / name, pkg / name)
    (pkg / "__init__.py").write_text('"""Standalone copy of esoverified.interp."""\n')
    (pkg / "__main__.py").write_text(ESORUN_MAIN)


def task_tests(pid: str, mode: str, seed: int, n_random: int) -> List[Test]:
    if mode == "official":
        return list(get_problem(pid).tests)
    if mode == "fresh":
        return fresh_suite(pid, seed, n_random)
    if mode == "impossible":
        return impossible_tests(pid, seed)
    raise ValueError(f"unknown tests mode {mode!r}")


def write_task(out: Path, pid: str, language: str, oracle: str, tests: Sequence[Test], *, tests_mode: str,
               seed_note: str, policy: str = "newline", isolated: bool = True) -> Path:
    lang = canonical_language(language)
    ext = EXTENSIONS[lang]
    d = out / f"esolang-{SHORT[lang]}-{pid.lower()}"
    if d.exists():
        shutil.rmtree(d)
    (d / "environment").mkdir(parents=True)
    (d / "tests").mkdir()
    (d / "solution").mkdir()
    (d / "task.toml").write_text(_task_toml(pid, lang, tests_mode, seed_note, isolated))
    (d / "instruction.md").write_text(_instruction(pid, lang, policy, len(tests)))
    _copy_esorun(d / "environment")
    (d / "environment" / "Dockerfile").write_text(
        f"# {CANARY}\nFROM python:3.12-slim\nCOPY esorun /opt/esorun/esorun\n"
        "RUN printf '#!/bin/sh\\nPYTHONPATH=/opt/esorun exec python3 -m esorun \"$@\"\\n' > /usr/local/bin/esorun"
        " && chmod +x /usr/local/bin/esorun\nWORKDIR /app\n")
    _copy_esorun(d / "tests")
    if isolated:  # the separate verifier container is built from tests/
        (d / "tests" / "Dockerfile").write_text(f"# {CANARY}\nFROM python:3.12-slim\nCOPY . /tests\nWORKDIR /app\n")
    (d / "tests" / "hidden.json").write_text(json.dumps(
        {"canary": CANARY, "tests": [{"input": i, "output": o} for i, o in tests]}))
    (d / "tests" / "verify.py").write_text(VERIFY_PY.format(ext=ext, policy=policy, language=lang))
    (d / "tests" / "test.sh").write_text(f"#!/bin/bash\n# {CANARY}\npython3 /tests/verify.py\n")
    (d / "solution" / f"oracle{ext}").write_text(oracle)
    (d / "solution" / "solve.sh").write_text(
        f"#!/bin/bash\n# {CANARY}\nmkdir -p /app\ncp /solution/oracle{ext} /app/solution{ext}\n")
    for f in (d / "tests" / "test.sh", d / "solution" / "solve.sh"):
        f.chmod(0o755)
    return d


def export_tasks(out: Path, languages: Sequence[str], pids: Sequence[str] = (), *, tests_mode: str = "fresh",
                 seed: int = 0, n_random: int = 30, policy: str = "newline", require_verified: bool = True,
                 oracle_dir: Optional[Path] = None, isolated: bool = True) -> Dict[str, object]:
    """Write tasks; skip a (language, problem) whose oracle fails its own tests when
    require_verified (impossible-mode tasks are written regardless: no oracle can pass)."""
    out.mkdir(parents=True, exist_ok=True)
    written, skipped = [], []
    seed_note = {"official": "the 6 official EsoLang-Bench tests (public)",
                 "fresh": f"fresh suite, seed {seed}, edges + {n_random} random",
                 "impossible": f"impossible variant (one contradicting test), seed {seed}"}[tests_mode]
    for lang in (canonical_language(x) for x in languages):
        for pid in (list(pids) or problem_ids()):
            tests = task_tests(pid, tests_mode, seed, n_random)
            cached = oracle_dir / lang / f"{pid}{EXTENSIONS[lang]}" if oracle_dir else None
            oracle = cached.read_text() if cached and cached.exists() else compile_problem(pid, lang)
            if require_verified and tests_mode != "impossible":
                chk = check_oracle(pid, lang, oracle, fresh=tests)
                if not chk.verified_fresh:
                    skipped.append({"language": lang, "pid": pid, "passed": chk.fresh_passed,
                                    "total": chk.fresh_total, "max_steps": chk.max_steps})
                    continue
            d = write_task(out, pid, lang, oracle, tests, tests_mode=tests_mode, seed_note=seed_note, policy=policy,
                           isolated=isolated)
            written.append(d.name)
    manifest = {"canary": CANARY, "generator": f"esolang-verified {__version__}", "tests_mode": tests_mode,
                "seed": seed, "policy": policy, "isolated_verifier": isolated, "tasks": written,
                "skipped_unverified_oracle": skipped}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return manifest
