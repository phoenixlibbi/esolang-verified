"""Constant folding and small algebraic simplifications on IR expressions.

Mostly matters for Brainfuck, where a general long division is far more expensive than
division by a small constant: ``tdiv(x, 2)`` expands to ``udiv(iabs(x), iabs(2))`` and
folding ``iabs(2)`` to ``2`` turns it into the fast constant path.
"""

from __future__ import annotations

from typing import List

from .ir import Bin, Const, Expr, Idx, If, PrintChar, PrintInt, Program, ReadChar, Sel, Set, Stmt, Store, Un, Var, While

_FOLD = {
    "add": lambda a, b: a + b, "sub": lambda a, b: a - b, "mul": lambda a, b: a * b,
    "eq": lambda a, b: int(a == b), "ne": lambda a, b: int(a != b), "lt": lambda a, b: int(a < b),
    "le": lambda a, b: int(a <= b), "gt": lambda a, b: int(a > b), "ge": lambda a, b: int(a >= b),
    "and": lambda a, b: int(bool(a) and bool(b)), "or": lambda a, b: int(bool(a) or bool(b)),
}


def fold(e: Expr) -> Expr:
    if isinstance(e, (Const, Var)):
        return e
    if isinstance(e, Idx):
        return Idx(e.arr, fold(e.index))
    if isinstance(e, Un):
        a = fold(e.a)
        if isinstance(a, Const):
            return Const(-a.value if e.op == "neg" else int(not a.value))
        if e.op == "neg" and isinstance(a, Un) and a.op == "neg":
            return a.a
        return Un(e.op, a)
    if isinstance(e, Sel):
        c, a, b = fold(e.cond), fold(e.a), fold(e.b)
        if isinstance(c, Const):
            return a if c.value else b
        return Sel(c, a, b)
    if isinstance(e, Bin):
        a, b = fold(e.a), fold(e.b)
        if isinstance(a, Const) and isinstance(b, Const):
            if e.op in _FOLD:
                return Const(_FOLD[e.op](a.value, b.value))
            if e.op in ("udiv", "umod") and a.value >= 0 and b.value > 0:
                return Const(a.value // b.value if e.op == "udiv" else a.value % b.value)
        if e.op == "add":
            if isinstance(b, Const) and b.value == 0:
                return a
            if isinstance(a, Const) and a.value == 0:
                return b
        if e.op == "sub" and isinstance(b, Const) and b.value == 0:
            return a
        if e.op == "mul":
            for x, y in ((a, b), (b, a)):
                if isinstance(x, Const) and x.value == 1:
                    return y
        if e.op == "udiv" and isinstance(b, Const) and b.value == 1:
            return a
        return Bin(e.op, a, b)
    raise TypeError(e)


def simplify_block(ss: List[Stmt]) -> List[Stmt]:
    out: List[Stmt] = []
    for s in ss:
        if isinstance(s, Set):
            out.append(Set(s.var, fold(s.expr)))
        elif isinstance(s, Store):
            out.append(Store(s.arr, fold(s.index), fold(s.expr)))
        elif isinstance(s, If):
            c = fold(s.cond)
            if isinstance(c, Const):
                out.extend(simplify_block(s.then if c.value else s.other))
            else:
                out.append(If(c, simplify_block(s.then), simplify_block(s.other)))
        elif isinstance(s, While):
            c = fold(s.cond)
            if isinstance(c, Const) and not c.value:
                continue
            out.append(While(c, simplify_block(s.body)))
        elif isinstance(s, PrintChar):
            out.append(PrintChar(fold(s.expr)))
        elif isinstance(s, PrintInt):
            out.append(PrintInt(fold(s.expr)))
        elif isinstance(s, ReadChar):
            out.append(s)
        else:
            raise TypeError(s)
    return out


def simplify(prog: Program) -> Program:
    return Program(prog.name, list(prog.scalars), dict(prog.arrays), simplify_block(prog.body), prog.max_value,
                   prog.max_intermediate, dict(prog.array_max), list(prog.byte_vars))
