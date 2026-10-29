"""X01-X20 in esoc IR."""

from __future__ import annotations

from ..ir import sel, udiv, umod
from ..lib import SPACE, tdiv
from . import program
from .easy import LINE
from .hard import yes_no
from .medium import gcd_into, print_sep, read_n_ints


@program("X01")
def x01(P, I):
    n, p, first = P.var("n"), P.var("p", 2), P.var("first", 1)
    I.read_int(n)
    with P.while_(p * p <= n):
        with P.while_(umod(n, p).eq(0)):
            print_sep(P, first)
            P.print_int(p)
            P.set(n, udiv(n, p))
        P.set(p, p + 1)
    with P.if_(n > 1):
        print_sep(P, first)
        P.print_int(n)


@program("X02")
def x02(P, I):
    a, n, best, i, j, ans = P.array("a", 64), P.var("n"), P.array("best", 64), P.var("i", 0), P.var("j"), P.var("ans", 0)
    read_n_ints(P, I, a, n)
    with P.while_(i < n):
        P.store(best, i, 1)
        P.set(j, 0)
        with P.while_(j < i):
            with P.if_((a[j] < a[i]) & (best[j] + 1 > best[i])):
                P.store(best, i, best[j] + 1)
            P.set(j, j + 1)
        P.set(ans, sel(best[i] > ans, best[i], ans))
        P.set(i, i + 1)
    P.print_int(ans)


@program("X03")
def x03(P, I):
    A, B = P.array("A", 64), P.array("B", 64)
    m, n, p, i, j, k, v, s = (P.var("m"), P.var("n"), P.var("p"), P.var("i"), P.var("j"), P.var("k"),
                              P.var("v"), P.var("s", 0))
    I.read_int(m)
    I.read_int(n)
    I.read_int(p)
    P.set(k, 0)
    with P.while_(k < m * n):
        I.read_int(v)
        P.store(A, k, v)
        P.set(k, k + 1)
    P.set(k, 0)
    with P.while_(k < n * p):
        I.read_int(v)
        P.store(B, k, v)
        P.set(k, k + 1)
    I.read_int(i)
    I.read_int(j)
    P.set(k, 0)
    with P.while_(k < n):
        P.set(s, s + A[i * n + k] * B[k * p + j])
        P.set(k, k + 1)
    P.print_int(s)


@program("X04")
def x04(P, I):
    st, sp, a, b, c = P.array("st", 64), P.var("sp", 0), P.var("a"), P.var("b"), P.var("c")
    with P.while_(~I.at_eol()):
        P.set(c, I.look)
        with P.if_(c.ne(SPACE)):
            with P.if_((c >= 48) & (c <= 57)):
                P.store(st, sp, c - 48)
                P.set(sp, sp + 1)
            with P.else_():
                P.set(b, st[sp - 1])
                P.set(a, st[sp - 2])
                P.set(sp, sp - 2)
                with P.if_(c.eq(ord("+"))):
                    P.store(st, sp, a + b)
                with P.else_():
                    with P.if_(c.eq(ord("-"))):
                        P.store(st, sp, a - b)
                    with P.else_():
                        with P.if_(c.eq(ord("*"))):
                            P.store(st, sp, a * b)
                        with P.else_():
                            P.store(st, sp, tdiv(a, b))
                P.set(sp, sp + 1)
        I.advance()
    P.print_int(st[sp - 1])


@program("X05")
def x05(P, I):
    a, n, b, m, i, j = P.array("a", 64), P.var("n"), P.array("b", 64), P.var("m"), P.var("i", 0), P.var("j", 0)
    first = P.var("first", 1)
    I.read_ints_line(a, n)
    I.read_ints_line(b, m)
    with P.while_((i < n) | (j < m)):
        print_sep(P, first)
        with P.if_((j >= m) | ((i < n) & (a[sel(i < n, i, 0)] <= b[sel(j < m, j, 0)]))):
            P.print_int(a[i])
            P.set(i, i + 1)
        with P.else_():
            P.print_int(b[j])
            P.set(j, j + 1)


@program("X06", max_value=2 ** 31 - 1, max_intermediate=10 ** 13)
def x06(P, I):
    b, e, m, r = P.var("b"), P.var("e"), P.var("m"), P.var("r")
    I.read_int(b)
    I.read_int(e)
    I.read_int(m)
    P.set(r, umod(1, m))
    P.set(b, umod(b, m))
    with P.while_(e > 0):
        with P.if_(umod(e, 2).eq(1)):
            P.set(r, umod(r * b, m))
        P.set(b, umod(b * b, m))
        P.set(e, udiv(e, 2))
    P.print_int(r)


@program("X07")
def x07(P, I):
    s, n, c, lo, hi, best, side = (P.array("s", LINE), P.var("n"), P.var("c", 0), P.var("lo"), P.var("hi"),
                                   P.var("best", 0), P.var("side"))
    I.read_line(s, n)
    with P.while_(c < n):
        P.set(side, 0)
        with P.while_(side < 2):
            P.set(lo, c)
            P.set(hi, c + side)
            with P.while_((lo >= 0) & (hi < n) & s[sel(lo >= 0, lo, 0)].eq(s[sel(hi < n, hi, 0)])):
                P.set(lo, lo - 1)
                P.set(hi, hi + 1)
            P.set(best, sel(hi - lo - 1 > best, hi - lo - 1, best))
            P.set(side, side + 1)
        P.set(c, c + 1)
    P.print_int(best)


@program("X08")
def x08(P, I):
    lo, hi, x, cnt = P.var("lo"), P.var("hi"), P.var("x"), P.var("cnt", 0)
    I.read_int(lo)
    I.read_int(hi)
    with P.while_(lo <= hi):
        P.set(x, lo)
        with P.while_(x > 0):
            P.set(cnt, cnt + umod(x, 2))
            P.set(x, udiv(x, 2))
        P.set(lo, lo + 1)
    P.print_int(cnt)


@program("X09")
def x09(P, I):
    d, best = P.var("d", 0), P.var("best", 0)
    with P.while_(~I.at_eol()):
        P.set(d, sel(I.look.eq(ord("(")), d + 1, sel(d > 0, d - 1, 0)))
        P.set(best, sel(d > best, d, best))
        I.advance()
    P.print_int(best)


@program("X10")
def x10(P, I):
    s, n, t, m, k, j, ok, found = (P.array("s", LINE), P.var("n"), P.array("t", LINE), P.var("m"), P.var("k", 0),
                                   P.var("j"), P.var("ok"), P.var("found", 0))
    I.read_line(s, n)
    I.read_line(t, m)
    with P.if_(n.eq(m)):
        with P.while_((k < n) & found.eq(0)):
            P.set(ok, 1)
            P.set(j, 0)
            with P.while_(ok & (j < n)):
                with P.if_(s[umod(j + k, n)].ne(t[j])):
                    P.set(ok, 0)
                P.set(j, j + 1)
            P.set(found, ok)
            P.set(k, k + 1)
    yes_no(P, found)


@program("X11")
def x11(P, I):
    a, n, i, j, c = P.array("a", 64), P.var("n"), P.var("i", 0), P.var("j"), P.var("c", 0)
    read_n_ints(P, I, a, n)
    with P.while_(i < n):
        P.set(j, i + 1)
        with P.while_(j < n):
            P.set(c, c + (a[i] > a[j]))
            P.set(j, j + 1)
        P.set(i, i + 1)
    P.print_int(c)


@program("X12")
def x12(P, I):
    a, b, g = P.var("a"), P.var("b"), P.var("g")
    I.read_int(a)
    I.read_int(b)
    gcd_into(P, g, a, b)
    P.print_int(udiv(a, g) * b)


@program("X13")
def x13(P, I):
    st, sp, ok, c, want = P.array("st", LINE), P.var("sp", 0), P.var("ok", 1), P.var("c"), P.var("want")
    with P.while_(~I.at_eol()):
        P.set(c, I.look)
        with P.if_(c.eq(ord("(")) | c.eq(ord("[")) | c.eq(ord("{"))):
            P.store(st, sp, c)
            P.set(sp, sp + 1)
        with P.else_():
            P.set(want, sel(c.eq(ord(")")), ord("("), sel(c.eq(ord("]")), ord("["), ord("{"))))
            with P.if_(sp.eq(0)):
                P.set(ok, 0)
            with P.else_():
                with P.if_(st[sp - 1].ne(want)):
                    P.set(ok, 0)
                P.set(sp, sp - 1)
        I.advance()
    yes_no(P, ok & sp.eq(0))


@program("X14")
def x14(P, I):
    a, n, i, j, r, first = P.array("a", 64), P.var("n"), P.var("i", 0), P.var("j"), P.var("r"), P.var("first", 1)
    found = P.var("found")
    read_n_ints(P, I, a, n)
    with P.while_(i < n):
        P.set(r, -1)
        P.set(found, 0)
        P.set(j, i + 1)
        with P.while_((j < n) & found.eq(0)):   # -1 can be a real value: use a flag
            with P.if_(a[j] > a[i]):
                P.set(r, a[j])
                P.set(found, 1)
            P.set(j, j + 1)
        print_sep(P, first)
        P.print_int(r)
        P.set(i, i + 1)


@program("X15")
def x15(P, I):
    m, R, C, k, v = P.array("m", 64), P.var("R"), P.var("C"), P.var("k", 0), P.var("v")
    top, bot, left, right, i, first = P.var("top", 0), P.var("bot"), P.var("left", 0), P.var("right"), P.var("i"), \
        P.var("first", 1)
    I.read_int(R)
    I.read_int(C)
    with P.while_(k < R * C):
        I.read_int(v)
        P.store(m, k, v)
        P.set(k, k + 1)
    P.set(bot, R - 1)
    P.set(right, C - 1)

    def emit(idx):
        print_sep(P, first)
        P.print_int(m[idx])

    with P.while_((top <= bot) & (left <= right)):
        P.set(i, left)
        with P.while_(i <= right):
            emit(top * C + i)
            P.set(i, i + 1)
        P.set(i, top + 1)
        with P.while_(i <= bot):
            emit(i * C + right)
            P.set(i, i + 1)
        with P.if_(top < bot):
            P.set(i, right - 1)
            with P.while_(i >= left):
                emit(bot * C + i)
                P.set(i, i - 1)
        with P.if_(left < right):
            P.set(i, bot - 1)
            with P.while_(i > top):
                emit(i * C + left)
                P.set(i, i - 1)
        P.set(top, top + 1)
        P.set(bot, bot - 1)
        P.set(left, left + 1)
        P.set(right, right - 1)


@program("X16")
def x16(P, I):
    a, b, c = P.var("a"), P.var("b"), P.var("c", 0)
    I.read_int(a)
    I.read_int(b)
    with P.while_((a > 0) | (b > 0)):
        P.set(c, c + umod(a, 2).ne(umod(b, 2)))
        P.set(a, udiv(a, 2))
        P.set(b, udiv(b, 2))
    P.print_int(c)


def roman_value(c):
    return sel(c.eq(ord("I")), 1, sel(c.eq(ord("V")), 5, sel(c.eq(ord("X")), 10, sel(c.eq(ord("L")), 50,
               sel(c.eq(ord("C")), 100, sel(c.eq(ord("D")), 500, sel(c.eq(ord("M")), 1000, 0)))))))


@program("X17")
def x17(P, I):
    s, n, i, tot, v, w = P.array("s", 64), P.var("n"), P.var("i", 0), P.var("tot", 0), P.var("v"), P.var("w")
    I.read_line(s, n)
    with P.while_(i < n):
        P.set(v, roman_value(s[i]))
        P.set(w, sel(i + 1 < n, roman_value(s[sel(i + 1 < n, i + 1, 0)]), 0))
        P.set(tot, tot + sel(w > v, -v, v))
        P.set(i, i + 1)
    P.print_int(tot)


ROMAN = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
         (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]


@program("X18")
def x18(P, I):
    n = P.var("n")
    I.read_int(n)
    for value, sym in ROMAN:
        with P.while_(n >= value):
            P.print_str(sym)
            P.set(n, n - value)


@program("X19")
def x19(P, I):
    a, n, seen, i, ok = P.array("a", 64), P.var("n"), P.array("seen", 66), P.var("i", 0), P.var("ok", 1)
    read_n_ints(P, I, a, n)
    with P.while_(i < n):
        with P.if_((a[i] < 1) | (a[i] > n)):
            P.set(ok, 0)
        with P.else_():
            with P.if_(seen[a[i]].ne(0)):
                P.set(ok, 0)
            P.store(seen, a[i], 1)
        P.set(i, i + 1)
    yes_no(P, ok)


@program("X20")
def x20(P, I):
    n, k, r, i = P.var("n"), P.var("k"), P.var("r", 0), P.var("i", 2)
    I.read_int(n)
    I.read_int(k)
    with P.while_(i <= n):
        P.set(r, umod(r + k, i))
        P.set(i, i + 1)
    P.print_int(r + 1)

