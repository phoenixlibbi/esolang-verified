"""Deliberately wrong programs ("mutants") for the test-strength audit.

Two sources:

* problem-specific logic slips written next to each reference solution
  (floor instead of truncating division, case-insensitive compare, ties broken the
  wrong way, ...), see :mod:`esoforge.problems`;
* generic esolang bugs applied by tag: values stored in one 8-bit cell, signs dropped,
  only the first k digits parsed, fixed-size input buffers, single-digit printing,
  off-by-one outputs.

A mutant is a function ``input -> output`` like a reference solution. If it raises, the
run counts as a crash (its output never matches).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, List

from .problems import ProblemSpec, get_spec

Solve = Callable[[str], str]
_INT = re.compile(r"-?\d+")


@dataclass(frozen=True)
class Mutant:
    name: str
    family: str          # "specific" or the generic family name
    fn: Solve


def _map_ints(s: str, f: Callable[[int], int]) -> str:
    return _INT.sub(lambda m: str(f(int(m.group()))), s)


def _truncate_digits(k: int) -> Callable[[str], str]:
    def tr(s: str) -> str:
        def one(m: "re.Match[str]") -> str:
            tok = m.group()
            sign = "-" if tok.startswith("-") else ""
            return sign + tok.lstrip("-")[:k]
        return _INT.sub(one, s)
    return tr


def _first_line_prefix(k: int) -> Callable[[str], str]:
    def tr(s: str) -> str:
        head, sep, rest = s.partition("\n")
        return head[:k] + sep + rest
    return tr


def _on_input(solve: Solve, tr: Callable[[str], str]) -> Solve:
    return lambda s: solve(tr(s))


def _on_output(solve: Solve, tr: Callable[[str], str]) -> Solve:
    return lambda s: tr(solve(s))


def _last_int(s: str, delta: int) -> str:
    ms = list(_INT.finditer(s))
    if not ms:
        return s
    m = ms[-1]
    return s[:m.start()] + str(int(m.group()) + delta) + s[m.end():]


def generic_mutants(spec: ProblemSpec) -> List[Mutant]:
    t = spec.tags
    f = spec.solve
    out: List[Mutant] = []
    if "int_in" in t:
        out.append(Mutant("byte_input", "byte_cell", _on_input(f, lambda s: _map_ints(s, lambda v: v % 256))))
        for k in (1, 2, 3):
            out.append(Mutant(f"first_{k}_digits", "digit_limit", _on_input(f, _truncate_digits(k))))
        if "neg_in" in t:
            out.append(Mutant("sign_ignored", "sign", _on_input(f, lambda s: _map_ints(s, abs))))
    if "int_out" in t:
        out.append(Mutant("byte_output", "byte_cell", _on_output(f, lambda s: _map_ints(s, lambda v: v % 256))))
        out.append(Mutant("unsigned_output", "sign", _on_output(f, lambda s: s.replace("-", ""))))
        out.append(Mutant("last_digit_only", "digit_limit",
                          _on_output(f, lambda s: _map_ints(s, lambda v: (abs(v) % 10) * (1 if v >= 0 else -1)))))
        out.append(Mutant("plus_one", "off_by_one", _on_output(f, lambda s: _last_int(s, 1))))
        out.append(Mutant("minus_one", "off_by_one", _on_output(f, lambda s: _last_int(s, -1))))
    if "str_in" in t:
        for k in (8, 16):
            out.append(Mutant(f"buffer_{k}", "fixed_buffer", _on_input(f, _first_line_prefix(k))))
    if "ws_sensitive" in t:
        out.append(Mutant("trim_lines", "whitespace",
                          _on_input(f, lambda s: "\n".join(x.strip() for x in s.split("\n")))))
    return out


def mutants_for(pid: str) -> List[Mutant]:
    spec = get_spec(pid)
    specific = [Mutant(name, "specific", fn) for name, fn in spec.mutants]
    return specific + generic_mutants(spec)


CRASH = "\x00<crash>"


def safe_call(fn: Solve, s: str) -> str:
    try:
        out = fn(s)
        return out if isinstance(out, str) else CRASH
    except Exception:  # a mutant crashing is a legitimate (detectable) failure
        return CRASH
