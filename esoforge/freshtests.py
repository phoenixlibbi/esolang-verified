"""Fresh, private test suites.

The official 6 tests per problem are public (Hugging Face dataset and the original
EsolangBench GitHub repo), so they may be in any model's training data. Here each
lab draws its own suite from a secret seed: the problem's edge cases plus random
inputs from its generator, with expected outputs from the reference solution. Every
suite is gated: the reference must reproduce all six official tests first.
"""

from __future__ import annotations

import hashlib
import json
import random
from typing import Dict, List, Sequence, Tuple

from . import __version__
from .dataset import get_problem, problem_ids
from .problems import get_spec

# Put this string in anything you export so training-data filters can drop it.
CANARY = "ESOFORGE CANARY GUID 6f1c2a7e-3b9d-4c8e-9a51-esolang-env-forge"

Test = Tuple[str, str]


class GoldSanityError(AssertionError):
    pass


def check_reference(pid: str) -> None:
    """The reference must reproduce every official test exactly (byte for byte)."""
    spec = get_spec(pid)
    for inp, exp in get_problem(pid).tests:
        got = spec.solve(inp)
        if got != exp:
            raise GoldSanityError(f"{pid}: reference gives {got!r} for {inp!r}, official expects {exp!r}")


def input_pool(pid: str, seed: int, n_random: int, include_edges: bool = True) -> List[str]:
    spec = get_spec(pid)
    rng = random.Random(f"{seed}:{pid}")
    seen: Dict[str, None] = {}
    if include_edges:
        for e in spec.edges:
            seen.setdefault(e, None)
    attempts = 0
    target = len(seen) + n_random
    while len(seen) < target and attempts < n_random * 20:
        seen.setdefault(spec.gen(rng), None)
        attempts += 1
    return list(seen)


def fresh_suite(pid: str, seed: int = 0, n_random: int = 30, include_edges: bool = True) -> List[Test]:
    check_reference(pid)
    spec = get_spec(pid)
    return [(x, spec.solve(x)) for x in input_pool(pid, seed, n_random, include_edges)]


def suite_digest(tests: Sequence[Test]) -> str:
    return hashlib.sha256(json.dumps(list(tests)).encode()).hexdigest()[:16]


def export_suites(seed: int, n_random: int = 30, pids: Sequence[str] = ()) -> Dict[str, object]:
    pids = list(pids) or problem_ids()
    suites = {pid: fresh_suite(pid, seed, n_random) for pid in pids}
    return {
        "canary": CANARY,
        "generator": f"esolang-env-forge {__version__}",
        "seed": seed,
        "n_random": n_random,
        "problems": {pid: {"digest": suite_digest(t), "tests": [{"input": i, "output": o} for i, o in t]}
                     for pid, t in suites.items()},
    }
