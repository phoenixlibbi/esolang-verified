"""Test-strength audit: how many deliberately wrong programs pass the official tests?

For each problem and each mutant (see :mod:`esoforge.mutants`):

1. **Is it really wrong?** It must differ from the reference on at least one input from
   a large pool (edge cases + random inputs the statement allows). Mutants that never
   differ are "equivalent" and excluded.
2. **Do the official 6 tests catch it?** If it matches the expected output on all six
   (under the official ``strip()`` comparison) it *survives*: a wrong program the
   benchmark would score as solved.
3. **Does a fresh suite catch it?** The same question for an independently seeded fresh
   suite (edges + 30 random tests), which is *not* tuned to the mutants.

Mutation score = killed / non-equivalent. This needs no model: every number is
reproducible with ``esoforge audit``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .dataset import get_problem, problem_ids
from .freshtests import check_reference, fresh_suite, input_pool
from .grading import outputs_match
from .mutants import CRASH, Mutant, mutants_for, safe_call
from .problems import get_spec

POOL_SEED = 20261030
POOL_RANDOM = 400


@dataclass
class MutantVerdict:
    pid: str
    name: str
    family: str
    equivalent: bool                 # never differs from the reference on the pool
    killed_official: bool
    killed_fresh: bool
    policy_only: bool                # differs only in surrounding whitespace (invisible to strip())
    witness: Optional[Tuple[str, str, str]] = None  # (input, expected, mutant output)


@dataclass
class ProblemAudit:
    pid: str
    title: str
    mutants: List[MutantVerdict] = field(default_factory=list)

    @property
    def valid(self) -> List[MutantVerdict]:
        return [m for m in self.mutants if not m.equivalent]

    @property
    def survivors(self) -> List[MutantVerdict]:
        return [m for m in self.valid if not m.killed_official]

    def score(self, which: str = "official") -> Optional[float]:
        v = self.valid
        if not v:
            return None
        k = sum(m.killed_official if which == "official" else m.killed_fresh for m in v)
        return k / len(v)


def _differs(fn, ref_out: str, inp: str, policy: str) -> Tuple[bool, str]:
    got = safe_call(fn, inp)
    if got == CRASH:
        return True, got
    return not outputs_match(got, ref_out, policy), got


def audit_problem(pid: str, *, pool_seed: int = POOL_SEED, pool_random: int = POOL_RANDOM,
                  fresh_seed: int = 0, fresh_random: int = 30, mutants: Optional[Sequence[Mutant]] = None,
                  policy: str = "official") -> ProblemAudit:
    check_reference(pid)
    prob = get_problem(pid)
    spec = get_spec(pid)
    pool = input_pool(pid, pool_seed, pool_random)
    pool_ref = [(x, spec.solve(x)) for x in pool]
    pool_ref.sort(key=lambda t: (len(t[0]), t[0]))  # shortest witness first
    fresh = fresh_suite(pid, fresh_seed, fresh_random)
    res = ProblemAudit(pid, prob.title)
    for m in (mutants if mutants is not None else mutants_for(pid)):
        witness = None
        exact_diff = False
        for x, ref_out in pool_ref:
            d, got = _differs(m.fn, ref_out, x, policy)
            if d:
                witness = (x, ref_out, got if got != CRASH else "<crash>")
                break
            if not exact_diff and got != ref_out:
                exact_diff = True
        equivalent = witness is None
        killed_official = any(_differs(m.fn, exp, inp, policy)[0] for inp, exp in prob.tests)
        killed_fresh = any(_differs(m.fn, exp, inp, policy)[0] for inp, exp in fresh)
        res.mutants.append(MutantVerdict(pid, m.name, m.family, equivalent, killed_official, killed_fresh,
                                         policy_only=equivalent and exact_diff, witness=witness))
    return res


@dataclass
class AuditSummary:
    problems: int
    mutants_total: int
    mutants_valid: int
    equivalent: int
    survivors_official: int
    survivors_fresh: int
    problems_with_survivor: int
    score_official: float
    score_fresh: float
    by_family: Dict[str, Dict[str, int]]
    by_tier: Dict[str, Dict[str, int]]
    policy_only: int


def summarize(audits: Sequence[ProblemAudit]) -> AuditSummary:
    allm = [m for a in audits for m in a.mutants]
    valid = [m for m in allm if not m.equivalent]
    surv_o = [m for m in valid if not m.killed_official]
    surv_f = [m for m in valid if not m.killed_fresh]
    fam: Dict[str, Dict[str, int]] = {}
    tier: Dict[str, Dict[str, int]] = {}
    for m in valid:
        for key, table in ((m.family, fam), ({"E": "easy", "M": "medium", "H": "hard", "X": "extra_hard"}[m.pid[0]],
                                             tier)):
            row = table.setdefault(key, {"valid": 0, "survive_official": 0, "survive_fresh": 0})
            row["valid"] += 1
            row["survive_official"] += not m.killed_official
            row["survive_fresh"] += not m.killed_fresh
    return AuditSummary(
        problems=len(audits), mutants_total=len(allm), mutants_valid=len(valid),
        equivalent=len(allm) - len(valid), survivors_official=len(surv_o), survivors_fresh=len(surv_f),
        problems_with_survivor=sum(1 for a in audits if a.survivors),
        score_official=(len(valid) - len(surv_o)) / len(valid) if valid else 1.0,
        score_fresh=(len(valid) - len(surv_f)) / len(valid) if valid else 1.0,
        by_family=fam, by_tier=tier, policy_only=sum(m.policy_only for m in allm))


def audit_all(pids: Sequence[str] = (), **kw) -> List[ProblemAudit]:
    return [audit_problem(pid, **kw) for pid in (list(pids) or problem_ids())]


def to_json(audits: Sequence[ProblemAudit]) -> Dict[str, object]:
    return {
        "summary": asdict(summarize(audits)),
        "problems": [{"pid": a.pid, "title": a.title, "score_official": a.score("official"),
                      "score_fresh": a.score("fresh"), "mutants": [asdict(m) for m in a.mutants]}
                     for a in audits],
    }
