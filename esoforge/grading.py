"""Output comparison policies and program grading.

``official`` is what the paper's harness does: ``output.strip() == expected.strip()``.
That makes leading/trailing whitespace invisible, so "echo the line exactly" problems
cannot detect a solution that trims. ``exact`` compares byte for byte, and
``newline`` ignores only one trailing newline (the usual judge convention).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

from .interp import run
from .interp.common import DEFAULT_MAX_STEPS

POLICIES = ("official", "exact", "newline")


def outputs_match(got: Optional[str], expected: str, policy: str = "official") -> bool:
    if got is None:
        return False
    if policy == "official":
        return got.strip() == expected.strip()
    if policy == "exact":
        return got == expected
    if policy == "newline":
        return (got[:-1] if got.endswith("\n") else got) == expected
    raise ValueError(f"unknown policy {policy!r}")


@dataclass
class TestResult:
    status: str                  # PASS, WRONG ANSWER, RUNTIME ERROR
    output: Optional[str]
    error: Optional[str]
    steps: int


@dataclass
class GradeResult:
    passed: int
    total: int
    results: List[TestResult] = field(default_factory=list)

    @property
    def solved(self) -> bool:
        return self.total > 0 and self.passed == self.total

    @property
    def fraction(self) -> float:
        return self.passed / self.total if self.total else 0.0


def grade_program(language: str, program: str, tests: Sequence[Tuple[str, str]], *,
                  policy: str = "official", dialect: str = "official",
                  max_steps: int = DEFAULT_MAX_STEPS, engine: str = "esoforge") -> GradeResult:
    """Run `program` on every (input, expected) pair. ``engine="upstream"`` uses the
    paper's own interpreters (slower; esoforge's are differential-tested against them)."""
    results: List[TestResult] = []
    passed = 0
    for inp, exp in tests:
        if engine == "upstream":
            from .difftest import upstream_outcome
            o = upstream_outcome(language, program, inp, max_steps)
            out, err, steps = o.output, o.error_kind, 0
        else:
            r = run(language, program, inp, dialect=dialect, max_steps=max_steps)
            out, err, steps = r.output, r.error, r.steps
        if err is not None:
            status = "RUNTIME ERROR"
        elif outputs_match(out, exp, policy):
            status = "PASS"
            passed += 1
        else:
            status = "WRONG ANSWER"
        results.append(TestResult(status, out, err, steps))
    return GradeResult(passed, len(tests), results)
