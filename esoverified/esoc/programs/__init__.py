"""IR programs for all 80 EsoLang-Bench problems, written once and compiled to every
target language. Each is checked against the Python reference on the official tests and
on fresh suites (``tests/test_esoc_programs.py``)."""

from __future__ import annotations

from typing import Callable, Dict, Optional, Tuple

from ..ir import Builder, Program
from ..lib import Input

Writer = Callable[[Builder, Input], None]
_REGISTRY: Dict[str, Tuple[Writer, int, Optional[int]]] = {}


def program(pid: str, max_value: int = 2 ** 31 - 1, max_intermediate: Optional[int] = None):
    """Register an IR program writer. ``max_value`` bounds every stored value and
    ``max_intermediate`` every intermediate expression value (default: max_value)."""
    def deco(fn: Writer) -> Writer:
        if pid in _REGISTRY:
            raise ValueError(f"duplicate program {pid}")
        _REGISTRY[pid] = (fn, max_value, max_intermediate)
        return fn
    return deco


def _load() -> None:
    from . import easy, medium, hard, extra  # noqa: F401


def build(pid: str) -> Program:
    _load()
    fn, mv, mi = _REGISTRY[pid.upper()]
    P = Builder(pid.upper(), max_value=mv, max_intermediate=mi)
    fn(P, Input(P))
    return P.build()


def available() -> list:
    _load()
    return sorted(_REGISTRY, key=lambda p: ("EMHX".index(p[0]), int(p[1:])))
