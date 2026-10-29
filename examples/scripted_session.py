"""A scripted, model-free agent session against the hardened grader.

It plays the paper's protocol end to end: fetch a problem, run the program locally,
submit it. The "agent" submits esoc's compiled oracle, except on one problem where it
first submits a wrong program, so the session shows both outcomes.

    python examples/scripted_session.py --language befunge98 --problems E01 E04 E19
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from esoverified import EXTENSIONS, canonical_language
from esoverified.esoc import compile_problem
from esoverified.harness import GraderServer, HarnessConfig, Session, write_client


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--language", default="befunge98")
    ap.add_argument("--problems", nargs="*", default=["E01", "E04", "E19"])
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()
    lang = canonical_language(a.language)
    session = Session(HarnessConfig(language=lang, problems=a.problems, tests="fresh", fresh_seed=a.seed,
                                    policy="newline"))
    server = GraderServer(session)
    server.start_background()
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp)
        write_client(ws, server.address)

        def harness(*args: str) -> str:
            return subprocess.run([sys.executable, "harness.py", *args], cwd=ws, capture_output=True,
                                  text=True).stdout.strip()

        for i, pid in enumerate(a.problems):
            print(harness("fetch").splitlines()[1])
            prog = ws / f"{pid}{EXTENSIONS[lang]}"
            if i == 0:  # first try a wrong program on the first problem
                prog.write_text({"brainfuck": "", "befunge98": "@", "whitespace": "\n\n\n"}[lang])
                print("  wrong attempt ->", harness("submit", pid, prog.name).replace("\n", " | "))
            prog.write_text(compile_problem(pid, lang))
            print("  local run       ->", harness("run", prog.name, "--input", "3 4")[:60])
            print("  oracle submit   ->", harness("submit", pid, prog.name).replace("\n", " | "))
    server.shutdown()
    exp = session.export()
    print(json.dumps({"solved": exp["solved"], "total": exp["total"],
                      "submissions": {p: len(s["submissions"]) for p, s in exp["problems"].items()}}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
