"""M01-M20 in esoc IR."""

from __future__ import annotations

from ..ir import Builder, sel, udiv, umod
from ..lib import SPACE, Input, iabs
from . import program
from .easy import LINE, count_line, echo_line, is_vowel


def print_sep(P: Builder, first, sep: int = SPACE) -> None:
    """Print a separator unless this is the first item."""
    with P.if_(first.eq(0)):
        P.print_char(sep)
    P.set(first, 0)


def read_n_ints(P: Builder, I: Input, arr, n) -> None:
    """Read N, then N integers (from the next line) into arr."""
    i, v = P.temp(), P.temp()
    I.read_int(n)
    P.set(i, 0)
    with P.while_(i < n):
        I.read_int(v)
        P.store(arr, i, v)
        P.set(i, i + 1)


def print_ints(P: Builder, arr, n) -> None:
    i = P.temp(0)
    with P.while_(i < n):
        with P.if_(i > 0):
            P.print_char(SPACE)
        P.print_int(arr[i])
        P.set(i, i + 1)


def sort_ints(P: Builder, arr, n) -> None:
    """Insertion sort arr[0:n] ascending."""
    i, j, key = P.temp(), P.temp(), P.temp()
    P.set(i, 1)
    with P.while_(i < n):
        P.set(key, arr[i])
        P.set(j, i - 1)
        with P.while_((j >= 0) & (arr[sel(j >= 0, j, 0)] > key)):
            P.store(arr, j + 1, arr[j])
            P.set(j, j - 1)
        P.store(arr, j + 1, key)
        P.set(i, i + 1)


@program("M01")
def m01(P, I):
    s, n, i, ok = P.array("s", LINE), P.var("n"), P.var("i", 0), P.var("ok", 1)
    I.read_line(s, n)
    with P.while_(i < n - 1 - i):
        with P.if_(s[i].ne(s[n - 1 - i])):
            P.set(ok, 0)
        P.set(i, i + 1)
    with P.if_(ok):
        P.print_str("yes")
    with P.else_():
        P.print_str("no")


@program("M02")
def m02(P, I):
    P.print_int(count_line(P, I, lambda c: c.eq(SPACE)) + 1)


@program("M03")
def m03(P, I):
    s, n, i, j = P.array("s", LINE), P.var("n"), P.var("i", 0), P.var("j")
    I.read_line(s, n)
    with P.while_(i < n):
        P.set(j, i)
        with P.while_((j < n) & s[sel(j < n, j, 0)].eq(s[i])):
            P.set(j, j + 1)
        P.print_char(s[i])
        P.print_int(j - i)
        P.set(i, j)


@program("M04")
def m04(P, I):
    echo_line(P, I, transform=lambda c: umod(c - 97 + 3, 26) + 97)


@program("M05")
def m05(P, I):
    a, b, op = P.var("a"), P.var("b"), P.var("op")
    I.read_int(a)
    I.skip_ws()
    P.set(op, I.look)
    I.advance()
    I.read_int(b)
    with P.if_(op.eq(ord("+"))):
        P.print_int(a + b)
    with P.else_():
        with P.if_(op.eq(ord("-"))):
            P.print_int(a - b)
        with P.else_():
            P.print_int(a * b)


def gcd_into(P: Builder, g, a, b) -> None:
    x, y, t = P.temp(), P.temp(), P.temp()
    P.set(x, iabs(a))
    P.set(y, iabs(b))
    with P.while_(y > 0):
        P.set(t, umod(x, y))
        P.set(x, y)
        P.set(y, t)
    P.set(g, x)


@program("M06")
def m06(P, I):
    a, b, g = P.var("a"), P.var("b"), P.var("g")
    I.read_int(a)
    I.read_int(b)
    gcd_into(P, g, a, b)
    P.print_int(g)


@program("M07", max_value=10 ** 7)
def m07(P, I):
    n, f = P.var("n"), P.var("f", 1)
    I.read_int(n)
    with P.while_(n > 1):
        P.set(f, f * n)
        P.set(n, n - 1)
    P.print_int(f)


@program("M08")
def m08(P, I):
    """Fibonacci with decimal digit arrays (F90 has 19 digits; every backend stays exact)."""
    D = 24
    a, b, c = P.array("a", D), P.array("b", D), P.array("c", D)
    n, i, k, carry, s = P.var("n"), P.var("i"), P.var("k"), P.var("carry"), P.var("s")
    I.read_int(n)
    P.store(a, 0, 0)          # F0 = 0
    P.store(b, 0, 1)          # F1 = 1
    P.set(i, 1)
    with P.while_(i < n):
        P.set(carry, 0)
        P.set(k, 0)
        with P.while_(k < D):
            P.set(s, a[k] + b[k] + carry)
            P.store(c, k, umod(s, 10))
            P.set(carry, udiv(s, 10))
            P.set(k, k + 1)
        P.set(k, 0)
        with P.while_(k < D):
            P.store(a, k, b[k])
            P.store(b, k, c[k])
            P.set(k, k + 1)
        P.set(i, i + 1)
    P.set(k, D - 1)
    with P.while_((k > 0) & b[k].eq(0)):
        P.set(k, k - 1)
    with P.while_(k >= 0):
        P.print_char(48 + b[sel(k >= 0, k, 0)])
        P.set(k, k - 1)


@program("M09")
def m09(P, I):
    n, bits, k = P.var("n"), P.array("bits", 64), P.var("k", 0)
    I.read_int(n)
    with P.if_(n.eq(0)):
        P.print_char(48)
    with P.while_(n > 0):
        P.store(bits, k, umod(n, 2))
        P.set(n, udiv(n, 2))
        P.set(k, k + 1)
    with P.while_(k > 0):
        P.set(k, k - 1)
        P.print_char(48 + bits[k])


@program("M10", max_value=2 ** 42)
def m10(P, I):
    v = P.var("v", 0)
    with P.while_(~I.at_eol()):
        P.set(v, v * 2 + I.look - 48)
        I.advance()
    P.print_int(v)


@program("M11")
def m11(P, I):
    s, n, p, m = P.array("s", LINE), P.var("n"), P.array("p", LINE), P.var("m")
    i, j, ok, cnt = P.var("i", 0), P.var("j"), P.var("ok"), P.var("cnt", 0)
    I.read_line(s, n)
    I.read_line(p, m)
    with P.while_(i + m <= n):
        P.set(ok, 1)
        P.set(j, 0)
        with P.while_(ok & (j < m)):
            with P.if_(s[i + j].ne(p[j])):
                P.set(ok, 0)
            P.set(j, j + 1)
        P.set(cnt, cnt + ok)
        P.set(i, i + 1)
    P.print_int(cnt)


@program("M12")
def m12(P, I):
    echo_line(P, I, keep=lambda c: ~is_vowel(c))


@program("M13")
def m13(P, I):
    a, n = P.array("a", 64), P.var("n")
    read_n_ints(P, I, a, n)
    sort_ints(P, a, n)
    print_ints(P, a, n)


@program("M14")
def m14(P, I):
    a, n, i, mx, second, found = (P.array("a", 64), P.var("n"), P.var("i"), P.var("mx"), P.var("second"),
                                  P.var("found", 0))
    read_n_ints(P, I, a, n)
    P.set(mx, a[0])
    P.set(i, 1)
    with P.while_(i < n):
        P.set(mx, sel(a[i] > mx, a[i], mx))
        P.set(i, i + 1)
    P.set(i, 0)
    with P.while_(i < n):
        with P.if_(a[i] < mx):
            with P.if_(found.eq(0) | (a[i] > second)):
                P.set(second, a[i])
                P.set(found, 1)
        P.set(i, i + 1)
    P.print_int(second)


@program("M15")
def m15(P, I):
    cnt, k, ok = P.array("cnt", 128), P.var("k"), P.var("ok", 1)
    with P.while_(~I.at_eol()):
        P.store(cnt, I.look, cnt[I.look] + 1)
        I.advance()
    I.skip_line()
    with P.while_(~I.at_eol()):
        P.store(cnt, I.look, cnt[I.look] - 1)
        I.advance()
    P.set(k, 0)
    with P.while_(k < 128):
        with P.if_(cnt[k].ne(0)):
            P.set(ok, 0)
        P.set(k, k + 1)
    with P.if_(ok):
        P.print_str("yes")
    with P.else_():
        P.print_str("no")


@program("M16")
def m16(P, I):
    s, n, t, m, i = P.array("s", LINE), P.var("n"), P.array("t", LINE), P.var("m"), P.var("i", 0)
    I.read_line(s, n)
    I.read_line(t, m)
    with P.while_(i < n):
        P.print_char(s[i])
        P.print_char(t[i])
        P.set(i, i + 1)


@program("M17")
def m17(P, I):
    echo_line(P, I, transform=lambda c: sel(c.eq(SPACE), ord("_"), c))


@program("M18")
def m18(P, I):
    n, i, v, s = P.var("n"), P.var("i", 0), P.var("v"), P.var("s", 0)
    I.read_int(n)
    with P.while_(i < n):
        I.read_int(v)
        P.set(s, s + v)
        P.set(i, i + 1)
    P.print_int(s)


@program("M19")
def m19(P, I):
    i = P.var("i", 0)
    with P.while_(~I.at_eol()):
        with P.if_(umod(i, 2).eq(0)):
            P.print_char(I.look)
        P.set(i, i + 1)
        I.advance()


@program("M20")
def m20(P, I):
    seen, n = P.array("seen", 256), P.var("n", 0)
    with P.while_(~I.at_eol()):
        with P.if_(seen[I.look].eq(0)):
            P.store(seen, I.look, 1)
            P.set(n, n + 1)
        I.advance()
    P.print_int(n)

