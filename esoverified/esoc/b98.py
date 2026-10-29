"""IR -> Befunge-98 that runs on the official interpreter (and on the spec dialect).

Layout
------
* Rows ``0..D-1`` hold data at columns ``1..W``; cell ``(0,0)`` is ``v`` and the rest of
  column 0 in those rows is empty, so the IP falls straight into the first code row.
* Every basic block is one row starting with ``>`` in column 0. A block ends with an
  absolute jump: push ``(dx, dy)`` = (target - here) and execute ``x``; the IP lands on
  the target row's ``>``. A conditional jump computes ``dy`` from the condition.

Storage
-------
The official interpreter keeps only a byte per fungespace cell (``p`` stores
``chr(v % 256)``), so each value takes ``K`` cells holding ``v + 2**(8K-1)`` in base 256
(little-endian). ``K`` comes from the program's ``max_value``. Division is only used on
non-negative operands below 2**53, where the official ``int(a / b)`` is exact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .ir import Bin, Const, Expr, Idx, If, PrintChar, PrintInt, Program, ReadChar, Sel, Set, Stmt, Store, Un, Var, While
from .lower import lower_print_int

W = 64  # data cells per row


def push_num(n: int) -> str:
    """Befunge code pushing integer n."""
    if n < 0:
        return "0" + push_num(-n) + "-"
    if n < 16:
        return "0123456789abcdef"[n]
    if 32 <= n <= 126:  # ' pushes the next cell's code point literally (even ';' or ' ')
        return "'" + chr(n)
    if n < 32:
        return "f" + push_num(n - 15) + "+"
    q, r = divmod(n, 126)
    code = push_num(q) + "'~*"
    if r:
        code += push_num(r) + "+"
    return code


def with_zero_init(prog: Program) -> Program:
    """Fungespace starts as spaces, not encoded zeros: initialize every scalar and array
    element to 0 before the program body (IR semantics say they start at 0)."""
    zi = "_zero_i"
    body: List[Stmt] = [Set(n, Const(0)) for n in prog.scalars]
    for name, size in prog.arrays.items():
        body.append(Set(zi, Const(0)))
        body.append(While(Bin("lt", Var(zi), Const(size)),
                          [Store(name, Var(zi), Const(0)), Set(zi, Bin("add", Var(zi), Const(1)))]))
    scalars = list(prog.scalars) + ([zi] if prog.arrays else [])
    return Program(prog.name, scalars, dict(prog.arrays), body + list(prog.body), prog.max_value,
                   prog.max_intermediate, dict(prog.array_max), list(prog.byte_vars))


def width_for(max_value: int) -> int:
    k = 1
    while 2 ** (8 * k - 1) <= max_value:
        k += 1
    return max(k, 2)


@dataclass
class Block:
    code: List[str] = field(default_factory=list)
    term: Optional[tuple] = None   # ("goto", t) | ("branch", t_true, t_false) | ("halt",)


class B98Compiler:
    def __init__(self, prog: Program) -> None:
        self.prog = with_zero_init(lower_print_int(prog))
        self.K = width_for(prog.max_value)
        self.BIAS = 2 ** (8 * self.K - 1)
        slot = 0
        self.addr: Dict[str, int] = {}
        for n in self.prog.scalars:
            self.addr[n] = slot
            slot += 1
        self.base: Dict[str, int] = {}
        for n, size in self.prog.arrays.items():
            self.base[n] = slot
            slot += size
        self.cells = slot * self.K
        self.D = max(1, -(-self.cells // W))
        self.blocks: List[Block] = [Block()]

    # ---------------------------------------------------------------- data access
    @staticmethod
    def _xy(cell: int) -> str:
        return push_num(1 + cell % W) + push_num(cell // W)

    def _coords_from_stack(self) -> str:
        # stack: [c]  ->  [x, y]
        return ":" + push_num(W) + "%1+\\" + push_num(W) + "/"

    def _load_static(self, slot: int) -> str:
        K = self.K
        parts = []
        for j in reversed(range(K)):
            if j != K - 1:
                parts.append(push_num(256) + "*")
            parts.append(self._xy(slot * K + j) + "g")
            if j != K - 1:
                parts.append("+")
        parts.append(push_num(self.BIAS) + "-")
        return "".join(parts)

    def _cell_index(self, arr: str, idx: Expr, j: int) -> str:
        # pushes (base + idx) * K + j, then converts to coordinates
        return (self.expr(idx) + push_num(self.base[arr]) + "+" + push_num(self.K) + "*" +
                (push_num(j) + "+" if j else "") + self._coords_from_stack())

    def _load_dynamic(self, arr: str, idx: Expr) -> str:
        K = self.K
        parts = []
        for j in reversed(range(K)):
            if j != K - 1:
                parts.append(push_num(256) + "*")
            parts.append(self._cell_index(arr, idx, j) + "g")
            if j != K - 1:
                parts.append("+")
        parts.append(push_num(self.BIAS) + "-")
        return "".join(parts)

    def _store_bytes(self, coords_for_j) -> str:
        # stack: [v]  -> stores v, leaves nothing
        parts = [push_num(self.BIAS) + "+"]
        for j in range(self.K):
            parts.append(":" + push_num(256) + "%" + coords_for_j(j) + "p")
            if j != self.K - 1:
                parts.append(push_num(256) + "/")
        parts.append("$")
        return "".join(parts)

    # ---------------------------------------------------------------- expressions
    def expr(self, e: Expr) -> str:
        if isinstance(e, Const):
            return push_num(e.value)
        if isinstance(e, Var):
            return self._load_static(self.addr[e.name])
        if isinstance(e, Idx):
            return self._load_dynamic(e.arr, e.index)
        if isinstance(e, Un):
            return ("0" + self.expr(e.a) + "-") if e.op == "neg" else (self.expr(e.a) + "!")
        if isinstance(e, Sel):
            # c01 * (a - b) + b
            return self.expr(e.cond) + "!!" + self.expr(e.a) + self.expr(e.b) + "-*" + self.expr(e.b) + "+"
        if isinstance(e, Bin):
            a, b, op = e.a, e.b, e.op
            if op == "add": return self.expr(a) + self.expr(b) + "+"
            if op == "sub": return self.expr(a) + self.expr(b) + "-"
            if op == "mul": return self.expr(a) + self.expr(b) + "*"
            if op == "udiv": return self.expr(a) + self.expr(b) + "/"
            if op == "umod": return self.expr(a) + self.expr(b) + "%"
            if op == "gt": return self.expr(a) + self.expr(b) + "`"
            if op == "lt": return self.expr(b) + self.expr(a) + "`"
            if op == "le": return self.expr(a) + self.expr(b) + "`!"
            if op == "ge": return self.expr(b) + self.expr(a) + "`!"
            if op == "eq": return self.expr(a) + self.expr(b) + "-!"
            if op == "ne": return self.expr(a) + self.expr(b) + "-!!"
            if op == "and": return self.expr(a) + "!!" + self.expr(b) + "!!*"
            if op == "or": return self.expr(a) + "!!" + self.expr(b) + "!!+!!"
        raise TypeError(e)

    # ---------------------------------------------------------------- statements -> blocks
    def new_block(self) -> int:
        self.blocks.append(Block())
        return len(self.blocks) - 1

    def stmts(self, ss: List[Stmt], cur: int) -> int:
        for s in ss:
            B = self.blocks[cur]
            if isinstance(s, Set):
                B.code.append(self.expr(s.expr) + self._store_bytes(
                    lambda j, slot=self.addr[s.var]: self._xy(slot * self.K + j)))
            elif isinstance(s, Store):
                B.code.append(self.expr(s.expr) + self._store_bytes(
                    lambda j, arr=s.arr, idx=s.index: self._cell_index(arr, idx, j)))
            elif isinstance(s, ReadChar):
                B.code.append("~" + self._store_bytes(lambda j, slot=self.addr[s.var]: self._xy(slot * self.K + j)))
            elif isinstance(s, PrintChar):
                B.code.append(self.expr(s.expr) + ",")
            elif isinstance(s, If):
                B.code.append(self.expr(s.cond))
                t, f, join = self.new_block(), self.new_block(), self.new_block()
                B.term = ("branch", t, f)
                self.blocks[self.stmts(s.then, t)].term = ("goto", join)
                self.blocks[self.stmts(s.other, f)].term = ("goto", join)
                cur = join
            elif isinstance(s, While):
                head, body, done = self.new_block(), self.new_block(), self.new_block()
                B.term = ("goto", head)
                self.blocks[head].code.append(self.expr(s.cond))
                self.blocks[head].term = ("branch", body, done)
                self.blocks[self.stmts(s.body, body)].term = ("goto", head)
                cur = done
            elif isinstance(s, PrintInt):  # pragma: no cover - lowered earlier
                raise AssertionError("print_int should have been lowered")
            else:
                raise TypeError(s)
        return cur

    # ---------------------------------------------------------------- layout
    def _jump(self, prefix: str, row: int, term: tuple) -> str:
        if term[0] == "halt":
            return prefix + "@"
        target_row = lambda b: self.D + b  # noqa: E731
        col = len(prefix) + 4
        for _ in range(50):
            dx = -col
            if term[0] == "goto":
                code = push_num(dx) + push_num(target_row(term[1]) - row) + "x"
            else:
                t, f = target_row(term[1]), target_row(term[2])
                code = "!!" + push_num(t - f) + "*" + push_num(f - row) + "+" + push_num(dx) + "\\x"
            new_col = len(prefix) + len(code) - 1
            if new_col == col:
                return prefix + code
            if new_col < col:  # pad so the x lands exactly where dx says
                return prefix + " " * (col - new_col) + code
            col = new_col
        raise RuntimeError("jump layout did not converge")

    def compile(self) -> str:
        last = self.stmts(self.prog.body, 0)
        self.blocks[last].term = ("halt",)
        for b in self.blocks:
            if b.term is None:  # unreachable empty join blocks
                b.term = ("halt",)
        rows = []
        for i in range(self.D):
            rows.append(("v" if i == 0 else " ") + " " * W)
        for i, b in enumerate(self.blocks):
            rows.append(self._jump(">" + "".join(b.code), self.D + i, b.term))
        return "\n".join(rows) + "\n"


def compile_b98(prog: Program) -> str:
    return B98Compiler(prog).compile()
