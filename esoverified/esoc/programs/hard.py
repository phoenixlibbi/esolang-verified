"""H01-H20 in esoc IR."""

from __future__ import annotations

from ..ir import Builder, sel, udiv, umod
from ..lib import NL, SPACE, Input, fmod, is_digit, print_range
from . import program
from .easy import LINE, count_line, echo_line
from .medium import print_sep, read_n_ints


def yes_no(P: Builder, cond) -> None:
    with P.if_(cond):
        P.print_str("yes")
    with P.else_():
        P.print_str("no")


@program("H01")
def h01(P, I):
    d, ok = P.var("d", 0), P.var("ok", 1)
    with P.while_(~I.at_eol()):
        P.set(d, d + sel(I.look.eq(ord("(")), 1, -1))
        with P.if_(d < 0):
            P.set(ok, 0)
            P.set(d, 0)
        I.advance()
    yes_no(P, ok & d.eq(0))


@program("H02", max_value=2 ** 46)
def h02(P, I):
    total, term, sign, num, op = P.var("total", 0), P.var("term"), P.var("sign", 1), P.var("num"), P.var("op")
    I.read_int(term)
    with P.while_(~I.at_eol()):
        P.set(op, I.look)
        I.advance()
        I.read_int(num)
        with P.if_(op.eq(ord("*"))):
            P.set(term, term * num)
        with P.else_():
            P.set(total, total + sign * term)
            P.set(sign, sel(op.eq(ord("+")), 1, -1))
            P.set(term, num)
    P.print_int(total + sign * term)


def sieve(P: Builder, comp, limit) -> None:
    i, j = P.temp(), P.temp()
    P.set(i, 2)
    with P.while_(i * i <= limit):
        with P.if_(comp[i].eq(0)):
            P.set(j, i * i)
            with P.while_(j <= limit):
                P.store(comp, j, 1)
                P.set(j, j + i)
        P.set(i, i + 1)


@program("H03")
def h03(P, I):
    comp, n, i, c = P.array("comp", 3002), P.var("n"), P.var("i", 2), P.var("c", 0)
    I.read_int(n)
    sieve(P, comp, n)
    with P.while_(i <= n):
        P.set(c, c + comp[i].eq(0))
        P.set(i, i + 1)
    P.print_int(c)


@program("H04")
def h04(P, I):
    LIM = 2800  # the 400th prime is 2741
    comp, k, i = P.array("comp", LIM + 1), P.var("k"), P.var("i", 1)
    I.read_int(k)
    sieve(P, comp, LIM)
    with P.while_(k > 0):
        P.set(i, i + 1)
        P.set(k, k - comp[i].eq(0))
    P.print_int(i)


@program("H05")
def h05(P, I):
    D = 72
    a, n, b, m = P.array("a", D), P.var("n"), P.array("b", D), P.var("m")
    r, k, carry, s, x, y = P.array("r", D + 1), P.var("k", 0), P.var("carry", 0), P.var("s"), P.var("x"), P.var("y")
    I.read_line(a, n)
    I.read_line(b, m)
    # digits are stored most significant first; add from the right
    with P.while_((k < n) | (k < m) | carry.ne(0)):
        P.set(x, sel(k < n, a[sel(k < n, n - 1 - k, 0)] - 48, 0))
        P.set(y, sel(k < m, b[sel(k < m, m - 1 - k, 0)] - 48, 0))
        P.set(s, x + y + carry)
        P.store(r, k, umod(s, 10))
        P.set(carry, udiv(s, 10))
        P.set(k, k + 1)
    with P.while_((k > 1) & r[k - 1].eq(0)):
        P.set(k, k - 1)
    with P.while_(k > 0):
        P.set(k, k - 1)
        P.print_char(48 + r[k])


@program("H06")
def h06(P, I):
    s, n, i, start, best_s, best_l = (P.array("s", LINE), P.var("n"), P.var("i", 0), P.var("start", 0),
                                      P.var("best_s", 0), P.var("best_l", 0))
    I.read_line(s, n)
    with P.while_(i <= n):
        with P.if_((i.eq(n)) | s[sel(i < n, i, 0)].eq(SPACE)):
            with P.if_(i - start > best_l):
                P.set(best_l, i - start)
                P.set(best_s, start)
            P.set(start, i + 1)
        P.set(i, i + 1)
    print_range(P, s, best_s, best_s + best_l)


@program("H07")
def h07(P, I):
    p, L, t, m, n, j, k = (P.array("p", LINE), P.var("L"), P.array("t", LINE), P.var("m"), P.var("n"),
                           P.var("j", 1), P.var("k"))
    I.read_int(n)
    I.skip_line()
    I.read_line(p, L)
    with P.while_(j < n):
        I.read_line(t, m)
        P.set(k, 0)
        with P.while_((k < L) & (k < m) & p[sel(k < L, k, 0)].eq(t[sel(k < m, k, 0)])):
            P.set(k, k + 1)
        P.set(L, k)
        P.set(j, j + 1)
    print_range(P, p, 0, L)


@program("H08")
def h08(P, I):
    cnt, d = P.array("cnt", 10), P.var("d", 0)
    with P.while_(~I.at_eol()):
        P.store(cnt, I.look - 48, cnt[I.look - 48] + 1)
        I.advance()
    with P.while_(d < 10):
        with P.if_(d > 0):
            P.print_char(SPACE)
        P.print_int(cnt[d])
        P.set(d, d + 1)


@program("H09")
def h09(P, I):
    k = P.var("k")
    I.read_int(k)
    I.skip_line()
    echo_line(P, I, transform=lambda c: fmod(c - 97 + k, 26) + 97)


@program("H10")
def h10(P, I):
    prev = P.var("prev", -1, byte=True)
    with P.while_(~I.at_eol()):
        with P.if_(I.look.ne(prev)):
            P.print_char(I.look)
        P.set(prev, I.look)
        I.advance()


@program("H11")
def h11(P, I):
    c, k = P.var("c"), P.var("k")
    with P.while_(~I.at_eol()):
        P.set(c, I.look)
        I.advance()
        P.set(k, I.look - 48)
        I.advance()
        with P.while_(k > 0):
            P.print_char(c)
            P.set(k, k - 1)


@program("H12")
def h12(P, I):
    s = P.var("s", 0)
    with P.while_(~I.at_eol()):
        P.set(s, s + I.look)
        I.advance()
    P.print_int(s)


@program("H13")
def h13(P, I):
    c, n, x, acc, i = P.array("c", 32), P.var("n"), P.var("x"), P.var("acc", 0), P.var("i", 0)
    v = P.var("v")
    I.read_int(n)
    with P.while_(i <= n):
        I.read_int(v)
        P.store(c, i, v)
        P.set(i, i + 1)
    I.read_int(x)
    P.set(i, 0)
    with P.while_(i <= n):
        P.set(acc, acc * x + c[i])
        P.set(i, i + 1)
    P.print_int(acc)


@program("H14")
def h14(P, I):
    n, d, first = P.var("n"), P.var("d", 1), P.var("first", 1)
    I.read_int(n)
    with P.while_(d <= n):
        with P.if_(umod(n, d).eq(0)):
            print_sep(P, first)
            P.print_int(d)
        P.set(d, d + 1)


@program("H15")
def h15(P, I):
    x = P.var("x", 0)
    with P.while_(~I.at_eol()):
        P.set(x, x + sel(I.look.eq(ord("R")), 1, -1))
        I.advance()
    P.print_int(x)


@program("H16")
def h16(P, I):
    prev, run, best = P.var("prev", -1, byte=True), P.var("run", 0), P.var("best", 0)
    with P.while_(~I.at_eol()):
        P.set(run, sel(I.look.eq(prev), run + 1, 1))
        P.set(best, sel(run > best, run, best))
        P.set(prev, I.look)
        I.advance()
    P.print_int(best)


@program("H17")
def h17(P, I):
    a, n, i, j, c, best, bestc = (P.array("a", 64), P.var("n"), P.var("i", 0), P.var("j"), P.var("c"),
                                  P.var("best"), P.var("bestc", 0))
    read_n_ints(P, I, a, n)
    with P.while_(i < n):
        P.set(c, 0)
        P.set(j, 0)
        with P.while_(j < n):
            P.set(c, c + a[j].eq(a[i]))
            P.set(j, j + 1)
        with P.if_((c > bestc) | (c.eq(bestc) & (a[i] < best))):
            P.set(bestc, c)
            P.set(best, a[i])
        P.set(i, i + 1)
    P.print_int(best)


@program("H18")
def h18(P, I):
    s = P.var("s", 0)
    with P.while_(~I.at_eol()):
        P.set(s, umod(s + I.look - 48, 3))
        I.advance()
    yes_no(P, s.eq(0))


@program("H19")
def h19(P, I):
    x = P.var("x", 0)
    with P.while_(~I.at_eol()):
        P.set(x, sel(I.look.eq(ord("+")), x + 1, sel(I.look.eq(ord("-")), x - 1, 0)))
        I.advance()
    P.print_int(x)


@program("H20")
def h20(P, I):
    STRIDE, MAXN = 64, 16
    txt, ln, order = P.array("txt", STRIDE * MAXN), P.array("ln", MAXN), P.array("order", MAXN)
    n, i, j, k, m, less, t = P.var("n"), P.var("i", 0), P.var("j"), P.var("k"), P.var("m"), P.var("less"), P.var("t")
    I.read_int(n)
    I.skip_line()
    with P.while_(i < n):
        P.set(m, 0)
        with P.while_(~I.at_eol()):
            P.store(txt, i * STRIDE + m, I.look)
            P.set(m, m + 1)
            I.advance()
        with P.if_(I.look.eq(NL)):
            I.advance()
        P.store(ln, i, m)
        P.store(order, i, i)
        P.set(i, i + 1)
    # bubble sort indices by lexicographic order
    P.set(i, 0)
    with P.while_(i < n):
        P.set(j, 0)
        with P.while_(j < n - 1 - i):
            a, b = order[j], order[j + 1]
            # less = (string b < string a)
            P.set(k, 0)
            with P.while_((k < ln[b]) & (k < ln[a]) & txt[b * STRIDE + k].eq(txt[a * STRIDE + k])):
                P.set(k, k + 1)
            P.set(less, sel(k < ln[b], sel(k < ln[a], txt[b * STRIDE + k] < txt[a * STRIDE + k], 0),
                            ln[b] < ln[a]))
            with P.if_(less):
                P.set(t, order[j])
                P.store(order, j, order[j + 1])
                P.store(order, j + 1, t)
            P.set(j, j + 1)
        P.set(i, i + 1)
    P.set(i, 0)
    with P.while_(i < n):
        with P.if_(i > 0):
            P.print_char(SPACE)
        print_range(P, txt, order[i] * STRIDE, order[i] * STRIDE + ln[order[i]])
        P.set(i, i + 1)


__all__ = ["yes_no", "sieve", "count_line", "is_digit"]
