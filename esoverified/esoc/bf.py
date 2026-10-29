"""IR -> Brainfuck (8-bit wrapping cells, EOF reads 0).

This is the paper's "metaprogramming" strategy as a compiler: a Python object tracks the
tape pointer, allocates cells, and emits Brainfuck for named, tested primitives.

Numbers
-------
Every value is a signed decimal block ``[sign, d0, d1, ..., d(D-1)]`` (little-endian
digits, sign 1 = negative, zero always has sign 0). ``D`` comes from the program's
``max_intermediate``. Addition, subtraction, comparison, multiplication and long
division work digit by digit; division by a small constant (2..25) and by 10 have
fast paths.

Arrays
------
An array is a row of records ``[walker | element]``. To reach index ``i`` a *walker*
(two copies of ``i`` as decimal counters, scratch cells and, for writes, the payload)
moves record by record while counting down, then walks back. Access costs grow with
the index, which is the fundamental price of random access on a Brainfuck tape.

Input
-----
``,`` stores 0 at end of input, so a read 0 means EOF (-1 in the IR). Inputs never
contain NUL characters.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Dict, Iterator, List, Optional, Tuple

from .ir import (Arr, Bin, Const, Expr, Idx, If, PrintChar, PrintInt, Program, ReadChar, Sel, Set, Stmt, Store,
                 Un, Var, While)


# ===================================================================== emitter

class Emitter:
    def __init__(self, trick: int = -1) -> None:
        self.code: List[str] = []
        self.pos = 0
        # 4 contiguous zero cells [f, p, m, z] reserved for ge_const's O(1) zero test
        self.trick = trick

    def at(self, c: int) -> None:
        d = c - self.pos
        if d > 0:
            self.code.append(">" * d)
        elif d < 0:
            self.code.append("<" * (-d))
        self.pos = c

    def raw(self, s: str) -> None:
        self.code.append(s)

    def add(self, c: int, k: int) -> None:
        k %= 256
        if not k:
            return
        self.at(c)
        self.code.append("+" * k if k <= 128 else "-" * (256 - k))

    def clear(self, c: int) -> None:
        self.at(c)
        self.raw("[-]")

    @contextmanager
    def loop(self, c: int) -> Iterator[None]:
        self.at(c)
        self.raw("[")
        yield
        self.at(c)
        self.raw("]")

    def move(self, src: int, dsts: List[Tuple[int, int]]) -> None:
        """dst += f * src for each (dst, f); src becomes 0."""
        with self.loop(src):
            self.add(src, -1)
            for d, f in dsts:
                self.add(d, f)

    def copy(self, src: int, dst: int, tmp: int) -> None:
        """dst += src (tmp must be 0; stays 0)."""
        self.move(src, [(dst, 1), (tmp, 1)])
        self.move(tmp, [(src, 1)])

    def text(self) -> str:
        return "".join(self.code)


# ===================================================================== byte routines
# Every routine takes the cells it may use; scratch cells must be 0 on entry and are 0 on exit.

def set_flag(e: Emitter, c: int, v: int = 1) -> None:
    e.clear(c)
    e.add(c, v)


def dec_both(e: Emitter, x: int, y: int, k: int, t1: int, t2: int, t3: int) -> None:
    """Decrement x and y together until one is 0 (x, y small bytes)."""
    e.add(k, 1)
    with e.loop(k):
        e.add(k, -1)
        e.copy(x, t1, t2)
        with e.loop(t1):
            e.clear(t1)
            e.copy(y, t2, t3)
            with e.loop(t2):
                e.clear(t2)
                e.add(x, -1)
                e.add(y, -1)
                e.add(k, 1)


def ge_const(e: Emitter, v: int, c: int, out: int, s: List[int]) -> None:
    """out = 1 if byte v >= c else 0 (v unchanged), in O(v + c) steps.

    Copies v into p, then c times: if p != 0 decrement it, else raise flag f. The
    zero test is the classic layout trick on contiguous cells [f, p, m=1, z=0]:
    ``[->-]>`` leaves the pointer on z when p was nonzero and on m when it was zero,
    so the following ``[...]`` runs only in the zero case. f = 1 means v < c.
    Uses s[0..1] as scratch and the emitter's reserved trick cells."""
    if c <= 0:
        set_flag(e, out, 1)
        return
    f = e.trick
    if f < 0:
        raise RuntimeError("ge_const needs emitter.trick cells")
    p, m = f + 1, f + 2
    e.copy(v, p, s[0])
    e.add(m, 1)
    b = s[1]
    e.add(b, c)
    with e.loop(b):
        e.add(b, -1)
        e.at(p)
        e.raw("[->-]>[<<[-]+>>->]<+<")
        e.pos = p
    e.clear(p)
    e.clear(m)
    set_flag(e, out, 1)
    with e.loop(f):
        e.clear(f)
        e.clear(out)


def eq_const(e: Emitter, v: int, c: int, out: int, t1: int, t2: int) -> None:
    """out = 1 if byte v == c."""
    e.copy(v, t1, t2)
    e.add(t1, -c)
    set_flag(e, out, 1)
    with e.loop(t1):
        e.clear(t1)
        e.clear(out)


def nz_cells(e: Emitter, cells: List[int], out: int, t1: int, t2: int) -> None:
    """out = 1 if any cell is nonzero."""
    e.clear(out)
    for d in cells:
        e.copy(d, t1, t2)
        with e.loop(t1):
            e.clear(t1)
            set_flag(e, out, 1)


def if_else(e: Emitter, f: int, t: int, then: Callable[[], None], other: Callable[[], None]) -> None:
    """Consumes flag f (0/1); t is a zero scratch cell."""
    e.add(t, 1)
    with e.loop(f):
        then()
        e.clear(f)
        e.clear(t)
    with e.loop(t):
        other()
        e.add(t, -1)


def bcd_dec(e: Emitter, digits: List[int], s: List[int]) -> None:
    """Decrement a nonnegative decimal counter by 1 (must be > 0). Uses s[0..5]."""
    b, t, t3, z, x, x2 = s[:6]
    e.add(b, 1)
    for d in digits:
        e.copy(b, t, t3)
        with e.loop(t):
            e.clear(t)
            set_flag(e, z, 1)
            e.copy(d, x, x2)
            with e.loop(x):
                e.clear(x)
                e.clear(z)
            if_else(e, z, x, lambda d=d: e.add(d, 9), lambda d=d: (e.add(d, -1), e.clear(b)))
    e.clear(b)


# ===================================================================== compiler

@dataclass
class Block:
    base: int
    D: int

    @property
    def sign(self) -> int:
        return self.base

    def digit(self, k: int) -> int:
        return self.base + 1 + k

    @property
    def digits(self) -> List[int]:
        return [self.base + 1 + k for k in range(self.D)]

    @property
    def cells(self) -> List[int]:
        return [self.base + k for k in range(self.D + 1)]


@dataclass
class ArrayLayout:
    name: str
    base: int
    size: int
    DI: int        # index digits
    B: int         # element digits
    R: int         # record size

    # walker offsets inside a record
    F = 0
    S = 1          # 6 scratch cells: 1..6

    @property
    def C1(self) -> int: return 7
    @property
    def C2(self) -> int: return 7 + self.DI
    @property
    def PAY(self) -> int: return 7 + 2 * self.DI
    @property
    def ELEM(self) -> int: return 7 + 2 * self.DI + self.B + 1
    @property
    def walker_size(self) -> int: return self.ELEM


SCRATCH = 24


class BFCompiler:
    def __init__(self, prog: Program, temp_slots: Optional[int] = None, flag_slots: Optional[int] = None) -> None:
        from .simplify import simplify
        self.prog = simplify(prog)
        prog = self.prog
        self.D = max(3, len(str(prog.max_inter)))
        self.e = Emitter()
        # Layout: [byte variables][scratch][flags][temporaries][variables][arrays].
        # Copying a byte costs (value x distance) steps, so characters live right next to
        # the scratch cells; flag and temporary counts are measured by a first pass.
        self.bytes: Dict[str, int] = {}   # byte variables: one cell, 0 encodes -1 (EOF)
        nxt = 0
        for n in prog.scalars:
            if n in prog.byte_vars:
                self.bytes[n] = nxt
                nxt += 1
        self.e.trick = nxt                # 4 reserved cells for ge_const
        nxt += 4
        self.free_scratch = list(range(nxt + SCRATCH - 1, nxt - 1, -1))
        nxt += SCRATCH
        self.flag_slots = flag_slots if flag_slots is not None else 1024
        self.flag_base = nxt
        self.free_flags: List[int] = list(range(nxt + self.flag_slots - 1, nxt - 1, -1))
        self.flags_used = 0
        nxt += self.flag_slots
        self.temp_slots = temp_slots if temp_slots is not None else 4096
        self.temp_base = nxt
        nxt += self.temp_slots * (self.D + 1)
        self.vars: Dict[str, Block] = {}
        for n in prog.scalars:
            if n not in prog.byte_vars:
                self.vars[n] = Block(nxt, self.D)
                nxt += self.D + 1
        self.arrays: Dict[str, ArrayLayout] = {}
        for n, size in prog.arrays.items():
            emax = prog.array_max.get(n, prog.max_value)
            B = max(1, len(str(emax)))
            DI = max(1, len(str(size - 1)))
            if DI > self.D:
                raise OverflowError(f"array {n} index needs {DI} digits > D={self.D}")
            lay = ArrayLayout(n, nxt, size, DI, B, 0)
            lay.R = lay.ELEM + B + 1
            self.arrays[n] = lay
            nxt += lay.R * size + lay.R
        self.free_blocks: List[int] = []
        self.next_temp = self.temp_base
        self.max_temp = self.temp_base

    # ------------------------------------------------------------ allocation
    def sc(self) -> int:
        return self.free_scratch.pop()

    def release(self, *cells: int) -> None:
        self.free_scratch.extend(cells)

    @contextmanager
    def scratch(self, n: int) -> Iterator[List[int]]:
        cells = [self.sc() for _ in range(n)]
        try:
            yield cells
        finally:
            self.release(*reversed(cells))

    def temp_block(self) -> Block:
        if self.free_blocks:
            return Block(self.free_blocks.pop(), self.D)
        b = Block(self.next_temp, self.D)
        self.next_temp += self.D + 1
        if self.next_temp > self.temp_base + self.temp_slots * (self.D + 1):
            raise OverflowError("out of temporary slots")
        return b

    def free(self, b: Block, is_temp: bool) -> None:
        if is_temp:
            for c in b.cells:
                self.e.clear(c)
            self.free_blocks.append(b.base)

    # ------------------------------------------------------------ block primitives
    def b_clear(self, b: Block) -> None:
        for c in b.cells:
            self.e.clear(c)

    def b_copy(self, a: Block, r: Block) -> None:
        self.b_clear(r)
        with self.scratch(1) as (t,):
            for ca, cr in zip(a.cells, r.cells):
                self.e.copy(ca, cr, t)

    def b_move(self, a: Block, r: Block) -> None:
        self.b_clear(r)
        for ca, cr in zip(a.cells, r.cells):
            self.e.move(ca, [(cr, 1)])

    def b_set(self, r: Block, v: int) -> None:
        self.b_clear(r)
        s = str(abs(v))
        if len(s) > self.D:
            raise OverflowError(f"constant {v} needs more than {self.D} digits")
        if v < 0:
            self.e.add(r.sign, 1)
        for k, ch in enumerate(reversed(s)):
            self.e.add(r.digit(k), int(ch))

    def b_nz(self, a: Block, out: int) -> None:
        with self.scratch(2) as (t1, t2):
            nz_cells(self.e, a.digits, out, t1, t2)

    def normalize_sign(self, r: Block) -> None:
        with self.scratch(2) as (nz, z):
            self.b_nz(r, nz)
            set_flag(self.e, z, 1)
            with self.e.loop(nz):
                self.e.clear(nz)
                self.e.clear(z)
            with self.e.loop(z):
                self.e.clear(z)
                self.e.clear(r.sign)

    def mag_cmp(self, a: Block, b: Block, lt: int, gt: int) -> None:
        e = self.e
        e.clear(lt)
        e.clear(gt)
        with self.scratch(8) as (u, t, x, y, k, t1, t2, t3):
            e.add(u, 1)
            for i in reversed(range(self.D)):
                e.copy(u, t, t1)
                with e.loop(t):
                    e.clear(t)
                    e.copy(a.digit(i), x, t1)
                    e.copy(b.digit(i), y, t1)
                    dec_both(e, x, y, k, t1, t2, t3)
                    with e.loop(x):
                        e.clear(x)
                        set_flag(e, gt, 1)
                        e.clear(u)
                    with e.loop(y):
                        e.clear(y)
                        set_flag(e, lt, 1)
                        e.clear(u)
            e.clear(u)

    def mag_add(self, a: Block, b: Block, r: Block) -> None:
        e = self.e
        for c in r.digits:
            e.clear(c)
        with self.scratch(7) as (carry, g, *s):
            for i in range(self.D):
                rk = r.digit(i)
                e.copy(a.digit(i), rk, s[0])
                e.copy(b.digit(i), rk, s[0])
                e.move(carry, [(rk, 1)])
                ge_const(e, rk, 10, g, s)
                with e.loop(g):
                    e.clear(g)
                    e.add(rk, -10)
                    e.add(carry, 1)
            e.clear(carry)

    def mag_sub(self, a: Block, b: Block, r: Block) -> None:
        """r = |a| - |b| (requires |a| >= |b|)."""
        e = self.e
        for c in r.digits:
            e.clear(c)
        with self.scratch(8) as (br, g, t, *s):
            for i in range(self.D):
                rk = r.digit(i)
                e.copy(a.digit(i), rk, s[0])
                e.add(rk, 10)
                e.copy(b.digit(i), t, s[0])
                e.move(t, [(rk, -1)])
                e.move(br, [(rk, -1)])
                ge_const(e, rk, 10, g, s)
                if_else(e, g, t, lambda rk=rk: e.add(rk, -10), lambda: e.add(br, 1))
            e.clear(br)

    def b_add(self, a: Block, b: Block, r: Block, negate_b: bool = False) -> None:
        """r = a + b (or a - b). r must not alias a or b."""
        e = self.e
        with self.scratch(7) as (sb, diff, tt, lt, gt, t2, tf):
            e.copy(b.sign, sb, tt)
            if negate_b:  # flip b's sign only if b is nonzero
                with self.scratch(1) as (nz,):
                    self.b_nz(b, nz)
                    with e.loop(nz):
                        e.clear(nz)
                        # sb = 1 - sb
                        e.move(sb, [(tt, 1)])
                        e.add(sb, 1)
                        e.move(tt, [(sb, -1)])
            # diff = (sign a != sb)
            e.copy(a.sign, tt, t2)
            e.copy(sb, tt, t2)
            eq_const(e, tt, 1, diff, t2, lt)
            e.clear(tt)

            def same():
                self.mag_add(a, b, r)
                e.clear(r.sign)
                e.copy(a.sign, r.sign, tt)

            def different():
                self.mag_cmp(a, b, lt, gt)
                e.clear(gt)

                def b_bigger():
                    self.mag_sub(b, a, r)
                    e.clear(r.sign)
                    e.copy(sb, r.sign, tt)

                def a_bigger():
                    self.mag_sub(a, b, r)
                    e.clear(r.sign)
                    e.copy(a.sign, r.sign, tt)
                if_else(e, lt, t2, b_bigger, a_bigger)

            if_else(e, diff, tf, different, same)
            e.clear(sb)
        self.normalize_sign(r)

    def b_neg(self, a: Block, r: Block) -> None:
        e = self.e
        self.b_copy(a, r)
        with self.scratch(2) as (nz, t):
            self.b_nz(r, nz)
            with e.loop(nz):
                e.clear(nz)
                e.move(r.sign, [(t, 1)])
                e.add(r.sign, 1)
                e.move(t, [(r.sign, -1)])

    def b_mul(self, a: Block, b: Block, r: Block) -> None:
        e = self.e
        self.b_clear(r)
        part = self.temp_block()
        acc = self.temp_block()
        with self.scratch(9) as (carry, m, x, g, *s):
            for j in range(self.D):
                for c in part.digits:
                    e.clear(c)
                for k in range(self.D - j):
                    e.copy(b.digit(j), m, s[0])
                    with e.loop(m):
                        e.add(m, -1)
                        e.copy(a.digit(k), x, s[0])
                    e.move(carry, [(x, 1)])
                    ge_const(e, x, 10, g, s)
                    with e.loop(g):
                        e.clear(g)
                        e.add(x, -10)
                        e.add(carry, 1)
                        ge_const(e, x, 10, g, s)
                    e.move(x, [(part.digit(j + k), 1)])
                e.clear(carry)
                self.mag_add(r, part, acc)
                for cr, ca in zip(r.digits, acc.digits):
                    e.clear(cr)
                    e.move(ca, [(cr, 1)])
            # sign = sign a xor sign b
            e.copy(a.sign, x, s[0])
            e.copy(b.sign, x, s[0])
            eq_const(e, x, 1, r.sign, s[0], s[1])
            e.clear(x)
        self.free(part, True)
        self.free(acc, True)
        self.normalize_sign(r)

    def b_divmod(self, a: Block, b: Block, q: Optional[Block], rem: Block) -> None:
        """Unsigned long division: q = a // b, rem = a % b (a >= 0, b > 0)."""
        e = self.e
        if q is not None:
            self.b_clear(q)
        self.b_clear(rem)
        t = self.temp_block()
        with self.scratch(5) as (qd, ge, lt, gt, tt):
            for k in reversed(range(self.D)):
                e.clear(rem.digit(self.D - 1))
                for i in reversed(range(1, self.D)):
                    e.move(rem.digit(i - 1), [(rem.digit(i), 1)])
                e.copy(a.digit(k), rem.digit(0), tt)

                def compute_ge():
                    self.mag_cmp(rem, b, lt, gt)
                    e.clear(gt)
                    set_flag(e, ge, 1)
                    with e.loop(lt):
                        e.clear(lt)
                        e.clear(ge)

                compute_ge()
                with e.loop(ge):
                    e.clear(ge)
                    self.mag_sub(rem, b, t)
                    for cr, ct in zip(rem.digits, t.digits):
                        e.clear(cr)
                        e.move(ct, [(cr, 1)])
                    e.add(qd, 1)
                    compute_ge()
                if q is not None:
                    e.move(qd, [(q.digit(k), 1)])
                else:
                    e.clear(qd)
        self.free(t, True)

    def b_divmod_const(self, a: Block, c: int, q: Optional[Block], rem: Optional[Block]) -> None:
        """a // c and a % c for a >= 0 and 1 <= c <= 25."""
        e = self.e
        if q is not None:
            self.b_clear(q)
        if rem is not None:
            self.b_clear(rem)
        if c == 1:
            if q is not None:
                self.b_copy(a, q)
            return
        if c == 10:
            with self.scratch(1) as (t,):
                if q is not None:
                    for k in range(1, self.D):
                        e.copy(a.digit(k), q.digit(k - 1), t)
                if rem is not None:
                    e.copy(a.digit(0), rem.digit(0), t)
            return
        with self.scratch(9) as (r, x, qd, g, *s):
            for k in reversed(range(self.D)):
                e.move(r, [(x, 10)])
                e.copy(a.digit(k), x, s[0])
                ge_const(e, x, c, g, s)
                with e.loop(g):
                    e.clear(g)
                    e.add(x, -c)
                    e.add(qd, 1)
                    ge_const(e, x, c, g, s)
                if q is not None:
                    e.move(qd, [(q.digit(k), 1)])
                else:
                    e.clear(qd)
                e.move(x, [(r, 1)])
            if rem is not None:
                # r < 25: split into two digits
                ge_const(e, r, 10, g, s)
                with e.loop(g):
                    e.clear(g)
                    e.add(r, -10)
                    e.add(rem.digit(1), 1)
                    ge_const(e, r, 10, g, s)
                e.move(r, [(rem.digit(0), 1)])
            else:
                e.clear(r)

    def b_from_byte(self, x: int, r: Block) -> None:
        """r = byte x (x consumed)."""
        e = self.e
        self.b_clear(r)
        with self.scratch(7) as (g, *s):
            for k in range(3):
                if k == 2:
                    e.move(x, [(r.digit(2), 1)])
                    break
                ge_const(e, x, 10, g, s)
                q = s[5]
                with e.loop(g):
                    e.clear(g)
                    e.add(x, -10)
                    e.add(q, 1)
                    ge_const(e, x, 10, g, s)
                e.move(x, [(r.digit(k), 1)])
                e.move(q, [(x, 1)])

    def b_to_byte(self, a: Block, out: int) -> None:
        """out = (d0 + 10 d1 + 100 d2) mod 256, i.e. a mod 256 for 0 <= a < 1000."""
        e = self.e
        with self.scratch(2) as (t, t2):
            for k, f in ((0, 1), (1, 10), (2, 100)):
                e.copy(a.digit(k), t, t2)
                e.move(t, [(out, f)])

    # ------------------------------------------------------------ comparisons
    def cmp_flag(self, op: str, a: Block, b: Block, out: int) -> None:
        """out = (a op b) for signed blocks, op in lt gt le ge eq ne."""
        e = self.e
        if op in ("gt", "le"):
            self.cmp_flag("lt" if op == "gt" else "ge", b, a, out)
            return
        with self.scratch(6) as (lt, gt, sa, sb, t, t2):
            self.mag_cmp(a, b, lt, gt)
            e.copy(a.sign, sa, t)
            e.copy(b.sign, sb, t)
            e.clear(out)
            if op in ("eq", "ne"):
                # values differ iff magnitudes differ or signs differ (zero always has sign 0)
                e.move(lt, [(gt, 1)])         # gt = 1 if magnitudes differ
                e.move(sa, [(t, 1)])
                e.move(sb, [(t, -1)])         # t = sa - sb: nonzero iff signs differ
                with e.loop(t):
                    e.clear(t)
                    set_flag(e, gt, 1)
                if op == "eq":
                    set_flag(e, out, 1)
                    with e.loop(gt):
                        e.clear(gt)
                        e.clear(out)
                else:
                    with e.loop(gt):
                        e.clear(gt)
                        set_flag(e, out, 1)
                return
            # lt / ge
            def neg_a():
                def both_neg():  # a < b iff |a| > |b|
                    e.clear(lt)
                    e.move(gt, [(out, 1)])
                def a_neg_b_pos():
                    e.clear(lt)
                    e.clear(gt)
                    set_flag(e, out, 1)
                if_else(e, sb, t2, both_neg, a_neg_b_pos)

            def pos_a():
                def a_pos_b_neg():
                    e.clear(lt)
                    e.clear(gt)
                def both_pos():
                    e.clear(gt)
                    e.move(lt, [(out, 1)])
                if_else(e, sb, t2, a_pos_b_neg, both_pos)

            if_else(e, sa, t, neg_a, pos_a)
            if op == "ge":
                e.move(out, [(t, 1)])
                set_flag(e, out, 1)
                with e.loop(t):
                    e.clear(t)
                    e.clear(out)

    # ------------------------------------------------------------ expressions
    def expr(self, x: Expr) -> Tuple[Block, bool]:
        """Evaluate into a block. Returns (block, is_temp)."""
        e = self.e
        if isinstance(x, Var):
            if x.name in self.bytes:
                r = self.temp_block()
                self.byte_to_block(self.bytes[x.name], r)
                return r, True
            return self.vars[x.name], False
        if isinstance(x, Const):
            r = self.temp_block()
            self.b_set(r, x.value)
            return r, True
        if isinstance(x, Idx):
            ib, it = self.expr(x.index)
            r = self.temp_block()
            self.array_read(x.arr, ib, r)
            self.free(ib, it)
            return r, True
        if isinstance(x, Un):
            a, at = self.expr(x.a)
            r = self.temp_block()
            if x.op == "neg":
                self.b_neg(a, r)
            else:
                self.free(a, at)
                self.free_blocks.append(r.base)
                return self._flag_block(lambda f: self.flag_expr(x, f))
            self.free(a, at)
            return r, True
        if isinstance(x, Sel):
            c, ct = self.expr(x.cond)
            r = self.temp_block()
            f, t = self._flag_cell(), self._flag_cell()   # held across nested evaluation
            self.b_nz(c, f)
            self.free(c, ct)

            def take(sub):
                v, vt = self.expr(sub)
                self.b_copy(v, r)
                self.free(v, vt)
            if_else(e, f, t, lambda: take(x.a), lambda: take(x.b))
            self._release_flag(t)
            self._release_flag(f)
            return r, True
        if isinstance(x, Bin):
            return self.binop(x)
        raise TypeError(x)

    _MIRROR = {"lt": "gt", "gt": "lt", "le": "ge", "ge": "le", "eq": "eq", "ne": "ne"}

    def _is_byte(self, x: Expr) -> bool:
        return isinstance(x, Var) and x.name in self.bytes

    def binop(self, x: Bin) -> Tuple[Block, bool]:
        e, op = self.e, x.op
        a_, b_ = x.a, x.b
        if op in self._MIRROR and isinstance(a_, Const) and not isinstance(b_, Const):
            a_, b_, op = b_, a_, self._MIRROR[op]
        if op in self._CMP or op in ("and", "or"):
            return self._flag_block(lambda f: self.flag_expr(x, f))
        if op in ("add", "sub"):
            c_ = None
            if isinstance(b_, Const):
                c_, other = (b_.value if op == "add" else -b_.value), a_
            elif isinstance(a_, Const) and op == "add":
                c_, other = a_.value, b_
            if c_ is not None and abs(c_) < 10 ** min(self.D, 6):
                a, at = self.expr(other)
                r = self.temp_block()
                self.add_small(a, c_, r)
                self.free(a, at)
                return r, True
        if op == "mul":
            if isinstance(a_, Const) and not isinstance(b_, Const):
                a_, b_ = b_, a_
            if isinstance(b_, Const) and 2 <= b_.value <= 10:
                a, at = self.expr(a_)
                r = self.temp_block()
                self.mul_small(a, b_.value, r)
                self.free(a, at)
                return r, True
        if op in ("udiv", "umod") and isinstance(x.b, Const) and 1 <= x.b.value <= 25:
            a, at = self.expr(x.a)
            r = self.temp_block()
            if op == "udiv":
                self.b_divmod_const(a, x.b.value, r, None)
            else:
                self.b_divmod_const(a, x.b.value, None, r)
            self.free(a, at)
            return r, True
        a, at = self.expr(x.a)
        b, bt = self.expr(x.b)
        r = self.temp_block()
        if op == "add":
            self.b_add(a, b, r)
        elif op == "sub":
            self.b_add(a, b, r, negate_b=True)
        elif op == "mul":
            self.b_mul(a, b, r)
        elif op == "udiv":
            rem = self.temp_block()
            self.b_divmod(a, b, r, rem)
            self.free(rem, True)
        elif op == "umod":
            self.b_divmod(a, b, None, r)
        elif op in ("lt", "gt", "le", "ge", "eq", "ne"):
            self.b_clear(r)
            with self.scratch(1) as (f,):
                self.cmp_flag(op, a, b, f)
                e.move(f, [(r.digit(0), 1)])
        elif op in ("and", "or"):
            self.b_clear(r)
            with self.scratch(3) as (fa, fb, t):
                self.b_nz(a, fa)
                self.b_nz(b, fb)
                e.move(fb, [(fa, 1)])            # fa in {0,1,2}
                if op == "and":
                    eq_const(e, fa, 2, r.digit(0), t, fb)
                else:
                    with e.loop(fa):
                        e.clear(fa)
                        set_flag(e, r.digit(0), 1)
                e.clear(fa)
        else:
            raise ValueError(op)
        self.free(a, at)
        self.free(b, bt)
        return r, True

    def _flag_block(self, compute) -> Tuple[Block, bool]:
        r = self.temp_block()
        self.b_clear(r)
        with self.scratch(1) as (f,):
            compute(f)
            self.e.move(f, [(r.digit(0), 1)])
        return r, True

    def _fast_compare_flag(self, op: str, a: Expr, b: Expr, f: int) -> bool:
        """Cheap comparisons straight into flag f: byte variable vs constant, byte vs byte
        (in)equality, and any value vs 0. Returns False when no fast path applies."""
        e = self.e
        if self._is_byte(a) and isinstance(b, Const):
            cell, c = self.bytes[a.name], b.value

            def lt_const(cc: int) -> None:  # f = (v < cc)
                if cc <= -1:
                    e.clear(f)
                elif cc > 255:
                    set_flag(e, f, 1)
                else:
                    with self.scratch(5) as sc:
                        ge_const(e, cell, max(cc, 1), f, sc)
                    self._not(f)

            if op in ("eq", "ne"):
                if c == -1 or 1 <= c <= 255:
                    with self.scratch(2) as (t1, t2):
                        eq_const(e, cell, 0 if c == -1 else c, f, t1, t2)
                else:
                    e.clear(f)
                if op == "ne":
                    self._not(f)
            elif op == "lt":
                lt_const(c)
            elif op == "ge":
                lt_const(c)
                self._not(f)
            elif op == "le":
                lt_const(c + 1)
            else:  # gt
                lt_const(c + 1)
                self._not(f)
            return True
        if op in ("eq", "ne") and self._is_byte(a) and self._is_byte(b):
            ca, cb = self.bytes[a.name], self.bytes[b.name]
            with self.scratch(3) as (t, t2, t3):
                e.copy(ca, t, t3)
                e.copy(cb, t2, t3)
                e.move(t2, [(t, -1)])
                set_flag(e, f, 1 if op == "eq" else 0)
                with e.loop(t):
                    e.clear(t)
                    set_flag(e, f, 0 if op == "eq" else 1)
            return True
        if isinstance(b, Const) and b.value == 0 and not self._is_byte(a):
            v, vt = self.expr(a)
            with self.scratch(3) as (nz, t, t3):
                if op in ("eq", "ne"):
                    self.b_nz(v, f)
                    if op == "eq":
                        self._not(f)
                elif op in ("lt", "ge"):
                    e.copy(v.sign, f, t)
                    if op == "ge":
                        self._not(f)
                else:  # gt / le: positive means nonzero and sign 0
                    self.b_nz(v, nz)
                    e.copy(v.sign, t, t3)
                    e.move(t, [(nz, -1)])      # nz - sign is 1 only when positive
                    eq_const(e, nz, 1, f, t, t3)
                    e.clear(nz)
                    if op == "le":
                        self._not(f)
            self.free(v, vt)
            return True
        return False

    def _not(self, f: int) -> None:
        """f = 1 - f for a 0/1 flag."""
        with self.scratch(1) as (t,):
            self.e.move(f, [(t, 1)])
            self.e.add(f, 1)
            self.e.move(t, [(f, -1)])

    def byte_to_block(self, cell: int, r: Block) -> None:
        e = self.e
        with self.scratch(3) as (x, z, t):
            e.copy(cell, x, t)
            set_flag(e, z, 1)
            with self.scratch(1) as (y,):
                e.copy(x, t, y)
                with e.loop(t):
                    e.clear(t)
                    e.clear(z)
            self.b_from_byte(x, r)
            with e.loop(z):
                e.clear(z)
                e.add(r.sign, 1)
                e.add(r.digit(0), 1)

    def _mag_inc(self, r: Block, k: int, c: int, s: List[int], g: int) -> None:
        """Add c (1..9) to digit k of r's magnitude; carry only travels when needed."""
        e = self.e
        if k >= self.D:
            return
        e.add(r.digit(k), c)
        ge_const(e, r.digit(k), 10, g, s)
        with e.loop(g):
            e.clear(g)
            e.add(r.digit(k), -10)
            self._mag_inc(r, k + 1, 1, s, g)

    def _mag_dec(self, r: Block, k: int, c: int, s: List[int], g: int) -> None:
        """Subtract c (1..9) from digit k (the magnitude must stay >= 0)."""
        e = self.e
        if k >= self.D:
            return
        e.add(r.digit(k), 10 - c)          # digit + 10 - c is in [1, 19]
        ge_const(e, r.digit(k), 10, g, s)
        t = self._flag_cell()
        def no_borrow():
            e.add(r.digit(k), -10)
        def borrow():
            self._mag_dec(r, k + 1, 1, s, g)
        if_else(e, g, t, no_borrow, borrow)
        self._release_flag(t)

    def add_small(self, a: Block, c: int, r: Block) -> None:
        """r = a + c for a constant c (|c| < 10**D) without a full signed addition: digits
        of |c| are added or subtracted in place and carries/borrows travel only when needed."""
        e = self.e
        self.b_copy(a, r)
        if c == 0:
            return
        cdig = [int(ch) for ch in reversed(str(abs(c)))]
        if len(cdig) > self.D:
            raise OverflowError(f"constant {c} needs more than {self.D} digits")
        same = self._flag_cell()
        with self.scratch(1) as (t,):
            e.copy(r.sign, same, t)
        if c > 0:            # same direction as the magnitude iff a >= 0
            self._not(same)
        g = self._flag_cell()
        tf = self._flag_cell()

        def grow():
            with self.scratch(5) as sc:
                for k, d in enumerate(cdig):
                    if d:
                        self._mag_inc(r, k, d, sc, g)

        def shrink():
            if len(cdig) == 1:
                big = self._flag_cell()
                with self.scratch(5) as sc:   # |a| >= c iff a higher digit is nonzero or d0 >= c
                    nz_cells(e, r.digits[1:], big, sc[0], sc[1])
                    ge_const(e, r.digit(0), cdig[0], g, sc)
                e.move(g, [(big, 1)])
                with self.scratch(1) as (o,):
                    with e.loop(big):
                        e.clear(big)
                        set_flag(e, o, 1)
                    e.move(o, [(big, 1)])
            else:
                cb = self.temp_block()
                self.b_set(cb, abs(c))
                lt, gt = self._flag_cell(), self._flag_cell()
                self.mag_cmp(r, cb, lt, gt)
                e.clear(gt)
                self._release_flag(gt)
                big = lt
                self._not(big)
            t2 = self._flag_cell()

            def sub_mag():
                with self.scratch(5) as sc:
                    for k, d in enumerate(cdig):
                        if d:
                            self._mag_dec(r, k, d, sc, g)

            def flip():  # |a| < |c|: result is |c| - |a| with the opposite sign
                tmp = self.temp_block()
                cc = self.temp_block()
                self.b_set(cc, abs(c))
                self.mag_sub(cc, r, tmp)
                with self.scratch(1) as (t3,):
                    for cr, ct in zip(r.digits, tmp.digits):
                        e.clear(cr)
                        e.move(ct, [(cr, 1)])
                    e.move(r.sign, [(t3, 1)])
                    e.add(r.sign, 1)
                    e.move(t3, [(r.sign, -1)])
                self.free(cc, True)
                self.free(tmp, True)
            if_else(e, big, t2, sub_mag, flip)
            self._release_flag(t2)
            self._release_flag(big)
            if len(cdig) > 1:
                self.free(cb, True)

        if_else(e, same, tf, grow, shrink)
        for f in (tf, g):
            self._release_flag(f)
        self._release_flag(same)
        self.normalize_sign(r)

    def mul_small(self, a: Block, k: int, r: Block) -> None:
        """r = a * k for 2 <= k <= 10."""
        e = self.e
        self.b_clear(r)
        if k == 10:
            with self.scratch(1) as (t,):
                for i in range(self.D - 1):
                    e.copy(a.digit(i), r.digit(i + 1), t)
                e.copy(a.sign, r.sign, t)
            return
        with self.scratch(9) as (carry, x, g, t, *s):
            for i in range(self.D):
                e.copy(a.digit(i), t, s[0])
                e.move(t, [(x, k)])
                e.move(carry, [(x, 1)])
                ge_const(e, x, 10, g, s)
                with e.loop(g):
                    e.clear(g)
                    e.add(x, -10)
                    e.add(carry, 1)
                    ge_const(e, x, 10, g, s)
                e.move(x, [(r.digit(i), 1)])
            e.clear(carry)
            e.copy(a.sign, r.sign, t)
        self.normalize_sign(r)

    # ------------------------------------------------------------ arrays
    def _walk(self, lay: ArrayLayout, counter: int, carry: List[int], step: int) -> None:
        """Move the walker `step` records (+R or -R) while counter (relative digits) > 0.
        Positions are relative to the walker's current record, which the tracker calls
        record 0."""
        e = self.e
        base = lay.base
        f = base + lay.F
        S = [base + lay.S + i for i in range(6)]
        cdig = [base + counter + k for k in range(lay.DI)]
        nz_cells(e, cdig, f, S[0], S[1])
        e.at(f)
        e.raw("[")
        e.clear(f)
        moving = cdig + [base + off for off in carry]
        for c in moving:
            e.move(c, [(c + step, 1)])
        bcd_dec(e, [c + step for c in cdig], [s + step for s in S])
        nz_cells(e, [c + step for c in cdig], f + step, S[0] + step, S[1] + step)
        e.at(f + step)
        e.raw("]")
        e.pos = f  # the walker's record is "record 0" again for the tracker

    def array_read(self, name: str, idx: Block, r: Block) -> None:
        e = self.e
        lay = self.arrays[name]
        base = lay.base
        with self.scratch(1) as (t,):
            for k in range(lay.DI):
                e.copy(idx.digit(k), base + lay.C1 + k, t)
                e.copy(idx.digit(k), base + lay.C2 + k, t)
        c2 = [lay.C2 + k for k in range(lay.DI)]
        pay = [lay.PAY + k for k in range(lay.B + 1)]
        self._walk(lay, lay.C1, c2, lay.R)
        # copy element into payload (relative to the current record)
        for k in range(lay.B + 1):
            e.copy(base + lay.ELEM + k, base + lay.PAY + k, base + lay.S)
        self._walk(lay, lay.C2, pay, -lay.R)
        self.b_clear(r)
        e.move(base + lay.PAY, [(r.sign, 1)])
        for k in range(lay.B):
            e.move(base + lay.PAY + 1 + k, [(r.digit(k), 1)])

    def array_write(self, name: str, idx: Block, v: Block) -> None:
        e = self.e
        lay = self.arrays[name]
        base = lay.base
        with self.scratch(1) as (t,):
            for k in range(lay.DI):
                e.copy(idx.digit(k), base + lay.C1 + k, t)
                e.copy(idx.digit(k), base + lay.C2 + k, t)
            e.copy(v.sign, base + lay.PAY, t)
            for k in range(lay.B):
                e.copy(v.digit(k), base + lay.PAY + 1 + k, t)
        c2 = [lay.C2 + k for k in range(lay.DI)]
        pay = [lay.PAY + k for k in range(lay.B + 1)]
        self._walk(lay, lay.C1, c2 + pay, lay.R)
        for k in range(lay.B + 1):
            e.clear(base + lay.ELEM + k)
            e.move(base + lay.PAY + k, [(base + lay.ELEM + k, 1)])
        self._walk(lay, lay.C2, [], -lay.R)

    # ------------------------------------------------------------ statements
    def cond_flag(self, c: Expr, f: int) -> None:
        self.flag_expr(c, f)

    _CMP = ("lt", "gt", "le", "ge", "eq", "ne")

    def flag_expr(self, x: Expr, f: int) -> None:
        """f (a zero cell) = 1 if x is nonzero/true else 0, without building number blocks
        for comparisons and logic."""
        e = self.e
        if isinstance(x, Const):
            set_flag(e, f, 1 if x.value else 0)
            return
        if isinstance(x, Un) and x.op == "not":
            self.flag_expr(x.a, f)
            self._not(f)
            return
        if isinstance(x, Bin) and x.op in ("and", "or"):
            g = self._flag_cell()
            self.flag_expr(x.a, f)
            self.flag_expr(x.b, g)
            e.move(g, [(f, 1)])                      # f in {0, 1, 2}
            if x.op == "and":
                with self.scratch(3) as (o, t1, t2):
                    eq_const(e, f, 2, o, t1, t2)
                    e.clear(f)
                    e.move(o, [(f, 1)])
            else:
                with self.scratch(1) as (o,):
                    with e.loop(f):
                        e.clear(f)
                        set_flag(e, o, 1)
                    e.move(o, [(f, 1)])
            self._release_flag(g)
            return
        if isinstance(x, Bin) and x.op in self._CMP:
            a_, b_, op = x.a, x.b, x.op
            if isinstance(a_, Const) and not isinstance(b_, Const):
                a_, b_, op = b_, a_, self._MIRROR[op]
            if self._fast_compare_flag(op, a_, b_, f):
                return
            a, at = self.expr(a_)
            b, bt = self.expr(b_)
            self.cmp_flag(op, a, b, f)
            self.free(a, at)
            self.free(b, bt)
            return
        if self._is_byte(x):  # truth of a byte variable: nonzero and not EOF
            with self.scratch(2) as (t1, t2):
                eq_const(e, self.bytes[x.name], 0, f, t1, t2)
            self._not(f)
            return
        v, vt = self.expr(x)
        self.b_nz(v, f)
        self.free(v, vt)

    def stmts(self, ss: List[Stmt]) -> None:
        e = self.e
        for s in ss:
            if isinstance(s, Set) and s.var in self.bytes:
                cell = self.bytes[s.var]
                if isinstance(s.expr, Const) and (s.expr.value == -1 or 1 <= s.expr.value <= 255):
                    set_flag(e, cell, 0 if s.expr.value == -1 else s.expr.value)
                elif self._is_byte(s.expr):
                    if self.bytes[s.expr.name] != cell:
                        e.clear(cell)
                        with self.scratch(1) as (t,):
                            e.copy(self.bytes[s.expr.name], cell, t)
                else:
                    raise TypeError(f"byte variable {s.var} can only take read_char, a byte variable or a constant")
            elif isinstance(s, ReadChar) and s.var in self.bytes:
                e.at(self.bytes[s.var])
                e.raw(",")  # EOF reads 0, which is how byte variables encode -1
            elif isinstance(s, PrintChar) and self._is_byte(s.expr):
                with self.scratch(2) as (o, t):
                    e.copy(self.bytes[s.expr.name], o, t)
                    e.at(o)
                    e.raw(".")
                    e.clear(o)
            elif isinstance(s, Set):
                v, vt = self.expr(s.expr)
                dst = self.vars[s.var]
                if vt:
                    self.b_move(v, dst)
                    self.free_blocks.append(v.base)
                elif v.base != dst.base:
                    self.b_copy(v, dst)
            elif isinstance(s, Store):
                ib, it = self.expr(s.index)
                vb, vt = self.expr(s.expr)
                self.array_write(s.arr, ib, vb)
                self.free(ib, it)
                self.free(vb, vt)
            elif isinstance(s, If):
                f = self._flag_cell()
                t = self._flag_cell()
                self.cond_flag(s.cond, f)
                if_else(e, f, t, lambda s=s: self.stmts(s.then), lambda s=s: self.stmts(s.other))
                self._release_flag(t)
                self._release_flag(f)
            elif isinstance(s, While):
                f = self._flag_cell()
                self.cond_flag(s.cond, f)
                with e.loop(f):
                    e.clear(f)
                    self.stmts(s.body)
                    self.cond_flag(s.cond, f)
                self._release_flag(f)
            elif isinstance(s, ReadChar):
                dst = self.vars[s.var]
                with self.scratch(3) as (x, z, t):
                    e.at(x)
                    e.raw(",")
                    # EOF (0) -> -1
                    set_flag(e, z, 1)
                    with self.scratch(1) as (y,):
                        e.copy(x, t, y)
                        with e.loop(t):
                            e.clear(t)
                            e.clear(z)
                    self.b_from_byte(x, dst)
                    with e.loop(z):
                        e.clear(z)
                        e.add(dst.sign, 1)
                        e.add(dst.digit(0), 1)
            elif isinstance(s, PrintChar):
                v, vt = self.expr(s.expr)
                with self.scratch(1) as (o,):
                    self.b_to_byte(v, o)
                    e.at(o)
                    e.raw(".")
                    e.clear(o)
                self.free(v, vt)
            elif isinstance(s, PrintInt):
                v, vt = self.expr(s.expr)
                self.print_int(v)
                self.free(v, vt)
            else:
                raise TypeError(s)

    # flags for if/while live in temp space so nested scratch use cannot clobber them
    def _flag_cell(self) -> int:
        c = self.free_flags.pop()
        self.flags_used = max(self.flags_used, self.flag_base + self.flag_slots - len(self.free_flags) - self.flag_base)
        return c

    def _release_flag(self, c: int) -> None:
        self.e.clear(c)
        self.free_flags.append(c)

    def print_int(self, v: Block) -> None:
        e = self.e
        with self.scratch(6) as (lead, f, t, o, t2, t3):
            with self.scratch(1) as (sg,):
                e.copy(v.sign, sg, t)
                with e.loop(sg):
                    e.clear(sg)
                    e.add(o, 45)
                    e.at(o)
                    e.raw(".")
                    e.clear(o)
            e.add(lead, 1)  # still skipping leading zeros
            for k in reversed(range(self.D)):
                if k == 0:
                    e.copy(v.digit(0), o, t)
                    e.add(o, 48)
                    e.at(o)
                    e.raw(".")
                    e.clear(o)
                    break
                # print if digit != 0 or not leading
                e.copy(v.digit(k), f, t)
                with e.loop(f):           # nonzero digit: stop skipping
                    e.clear(f)
                    e.clear(lead)
                set_flag(e, f, 1)
                e.copy(lead, t2, t3)
                with e.loop(t2):          # still leading (digit was 0): don't print
                    e.clear(t2)
                    e.clear(f)
                with e.loop(f):
                    e.clear(f)
                    e.copy(v.digit(k), o, t)
                    e.add(o, 48)
                    e.at(o)
                    e.raw(".")
                    e.clear(o)
            e.clear(lead)

    def compile(self) -> str:
        self.stmts(self.prog.body)
        return self.e.text()


def compile_bf(prog: Program) -> str:
    first = BFCompiler(prog)
    first.compile()
    temps = (first.next_temp - first.temp_base) // (first.D + 1)
    return BFCompiler(prog, temp_slots=temps, flag_slots=first.flags_used).compile()
