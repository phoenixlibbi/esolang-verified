"""Random IR programs for differential testing of the backends against the IR
reference interpreter (all values stay small so every backend is exact)."""

from __future__ import annotations

import random
from typing import List

from .ir import Builder, Expr, Program, Var, sel, udiv, umod
from .lib import Input, fmod, iabs, tdiv


def random_program(rng: random.Random, n_stmts: int = 12, depth: int = 2) -> Program:
    P = Builder("fuzz", max_value=10 ** 6, max_intermediate=10 ** 6)
    I = Input(P)
    xs: List[Var] = [P.var(f"v{i}") for i in range(3)]
    arr = P.array("a", 6)
    for v in xs:
        I.read_int(v)

    def leaf() -> Expr:
        if rng.random() < 0.4:
            return rng.choice(xs)
        return rng.choice(xs) + rng.randint(-9, 9)

    def expr(d: int) -> Expr:
        if d <= 0:
            return leaf()
        k = rng.randrange(10)
        a, b = expr(d - 1), expr(d - 1)
        if k == 0: return a + b
        if k == 1: return a - b
        if k == 2: return umod(iabs(a), 7) * rng.randint(-3, 3)
        if k == 3: return tdiv(a, rng.choice([1, 2, 3, -4, 10]))
        if k == 4: return fmod(a, rng.choice([2, 5, -3]))
        if k == 5: return sel(a < b, a, b)
        if k == 6: return (a > b) + (a.eq(b)) * 2
        if k == 7: return ((a >= 0) & (b <= 0)) | ~(a.ne(b))
        if k == 8: return arr[umod(iabs(a), 6)]
        return udiv(iabs(a), 3) - iabs(b)

    for _ in range(n_stmts):
        r = rng.random()
        if r < 0.35:
            P.set(rng.choice(xs), expr(depth))
        elif r < 0.5:
            P.store(arr, umod(iabs(expr(1)), 6), expr(depth - 1))
        elif r < 0.65:
            with P.if_(expr(1) > expr(1)):
                P.set(rng.choice(xs), expr(1))
            with P.else_():
                P.print_int(expr(1))
                P.print_char(32)
        elif r < 0.75:
            k = P.temp(rng.randint(0, 3))
            with P.while_(k > 0):
                P.set(k, k - 1)
                P.set(rng.choice(xs), expr(1))
        else:
            P.print_int(expr(depth))
            P.print_char(32)
    for v in xs:
        P.print_int(v)
        P.print_char(32)
    return P.build()


def random_input(rng: random.Random) -> str:
    return " ".join(str(rng.randint(-60, 60)) for _ in range(3))
