"""Reference oracle programs in the target languages, and their verification.

An oracle is the esoc-compiled program for a problem. It is *verified* for a test
suite when it reproduces every expected output under the official interpreter
semantics within the official 10,000,000-step cap. Brainfuck oracles can be correct
but too slow for long inputs (random access on a tape costs time proportional to the
index), so verification is reported per suite rather than assumed.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

from . import EXTENSIONS, LANGUAGES, canonical_language
from .dataset import get_problem, problem_ids
from .esoc import compile_problem
from .freshtests import fresh_suite
from .grading import grade_program

Test = Tuple[str, str]


@dataclass
class OracleCheck:
    pid: str
    language: str
    bytes: int
    official_passed: int
    official_total: int
    fresh_passed: int
    fresh_total: int
    max_steps: int

    @property
    def verified_official(self) -> bool:
        return self.official_passed == self.official_total

    @property
    def verified_fresh(self) -> bool:
        return self.fresh_total > 0 and self.fresh_passed == self.fresh_total


def check_oracle(pid: str, language: str, source: Optional[str] = None, fresh: Optional[Sequence[Test]] = None,
                 fresh_seed: int = 0, fresh_random: int = 30) -> OracleCheck:
    lang = canonical_language(language)
    src = source if source is not None else compile_problem(pid, lang)
    off = grade_program(lang, src, get_problem(pid).tests, policy="exact")
    fr_tests = list(fresh) if fresh is not None else fresh_suite(pid, fresh_seed, fresh_random)
    fr = grade_program(lang, src, fr_tests, policy="exact")
    steps = max([r.steps for r in off.results + fr.results] or [0])
    return OracleCheck(pid, lang, len(src), off.passed, off.total, fr.passed, fr.total, steps)


def build_oracles(out_dir: Path, languages: Sequence[str] = LANGUAGES, pids: Sequence[str] = (),
                  fresh_seed: int = 0, fresh_random: int = 30) -> Dict[str, Dict[str, dict]]:
    """Compile, verify and write oracles to out_dir/<language>/<pid>.<ext> with a manifest."""
    manifest: Dict[str, Dict[str, dict]] = {}
    for lang in (canonical_language(x) for x in languages):
        d = out_dir / lang
        d.mkdir(parents=True, exist_ok=True)
        manifest[lang] = {}
        for pid in (list(pids) or problem_ids()):
            src = compile_problem(pid, lang)
            (d / f"{pid}{EXTENSIONS[lang]}").write_text(src)
            chk = check_oracle(pid, lang, src, fresh_seed=fresh_seed, fresh_random=fresh_random)
            manifest[lang][pid] = {**asdict(chk), "verified_official": chk.verified_official,
                                   "verified_fresh": chk.verified_fresh}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return manifest


def coverage(manifest: Dict[str, Dict[str, dict]]) -> Dict[str, Dict[str, int]]:
    return {lang: {"problems": len(rows),
                   "verified_official": sum(r["verified_official"] for r in rows.values()),
                   "verified_fresh": sum(r["verified_fresh"] for r in rows.values())}
            for lang, rows in manifest.items()}

