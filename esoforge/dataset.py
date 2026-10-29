"""The EsoLang-Bench problem set (80 problems, 6 official tests each).

A pinned copy of the public dataset ships with the package so every number this
tool reports is reproducible offline. Source and licence: see NOTICE.md.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple

DATA_PATH = Path(__file__).parent / "data" / "esolang_bench.jsonl"
# huggingface.co/datasets/Lossfunk/Esolang-Bench @ a38a25fc6a19f477935f3b3f75567f88cefe8694, data/test.jsonl
DATA_SHA256 = "04ce0dbfd5f756225171829efd6674e388427de918d7873a1500bd4af8f05889"
DATA_SOURCE = ("https://huggingface.co/datasets/Lossfunk/Esolang-Bench/blob/"
               "a38a25fc6a19f477935f3b3f75567f88cefe8694/data/test.jsonl")

TIERS = ("easy", "medium", "hard", "extra_hard")
TIER_PREFIX = {"E": "easy", "M": "medium", "H": "hard", "X": "extra_hard"}


@dataclass(frozen=True)
class Problem:
    id: str
    difficulty: str
    title: str
    description: str
    tests: Tuple[Tuple[str, str], ...]  # (input, expected_output) pairs: the official "hidden" tests


class DatasetIntegrityError(RuntimeError):
    pass


def _order_key(pid: str) -> Tuple[int, int]:
    return ("EMHX".index(pid[0]), int(pid[1:]))


@lru_cache(maxsize=None)
def load_problems(path: str = "", verify: bool = True) -> Dict[str, Problem]:
    """Load problems keyed by id, in benchmark order (E01..E20, M.., H.., X..)."""
    p = Path(path) if path else DATA_PATH
    raw = p.read_bytes()
    if verify and not path:
        digest = hashlib.sha256(raw).hexdigest()
        if digest != DATA_SHA256:
            raise DatasetIntegrityError(f"{p} sha256 {digest} != pinned {DATA_SHA256}")
    problems: List[Problem] = []
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        tests = tuple((t["input"], t["output"]) for t in d["test_cases"])
        problems.append(Problem(d["id"], d["difficulty"], d["title"], d["description"], tests))
    problems.sort(key=lambda pr: _order_key(pr.id))
    return {pr.id: pr for pr in problems}


def problem_ids() -> List[str]:
    return list(load_problems())


def get_problem(pid: str) -> Problem:
    pid = pid.strip().upper()
    probs = load_problems()
    if pid not in probs:
        raise KeyError(f"unknown problem id {pid!r}")
    return probs[pid]
