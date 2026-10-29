"""IR -> Whitespace.

Scalars and array elements live on the heap (scalars at 0..S-1, arrays after them);
expressions evaluate on the stack. Whitespace integers are unbounded, so values need no
special storage. Division is only emitted as ``udiv``/``umod`` on non-negative operands,
where the official dialect's ``int(a / b)`` and the spec's floor agree (exactly while
|a| < 2**53, which every EsoLang program respects).
"""

from __future__ import annotations

from itertools import count
from typing import Dict, List, Tuple

from .ir import Bin, Const, Expr, Idx, If, PrintChar, PrintInt, Program, ReadChar, Sel, Set, Stmt, Store, Un, Var, While
from .wsasm import assemble

Op = Tuple[str, object]


class WSCompiler:
    def __init__(self, prog: Program) -> None:
        self.prog = prog
        self.addr: Dict[str, int] = {n: i for i, n in enumerate(prog.scalars)}
        base = len(prog.scalars)
        self.base: Dict[str, int] = {}
        for name, size in prog.arrays.items():
            self.base[name] = base
            base += size
        self.code: List[Op] = []
        self._labels = count()

    def label(self) -> str:
        return f"L{next(self._labels)}"

    def emit(self, op: str, arg: object = None) -> None:
        self.code.append((op, arg))

    # ---------------------------------------------------------------- exprs
    def expr(self, e: Expr) -> None:
        E = self.emit
        if isinstance(e, Const):
            E("push", e.value)
        elif isinstance(e, Var):
            E("push", self.addr[e.name]); E("retrieve")
        elif isinstance(e, Idx):
            E("push", self.base[e.arr]); self.expr(e.index); E("add"); E("retrieve")
        elif isinstance(e, Un):
            if e.op == "neg":
                E("push", 0); self.expr(e.a); E("sub")
            else:
                self._truth(e.a, invert=True)
        elif isinstance(e, Sel):
            lb, le = self.label(), self.label()
            self.expr(e.cond); E("jz", lb)
            self.expr(e.a); E("jump", le)
            E("label", lb); self.expr(e.b)
            E("label", le)
        elif isinstance(e, Bin):
            self._bin(e)
        else:
            raise TypeError(e)

    def _truth(self, e: Expr, invert: bool = False) -> None:
        """Push 1 if e != 0 else 0 (inverted when invert)."""
        lz, le = self.label(), self.label()
        self.expr(e)
        self.emit("jz", lz)
        self.emit("push", 0 if invert else 1); self.emit("jump", le)
        self.emit("label", lz); self.emit("push", 1 if invert else 0)
        self.emit("label", le)

    def _bin(self, e: Bin) -> None:
        E, op = self.emit, e.op
        if op in ("add", "sub", "mul"):
            self.expr(e.a); self.expr(e.b); E(op)
        elif op == "udiv":
            self.expr(e.a); self.expr(e.b); E("div")
        elif op == "umod":
            self.expr(e.a); self.expr(e.b); E("mod")
        elif op in ("eq", "ne"):
            lt, le = self.label(), self.label()
            self.expr(e.a); self.expr(e.b); E("sub"); E("jz", lt)
            E("push", 1 if op == "ne" else 0); E("jump", le)
            E("label", lt); E("push", 0 if op == "ne" else 1)
            E("label", le)
        elif op in ("lt", "gt", "le", "ge"):
            # lt: a - b < 0 ; gt: b - a < 0 ; le = not gt ; ge = not lt
            first, second = (e.a, e.b) if op in ("lt", "ge") else (e.b, e.a)
            yes = 1 if op in ("lt", "gt") else 0
            ln, le = self.label(), self.label()
            self.expr(first); self.expr(second); E("sub"); E("jn", ln)
            E("push", 1 - yes); E("jump", le)
            E("label", ln); E("push", yes)
            E("label", le)
        elif op == "and":
            l0, le = self.label(), self.label()
            self.expr(e.a); E("jz", l0)
            self.expr(e.b); E("jz", l0)
            E("push", 1); E("jump", le)
            E("label", l0); E("push", 0)
            E("label", le)
        elif op == "or":
            lb, l0, le = self.label(), self.label(), self.label()
            self.expr(e.a); E("jz", lb)
            E("push", 1); E("jump", le)
            E("label", lb); self.expr(e.b); E("jz", l0)
            E("push", 1); E("jump", le)
            E("label", l0); E("push", 0)
            E("label", le)
        else:
            raise ValueError(op)

    # ---------------------------------------------------------------- stmts
    def block(self, stmts: List[Stmt]) -> None:
        E = self.emit
        for s in stmts:
            if isinstance(s, Set):
                E("push", self.addr[s.var]); self.expr(s.expr); E("store")
            elif isinstance(s, Store):
                E("push", self.base[s.arr]); self.expr(s.index); E("add"); self.expr(s.expr); E("store")
            elif isinstance(s, If):
                lelse, lend = self.label(), self.label()
                self.expr(s.cond); E("jz", lelse)
                self.block(s.then); E("jump", lend)
                E("label", lelse); self.block(s.other)
                E("label", lend)
            elif isinstance(s, While):
                ltop, lend = self.label(), self.label()
                E("label", ltop); self.expr(s.cond); E("jz", lend)
                self.block(s.body); E("jump", ltop)
                E("label", lend)
            elif isinstance(s, ReadChar):
                E("push", self.addr[s.var]); E("read_char")
            elif isinstance(s, PrintChar):
                self.expr(s.expr); E("out_char")
            elif isinstance(s, PrintInt):
                self.expr(s.expr); E("out_num")
            else:
                raise TypeError(s)

    def compile(self) -> str:
        self.block(self.prog.body)
        self.emit("end")
        return assemble(self.code)


def compile_ws(prog: Program) -> str:
    return WSCompiler(prog).compile()
