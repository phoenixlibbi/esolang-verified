"""esoc intermediate representation: a tiny structured language every backend compiles.

Values are integers (characters are their code points). A program has scalar variables,
fixed-size integer arrays, and these statements:

    set(var, expr)  store(arr, idx, expr)  if/else  while  read_char(var) (-1 at EOF)
    print_char(expr)  print_int(expr)

Expressions are pure trees: constants, variables, array reads, ``+ - *``, unsigned
``udiv``/``umod`` (operands must be >= 0 and > 0; signed variants are library macros so
every backend shares one definition), comparisons, ``and/or/not`` on 0/1 values,
negation and ``sel(c, a, b)``.

Programs are written with the :class:`Builder` (operator overloading + ``with`` blocks)
and run by :func:`interpret`, the reference semantics backends are differential-tested
against.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Union

# ------------------------------------------------------------------ expressions

class Expr:
    def __add__(self, o): return Bin("add", self, lift(o))
    def __radd__(self, o): return Bin("add", lift(o), self)
    def __sub__(self, o): return Bin("sub", self, lift(o))
    def __rsub__(self, o): return Bin("sub", lift(o), self)
    def __mul__(self, o): return Bin("mul", self, lift(o))
    def __rmul__(self, o): return Bin("mul", lift(o), self)
    def __lt__(self, o): return Bin("lt", self, lift(o))
    def __le__(self, o): return Bin("le", self, lift(o))
    def __gt__(self, o): return Bin("gt", self, lift(o))
    def __ge__(self, o): return Bin("ge", self, lift(o))
    def __and__(self, o): return Bin("and", self, lift(o))
    def __rand__(self, o): return Bin("and", lift(o), self)
    def __or__(self, o): return Bin("or", self, lift(o))
    def __ror__(self, o): return Bin("or", lift(o), self)
    def __invert__(self): return Un("not", self)
    def __neg__(self): return Un("neg", self)
    def eq(self, o): return Bin("eq", self, lift(o))
    def ne(self, o): return Bin("ne", self, lift(o))
    __hash__ = object.__hash__


@dataclass(eq=False)
class Const(Expr):
    value: int


@dataclass(eq=False)
class Var(Expr):
    name: str


@dataclass(eq=False)
class Arr:
    name: str
    size: int

    def __getitem__(self, idx) -> "Idx":
        return Idx(self.name, lift(idx))


@dataclass(eq=False)
class Idx(Expr):
    arr: str
    index: Expr


@dataclass(eq=False)
class Bin(Expr):
    op: str
    a: Expr
    b: Expr


@dataclass(eq=False)
class Un(Expr):
    op: str
    a: Expr


@dataclass(eq=False)
class Sel(Expr):
    cond: Expr
    a: Expr
    b: Expr


BIN_OPS = ("add", "sub", "mul", "udiv", "umod", "eq", "ne", "lt", "le", "gt", "ge", "and", "or")


def lift(x: Union[int, str, Expr]) -> Expr:
    if isinstance(x, Expr):
        return x
    if isinstance(x, bool):
        return Const(int(x))
    if isinstance(x, int):
        return Const(x)
    if isinstance(x, str) and len(x) == 1:
        return Const(ord(x))
    raise TypeError(f"cannot use {x!r} as an expression")


def udiv(a, b) -> Expr: return Bin("udiv", lift(a), lift(b))
def umod(a, b) -> Expr: return Bin("umod", lift(a), lift(b))
def sel(c, a, b) -> Expr: return Sel(lift(c), lift(a), lift(b))


# ------------------------------------------------------------------ statements

@dataclass(eq=False)
class Stmt:
    pass


@dataclass(eq=False)
class Set(Stmt):
    var: str
    expr: Expr


@dataclass(eq=False)
class Store(Stmt):
    arr: str
    index: Expr
    expr: Expr


@dataclass(eq=False)
class If(Stmt):
    cond: Expr
    then: List[Stmt]
    other: List[Stmt]


@dataclass(eq=False)
class While(Stmt):
    cond: Expr
    body: List[Stmt]


@dataclass(eq=False)
class ReadChar(Stmt):
    var: str


@dataclass(eq=False)
class PrintChar(Stmt):
    expr: Expr


@dataclass(eq=False)
class PrintInt(Stmt):
    expr: Expr


@dataclass
class Program:
    name: str
    scalars: List[str] = field(default_factory=list)
    arrays: Dict[str, int] = field(default_factory=dict)
    body: List[Stmt] = field(default_factory=list)
    # Largest magnitude any stored value may reach (backends size their storage from it).
    max_value: int = 2 ** 31 - 1
    # Largest magnitude of any intermediate expression value (Brainfuck sizes temporaries
    # from it); defaults to max_value.
    max_intermediate: Optional[int] = None
    # Optional per-array bound on element magnitude (Brainfuck stores fewer digits).
    array_max: Dict[str, int] = field(default_factory=dict)
    # Scalars that only ever hold a character code or -1 (EOF): Brainfuck keeps them in a
    # single cell. They may only be assigned by read_char, another byte variable, or a
    # constant in {-1} or 1..255.
    byte_vars: List[str] = field(default_factory=list)

    @property
    def max_inter(self) -> int:
        return self.max_intermediate if self.max_intermediate is not None else self.max_value


# ------------------------------------------------------------------ builder

class Builder:
    """Write IR with Python syntax:

        P = Builder("sum")
        a, b = P.var("a"), P.var("b")
        P.set(a, a + b)
        with P.while_(a > 0):
            P.set(a, a - 1)
    """

    def __init__(self, name: str, max_value: int = 2 ** 31 - 1, max_intermediate: Optional[int] = None) -> None:
        self.prog = Program(name, max_value=max_value, max_intermediate=max_intermediate)
        self._stack: List[List[Stmt]] = [self.prog.body]
        self._last_if: Optional[If] = None
        self._tmp = 0

    # declarations
    def var(self, name: str, init: Optional[int] = None, byte: bool = False) -> Var:
        if name in self.prog.scalars or name in self.prog.arrays:
            raise ValueError(f"duplicate name {name}")
        self.prog.scalars.append(name)
        if byte:
            self.prog.byte_vars.append(name)
        v = Var(name)
        if init is not None:
            self.set(v, init)
        return v

    def temp(self, init: Optional[int] = None) -> Var:
        self._tmp += 1
        return self.var(f"_t{self._tmp}", init)

    def array(self, name: str, size: int, max_value: Optional[int] = None) -> Arr:
        if name in self.prog.scalars or name in self.prog.arrays:
            raise ValueError(f"duplicate name {name}")
        if size < 1:
            raise ValueError("array size must be >= 1")
        self.prog.arrays[name] = size
        if max_value is not None:
            self.prog.array_max[name] = max_value
        return Arr(name, size)

    # statements
    def _emit(self, s: Stmt) -> None:
        self._stack[-1].append(s)
        self._last_if = s if isinstance(s, If) else None

    def set(self, v: Var, e) -> None:
        self._emit(Set(v.name, lift(e)))

    def store(self, a: Arr, idx, e) -> None:
        self._emit(Store(a.name, lift(idx), lift(e)))

    def read_char(self, v: Var) -> None:
        self._emit(ReadChar(v.name))

    def print_char(self, e) -> None:
        self._emit(PrintChar(lift(e)))

    def print_int(self, e) -> None:
        self._emit(PrintInt(lift(e)))

    def print_str(self, s: str) -> None:
        for ch in s:
            self.print_char(ord(ch))

    @contextmanager
    def if_(self, cond) -> Iterator[None]:
        node = If(lift(cond), [], [])
        self._stack[-1].append(node)
        self._stack.append(node.then)
        try:
            yield
        finally:
            self._stack.pop()
            self._last_if = node

    @contextmanager
    def else_(self) -> Iterator[None]:
        node = self._last_if
        if node is None or node.other:
            raise SyntaxError("else_ must directly follow an if_ block")
        self._stack.append(node.other)
        try:
            yield
        finally:
            self._stack.pop()
            self._last_if = None

    @contextmanager
    def while_(self, cond) -> Iterator[None]:
        node = While(lift(cond), [])
        self._stack[-1].append(node)
        self._stack.append(node.body)
        try:
            yield
        finally:
            self._stack.pop()
            self._last_if = None

    def build(self) -> Program:
        if len(self._stack) != 1:
            raise SyntaxError("unclosed block")
        return self.prog


# ------------------------------------------------------------------ reference interpreter

class IRError(RuntimeError):
    pass


@dataclass
class IRRun:
    output: str
    steps: int
    max_abs: int          # largest magnitude stored into a variable or array element
    max_index: Dict[str, int]
    max_inter: int = 0    # largest magnitude of any evaluated expression
    array_abs: Dict[str, int] = field(default_factory=dict)  # largest magnitude stored per array


def interpret(prog: Program, input_data: str = "", max_steps: int = 50_000_000) -> IRRun:
    env: Dict[str, int] = {n: 0 for n in prog.scalars}
    arrs: Dict[str, List[int]] = {n: [0] * s for n, s in prog.arrays.items()}
    out: List[str] = []
    pos = 0
    steps = 0
    max_abs = 0
    max_inter = 0
    max_index: Dict[str, int] = {n: -1 for n in prog.arrays}
    array_abs: Dict[str, int] = {n: 0 for n in prog.arrays}
    byte_vars = set(prog.byte_vars)

    def ev(e: Expr) -> int:
        nonlocal max_inter
        v = _ev(e)
        if abs(v) > max_inter:
            max_inter = abs(v)
        return v

    def _ev(e: Expr) -> int:
        if isinstance(e, Const):
            return e.value
        if isinstance(e, Var):
            return env[e.name]
        if isinstance(e, Idx):
            i = ev(e.index)
            if not 0 <= i < prog.arrays[e.arr]:
                raise IRError(f"index {i} out of range for {e.arr}[{prog.arrays[e.arr]}]")
            return arrs[e.arr][i]
        if isinstance(e, Sel):
            return ev(e.a) if ev(e.cond) else ev(e.b)
        if isinstance(e, Un):
            v = ev(e.a)
            return int(not v) if e.op == "not" else -v
        if isinstance(e, Bin):
            a, b = ev(e.a), ev(e.b)
            op = e.op
            if op == "add": return a + b
            if op == "sub": return a - b
            if op == "mul": return a * b
            if op in ("udiv", "umod"):
                if a < 0 or b <= 0:
                    raise IRError(f"{op} needs a >= 0 and b > 0, got {a}, {b}")
                return a // b if op == "udiv" else a % b
            if op == "eq": return int(a == b)
            if op == "ne": return int(a != b)
            if op == "lt": return int(a < b)
            if op == "le": return int(a <= b)
            if op == "gt": return int(a > b)
            if op == "ge": return int(a >= b)
            if op == "and": return int(bool(a) and bool(b))
            if op == "or": return int(bool(a) or bool(b))
        raise IRError(f"bad expression {e!r}")

    def note(v: int) -> None:
        nonlocal max_abs
        if abs(v) > max_abs:
            max_abs = abs(v)

    def exec_block(block: List[Stmt]) -> None:
        nonlocal pos, steps
        for s in block:
            steps += 1
            if steps > max_steps:
                raise IRError("step limit")
            if isinstance(s, Set):
                v = ev(s.expr)
                note(v)
                if s.var in byte_vars and not (v == -1 or 1 <= v <= 255):
                    raise IRError(f"byte variable {s.var} assigned {v}")
                env[s.var] = v
            elif isinstance(s, Store):
                i = ev(s.index)
                if not 0 <= i < prog.arrays[s.arr]:
                    raise IRError(f"index {i} out of range for {s.arr}[{prog.arrays[s.arr]}]")
                v = ev(s.expr)
                note(v)
                array_abs[s.arr] = max(array_abs[s.arr], abs(v))
                arrs[s.arr][i] = v
                max_index[s.arr] = max(max_index[s.arr], i)
            elif isinstance(s, If):
                exec_block(s.then if ev(s.cond) else s.other)
            elif isinstance(s, While):
                while ev(s.cond):
                    steps += 1
                    if steps > max_steps:
                        raise IRError("step limit")
                    exec_block(s.body)
            elif isinstance(s, ReadChar):
                if pos < len(input_data):
                    env[s.var] = ord(input_data[pos])
                    pos += 1
                else:
                    env[s.var] = -1
            elif isinstance(s, PrintChar):
                v = ev(s.expr)
                out.append(chr(v % 256))
            elif isinstance(s, PrintInt):
                out.append(str(ev(s.expr)))
            else:
                raise IRError(f"bad statement {s!r}")

    exec_block(prog.body)
    return IRRun("".join(out), steps, max_abs, max_index, max_inter, array_abs)


def walk_exprs(block: List[Stmt]) -> Iterator[Expr]:
    """Yield every top-level expression in a statement tree (used by backends' checks)."""
    for s in block:
        if isinstance(s, (Set, PrintChar, PrintInt)):
            yield s.expr
        elif isinstance(s, Store):
            yield s.index
            yield s.expr
        elif isinstance(s, If):
            yield s.cond
            yield from walk_exprs(s.then)
            yield from walk_exprs(s.other)
        elif isinstance(s, While):
            yield s.cond
            yield from walk_exprs(s.body)
