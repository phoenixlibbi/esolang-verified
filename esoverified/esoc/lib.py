"""Library macros on top of the IR: input parsing with one character of lookahead,
signed division, absolute value, line I/O. Every backend inherits these definitions,
so signed arithmetic means the same thing in all three target languages."""

from __future__ import annotations

from .ir import Arr, Builder, Expr, Var, lift, sel, udiv, umod

SPACE, NL, TAB, CR = 32, 10, 9, 13


def iabs(e) -> Expr:
    e = lift(e)
    return sel(e < 0, -e, e)


def is_neg_product(a, b) -> Expr:
    return (lift(a) < 0).ne(lift(b) < 0)


def tdiv(a, b) -> Expr:
    """Division truncating toward zero (C, Java, the EsoLang statements)."""
    q = udiv(iabs(a), iabs(b))
    return sel(is_neg_product(a, b), -q, q)


def tmod(a, b) -> Expr:
    """Remainder with the sign of the dividend (pairs with tdiv)."""
    r = umod(iabs(a), iabs(b))
    return sel(lift(a) < 0, -r, r)


def fdiv(a, b) -> Expr:
    """Floor division (Python //)."""
    a, b = lift(a), lift(b)
    q = udiv(iabs(a), iabs(b))
    r = umod(iabs(a), iabs(b))
    return sel(is_neg_product(a, b), -(q + r.ne(0)), q)


def fmod(a, b) -> Expr:
    """Floor modulo (Python %)."""
    a, b = lift(a), lift(b)
    return a - b * fdiv(a, b)


def is_digit(e) -> Expr:
    e = lift(e)
    return (e >= 48) & (e <= 57)


def is_lower(e) -> Expr:
    e = lift(e)
    return (e >= 97) & (e <= 122)


class Input:
    """Character-level reader keeping one character of lookahead in ``look``
    (-1 at end of input)."""

    def __init__(self, P: Builder) -> None:
        self.P = P
        self.look = P.var("_look", byte=True)
        P.read_char(self.look)

    def advance(self) -> None:
        self.P.read_char(self.look)

    def at_eol(self) -> Expr:
        return self.look.eq(NL) | self.look.eq(-1)

    def skip_ws(self) -> None:
        L = self.look
        with self.P.while_(L.eq(SPACE) | L.eq(NL) | L.eq(TAB) | L.eq(CR)):
            self.advance()

    def read_int(self, v: Var) -> None:
        """Skip whitespace, parse an optionally signed decimal integer into v."""
        P, L = self.P, self.look
        neg = P.temp(0)
        self.skip_ws()
        with P.if_(L.eq(ord("-"))):
            P.set(neg, 1)
            self.advance()
        with P.else_():
            with P.if_(L.eq(ord("+"))):
                self.advance()
        P.set(v, 0)
        with P.while_(is_digit(L)):
            P.set(v, v * 10 + (L - 48))
            self.advance()
        with P.if_(neg):
            P.set(v, -v)

    def read_line(self, arr: Arr, n: Var) -> None:
        """Read characters up to (and consume) the next newline into arr; n = length."""
        P, L = self.P, self.look
        P.set(n, 0)
        with P.while_(~self.at_eol()):
            P.store(arr, n, L)
            P.set(n, n + 1)
            self.advance()
        with P.if_(L.eq(NL)):
            self.advance()

    def read_token(self, arr: Arr, n: Var) -> None:
        """Skip whitespace, then read non-whitespace characters into arr."""
        P, L = self.P, self.look
        self.skip_ws()
        P.set(n, 0)
        with P.while_(~(L.eq(SPACE) | L.eq(NL) | L.eq(TAB) | L.eq(CR) | L.eq(-1))):
            P.store(arr, n, L)
            P.set(n, n + 1)
            self.advance()

    def skip_spaces(self) -> None:
        with self.P.while_(self.look.eq(SPACE) | self.look.eq(TAB) | self.look.eq(CR)):
            self.advance()

    def read_ints_line(self, arr: Arr, n: Var) -> None:
        """Read the integers on the current line into arr (n = count), consume the newline."""
        P = self.P
        v = P.temp()
        P.set(n, 0)
        self.skip_spaces()
        with P.while_(~self.at_eol()):
            self.read_int(v)
            P.store(arr, n, v)
            P.set(n, n + 1)
            self.skip_spaces()
        with P.if_(self.look.eq(NL)):
            self.advance()

    def skip_line(self) -> None:
        with self.P.while_(~self.at_eol()):
            self.advance()
        with self.P.if_(self.look.eq(NL)):
            self.advance()


def print_range(P: Builder, arr: Arr, start, end) -> None:
    i = P.temp()
    P.set(i, start)
    with P.while_(i < end):
        P.print_char(arr[i])
        P.set(i, i + 1)


def print_yes_no(P: Builder, cond) -> None:
    with P.if_(cond):
        P.print_str("yes")
    with P.else_():
        P.print_str("no")
