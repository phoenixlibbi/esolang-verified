"""esoverified command line."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

from . import EXTENSIONS, LANGUAGES, __version__, canonical_language


def _lang_from_file(path: str, explicit: Optional[str]) -> str:
    if explicit:
        return canonical_language(explicit)
    for lang, ext in EXTENSIONS.items():
        if path.endswith(ext):
            return lang
    raise SystemExit("cannot tell the language from the extension; pass --language")


def cmd_problems(a) -> int:
    from .dataset import load_problems
    for p in load_problems().values():
        print(f"{p.id}  {p.difficulty:10s}  {p.title}")
    return 0


def cmd_run(a) -> int:
    from .interp import run
    lang = _lang_from_file(a.file, a.language)
    data = a.input if a.input is not None else (Path(a.input_file).read_text() if a.input_file else sys.stdin.read()
                                                if not sys.stdin.isatty() else "")
    r = run(lang, Path(a.file).read_text(), data, dialect=a.dialect)
    print(f"RUNTIME ERROR: {r.error}" if r.error else f"OUTPUT: {r.output!r}")
    print(f"steps: {r.steps}", file=sys.stderr)
    return 0 if r.ok else 1


def cmd_grade(a) -> int:
    from .dataset import get_problem
    from .freshtests import fresh_suite
    from .grading import grade_program
    lang = _lang_from_file(a.file, a.language)
    tests = list(get_problem(a.problem).tests) if a.tests == "official" else fresh_suite(a.problem, a.seed, a.n_random)
    g = grade_program(lang, Path(a.file).read_text(), tests, policy=a.policy, dialect=a.dialect)
    for i, r in enumerate(g.results, 1):
        if a.verbose or r.status != "PASS":
            print(f"test {i}: {r.status}")
    print(f"{a.problem} ({a.tests}): {g.passed}/{g.total} {'SOLVED' if g.solved else ''}")
    return 0 if g.solved else 1


def cmd_audit(a) -> int:
    from .audit import audit_all, summarize, to_json
    audits = audit_all(a.problems)
    s = summarize(audits)
    if a.json:
        Path(a.json).write_text(json.dumps(to_json(audits), indent=1))
    print(f"wrong programs: {s.mutants_valid} (equivalent excluded: {s.equivalent})")
    print(f"pass all official tests: {s.survivors_official} "
          f"({100 * s.survivors_official / max(1, s.mutants_valid):.1f}%) in {s.problems_with_survivor}/{s.problems} problems")
    print(f"mutation score: official {100 * s.score_official:.1f}%  fresh {100 * s.score_fresh:.1f}%")
    if a.verbose:
        for au in audits:
            for m in au.survivors:
                print(f"  {au.pid} {m.family}/{m.name}: {m.witness}")
    return 0


def cmd_fresh(a) -> int:
    from .freshtests import export_suites
    data = export_suites(a.seed, a.n_random, a.problems)
    text = json.dumps(data, indent=1)
    if a.out:
        Path(a.out).write_text(text)
        print(f"wrote {sum(len(p['tests']) for p in data['problems'].values())} tests to {a.out}")
    else:
        print(text)
    return 0


def cmd_compile(a) -> int:
    from .esoc import compile_problem
    src = compile_problem(a.problem, a.language)
    if a.out:
        Path(a.out).write_text(src)
        print(f"wrote {len(src)} bytes to {a.out}", file=sys.stderr)
    else:
        sys.stdout.write(src)
    return 0


def cmd_oracles(a) -> int:
    from .oracles import build_oracles, coverage
    m = build_oracles(Path(a.out), a.languages, a.problems, a.seed, a.n_random)
    for lang, c in coverage(m).items():
        print(f"{lang}: {c['verified_official']}/{c['problems']} official, {c['verified_fresh']}/{c['problems']} fresh")
    return 0


def cmd_probes(a) -> int:
    from .probes import run_hardened_probes, run_official_probes
    results = []
    if a.target in ("official", "both"):
        results += run_official_probes()
    if a.target in ("hardened", "both"):
        results += run_hardened_probes()
    for r in results:
        print(f"[{r.target:9s}] {'EXPLOITED' if r.exploited else 'blocked  '}  {r.name}: {r.summary}")
        if a.verbose:
            for ev in r.evidence:
                print(f"            {ev}")
    if a.json:
        Path(a.json).write_text(json.dumps([asdict(r) for r in results], indent=1))
    return 0


def cmd_difftest(a) -> int:
    from .difftest import dialect_gaps, fuzz
    bad = 0
    for lang in LANGUAGES:
        rep = fuzz(lang, a.cases, a.seed)
        gaps = dialect_gaps(lang, a.cases, a.seed)
        bad += len(rep.mismatches)
        print(f"{lang}: {rep.agree}/{rep.cases} agree with the official interpreter; "
              f"{len(gaps)} programs behave differently in the spec dialect")
    return 1 if bad else 0


def cmd_serve(a) -> int:
    from .harness import GraderServer, HarnessConfig, Session, write_client
    cfg = HarnessConfig(language=a.language, problems=a.problems, tests=a.tests, fresh_seed=a.seed,
                        max_submissions=a.max_submissions, run_budget=a.run_budget, feedback=a.feedback,
                        policy=a.policy)
    log = Path(a.log) if a.log else None
    session = Session(cfg, log)
    srv = GraderServer(session, a.host, a.port)
    if a.workspace:
        write_client(Path(a.workspace), srv.address)
        print(f"client written to {Path(a.workspace) / 'harness.py'}")
    print(f"grader listening on {srv.address} ({cfg.language}, {len(cfg.problems)} problems, tests={cfg.tests})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if a.export:
            Path(a.export).write_text(json.dumps(session.export(), indent=1))
            print(f"session exported to {a.export}")
    return 0


def cmd_harbor(a) -> int:
    from .harbor import export_tasks
    m = export_tasks(Path(a.out), a.languages, a.problems, tests_mode=a.tests, seed=a.seed, n_random=a.n_random,
                     policy=a.policy, require_verified=not a.allow_unverified,
                     oracle_dir=Path(a.oracle_dir) if a.oracle_dir else None)
    print(f"wrote {len(m['tasks'])} tasks to {a.out}; skipped {len(m['skipped_unverified_oracle'])} "
          "whose oracle does not pass its own tests within the step limit")
    return 0


def cmd_report(a) -> int:
    from .report import build_report
    data = build_report(Path(a.out), a.problems, Path(a.oracle_manifest) if a.oracle_manifest else None)
    s = data["summary"]
    print(f"report cards for {s['problems']} problems written to {a.out}/REPORT.md and report_cards.json")
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="esoverified", description="EsoLang-Verified: audited, contamination-resistant "
                                 "EsoLang-Bench environments (no model needed).")
    ap.add_argument("--version", action="version", version=f"esoverified {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def problems_arg(p):
        p.add_argument("--problems", nargs="*", default=[], metavar="ID")

    p = sub.add_parser("problems", help="list the 80 problems")
    p.set_defaults(fn=cmd_problems)

    p = sub.add_parser("run", help="run a program like the official grader")
    p.add_argument("file")
    p.add_argument("--language")
    p.add_argument("--input")
    p.add_argument("--input-file")
    p.add_argument("--dialect", default="official", choices=["official", "spec"])
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("grade", help="grade a program on official or fresh tests")
    p.add_argument("file")
    p.add_argument("--problem", required=True)
    p.add_argument("--language")
    p.add_argument("--tests", default="fresh", choices=["official", "fresh"])
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--n-random", type=int, default=30)
    p.add_argument("--policy", default="newline", choices=["official", "exact", "newline"])
    p.add_argument("--dialect", default="official", choices=["official", "spec"])
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(fn=cmd_grade)

    p = sub.add_parser("audit", help="mutation-score audit of the official tests")
    problems_arg(p)
    p.add_argument("--json")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(fn=cmd_audit)

    p = sub.add_parser("fresh", help="export a private, seeded fresh test suite")
    problems_arg(p)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--n-random", type=int, default=30)
    p.add_argument("--out")
    p.set_defaults(fn=cmd_fresh)

    p = sub.add_parser("compile", help="compile a problem's reference program with esoc")
    p.add_argument("problem")
    p.add_argument("--language", required=True)
    p.add_argument("-o", "--out")
    p.set_defaults(fn=cmd_compile)

    p = sub.add_parser("oracles", help="compile and verify oracles for every problem")
    problems_arg(p)
    p.add_argument("--languages", nargs="*", default=list(LANGUAGES))
    p.add_argument("--out", required=True)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--n-random", type=int, default=30)
    p.set_defaults(fn=cmd_oracles)

    p = sub.add_parser("probes", help="run scripted exploits against the official and hardened harness")
    p.add_argument("--target", default="both", choices=["official", "hardened", "both"])
    p.add_argument("--json")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(fn=cmd_probes)

    p = sub.add_parser("difftest", help="differential-test the interpreters against the official ones")
    p.add_argument("--cases", type=int, default=1000)
    p.add_argument("--seed", type=int, default=0)
    p.set_defaults(fn=cmd_difftest)

    p = sub.add_parser("serve", help="run the hardened grader for an agent session")
    problems_arg(p)
    p.add_argument("--language", required=True)
    p.add_argument("--tests", default="fresh", choices=["official", "fresh", "impossible"])
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--max-submissions", type=int, default=3)
    p.add_argument("--run-budget", type=int)
    p.add_argument("--feedback", default="aggregate", choices=["aggregate", "per_test"])
    p.add_argument("--policy", default="newline", choices=["official", "exact", "newline"])
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=0)
    p.add_argument("--workspace", help="write the agent client (harness.py) here")
    p.add_argument("--log", help="append every event as JSON lines")
    p.add_argument("--export", help="write the session JSON here on exit")
    p.set_defaults(fn=cmd_serve)

    p = sub.add_parser("harbor", help="export Harbor tasks")
    problems_arg(p)
    p.add_argument("--languages", nargs="*", default=list(LANGUAGES))
    p.add_argument("--out", required=True)
    p.add_argument("--tests", default="fresh", choices=["official", "fresh", "impossible"])
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--n-random", type=int, default=30)
    p.add_argument("--policy", default="newline", choices=["official", "exact", "newline"])
    p.add_argument("--oracle-dir", help="reuse oracles written by `esoverified oracles`")
    p.add_argument("--allow-unverified", action="store_true")
    p.set_defaults(fn=cmd_harbor)

    p = sub.add_parser("report", help="write per-problem report cards")
    problems_arg(p)
    p.add_argument("--out", required=True)
    p.add_argument("--oracle-manifest")
    p.set_defaults(fn=cmd_report)
    return ap


def main(argv: Optional[List[str]] = None) -> int:
    a = build_parser().parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
