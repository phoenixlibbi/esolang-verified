"""E01-E20 in esoc IR."""

from __future__ import annotations

from ..ir import Builder, sel, udiv, umod
from ..lib import NL, SPACE, Input, iabs, is_digit, is_lower, print_range, tdiv
from . import program

LINE = 1024


def echo_line(P: Builder, I: Input, transform=None, keep=None) -> None:
    """Print the rest of the current line (optionally filtered/transformed), consume newline."""
    with P.while_(~I.at_eol()):
        c = I.look
        if keep is None:
            P.print_char(transform(c) if transform else c)
        else:
            with P.if_(keep(c)):
                P.print_char(transform(c) if transform else c)
        I.advance()
    with P.if_(I.look.eq(NL)):
        I.advance()


def count_line(P: Builder, I: Input, pred=None):
    n = P.temp(0)
    with P.while_(~I.at_eol()):
        if pred is None:
            P.set(n, n + 1)
        else:
            with P.if_(pred(I.look)):
                P.set(n, n + 1)
        I.advance()
    return n


def is_vowel(c):
    return (c.eq(97) | c.eq(101) | c.eq(105) | c.eq(111) | c.eq(117) |
            c.eq(65) | c.eq(69) | c.eq(73) | c.eq(79) | c.eq(85))


@program("E01")
def e01(P, I):
    P.print_str("Hello World!")


@program("E02")
def e02(P, I):
    echo_line(P, I)


@program("E03")
def e03(P, I):
    P.print_str("Hello, ")
    echo_line(P, I)
    P.print_str("!")


@program("E04")
def e04(P, I):
    a, b = P.var("a"), P.var("b")
    I.read_int(a)
    I.read_int(b)
    P.print_int(a + b)


@program("E05", max_value=10 ** 9)
def e05(P, I):
    a, b = P.var("a"), P.var("b")
    I.read_int(a)
    I.read_int(b)
    P.print_int(a * b)


@program("E06")
def e06(P, I):
    n = P.var("n")
    I.read_int(n)
    with P.if_(umod(iabs(n), 2).eq(0)):
        P.print_str("even")
    with P.else_():
        P.print_str("odd")


@program("E07")
def e07(P, I):
    P.print_int(count_line(P, I))


@program("E08")
def e08(P, I):
    s, n = P.array("s", LINE), P.var("n")
    I.read_line(s, n)
    with P.while_(n > 0):
        P.set(n, n - 1)
        P.print_char(s[n])


@program("E09")
def e09(P, I):
    P.print_int(count_line(P, I, is_vowel))


@program("E10", max_value=10 ** 9)
def e10(P, I):
    n = P.var("n")
    I.read_int(n)
    P.print_int(udiv(n * (n + 1), 2))


@program("E11")
def e11(P, I):
    s = P.var("s", 0)
    I.skip_ws()
    with P.if_(I.look.eq(ord("-"))):
        I.advance()
    with P.while_(is_digit(I.look)):
        P.set(s, s + I.look - 48)
        I.advance()
    P.print_int(s)


@program("E12")
def e12(P, I):
    a, b = P.var("a"), P.var("b")
    I.read_int(a)
    I.read_int(b)
    P.print_int(sel(a < b, a, b))


@program("E13")
def e13(P, I):
    a, b, c, m = P.var("a"), P.var("b"), P.var("c"), P.var("m")
    I.read_int(a)
    I.read_int(b)
    I.read_int(c)
    P.set(m, sel(a > b, a, b))
    P.print_int(sel(m > c, m, c))


@program("E14")
def e14(P, I):
    n, s, k = P.var("n"), P.array("s", LINE), P.var("k")
    I.read_int(n)
    I.skip_line()
    I.read_line(s, k)
    with P.while_(n > 0):
        print_range(P, s, 0, k)
        P.set(n, n - 1)


@program("E15")
def e15(P, I):
    echo_line(P, I)
    P.print_char(SPACE)
    echo_line(P, I)


@program("E16")
def e16(P, I):
    s, n = P.array("s", LINE), P.var("n")
    I.read_line(s, n)
    P.print_char(s[0])
    P.print_char(SPACE)
    P.print_char(s[n - 1])


@program("E17")
def e17(P, I):
    echo_line(P, I, transform=lambda c: sel(is_lower(c), c - 32, c))


@program("E18")
def e18(P, I):
    P.print_int(count_line(P, I, lambda c: c.eq(SPACE)))


@program("E19")
def e19(P, I):
    a, b = P.var("a"), P.var("b")
    I.read_int(a)
    I.read_int(b)
    P.print_int(tdiv(a + b, 2))


@program("E20")
def e20(P, I):
    a, b = P.var("a"), P.var("b")
    I.read_int(a)
    I.read_int(b)
    with P.if_(a < b):
        P.print_str("less")
    with P.else_():
        with P.if_(a > b):
            P.print_str("greater")
        with P.else_():
            P.print_str("equal")
