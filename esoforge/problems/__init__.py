"""Reference solutions, input generators and edge cases for all 80 problems.

Each problem has a :class:`ProblemSpec`:

* ``solve(input) -> output``: a plain-Python reference solution (the semantic oracle);
* ``gen(rng) -> input``: a random input that respects the problem statement;
* ``edges``: hand-picked inputs at the boundaries the statement allows
  (zero, negatives, values past 255, multi-digit counts, empty lines, ties...);
* ``tags``: which generic mutation operators make sense (see :mod:`esoforge.mutants`).

Only inputs the statement clearly allows are generated, so a fresh test can never
fail a solution that follows the statement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, FrozenSet, List, Tuple
import random

Solve = Callable[[str], str]
Gen = Callable[[random.Random], str]


@dataclass(frozen=True)
class ProblemSpec:
    pid: str
    solve: Solve
    gen: Gen
    edges: Tuple[str, ...]
    tags: FrozenSet[str] = field(default_factory=frozenset)
    mutants: Tuple[Tuple[str, Solve], ...] = ()


REGISTRY: Dict[str, ProblemSpec] = {}


def register(pid: str, solve: Solve, gen: Gen, edges: List[str], tags: str = "",
             mutants: Dict[str, Solve] | None = None) -> None:
    if pid in REGISTRY:
        raise ValueError(f"duplicate spec {pid}")
    REGISTRY[pid] = ProblemSpec(pid, solve, gen, tuple(edges), frozenset(tags.split()),
                                tuple((mutants or {}).items()))


def get_spec(pid: str) -> ProblemSpec:
    _load_all()
    return REGISTRY[pid.upper()]


def all_specs() -> Dict[str, ProblemSpec]:
    _load_all()
    return dict(sorted(REGISTRY.items(), key=lambda kv: ("EMHX".index(kv[0][0]), int(kv[0][1:]))))


_loaded = False


def _load_all() -> None:
    global _loaded
    if not _loaded:
        from . import easy, medium, hard, extra  # noqa: F401  (registration side effects)
        _loaded = True
