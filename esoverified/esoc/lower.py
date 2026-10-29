"""IR-to-IR lowering passes shared by backends without a native integer printer."""

from __future__ import annotations

from typing import List

from .ir import Builder, If, PrintChar, PrintInt, Program, Set, Stmt, Var, While, udiv, umod


def lower_print_int(prog: Program) -> Program:
    """Replace print_int(e) with digit-by-digit print_char using udiv/umod by powers of 10."""
    b = Builder(prog.name + "+pi", max_value=prog.max_value, max_intermediate=prog.max_intermediate)
    b.prog.scalars = list(prog.scalars)
    b.prog.arrays = dict(prog.arrays)
    b.prog.array_max = dict(prog.array_max)
    b.prog.byte_vars = list(prog.byte_vars)
    t = b.var("_pi_t")
    p = b.var("_pi_p")

    def lower(stmts: List[Stmt]) -> List[Stmt]:
        out: List[Stmt] = []
        for s in stmts:
            if isinstance(s, PrintInt):
                sub = Builder("tmp")
                sub.set(t, s.expr)
                with sub.if_(t < 0):
                    sub.print_char(45)
                    sub.set(t, -t)
                sub.set(p, 1)
                with sub.while_(p * 10 <= t):
                    sub.set(p, p * 10)
                with sub.while_(p > 0):
                    sub.print_char(48 + umod(udiv(t, p), 10))
                    sub.set(p, udiv(p, 10))
                out.extend(sub.prog.body)
            elif isinstance(s, If):
                out.append(If(s.cond, lower(s.then), lower(s.other)))
            elif isinstance(s, While):
                out.append(While(s.cond, lower(s.body)))
            else:
                out.append(s)
        return out

    b.prog.body = lower(prog.body)
    return b.prog


__all__ = ["lower_print_int", "Var", "Set", "PrintChar"]
