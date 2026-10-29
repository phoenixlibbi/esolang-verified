"""Differential testing of interpreters.

1. ``fuzz``: random programs run on esoverified's interpreter (official dialect) and on the
   paper's interpreter; output, success and error kind must agree.
2. ``dialect_gaps``: programs whose result differs between the official and the spec
   dialect, i.e. programs that depend on a quirk of the official interpreter.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from .esoc.wsasm import assemble
from .interp import run
from .upstream import esolang_error_class, official_interpreter


@dataclass
class Outcome:
    output: Optional[str]
    error_kind: Optional[str]

    def key(self) -> Tuple[Optional[str], Optional[str]]:
        return self.output, self.error_kind


def upstream_outcome(language: str, program: str, inp: str, max_steps: int) -> Outcome:
    err_cls = esolang_error_class()
    try:
        return Outcome(official_interpreter(language, max_steps).run(program, inp), None)
    except err_cls as e:  # type: ignore[misc]
        return Outcome(None, e.error_type)
    except (IndexError, KeyError, ValueError, OverflowError, RecursionError) as e:
        # upstream occasionally crashes with a Python error instead of an EsolangError
        return Outcome(None, f"PythonError:{type(e).__name__}")


def esoverified_outcome(language: str, program: str, inp: str, max_steps: int,
                     dialect: str = "official") -> Outcome:
    r = run(language, program, inp, dialect=dialect, max_steps=max_steps)
    return Outcome(r.output, None if r.ok else r.error.split(":", 1)[0])  # type: ignore[union-attr]


# ----------------------------------------------------------------- generators

def random_bf(rng: random.Random, length: int = 40) -> str:
    out: List[str] = []
    depth = 0
    for _ in range(length):
        r = rng.random()
        if r < 0.08:
            out.append("[")
            depth += 1
        elif r < 0.16 and depth:
            out.append("]")
            depth -= 1
        else:
            out.append(rng.choice("+++---<>>>.,"))
    out.extend("]" * depth)
    return "".join(out)


_WS_OPS = ["push", "push", "push", "dup", "swap", "discard", "copy", "slide", "add", "sub", "mul",
           "div", "mod", "store", "retrieve", "out_char", "out_num", "read_char", "read_num",
           "label", "jump", "jz", "jn", "call", "ret", "end"]


def random_ws(rng: random.Random, length: int = 25) -> str:
    prog: List[Tuple[str, object]] = []
    labels = ["a", "b", "c"]
    defined = set()
    for _ in range(length):
        op = rng.choice(_WS_OPS)
        if op == "push":
            prog.append((op, rng.choice([0, 1, 2, 3, 7, 10, -1, -5, 65, 300, 2 ** 60 + 3, -(2 ** 55)])))
        elif op in ("copy", "slide"):
            prog.append((op, rng.randint(0, 3)))
        elif op == "label":
            lbl = rng.choice([x for x in labels if x not in defined] or ["z" + str(len(prog))])
            defined.add(lbl)
            prog.append((op, lbl))
        elif op in ("jump", "jz", "jn", "call"):
            prog.append((op, rng.choice(labels)))
        else:
            prog.append((op, None))
    return assemble(prog)


_B98_CHARS = "0123456789abf+-*/%!`:\\$>v<^_|#.,&~gp@ \"'jrnx[]s;k"


def random_b98(rng: random.Random, w: int = 9, h: int = 4) -> str:
    rows = ["".join(rng.choice(_B98_CHARS) for _ in range(w)) for _ in range(h)]
    # make termination likely
    r = rng.randrange(h)
    c = rng.randrange(w)
    rows[r] = rows[r][:c] + "@" + rows[r][c + 1:]
    return "\n".join(rows)


GENERATORS: Dict[str, Callable[[random.Random], str]] = {
    "brainfuck": random_bf, "whitespace": random_ws, "befunge98": random_b98,
}


def random_input(rng: random.Random) -> str:
    return rng.choice(["", "5 7", "-3 10\n", "hello", "12345", "a b c", "9\n8\n", "99999999999999999999 3"])


@dataclass
class FuzzReport:
    language: str
    cases: int
    agree: int
    mismatches: List[Dict[str, object]]


def fuzz(language: str, cases: int = 500, seed: int = 0, max_steps: int = 5_000) -> FuzzReport:
    rng = random.Random(seed)
    gen = GENERATORS[language]
    agree = 0
    bad: List[Dict[str, object]] = []
    for _ in range(cases):
        prog = gen(rng)
        inp = random_input(rng)
        a = esoverified_outcome(language, prog, inp, max_steps)
        b = upstream_outcome(language, prog, inp, max_steps)
        if a.key() == b.key():
            agree += 1
        else:
            bad.append({"program": prog, "input": inp, "esoverified": a.key(), "official": b.key()})
    return FuzzReport(language, cases, agree, bad)


def dialect_gaps(language: str, cases: int = 500, seed: int = 0, max_steps: int = 5_000) -> List[Dict[str, object]]:
    rng = random.Random(seed)
    gen = GENERATORS[language]
    gaps = []
    for _ in range(cases):
        prog = gen(rng)
        inp = random_input(rng)
        a = esoverified_outcome(language, prog, inp, max_steps, "official")
        b = esoverified_outcome(language, prog, inp, max_steps, "spec")
        if a.key() != b.key():
            gaps.append({"program": prog, "input": inp, "official": a.key(), "spec": b.key()})
    return gaps
